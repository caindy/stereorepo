#!/usr/bin/env python3
"""Worktree containment and reviewer command confinement hook (solorepo's DR-110).

Before-tool hook for the reviewer role container in `.github/workflows/review.yml`,
registered on Claude Code's `PreToolUse` event and on Gemini CLI's `BeforeTool`.
Enforces two isolation boundaries before tool execution:

1. Filesystem Containment: Tool calls for `Read`, `Grep`, and `Glob` — and the
   harness tool names `TOOLS` maps onto them — must resolve inside the active
   repository worktree and outside `.git/` (which holds workflow tokens), or
   within a harness scratch directory (`HARNESS`). A key of `READERS` holding a
   glob pattern is bounded by the literal path its matches lie under rather than
   resolved as one, and refused where it can leave that bound whatever the bound
   is — a component matching `..`, or brace alternation, neither of which the
   literal prefix speaks for. A reader naming no key of `READERS` at all is
   refused, a search being the exception that may mean the worktree by naming
   nothing.
2. Command Confinement: Shell commands executed via `Bash` (Gemini CLI's
   `run_shell_command`) must adhere to an allowed grammar of single inspection
   commands (`git`, `gh`, and `.meta/say/` verbs with quoted heredocs) and
   explicit per-subcommand option allowlists. A working directory the call names
   in `dir_path`, which Gemini CLI's shell tool accepts and Claude Code's has no
   argument for, must resolve inside the worktree: run elsewhere, an allowed
   command reads what `git -C` is refused for pointing at. That is its own
   predicate (`elsewhere`), a directory commands run in carrying neither
   exemption a path read from carries.

When a command is refused, the hook computes and returns the nearest conforming
single command where derivable (solorepo's DR-175).

Input/Output Contract:
    Reads a before-tool event JSON object from stdin. Both harnesses carry the
    same two fields, so one reader serves each:
        {"tool_name": "Bash", "tool_input": {"command": "..."}}
    Exits with code 0 to permit execution.
    Exits with code 2 and writes an explanatory refusal message to stderr to block
    execution; Claude Code and Gemini CLI both read code 2 as a block and stderr
    as the reason given to the agent.

History in worktree_only.history.md (solorepo's DR-171).
"""
import json
import os
import pathlib
import re
import sys
from collections.abc import Iterator
from typing import Any

ROOT = pathlib.Path(
    os.environ.get("CLAUDE_PROJECT_DIR")
    or os.environ.get("GEMINI_PROJECT_DIR")
    or pathlib.Path.cwd()
).resolve()

# Harness tool names mapped onto the canonical four. Gemini CLI's `BeforeTool`
# payload carries the same `tool_name` and `tool_input` fields as Claude Code's
# `PreToolUse`, so the names are all that differ: `grep_search` was
# `search_file_content` and Gemini CLI still answers to both, `read_many_files`
# is the `@` syntax's bulk read, and `list_directory` reads a directory as
# `Glob` does.
TOOLS = {
    "run_shell_command": "Bash",
    "read_file": "Read",
    "read_many_files": "Read",
    "grep_search": "Grep",
    "search_file_content": "Grep",
    "glob": "Glob",
    "list_directory": "Glob",
}

# Each canonical reader with the input keys a harness names its paths in, and
# whether a key holds a path or a glob pattern. Paired with the tool that sends
# each: Claude Code's `Read` names `file_path`, its `Grep` names `path` and
# filters with `glob`, its `Glob` names `path` and `pattern`; Gemini CLI's
# `read_file` names `file_path`, its `read_many_files` names `include`, its
# `grep_search` names `path` and filters with `include`, its `glob` names `path`
# and `pattern`, and its `list_directory` names `dir_path`.
PATH, PATTERN = "path", "pattern"
READERS = {
    "Read": {"file_path": PATH, "include": PATTERN},
    "Grep": {"path": PATH, "include": PATTERN, "glob": PATTERN},
    "Glob": {"path": PATH, "dir_path": PATH, "pattern": PATTERN},
}

# The one reader that may name no path: a search with no `path` searches the
# worktree, which the bound permits anyway. Every other reader names what it
# reads, so an input naming none of its keys is an argument spelling this hook
# does not know — `google-github-actions/run-gemini-cli@v0` floats, so a key can
# be renamed or added upstream between runs — and is refused rather than taken
# for the worktree, a permit being the one failure a floating upstream must not
# have.
SEARCHES = ("Grep",)

# Characters a glob matcher acts on. A component holding one of them matches
# more than itself, so the literal path a pattern is bounded by ends before it.
# Brace alternation is the one this hook refuses rather than bounds: an
# alternative carries its own root, so one of them may be absolute or ascending
# whatever the components around it say, and which alternations a matcher
# honours is its grammar rather than this hook's.
ALTERNATION = set("{}")
GLOBBY = set("*?[]") | ALTERNATION

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


# Harness scratch directories permitted for reviewer scratch artifacts and tool
# outputs: Claude Code's project directory, and Gemini CLI's per-project
# temporary directory. Neither harness's configuration directory is named, the
# credentials beside it being what the boundary exists to keep out.
HARNESS = (
    (pathlib.Path.home() / ".claude" / "projects").resolve(),
    (pathlib.Path.home() / ".gemini" / "tmp").resolve(),
)


def outside(path: str | pathlib.Path) -> str | None:
    """Validate whether a target filesystem path remains within permitted boundaries.

    Parameters:
        path: Relative or absolute target path to evaluate.

    Returns:
        str | None: Error message detailing the boundary violation if the resolved
        path escapes the repository root or enters `.git/` (and is not within a
        harness scratch directory); None if access is permitted.
    """
    target = pathlib.Path(path).expanduser()
    if not target.is_absolute():
        target = ROOT / target
    target = target.resolve()
    if any(scratch in target.parents for scratch in HARNESS):
        return None
    if target != ROOT and ROOT not in target.parents:
        return f"{path} is outside the worktree {ROOT}"
    if target == (ROOT / ".git") or (ROOT / ".git") in target.parents:
        return f"{path} is inside .git/, where the action keeps a token"
    return None


def ascends(part: str) -> bool:
    """Judge whether one pattern component can match `..`.

    A metacharacter matches at least the empty string, so a component is an
    ascent wherever the characters it does spell are all dots: `..` itself, and
    the wildcard spellings of it — `..*`, `.?`, `[.][.]` — which a matcher's own
    grammar decides and this hook therefore does not wait to hear about. A
    component holding a literal that is not a dot is not one of them, so `*.py`
    and `.git` pass here (`.git` having its own clause).

    Parameters:
        part: One component of a glob pattern.

    Returns:
        bool: True where every character the component spells literally is a
        dot, so `..` is among what it matches.
    """
    literal = set(part) - GLOBBY
    return literal == {"."}


def outside_pattern(pattern: str) -> str | None:
    """Validate whether every path a glob pattern can match remains within permitted boundaries.

    A pattern is not the path it reads: `pathlib` takes each matcher
    metacharacter for an inert path component, so `**/.git/config` resolves to a
    path the worktree holds and `.git/` is no parent of, while a matcher for
    which `**` spans no directory reads `.git/config`. A pattern is therefore
    bounded by the components before its first metacharacter — the deepest
    directory every match lies under — and that bound holds only over what
    descends from it. Three things do not, and each is refused wherever it
    appears rather than bounded: a component naming `.git`, a component that can
    match `..` (`ascends`), and brace alternation, whose alternative carries a
    root of its own. The prefix rule alone cannot see any of them, its first
    metacharacter being where it stops looking: the literal prefix of
    `**/../../etc/passwd` is the worktree, as the prefix of `{/etc,.}/passwd`
    is, and neither pattern stays there.

    Parameters:
        pattern: Glob pattern a reader names the files it reads with.

    Returns:
        str | None: Error message detailing the boundary violation if a path the
        pattern can match escapes the repository root or enters `.git/`, or if
        the pattern is one this hook cannot bound; None if every such path is
        permitted.
    """
    if set(pattern) & ALTERNATION:
        return (f"{pattern} alternates, and an alternative carries its own root, "
                "which this hook does not bound")
    parts = pathlib.PurePath(pattern).parts
    if ".git" in parts:
        return f"{pattern} matches inside .git/, where the action keeps a token"
    if any(ascends(part) for part in parts):
        return f"{pattern} can match `..`, which leaves whatever bounds it"
    literal = []
    for part in parts:
        if set(part) & GLOBBY:
            break
        literal.append(part)
    prefix = str(pathlib.PurePath(*literal)) if literal else "."
    problem = outside(prefix)
    if problem is None or prefix == pattern:
        return problem
    return f"{pattern} matches under {prefix}, and {problem}"


def elsewhere(where: str | pathlib.Path) -> str | None:
    """Validate whether a working directory a shell call names is the worktree or under it.

    A working directory is not a read, so neither exemption `outside` carries
    belongs to it: a harness scratch directory is where the reviewer's artifacts
    go and not where its commands run, and `.git/` is refused nothing by the
    allowed grammar, which reads the same repository from either.

    Parameters:
        where: Directory the command is to run in, absolute or relative to the
            repository root.

    Returns:
        str | None: Error message naming the directory if it resolves outside the
        repository root; None if the command may run there.
    """
    target = pathlib.Path(where).expanduser()
    if not target.is_absolute():
        target = ROOT / target
    target = target.resolve()
    if target != ROOT and ROOT not in target.parents:
        return f"{where} is outside the worktree {ROOT}"
    return None


def targets(tool_input: dict[str, Any], keys: dict[str, str]) -> list[tuple[str, str]]:
    """Collect every path and pattern a reader's input names under the given keys.

    Parameters:
        tool_input: Input arguments passed to the tool call.
        keys: Input keys the reader may name a path in, each mapped to `PATH` or
            `PATTERN`.

    Returns:
        list[tuple[str, str]]: Each value named with the kind its key holds, in
        key order, a list-valued key contributing every entry; empty when the
        input names none of the keys.
    """
    found: list[tuple[str, str]] = []
    for key, kind in keys.items():
        value = tool_input.get(key)
        if isinstance(value, list):
            found.extend((entry, kind) for entry in value if entry)
        elif value:
            found.append((value, kind))
    return found


def words_of(text: str, literal: bool = False) -> list[str] | str:
    """Tokenize a single shell command on whitespace respecting quoting rules.

    Parameters:
        text: Command string to tokenize.
        literal: When True, preserves escape sequences and literal characters
            within double quotes for derivation rather than refusing expansion triggers.

    Returns:
        list[str] | str: List of tokenized string arguments if parsing succeeds;
        otherwise an explanatory string indicating which active shell expansion
        character or unclosed quote triggered refusal.

    A backslash inside a double quote escapes one of `ESCAPES` and is dropped,
    taking a newline with it; before anything else it stands for itself, which
    is what `\\s` and `\\b` want of it.
    """
    words, word, quote, seen, escaped = [], [], "", False, False
    for ch in text:
        if escaped:
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


def refused_option(words: list[str], allowed: set[str], takes_value: set[str]) -> int | None:
    """Locate the list index of the first disallowed option token.

    Parameters:
        words: Command arguments following the program/subcommand prefix.
        allowed: Permitted option flags for the command.
        takes_value: Option flags that consume an associated argument value.

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


def options_allowed(what: str, words: list[str], allowed: set[str],
                    takes_value: set[str]) -> str | None:
    """Validate that all options in the argument list conform to the allowed set.

    Parameters:
        what: Human-readable name of the command or subcommand being validated.
        words: Command arguments following the program/subcommand prefix.
        allowed: Permitted option flags for the command.
        takes_value: Option flags that consume an associated argument value.

    Returns:
        str | None: Refusal message if an unauthorized option is present; None if all options are allowed.
    """
    i = refused_option(words, allowed, takes_value)
    return None if i is None else f"`{words[i]}` is not an option `{what}` may carry here"


def form_of(words: list[str]) -> tuple[int, str, set[str], set[str]] | None:
    """Identify the matching program or subcommand specification for tokenized words.

    Parameters:
        words: Tokenized command words.

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


def unquoted(text: str) -> Iterator[tuple[int, str]]:
    """Iterate through unquoted characters and their positions in a shell command.

    Yields indices and characters that appear outside single or double quote boundaries.

    Parameters:
        text: Shell command text to scan.

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


def partition_unquoted(text: str, marker: str) -> tuple[str, str, str]:
    """Partition a command string on the first unquoted occurrence of a marker.

    Parameters:
        text: Shell command text to partition.
        marker: Substring marker to locate outside quoted spans.

    Returns:
        tuple[str, str, str]: Three-tuple of `(head, marker, tail)`. If marker is
        not found unquoted, returns `(text, "", "")`.
    """
    for i, _ in unquoted(text):
        if text.startswith(marker, i):
            return text[:i], marker, text[i + len(marker):]
    return text, "", ""


def command_allowed(command: str) -> str | None:
    """Evaluate whether a shell command string satisfies the confinement policy.

    Allowed commands comprise single, unchained commands from the authorized program
    list (`git` subcommands, `gh` subcommands, `python3 .meta/check_pr.py`), `.meta/say/`
    programs, or `.meta/say/` heredocs with quoted delimiters.

    Parameters:
        command: Raw command string from tool input.

    Returns:
        str | None: An explanatory refusal message describing why the command is
        disallowed; None if the command is authorized.

    A channel program is recognised by the directory that sanctions it
    (solorepo's DR-117) and carries no option list of its own. Git's top-level
    options carry none either, and the refusal says why: the subcommand comes
    first.
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
        return None
    form = form_of(words)
    if form:
        offset, what, allowed, takes_value = form
        return options_allowed(what, words[offset:], allowed, takes_value)
    if program == "git":
        subcommand = words[1] if len(words) > 1 else ""
        if subcommand.startswith("-"):
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


def before_operator(text: str) -> str:
    """Extract command text preceding the first unquoted chain or redirection operator.

    Trailing file descriptor digits directly attached to redirection operators (e.g. `2>`)
    are stripped to avoid corrupting the trailing argument of the preceding command.

    Parameters:
        text: Raw shell command string.

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


def requote(word: str) -> str:
    """Enclose a command token in single quotes unless already safe without quotes.

    Parameters:
        word: Command token to format.

    Returns:
        str: Quoted or unquoted representation of the token for bash interpretation.
    """
    return word if word and not (set(word) & SHELL) and not any(c.isspace() for c in word) else f"'{word}'"


def plain_form(command: str) -> str | None:
    """Derive the nearest conforming command candidate from a refused command string.

    Derives a valid command by extracting the command preceding chain operators,
    stripping disallowed options and their consumed arguments, and requoting tokens
    into single-quoted form.

    Parameters:
        command: Refused command string.

    Returns:
        str | None: Candidate conforming command string if validation succeeds under
        `command_allowed`; None if no conforming candidate can be derived.

    A word holding a single quote has no candidate: `requote` spells a word in
    single quotes and has nothing else to spell that one with. A long option
    written without `=` takes the word after it as its value, unless that word
    is itself an option, so stripping the option strips both.
    """
    if partition_unquoted(command, "<<")[1]:
        return None
    words = words_of(before_operator(command), literal=True)
    if isinstance(words, str) or not words:
        return None
    if any("'" in word for word in words):
        return None
    if re.fullmatch(r"\.meta/say/[a-z]+", words[0]):
        return None
    form = form_of(words)
    if form:
        offset, _, allowed, takes_value = form
        while (i := refused_option(words[offset:], allowed, takes_value)) is not None:
            i += offset
            owns = words[i].startswith("--") and "=" not in words[i] and i + 1 < len(words) and not words[i + 1].startswith("-")
            words = words[:i] + words[i + (2 if owns else 1):]
    candidate = " ".join(requote(word) for word in words)
    return candidate if command_allowed(candidate) is None else None


def blocked(tool: str, tool_input: dict[str, Any]) -> str | None:
    """Determine whether a tool invocation violates filesystem or confinement boundaries.

    Parameters:
        tool: Tool identifier, canonical ('Read', 'Grep', 'Glob', 'Bash') or a
            harness name `TOOLS` maps onto one.
        tool_input: Input arguments passed to the tool call.

    Returns:
        str | None: Refusal message detailing the policy violation if blocked; None if permitted.
    """
    try:
        tool = TOOLS.get(tool, tool)
        if tool in READERS:
            named = targets(tool_input, READERS[tool])
            if not named and tool not in SEARCHES:
                keys = ", ".join(f"`{key}`" for key in READERS[tool])
                return (f"Blocked: this call names no path under {keys}. The reviewer reads the "
                        "worktree and nothing else, and an argument this hook cannot bound is "
                        "refused rather than taken for the worktree.")
            for value, kind in named:
                problem = outside(value) if kind == PATH else outside_pattern(value)
                if problem:
                    return f"Blocked: {problem}. The reviewer reads the worktree and nothing else."
            return None
        if tool == "Bash":
            where = tool_input.get("dir_path")
            problem = elsewhere(where) if where else None
            if problem:
                return f"Blocked: {problem}. The reviewer runs its commands in the worktree and nowhere else."
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
    except Exception as exc:
        return f"Blocked: the hook could not read this call ({type(exc).__name__}: {exc}); refusing rather than guessing."


def main() -> int:
    """Execute the before-tool hook entry point reading event JSON from stdin.

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
