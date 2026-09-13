#!/usr/bin/env python3
"""Worktree containment and reviewer command confinement hook (solorepo's DR-110).

PreToolUse hook for the reviewer role container in `.github/workflows/review.yml`.
Enforces two isolation boundaries before tool execution:

1. Filesystem Containment: Tool calls for `Read`, `Grep`, and `Glob` must resolve
   inside the active repository worktree and outside `.git/` (which holds workflow
   tokens), or within the harness project directory (`~/.claude/projects/`).
2. Command Confinement: Shell commands executed via `Bash` must adhere to an allowed
   grammar of single inspection commands (`git`, `gh`, and `.meta/say/` verbs with
   quoted heredocs) and explicit per-subcommand option allowlists.

When a command is refused, the hook computes and returns the nearest conforming
single command where derivable (solorepo's DR-175).

Input/Output Contract:
    Reads a PreToolUse event JSON object from stdin:
        {"tool_name": "Bash", "tool_input": {"command": "..."}}
    Exits with code 0 to permit execution.
    Exits with code 2 and writes an explanatory refusal message to stderr to block execution.

History in worktree_only.history.md (solorepo's DR-171).
"""
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or pathlib.Path.cwd()).resolve()

READERS = {"Read": "file_path", "Grep": "path", "Glob": "path"}

# Characters the shell acts on. None of them may appear unquoted; inside quotes
# bash acts on almost nothing, and `EXPANDS` is the almost.
SHELL = set(';&|<>$`*?[]{}()~!#\\"\n')

# Characters that still expand inside double quotes per bash reference.
# Double quotes preserve literal character values except for $, `, \, and !.
QUOTES = {"'", '"'}
EXPANDS = set("$`\\!")

# Characters representing command or variable substitutions ($ and `).
# Substitutions produce dynamic output and cannot be derived into literal single quotes.
SUBSTITUTES = set("$`")

# Characters escaped by backslash inside double quotes per bash reference.
ESCAPES = set('$`"\\\n')

# Shell operators that separate commands or perform redirection.
# Truncation at chain operators preserves the leading command for nearest-form derivation.
CHAINS = set(";&|<>\n")

# Matches trailing file descriptor digits preceding redirection operators.
DESCRIPTOR = re.compile(r"(?:^|\s)\d+$")

# Allowed git subcommands and their permitted option flags.
# Options must match exact spelling without unlisted abbreviations.
GIT = {
    "log": {"--oneline", "--stat", "--numstat", "--shortstat", "--name-only",
            "--name-status", "--all",
            "--decorate", "--graph", "--follow", "--first-parent", "--reverse",
            "-p", "--patch", "-c", "--no-merges", "--merges"},
    "show": {"--stat", "--numstat", "--shortstat", "--name-only",
             "--name-status", "--oneline", "-p",
             "--patch", "--no-patch", "-s"},
    "diff": {"--stat", "--numstat", "--shortstat", "--name-only",
             "--name-status", "--cached", "--staged",
             "-p", "--patch", "-w", "--word-diff", "-M", "--no-color"},
    "status": {"--porcelain", "-s", "--short", "-b", "--branch", "-uno"},
    "grep": {"-n", "--line-number", "-i", "--ignore-case", "-l", "--files-with-matches",
             "-c", "--count", "-w", "--word-regexp", "-E", "--extended-regexp",
             "-F", "--fixed-strings", "-P", "--perl-regexp", "-h", "-H",
             "--name-only", "-v", "--invert-match", "--heading", "--break", "--no-color"},
    "ls-files": {"--cached", "--modified", "--deleted", "--others",
                 "--exclude-standard", "--full-name"},
    # Commit tree listing: reads git tree objects without mutating state or invoking external drivers.
    "ls-tree": {"-r", "-d", "-t", "-l", "--long", "--name-only", "--full-name",
                "--full-tree"},
}
# Per subcommand, because `-n` is a count for `log` and a flag for `grep`.
TAKES_VALUE = {
    "log": {"-n", "--max-count", "-S", "-G", "--since", "--until", "--author",
            "--grep", "--format", "--pretty", "--date"},
    "show": {"--format", "--pretty", "--date"},
    "diff": {"-U", "--unified"},
    "status": set(),
    "grep": {"-e", "--regexp", "-A", "-B", "-C"},
    "ls-files": set(),
    "ls-tree": set(),
}
# Matches numeric count flags and compact context flags (e.g. -n 5, -3, -A2, -B2, -C2, -U2).
NUMBER = re.compile(r"^-(\d+|[ABCU]\d+)$")

# Allowed non-git programs, their permitted options, and value-consuming options.
# Subcommands supporting `--help` print usage text directly without delegating to external pagers.
PROGRAMS = {
    ("gh", "pr", "view"): ({"--json", "-q", "--jq", "--comments", "--help"}, {"--json", "-q", "--jq"}),
    ("gh", "pr", "diff"): ({"--name-only", "--patch", "--help"}, set()),
    ("gh", "pr", "checks"): ({"--json", "-q", "--jq", "--required", "--help"}, {"--json", "-q", "--jq"}),
    ("python3", ".meta/check_pr.py"): ({"--threads", "--resume", "--help"}, set()),
}

# Mapping of common unauthorized programs to their sanctioned repository alternatives.
INSTEAD = {
    ("python3", ".meta/check.py"): "the gate runs on the pull request, and `gh pr checks` reads what it found",
    ("grep",): "the Grep tool searches the worktree, and `git grep` searches a commit",
    ("wc",): "the Read tool reads a file and counts what it read",
}


# Harness project directory permitted for reviewer scratch artifacts and tool outputs.
HARNESS = (pathlib.Path.home() / ".claude" / "projects").resolve()


def outside(path):
    """Validate whether a target filesystem path remains within permitted boundaries.

    Parameters:
        path (str | pathlib.Path): Relative or absolute target path to evaluate.

    Returns:
        str | None: Error message detailing the boundary violation if the resolved
        path escapes the repository root or enters `.git/` (and is not within the
        harness project directory); None if access is permitted.
    """
    target = pathlib.Path(path).expanduser()
    if not target.is_absolute():
        target = ROOT / target
    target = target.resolve()
    if HARNESS in target.parents:
        return None
    if target != ROOT and ROOT not in target.parents:
        return f"{path} is outside the worktree {ROOT}"
    if target == (ROOT / ".git") or (ROOT / ".git") in target.parents:
        return f"{path} is inside .git/, where the action keeps a token"
    return None


def words_of(text, literal=False):
    """Tokenize a single shell command on whitespace respecting quoting rules.

    Parameters:
        text (str): Command string to tokenize.
        literal (bool): When True, preserves escape sequences and literal characters
            within double quotes for derivation rather than refusing expansion triggers.

    Returns:
        list[str] | str: List of tokenized string arguments if parsing succeeds;
        otherwise an explanatory string indicating which active shell expansion
        character or unclosed quote triggered refusal.
    """
    words, word, quote, seen, escaped = [], [], "", False, False
    for ch in text:
        if escaped:
            # A `\` inside a double quote escapes one of `ESCAPES` and is
            # dropped, taking a newline with it; before anything else it stands
            # for itself, which is what `\s` and `\b` want of it.
            escaped = False
            if ch not in ESCAPES:
                word.append("\\")
            if ch != "\n":
                word.append(ch)
        elif quote:
            if ch == quote:
                quote = ""
            elif quote == '"' and ch in EXPANDS:
                if not literal or ch in SUBSTITUTES:
                    return f"`{ch}`"
                if ch == "\\":
                    escaped = True
                else:
                    word.append(ch)
            else:
                word.append(ch)
        elif ch in QUOTES:
            quote, seen = ch, True
        elif ch in SHELL:
            return f"`{ch!r}`" if ch == "\n" else f"`{ch}`"
        elif ch.isspace():
            if word or seen:
                words.append("".join(word))
            word, seen = [], False
        else:
            word.append(ch)
    if quote:
        return "an unclosed quote"
    if word or seen:
        words.append("".join(word))
    return words


def refused_option(words, allowed, takes_value):
    """Locate the list index of the first disallowed option token.

    Parameters:
        words (list[str]): Command arguments following the program/subcommand prefix.
        allowed (set[str]): Permitted option flags for the command.
        takes_value (set[str]): Option flags that consume an associated argument value.

    Returns:
        int | None: Index in `words` of the first unrecognized option flag, or
        None if all options are valid according to `allowed` and `takes_value`.
    """
    rest = iter(range(len(words)))
    for i in rest:
        word = words[i]
        if word == "--":
            return None
        if not word.startswith("-") or NUMBER.match(word):
            continue
        name, eq, _ = word.partition("=")
        if eq and name in takes_value:
            continue
        if word in takes_value:
            next(rest, None)
            continue
        if word not in allowed:
            return i
    return None


def options_allowed(what, words, allowed, takes_value):
    """Validate that all options in the argument list conform to the allowed set.

    Parameters:
        what (str): Human-readable name of the command or subcommand being validated.
        words (list[str]): Command arguments following the program/subcommand prefix.
        allowed (set[str]): Permitted option flags for the command.
        takes_value (set[str]): Option flags that consume an associated argument value.

    Returns:
        str | None: Refusal message if an unauthorized option is present; None if all options are allowed.
    """
    i = refused_option(words, allowed, takes_value)
    return None if i is None else f"`{words[i]}` is not an option `{what}` may carry here"


def form_of(words):
    """Identify the matching program or subcommand specification for tokenized words.

    Parameters:
        words (list[str]): Tokenized command words.

    Returns:
        tuple[int, str, set[str], set[str]] | None: A tuple of `(offset, name, allowed, takes_value)`
        defining the option offset index, human-readable command label, allowed option set,
        and value-taking option set; None if the command matches no authorized form.
    """
    if words[0] == "git":
        if len(words) > 1 and words[1] in GIT:
            return 2, f"git {words[1]}", GIT[words[1]], TAKES_VALUE[words[1]]
        return None
    for form, (allowed, takes_value) in PROGRAMS.items():
        if tuple(words[:len(form)]) == form:
            return len(form), " ".join(form), allowed, takes_value
    return None


def unquoted(text):
    """Iterate through unquoted characters and their positions in a shell command.

    Yields indices and characters that appear outside single or double quote boundaries.

    Parameters:
        text (str): Shell command text to scan.

    Yields:
        tuple[int, str]: Zero-indexed position and character for unquoted tokens.
    """
    quote = ""
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in QUOTES:
            quote = ch
        else:
            yield i, ch


def partition_unquoted(text, marker):
    """Partition a command string on the first unquoted occurrence of a marker.

    Parameters:
        text (str): Shell command text to partition.
        marker (str): Substring marker to locate outside quoted spans.

    Returns:
        tuple[str, str, str]: Three-tuple of `(head, marker, tail)`. If marker is
        not found unquoted, returns `(text, "", "")`.
    """
    for i, _ in unquoted(text):
        if text.startswith(marker, i):
            return text[:i], marker, text[i + len(marker):]
    return text, "", ""


def command_allowed(command):
    """Evaluate whether a shell command string satisfies the confinement policy.

    Allowed commands comprise single, unchained commands from the authorized program
    list (`git` subcommands, `gh` subcommands, `python3 .meta/check_pr.py`), `.meta/say/`
    programs, or `.meta/say/` heredocs with quoted delimiters.

    Parameters:
        command (str): Raw command string from tool input.

    Returns:
        str | None: An explanatory refusal message describing why the command is
        disallowed; None if the command is authorized.
    """
    head, marker, body = partition_unquoted(command, "<<")
    if marker:
        if not head.startswith(".meta/say/"):
            return "a heredoc is the channel's shape and nobody else's"
        opener, newline, rest = body.partition("\n")
        if not newline or not re.fullmatch(r"'[A-Za-z_]+'\s*", opener):
            return "a heredoc carries a quoted delimiter and nothing else on its line"
        delimiter = opener.strip()[1:-1]
        lines = [line.rstrip("\r") for line in rest.split("\n")]
        if delimiter not in lines:
            return "a heredoc ends with its delimiter on a line of its own"
        if any(line.strip() for line in lines[lines.index(delimiter) + 1:]):
            return "nothing follows a heredoc's closing delimiter"
    words = words_of(head)
    if isinstance(words, str):
        return f"{words}, which the shell would act on"
    if not words:
        return "an empty command"
    program = words[0]
    if re.fullmatch(r"\.meta/say/[a-z]+", program):
        # The channel's programs, by the directory that sanctions them (solorepo's DR-117).
        return None
    form = form_of(words)
    if form:
        offset, what, allowed, takes_value = form
        return options_allowed(what, words[offset:], allowed, takes_value)
    if program == "git":
        subcommand = words[1] if len(words) > 1 else ""
        if subcommand.startswith("-"):
            # Git top-level options (e.g. -C, --git-dir, -c) are disallowed to preserve worktree isolation.
            return (f"`git {subcommand}` is one of git's own options, and none of them is "
                    "carried. The three asked for are why: `-C` and `--git-dir` point git at "
                    "another repository, which the worktree already is, and `-c` sets a "
                    "configuration that runs a program — so carrying any would put the "
                    "boundary in git's own option list rather than this one. The subcommand "
                    "comes first")
        return f"`git {subcommand}` is not a subcommand the reviewer runs"
    instead = INSTEAD.get(tuple(words[:2])) or INSTEAD.get(tuple(words[:1]))
    return (f"`{' '.join(words[:3])}` is not a program the reviewer runs"
            + (f", and is not coming: {instead}" if instead else ""))


def before_operator(text):
    """Extract command text preceding the first unquoted chain or redirection operator.

    Trailing file descriptor digits directly attached to redirection operators (e.g. `2>`)
    are stripped to avoid corrupting the trailing argument of the preceding command.

    Parameters:
        text (str): Raw shell command string.

    Returns:
        str: Truncated command text prior to operators, or original text if no operator is present.
    """
    for i, ch in unquoted(text):
        if ch in CHAINS:
            head = text[:i]
            if ch in "<>":
                descriptor = DESCRIPTOR.search(head)
                if descriptor:
                    head = head[:descriptor.start()]
            return head
    return text


def requote(word):
    """Enclose a command token in single quotes unless already safe without quotes.

    Parameters:
        word (str): Command token to format.

    Returns:
        str: Quoted or unquoted representation of the token for bash interpretation.
    """
    return word if word and not (set(word) & SHELL) and not any(c.isspace() for c in word) else f"'{word}'"


def plain_form(command):
    """Derive the nearest conforming command candidate from a refused command string.

    Derives a valid command by extracting the command preceding chain operators,
    stripping disallowed options and their consumed arguments, and requoting tokens
    into single-quoted form.

    Parameters:
        command (str): Refused command string.

    Returns:
        str | None: Candidate conforming command string if validation succeeds under
        `command_allowed`; None if no conforming candidate can be derived.
    """
    if partition_unquoted(command, "<<")[1]:
        return None
    words = words_of(before_operator(command), literal=True)
    if isinstance(words, str) or not words:
        return None
    if any("'" in word for word in words):
        # Requoting uses single quotes; words containing single quotes cannot be cleanly requoted.
        return None
    if re.fullmatch(r"\.meta/say/[a-z]+", words[0]):
        return None
    form = form_of(words)
    if form:
        offset, _, allowed, takes_value = form
        while (i := refused_option(words[offset:], allowed, takes_value)) is not None:
            i += offset
            # Long options without '=' may consume the subsequent word as a value argument.
            owns = words[i].startswith("--") and "=" not in words[i] and i + 1 < len(words) and not words[i + 1].startswith("-")
            words = words[:i] + words[i + (2 if owns else 1):]
    candidate = " ".join(requote(word) for word in words)
    return candidate if command_allowed(candidate) is None else None


def blocked(tool, tool_input):
    """Determine whether a tool invocation violates filesystem or confinement boundaries.

    Parameters:
        tool (str): Tool identifier (e.g. 'Read', 'Grep', 'Glob', 'Bash').
        tool_input (dict): Input arguments passed to the tool call.

    Returns:
        str | None: Refusal message detailing the policy violation if blocked; None if permitted.
    """
    try:
        if tool in READERS:
            # Readers defaulting to empty path inspect the working directory root.
            problem = outside(tool_input.get(READERS[tool]) or ".")
            if problem:
                return f"Blocked: {problem}. The reviewer reads the worktree and nothing else."
            return None
        if tool == "Bash":
            command = tool_input.get("command", "")
            problem = command_allowed(command)
            if problem:
                plain = plain_form(command)
                return (f"Blocked: {problem}. The reviewer runs one plain command at a time: "
                        "`git log|show|diff|status|grep|ls-files|ls-tree` with plain options, "
                        "`gh pr view|diff|checks`, "
                        "`python3 .meta/check_pr.py`, or a program of `.meta/say/` with a quoted heredoc. "
                        "No pipes, redirects, chaining, or anything the shell would expand — "
                        "quoting is what stops it, and the four a double quote does not stop "
                        "here are `$`, a backtick, `\\` and `!`: a pattern holding one of them "
                        "goes in single quotes, which is most regexes — `'\\bdef\\b'`."
                        + (f" This one would be taken as: {plain}" if plain else ""))
        return None
    except Exception as exc:  # refusing is the safe answer to anything
        return f"Blocked: the hook could not read this call ({type(exc).__name__}: {exc}); refusing rather than guessing."


def main():
    """Execute the PreToolUse hook entry point reading event JSON from stdin.

    Returns:
        int: Process exit code 0 to permit execution, or 2 to block.
    """
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    try:
        problem = blocked(event.get("tool_name"), event.get("tool_input") or {})
    except BaseException as exc:
        problem = f"Blocked: the hook failed ({type(exc).__name__}); refusing rather than guessing."
    if problem:
        print(problem, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
