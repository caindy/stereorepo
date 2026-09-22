"""Command confinement: the single inspection commands a reviewer may run, and their options (solorepo's DR-110).

Shell commands executed via `Bash`, and Gemini CLI's `run_shell_command`, must
adhere to an allowed grammar of single inspection commands: `git`, `gh` and the
`.meta/say/` verbs with quoted heredocs, each subcommand with an explicit option
allowlist, because an option that runs a program or writes a file is a way out
of the worktree no path check sees. When a command is refused, `plain_form`
derives the nearest conforming single command where one exists, so the
refusal offers what to run instead of only what not to (solorepo's DR-175).
"""
import re

from lib.worktree_only import shell

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
    ("just", "pr"): ({"--threads", "--resume", "--help"}, set()),
}


# Mapping of common unauthorized programs to their sanctioned repository alternatives.
INSTEAD = {
    ("python3", ".meta/check.py"): "the gate runs on the pull request, and `gh pr checks` reads what it found",
    ("grep",): "the Grep tool searches the worktree, and `git grep` searches a commit",
    ("wc",): "the Read tool reads a file and counts what it read",
}


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


def command_allowed(command: str) -> str | None:
    """Evaluate whether a shell command string satisfies the confinement policy.

    Allowed commands comprise single, unchained commands from the authorized program
    list (`git` subcommands, `gh` subcommands, `python3 .meta/check_pr.py`, `just pr`), `.meta/say/`
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
    head, marker, body = shell.partition_unquoted(command, "<<")
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
    words = shell.words_of(head)
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
    if shell.partition_unquoted(command, "<<")[1]:
        return None
    words = shell.words_of(shell.before_operator(command), literal=True)
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
    candidate = " ".join(shell.requote(word) for word in words)
    return candidate if command_allowed(candidate) is None else None
