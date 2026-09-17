#!/usr/bin/env python3
"""Refuse any path to GitHub that does not sign what it posts (solorepo's DR-069).

A PreToolUse hook, so the harness runs it rather than the agent remembering to.
`.claude/settings.json` denies `gh`'s writing verbs and permits its read-only
ones; this catches everything else that can reach the same endpoint — `curl`, `python`, `wget`, a language's
HTTP client — because a deny list over one binary is not a boundary.

Inspects commands before execution and blocks unsanctioned access to GitHub
endpoints, ensuring operations route through the signing channel until credential-level
isolation is enforced (solorepo's DR-174, solorepo's DR-175).

The predicate reads command position rather than substrings. A command line is
split on the shell's own separators (`;`, `&&`, `||`, `|`, `&` and newlines),
each segment is lexed with `shlex`, and each segment is judged on its own:

- A segment is judged only where the program it runs is neither of the channel,
  nor one of `READING`, nor a `git` subcommand of `READING_PAIRS`. Judged, it
  reaches GitHub when a word of it naming `gh` is followed by the words of one
  of `GH_WRITES`, or when it names `ENDPOINT`.
- The program a segment runs is named behind a prefix of `TRANSPARENT`, whose
  members exec the rest of their words rather than doing the work themselves,
  so `timeout 5 bash -c <line>` is judged as the `bash` it is. A prefix whose
  own words ran out before one named a program was handed its command line some
  other way, and the segment is refused rather than read as running nothing.
- A segment is sanctioned when the program it runs is one of `.meta/say/` or
  `.meta/check_pr.py` (solorepo's DR-117), spelled as a bare path, an absolute
  one, one prefixed by `$CLAUDE_PROJECT_DIR`, or one behind an interpreter of
  `WRAPPERS`. Sanctioning a segment says nothing about the segments beside it,
  so a line passes only when every segment passes on its own.
- A heredoc body is an argument of the segment that opened it rather than a
  line of commands, and is read as text the segment carries. A body written
  under an unquoted delimiter is expanded by the shell before the segment runs,
  so one holding a substitution is refused rather than read as the text it is
  now.
- A shell interpreter's `-c` argument is another command line, and is read as
  one to the depth of `NESTING`, in addition to the words of the segment that
  handed it over rather than instead of them. An interpreter given no command
  line is about to run text this hook has not read, and is refused.
- What this hook cannot read it refuses: an unclosed quote, a `<<` whose
  delimiter it cannot parse, a substitution anywhere in a segment's text or in a
  heredoc body the shell will expand, a shell interpreter handed no command
  line, or a prefix of `TRANSPARENT` that consumed every word behind it.

Five lists are matched against the name of the program a segment runs, rather
than against its position: `READING`, `READING_PAIRS` — which is matched against
that name beside its first argument, `git` alone saying nothing about which —
`SHELLS`, `WRAPPERS` and `TRANSPARENT`. `RUNS_CODE` is matched by prefix against
the arguments of a program already named by `WRAPPERS`, and against no name at
all. Each list states the least this boundary holds rather than all of it, and
three of them say where it stops. `READING`: a program on it is not read
further, so one that can be made to spawn another — GNU `sed`'s `e` flag is the
one in reach — carries the same exemption. `WRAPPERS`: a program given code on
its command line is read no further than that code's own words, so `python3 -c`
reaching GitHub is caught by the endpoint it names and not by the client it
builds. `TRANSPARENT`: a prefix that execs but is not on it leaves the command
behind it read as the quoted word it is. A fourth limit is not a list's: what a
segment is fed through a pipe is not on its command line, so `echo <endpoint> |
xargs curl -X POST` names the endpoint in the segment that prints it and not in
the one that posts it. Full shell parsing would close the first two and nothing
closes the last: what is held is that a path spelled as a call to GitHub on a
line these lists can read is refused, and what is bought is that a read naming
these strings is not.

    echo '{"tool_name":"Bash","tool_input":{"command":"..."}}' | .meta/hooks/signed_channel.py

Exit 2 blocks the call and shows the message to the agent. The predicate is
separate from the plumbing so it can be watched failing without a harness.

History in signed_channel.history.md (solorepo's DR-171).
"""
import json
import os
import re
import shlex
import sys
from collections.abc import Iterator

# The endpoint, however it is spelled.
ENDPOINT = re.compile(r"api\.github\.com|graphql\.github\.com")

# The writing verbs of the CLI that wraps the endpoint, each spelled as the
# words that carry it. Reading is permitted; mutating actions must pass through
# the channel:
# - merge, close, update-branch: mutating operations that record an actor and require
#   proper attribution (solorepo's DR-113).
# - stack commands (link, merge, submit): commands that create or mutate pull requests (solorepo's DR-100).
# - workflow run: dispatches GitHub Actions jobs; must use .meta/say/move dispatch (solorepo's DR-151).
# Read-only operations (such as gh run list and gh workflow view) remain open.
GH_WRITES = (
    ("api",),
    ("pr", "comment"), ("pr", "review"), ("pr", "create"), ("pr", "edit"),
    ("pr", "merge"), ("pr", "close"), ("pr", "update-branch"),
    ("issue", "create"), ("issue", "comment"), ("issue", "edit"), ("issue", "close"),
    ("workflow", "run"),
    ("stack", "link"), ("stack", "merge"), ("stack", "submit"), ("stack", "unstack"),
    ("stack", "delete"), ("stack", "push"), ("stack", "sync"), ("stack", "rebase"),
)

# The channel is a directory of programs over one signing primitive (solorepo's DR-117),
# so what is sanctioned is the directory: a program added beside `post` and
# `move` is sanctioned by where it lives, not by a name added here. The tail
# names the program and whatever precedes it only says where the directory is,
# so an absolute path and a `$CLAUDE_PROJECT_DIR`-prefixed one are one spelling.
SANCTIONED = re.compile(r"(?:\A|/)\.meta/(?:say/[a-z][a-z_-]*|check_pr\.py)\Z")

# The interpreters a program of the channel is run under: `.meta/check_pr.py` is
# typed behind `python3`, and `uv` supplies the environment where one is needed.
WRAPPERS = frozenset({"python", "python3", "uv", "uvx"})

# Interpreter options that run code given on the command line, so a channel path
# written beside one is a mention rather than the program being run.
RUNS_CODE = frozenset({"-c", "-m", "-e"})

# Programs that print the text they are given. A segment running one of them
# carries the endpoint as text rather than as a destination, which is what lets
# a search for these strings, or a sentence naming them, through.
READING = frozenset({
    "grep", "egrep", "fgrep", "rg", "ag", "ack", "cat", "tac", "head", "tail",
    "less", "more", "sed", "echo", "printf", "wc", "sort", "uniq", "cut", "tr",
    "nl", "rev", "strings", "diff", "comm", "basename", "dirname", "true", "false",
})

# The same, for a program that prints the text it is given under a subcommand
# rather than under its own name. `git grep` is the search the reviewer's
# container prescribes and `git commit` records the message it is handed, so
# both carry the endpoint as text where `git` alone says nothing about which.
READING_PAIRS = frozenset({
    ("git", "grep"), ("git", "log"), ("git", "show"), ("git", "diff"), ("git", "commit"),
})

# Shell interpreters, whose `-c` argument is another command line and is read
# as one, and how far that nesting is followed before the line is refused for
# being unreadable rather than read further.
SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh"})
NESTING = 4

# The shell's own short options that take a value as the word after them, which
# is therefore not the command line even where no option before it held `c`.
OPTION_VALUES = frozenset({"-o", "+o", "-O", "+O"})

# Programs that exec the rest of their words rather than doing the work
# themselves, so the program a segment runs is named behind one and not by the
# segment's first word. Each is paired with the options whose value is the word
# after them, and with how many arguments of its own it takes before the command
# — `timeout` its duration, and the rest none.
TRANSPARENT = {
    "env": (frozenset({"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}), 0),
    "nohup": (frozenset(), 0),
    "setsid": (frozenset(), 0),
    "command": (frozenset(), 0),
    "nice": (frozenset({"-n", "--adjustment"}), 0),
    "ionice": (frozenset({"-c", "--class", "-n", "--classdata", "-p", "--pid"}), 0),
    "stdbuf": (frozenset({"-i", "--input", "-o", "--output", "-e", "--error"}), 0),
    "timeout": (frozenset({"-k", "--kill-after", "-s", "--signal"}), 1),
    "xargs": (frozenset({"-I", "-i", "--replace", "-n", "--max-args", "-L", "-P",
                         "--max-procs", "-d", "--delimiter", "-E", "-e", "-a",
                         "--arg-file", "-s", "--max-chars"}), 0),
}

# The substitutions, each of which produces at run time text this hook is
# reading now: a command substitution in either spelling, and a process
# substitution. A segment holding one anywhere in its text is refused rather
# than read, the program it runs being whatever the substitution prints, and so
# is a heredoc body the shell will expand before the segment carrying it runs.
SUBSTITUTION = re.compile(r"\$\(|`|<\(|>\(")

# An environment assignment written before the program it is set for.
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")

# A heredoc opener, whose delimiter may be quoted — which is what says whether
# the shell expands the body, POSIX Shell Command Language 2.7.4 expanding one
# written under an unquoted word and no other — and whose `-` form lets the
# closing delimiter be indented with tabs.
HEREDOC = re.compile(r"<<-?[ \t]*(?P<quote>['\"]?)(?P<word>[A-Za-z_][A-Za-z0-9_]*)(?P=quote)")

QUOTES = frozenset("'\"")

# The shell's own command separators. A run of them is one separator, so `&&`
# and `||` need no spelling of their own.
SEPARATORS = frozenset(";&|\n")

WHY = ("Blocked: this reaches GitHub without signing what it posts.\n"
       "Use the channel — .meta/say/post to say something, .meta/say/move to change "
       "state — which appends the Actor Trailer from the environment, which is what "
       "makes a comment attributable at all when every login here is the solo's. "
       "Your reading of PR First lists your verbs; a program's --help lists its own. "
       "Reading is fine through "
       "`.meta/check_pr.py --threads|--resume|--sweep`.")

UNREADABLE = ("Blocked: this hook could not read this command line, and refuses rather "
              "than guessing what it runs. Write one command per line with its program "
              "named literally, and quote what the shell should not act on.")


def bodies_after(command: str, index: int,
                 pending: list[tuple[str, bool, bool, int]]
                 ) -> tuple[int, list[tuple[int, bool, str]]]:
    """Collect the heredoc bodies that begin at an offset, one per opener awaiting one.

    Parameters:
        command: Raw command string from tool input.
        index: Offset of the first character after the newline ending the line
            the openers were written on.
        pending: Each opener awaiting a body, as `(delimiter, dashed, expands,
            offset)`, in the order the openers were written.

    Returns:
        tuple[int, list[tuple[int, bool, str]]]: The offset the shell text
        resumes at, and each body paired with whether the shell expands it and
        with the offset of the `<<` that opened it.

    A body runs to a line holding its delimiter alone, leading tabs ignored where
    the opener was written `<<-`. A delimiter that never arrives takes the rest of
    the command with it.
    """
    taken = []
    for word, dashed, expands, offset in pending:
        start = index
        while index < len(command):
            stop = command.find("\n", index)
            line = command[index:] if stop < 0 else command[index:stop]
            index = len(command) if stop < 0 else stop + 1
            if (line.lstrip("\t") if dashed else line).rstrip("\r") == word:
                break
        taken.append((offset, expands, command[start:index]))
    return index, taken


def without_heredocs(command: str) -> tuple[str, list[tuple[int, bool, str]]] | None:
    """Lift every heredoc body out of a command line, keeping each body's opener.

    Parameters:
        command: Raw command string from tool input.

    Returns:
        tuple[str, list[tuple[int, bool, str]]] | None: The shell text with every
        heredoc body removed, and each body paired with whether the shell expands
        it and with the offset in that text of the `<<` that opened it; None
        where the command holds an unclosed quote or a `<<` whose delimiter this
        hook cannot parse.

    A heredoc body is data the segment before it carries, so lifting it out keeps
    its lines from being read as commands of their own. `<<<` is a here-string,
    whose word is on the line already, and is left where it stands.
    """
    text, bodies, pending = "", [], []
    quote, index = "", 0
    while index < len(command):
        char = command[index]
        if char == "\\" and quote != "'" and index + 1 < len(command):
            text, index = text + command[index:index + 2], index + 2
            continue
        if quote:
            text, index = text + char, index + 1
            quote = "" if char == quote else quote
            continue
        if char in QUOTES:
            text, quote, index = text + char, char, index + 1
            continue
        if command.startswith("<<<", index):
            text, index = text + "<<<", index + 3
            continue
        if command.startswith("<<", index):
            opener = HEREDOC.match(command, index)
            if opener is None:
                return None
            pending.append((opener["word"], opener[0].startswith("<<-"),
                            opener["quote"] == "", len(text)))
            text, index = text + opener[0], opener.end()
            continue
        text, index = text + char, index + 1
        if char == "\n" and pending:
            index, taken = bodies_after(command, index, pending)
            bodies.extend(taken)
            pending = []
    return None if quote else (text, bodies)


def segments(text: str) -> Iterator[tuple[int, int, str]]:
    """Split shell text into the commands it runs, keeping each one's offsets.

    Parameters:
        text: Shell text with its heredoc bodies already lifted out.

    Yields:
        tuple[int, int, str]: The start offset, the end offset, and the text of
        each command the line runs, separated at unquoted `SEPARATORS`.
    """
    start, quote, index = 0, "", 0
    while index < len(text):
        char = text[index]
        if char == "\\" and quote != "'":
            index += 2
            continue
        if quote:
            quote = "" if char == quote else quote
            index += 1
            continue
        if char in QUOTES:
            quote, index = char, index + 1
            continue
        if char in SEPARATORS:
            yield start, index, text[start:index]
            while index < len(text) and text[index] in SEPARATORS:
                index += 1
            start = index
            continue
        index += 1
    yield start, len(text), text[start:]


def past_prefix(prefix: tuple[frozenset[str], int], words: list[str], at: int) -> int:
    """Walk a transparent prefix's own words to the one naming the command it runs.

    Parameters:
        prefix: The prefix, as `TRANSPARENT` pairs it: the options whose value is
            the word after them, and how many arguments of its own it takes.
        words: One segment's words, as `shlex` lexed them.
        at: The offset of the first word after the prefix.

    Returns:
        int: The offset of the word naming the program the prefix runs, or the
        end of the words where every one of them was consumed — which `env -S
        <line>` does, its option's value being the command line itself. An
        option this pairing does not name as taking a value is read as taking
        none, so a prefix written with one hides the command behind it the way
        an unlisted prefix does.
    """
    values, mine = prefix
    while at < len(words):
        word = words[at]
        if len(word) > 1 and word[0] in "-+":
            at += 2 if word in values else 1
            continue
        if mine:
            mine, at = mine - 1, at + 1
            continue
        return at
    return at


def program(words: list[str]) -> tuple[str | None, list[str]]:
    """Name the program a segment runs, and the arguments it runs it with.

    Parameters:
        words: One segment's words, as `shlex` lexed them.

    Returns:
        tuple[str | None, list[str]]: The word naming the program, after
        `os.path.expandvars`, and the words following it. A prefix of
        `TRANSPARENT` execs the rest of its words rather than doing the work
        itself, so the walk carries on behind one, and behind any run of them.
        The name is None where no word of the segment names a program: either
        it runs none, or a prefix consumed every word behind it, which
        `runs_nothing` tells apart.
    """
    at = 0
    while at < len(words):
        if ASSIGNMENT.match(words[at]):
            at += 1
            continue
        name = os.path.expandvars(words[at])
        prefix = TRANSPARENT.get(name.rsplit("/", 1)[-1])
        if prefix is None:
            return name, words[at + 1:]
        at = past_prefix(prefix, words, at + 1)
    return None, []


def runs_nothing(words: list[str]) -> bool:
    """Judge whether a segment names no program because there is none to name.

    Parameters:
        words: One segment's words, as `shlex` lexed them.

    Returns:
        bool: True where the segment is empty or environment assignments alone,
        which are the two ways `program` names nothing because nothing runs.
        It also names nothing where a transparent prefix consumed every word
        behind it — `env -S <line>` hands `env` the command line as the value of
        an option, and `env --split-string=<line>` as part of one — and that is
        a command this hook failed to find rather than one that was never there.
    """
    return all(ASSIGNMENT.match(word) for word in words)


def run_by(wrapper: str, arguments: list[str]) -> str | None:
    """The script an interpreter was given to run, which is its first argument naming one.

    Parameters:
        wrapper: The interpreter, named as `WRAPPERS` spells it.
        arguments: The words following it.

    Returns:
        str | None: The first argument that is neither an option nor `uv`'s own
        `run` subcommand, or None where the interpreter was given none. Only
        that position names the program being run, so an argument written
        elsewhere on the line is a mention of a path rather than a call to it.
    """
    for at, word in enumerate(arguments):
        if word.startswith("-"):
            continue
        if at == 0 and word == "run" and wrapper in ("uv", "uvx"):
            continue
        return word
    return None


def runs_channel(name: str, arguments: list[str]) -> bool:
    """Judge whether a segment runs a program of the channel.

    Parameters:
        name: The program the segment runs, as `program` resolved it.
        arguments: The words following it.

    Returns:
        bool: True where the program is one of `.meta/say/` or
        `.meta/check_pr.py`, either named directly or named as the script an
        interpreter of `WRAPPERS` is given to run, which is the one argument
        position that runs it. An interpreter handed code on its command line
        runs that code rather than a script, so any argument beginning with one
        of `RUNS_CODE` — attached to its own value, as `-cimport os` is, or
        written apart from it — sanctions nothing.
    """
    if SANCTIONED.search(name):
        return True
    if name.rsplit("/", 1)[-1] not in WRAPPERS:
        return False
    if any(word.startswith(tuple(RUNS_CODE)) for word in arguments):
        return False
    script = run_by(name.rsplit("/", 1)[-1], arguments)
    return script is not None and bool(SANCTIONED.search(os.path.expandvars(script)))


def writes(words: list[str]) -> bool:
    """Judge whether a segment's words run `gh` carrying one of the writing verbs.

    Parameters:
        words: One segment's words, as `shlex` lexed them.

    Returns:
        bool: True where a word naming `gh` is followed by the words of one of
        `GH_WRITES`, in order and next to one another. A verb spelled inside a
        single word is an argument rather than an invocation, so a pattern
        searched for with these words in it is not one.
    """
    for at, word in enumerate(words):
        if word.rsplit("/", 1)[-1] != "gh":
            continue
        after = words[at + 1:]
        if any(tuple(after[start:start + len(form)]) == form
               for form in GH_WRITES
               for start in range(len(after))):
            return True
    return False


def shell_code(arguments: list[str]) -> str | None:
    """The command line a shell interpreter was handed to run.

    Parameters:
        arguments: The words following the interpreter.

    Returns:
        str | None: The first argument that is not an option, where an option
        before it held `c`; None where the interpreter was given no command line
        to run. Bash reads the command from the first non-option argument rather
        than from the word after `-c`, so an option written between the two — as
        `bash -c -x <command>` does — does not hide the command line from this
        hook. `c` is looked for in any run of short options, `-lc` and `-cx`
        alike, and `OPTION_VALUES` names the short options whose own value
        follows them as a word.
    """
    taking, skip = False, False
    for word in arguments:
        if skip:
            skip = False
            continue
        if word.startswith("--"):
            continue
        if len(word) > 1 and word[0] in "-+":
            if word in OPTION_VALUES:
                skip = True
            elif "c" in word[1:]:
                taking = True
            continue
        return word if taking else None
    return None


def reaches(segment: str, data: str, depth: int) -> str | None:
    """Judge whether one command of a line reaches GitHub outside the signed channel.

    Parameters:
        segment: One command's text, as `segments` cut it.
        data: The heredoc bodies the command carries, joined.
        depth: How many shell interpreters this command is already nested under.

    Returns:
        str | None: The refusal to show the agent, or None where this command
        posts nothing unsigned.
    """
    try:
        words = shlex.split(segment)
    except ValueError:
        return UNREADABLE
    if SUBSTITUTION.search(segment):
        return UNREADABLE
    name, arguments = program(words)
    if name is None:
        return None if runs_nothing(words) else UNREADABLE
    if runs_channel(name, arguments):
        return None
    if "$" in name:
        return UNREADABLE
    called = name.rsplit("/", 1)[-1]
    if called in READING or (called, arguments[0] if arguments else "") in READING_PAIRS:
        return None
    if called in SHELLS:
        code = shell_code(arguments)
        if code is None:
            return UNREADABLE
        if (problem := blocked(code, depth + 1)) is not None:
            return problem
    if writes(words):
        return WHY
    if ENDPOINT.search(" ".join(words)) or ENDPOINT.search(data):
        return WHY
    return None


def blocked(command: str, depth: int = 0) -> str | None:
    """The predicate: does this command reach GitHub outside the signed channel?

    Parameters:
        command: Raw command string from tool input.
        depth: How many shell interpreters this command line is nested under; a
            line nested past `NESTING` is refused rather than read further.

    Returns:
        str | None: The refusal to show the agent, naming what to use instead;
        None where every command on the line posts nothing unsigned.
    """
    try:
        if depth > NESTING:
            return UNREADABLE
        read = without_heredocs(command)
        if read is None:
            return UNREADABLE
        text, bodies = read
        for start, end, segment in segments(text):
            carried = [(expands, body) for offset, expands, body in bodies
                       if start <= offset < end]
            if any(expands and SUBSTITUTION.search(body) for expands, body in carried):
                return UNREADABLE
            problem = reaches(segment, "".join(body for _, body in carried), depth)
            if problem:
                return problem
        return None
    except Exception as exc:
        return f"{UNREADABLE} ({type(exc).__name__}: {exc})"


def main() -> int:
    """Validates incoming pre-tool-use events to ensure mutating GitHub calls route through the signed channel."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if event.get("tool_name") != "Bash":
        return 0
    problem = blocked(event.get("tool_input", {}).get("command", ""))
    if problem:
        print(problem, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
