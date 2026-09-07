#!/usr/bin/env python3
"""Refuse a read outside the worktree, and a shell command that is not one plain
command the reviewer is allowed (DR-110).

A PreToolUse hook for the container the reviewer runs in. `review.yml` registers
it through the action's `settings` input and nothing else does, so on a laptop it
never runs: there the Role's credentials sit beside each other and DR-073 has
already said the machine is no boundary. In the container the run holds one
token, its input is a diff nobody vetted, and its transcript is a durable log, so
what the reviewer can read and run is the boundary, and this is the layer that
can look at an argument rather than a prefix.

Two rules. A `Read`, `Grep` or `Glob` resolves inside the worktree and outside
`.git/`, or it is refused: the credential lives in `~/.config`, and the action
writes a token into `.git/config`. And a shell command is one simple command
with no operator the shell would act on, whose program and options are on a
list, or it is refused: the first shape of this rule scanned a command line for
bad tokens, and the reviewer of #87 found six ways past it in two runs, each
because bash has more syntax than the scanner — abbreviated options, `$(...)`,
`;` glued to a word, `<(...)`, text after a heredoc opener, an option nobody had
listed. A scanner for the bad cannot be sound; a grammar for the allowed can.

    echo '{"tool_name":"Grep","tool_input":{"path":"/home/x/.config"}}' | .meta/hooks/worktree_only.py

Exit 2 blocks the call and shows the message to the agent. The predicate is
separate from the plumbing so it can be watched failing without a harness, and
the gate runs it against every command the reviewer found (`check.py`).
"""
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()

READERS = {"Read": "file_path", "Grep": "path", "Glob": "path"}

# Characters the shell acts on. None of them may appear outside single quotes;
# inside single quotes bash acts on nothing. A double quote is refused too,
# because `$` and a backtick expand inside it.
SHELL = set(';&|<>$`*?[]{}()~!#\\"\n')

# What the reviewer may run, and with what. A program not named here is
# refused; an option not named under its subcommand is refused, in its exact
# spelling, so an abbreviation git would accept is not one this accepts. An
# option in its subcommand's TAKES_VALUE consumes the token after it,
# whatever it looks like: `-e -O` is a pattern. A token that does not start with `-` is a ref, a
# path, a number or a pattern, and is git's to make sense of; after `--`
# every token is a pathspec.
GIT = {
    "log": {"--oneline", "--stat", "--name-only", "--name-status", "--all",
            "--decorate", "--graph", "--follow", "--first-parent", "--reverse",
            "-p", "--patch", "-c", "--no-merges", "--merges"},
    "show": {"--stat", "--name-only", "--name-status", "--oneline", "-p",
             "--patch", "--no-patch", "-s"},
    "diff": {"--stat", "--name-only", "--name-status", "--cached", "--staged",
             "-p", "--patch", "-w", "--word-diff", "-M", "--no-color"},
    "status": {"--porcelain", "-s", "--short", "-b", "--branch", "-uno"},
    "grep": {"-n", "--line-number", "-i", "--ignore-case", "-l", "--files-with-matches",
             "-c", "--count", "-w", "--word-regexp", "-E", "--extended-regexp",
             "-F", "--fixed-strings", "-P", "--perl-regexp", "-h", "-H",
             "--name-only", "-v", "--invert-match", "--heading", "--break", "--no-color"},
    "ls-files": {"--cached", "--modified", "--deleted", "--others",
                 "--exclude-standard", "--full-name"},
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
}
# `-3` is a count for `log`; `-A2`, `-B2`, `-C2` are context glued to its
# number, which git accepts and the reviewer types (#99).
NUMBER = re.compile(r"^-(\d+|[ABC]\d+)$")

# The other programs, by form, each with its own option list and the options
# that consume a value, vetted the way git's are: `check_pr.py --file` reads
# any path and `gh --repo` reaches any repository, and neither is listed.
PROGRAMS = {
    ("gh", "pr", "view"): ({"--json", "-q", "--jq", "--comments"}, {"--json", "-q", "--jq"}),
    ("gh", "pr", "diff"): ({"--name-only", "--patch"}, set()),
    ("gh", "pr", "checks"): ({"--json", "-q", "--jq", "--required"}, {"--json", "-q", "--jq"}),
    ("python3", ".meta/check_pr.py"): ({"--threads", "--resume"}, set()),
}


# The harness's own scratch: a tool result too large for the transcript is
# written here and the reader is told to read it, and the code-review skill's
# agents hand their findings back the same way. Refusing it left the reviewer
# waiting on agents whose results it could never read (#99). No credential
# lives under it; the token is in `~/.config` and `.git/config`.
HARNESS = (pathlib.Path.home() / ".claude" / "projects").resolve()


def outside(path):
    """Whether a path the reader was given leaves the worktree or enters `.git/`.

    Resolved, so a symlink inside the tree that points outside it counts as
    outside — `CLAUDE.md` is a symlink here, and a diff could add another.
    The harness's project directory is the one place outside the worktree a
    reader may go.
    """
    target = pathlib.Path(path).expanduser()
    if not target.is_absolute():
        target = ROOT / target
    target = target.resolve()
    if HARNESS in target.parents:
        return None
    if target != ROOT and ROOT not in target.parents:
        return f"{path} is outside the worktree {ROOT}"
    if (ROOT / ".git") == target or (ROOT / ".git") in target.parents:
        return f"{path} is inside .git/, where the action keeps a token"
    return None


def words_of(text):
    """Split one simple command on whitespace, honouring single quotes only.

    Returns the words, or a string saying which character the shell would act
    on. Nothing is expanded, because nothing that expands is admitted: a `'a.*'`
    pattern is a word, a bare `*` is a refusal.
    """
    words, word, quoted, seen = [], [], False, False
    for ch in text:
        if quoted:
            if ch == "'":
                quoted = False
            else:
                word.append(ch)
        elif ch == "'":
            quoted, seen = True, True
        elif ch in SHELL:
            return f"`{ch!r}`" if ch == "\n" else f"`{ch}`"
        elif ch.isspace():
            if word or seen:
                words.append("".join(word))
            word, seen = [], False
        else:
            word.append(ch)
    if quoted:
        return "an unclosed quote"
    if word or seen:
        words.append("".join(word))
    return words


def options_allowed(what, words, allowed, takes_value):
    """Every option among `words` is on the list, by exact spelling.

    A word that does not start with `-` is a ref, a path, a number or a
    pattern, and the program's to make sense of; `--` ends the options. An
    option that takes a value consumes the next word whatever it looks like,
    and is the only kind that may carry its value after `=`: the set is the
    subcommand's own, so nothing added for one reaches another (#87).
    """
    rest = iter(words)
    for word in rest:
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
            return f"`{word}` is not an option `{what}` may carry here"
    return None


def git_allowed(words):
    """One git subcommand from the list, with options from its list."""
    if len(words) < 2 or words[1] not in GIT:
        return f"`git {words[1] if len(words) > 1 else ''}` is not a subcommand the reviewer runs"
    return options_allowed(f"git {words[1]}", words[2:], GIT[words[1]], TAKES_VALUE[words[1]])


def partition_unquoted(text, marker):
    """`str.partition`, blind inside single quotes.

    `git log --grep='a<<b'` is one plain command to bash and was two halves
    of a heredoc to a raw split (#87). Double quotes need no case: they are
    refused before anything is read.
    """
    quoted = False
    for i, ch in enumerate(text):
        if ch == "'":
            quoted = not quoted
        elif not quoted and text.startswith(marker, i):
            return text[:i], marker, text[i + len(marker):]
    return text, "", ""


def command_allowed(command):
    """The predicate for the shell: one plain command, on the list.

    The channel's heredoc form is the one exception to the no-operator rule,
    and only in the one shape the prompt shows: `.meta/say ... <<'WORD'`,
    nothing after the delimiter on that line, the body below, the delimiter
    on a line of its own, and nothing after that. The body is never executed
    and is not read; the delimiter is quoted so the body is not expanded
    either. The first line that is the delimiter closes the body in bash,
    so it must be the last line there is: what followed it would be a
    second statement with the one token the container holds (#87).
    """
    head, marker, body = partition_unquoted(command, "<<")
    if marker:
        if not head.startswith(".meta/say"):
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
    if program == ".meta/say":
        return None
    if program == "git":
        return git_allowed(words)
    for form, (allowed, takes_value) in PROGRAMS.items():
        if tuple(words[:len(form)]) == form:
            return options_allowed(" ".join(form), words[len(form):], allowed, takes_value)
    return f"`{' '.join(words[:3])}` is not a program the reviewer runs"


def blocked(tool, tool_input):
    """The predicate: does this call read past the worktree, or run more than one plain command?

    Any exception is a refusal. Only exit 2 blocks a call; an uncaught error
    exits 1 and the call proceeds, so a path with a NUL byte in it would have
    crashed this open (#87). What the hook cannot read, it refuses.
    """
    try:
        if tool in READERS:
            # A reader with no path searches the working directory; that is
            # the worktree's root here, and it is checked rather than assumed.
            problem = outside(tool_input.get(READERS[tool]) or ".")
            if problem:
                return f"Blocked: {problem}. The reviewer reads the worktree and nothing else."
            return None
        if tool == "Bash":
            problem = command_allowed(tool_input.get("command", ""))
            if problem:
                return (f"Blocked: {problem}. The reviewer runs one plain command at a time: "
                        "`git log|show|diff|status|grep|ls-files` with plain options, `gh pr view|diff|checks`, "
                        "`python3 .meta/check_pr.py`, or `.meta/say` with a quoted heredoc. "
                        "No pipes, redirects, expansions or chaining.")
        return None
    except Exception as exc:  # noqa: BLE001 — refusing is the safe answer to anything
        return f"Blocked: the hook could not read this call ({type(exc).__name__}: {exc}); refusing rather than guessing."


def main():
    """Exit 2 on a refusal, and on anything unexpected: no other exit blocks."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    try:
        problem = blocked(event.get("tool_name"), event.get("tool_input") or {})
    except BaseException as exc:  # noqa: BLE001
        problem = f"Blocked: the hook failed ({type(exc).__name__}); refusing rather than guessing."
    if problem:
        print(problem, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
