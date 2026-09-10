#!/usr/bin/env python3
"""Refuse a read outside the worktree, and a shell command that is not one plain
command the reviewer is allowed (solorepo's DR-110).

A PreToolUse hook for the container the reviewer runs in. `review.yml` registers
it through the action's `settings` input and nothing else does, so on a laptop it
never runs: there the Role's credentials sit beside each other and solorepo's DR-073 has
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

A refusal names the nearest command the grammar takes, where the one refused
has one: the head of a chain, or the same command without the option that is
not carried. It is derived and then put back through the predicate rather than
suggested, so the retry is one turn and not a guess (#144).

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

# The part of `SHELL` that ends one command and starts something else:
# chaining, redirects and a newline. A derivation may cut there and lose only a
# second command. The rest of `SHELL` expands *within* an argument — `~`, `$`,
# `*`, a brace — so cutting at one of those truncates the first command's
# argument instead, and `git show HEAD~1:x` would be offered as `git show HEAD`:
# a different question, well-formed, with nothing in it to say what was dropped.
# An argument carrying an expansion has no nearest command, the same as a
# program off the list (#146).
CHAINS = set(";&|<>\n")

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

# A program off the list that the reviewer reaches for anyway, and where what
# it wanted is instead. Nothing can be derived for one of these — there is no
# nearest command on the list to a program that is not on it — so the refusal
# says why it is not coming, which is the only thing that stops the reach
# repeating run after run (#144).
#
# `check.py` is the one, and the reason it is not simply listed is not the
# option list. `check_pr.py` is one of the six paths `review.yml` restores from
# trunk before the session starts; `check.py` is not, and neither is the
# `render.py` it imports, so running it would execute the pull request's own
# code in the container that holds the reviewer's token, which is the boundary
# solorepo's DR-110 draws. It would not run in any case: the gate is `uvx --with linkml
# --with pyyaml python .meta/check.py` and the container installs neither.
INSTEAD = {
    ("python3", ".meta/check.py"): "the gate runs on the pull request, and `gh pr checks` reads what it found",
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


def refused_option(words, allowed, takes_value):
    """Where the first option the list does not carry sits in `words`, or None.

    A word that does not start with `-` is a ref, a path, a number or a
    pattern, and the program's to make sense of; `--` ends the options. An
    option that takes a value consumes the next word whatever it looks like,
    and is the only kind that may carry its value after `=`: the set is the
    subcommand's own, so nothing added for one reaches another (#87).

    The index rather than the message, because `plain_form` drops the word it
    names and a refusal reads it back out.
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
    """Every option among `words` is on the list, by exact spelling."""
    i = refused_option(words, allowed, takes_value)
    return None if i is None else f"`{words[i]}` is not an option `{what}` may carry here"


def form_of(words):
    """Which form on the list this command is, or None.

    `(offset, what, allowed, takes_value)`: where the options start, what to
    call the form in a refusal, and its two lists. One lookup for git's
    subcommands and the other programs both, so the predicate and the
    derivation below read the same table rather than two copies of it.
    """
    if words[0] == "git":
        if len(words) > 1 and words[1] in GIT:
            return 2, f"git {words[1]}", GIT[words[1]], TAKES_VALUE[words[1]]
        return None
    for form, (allowed, takes_value) in PROGRAMS.items():
        if tuple(words[:len(form)]) == form:
            return len(form), " ".join(form), allowed, takes_value
    return None


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
    and only in the one shape the prompt shows: `.meta/say/<program> ... <<'WORD'`,
    nothing after the delimiter on that line, the body below, the delimiter
    on a line of its own, and nothing after that. The body is never executed
    and is not read; the delimiter is quoted so the body is not expanded
    either. The first line that is the delimiter closes the body in bash,
    so it must be the last line there is: what followed it would be a
    second statement with the one token the container holds (#87).
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
        return f"`git {words[1] if len(words) > 1 else ''}` is not a subcommand the reviewer runs"
    instead = INSTEAD.get(tuple(words[:2]))
    return (f"`{' '.join(words[:3])}` is not a program the reviewer runs"
            + (f", and is not coming: {instead}" if instead else ""))


def before_operator(text):
    """The text up to the first character that ends the command, outside quotes.

    The head of a chain, a pipe or a redirect: `gh pr diff 86 | head` is
    `gh pr diff 86`, which is the command the reviewer wanted and the one this
    hook takes. `CHAINS` and not `SHELL`, because only those characters drop a
    second command; the rest would truncate this one's argument silently.
    """
    quoted = False
    for i, ch in enumerate(text):
        if ch == "'":
            quoted = not quoted
        elif not quoted and ch in CHAINS:
            return text[:i]
    return text


def requote(word):
    """One word of a derived command, spelled so bash gives it back whole.

    Single quotes always, because a word here cannot contain one: `\\` and `"`
    are refused, so there is no other way to have written it.
    """
    return word if word and not (set(word) & SHELL) and not any(c.isspace() for c in word) else f"'{word}'"


def plain_form(command):
    """A command on the list, derived from one that was refused, or None.

    A refusal that says only what is wrong costs a turn to guess at, and the
    guess is often wrong: across the nine review runs read for #144 the hook
    refused between 7 and 29 calls a run — a third of one review's turns —
    with the prompt already saying one plain command at a time. Most of them
    have a nearest command the hook would have taken, and it is derivable
    rather than guessable: the head of a chain, and the same command without
    the option the list does not carry.

    Nothing here is offered on trust. Whatever this returns has been through
    `command_allowed`, so a refusal names a command this hook accepts or names
    none, and a derivation that reaches somewhere unexpected — `git grep -O id
    x` becomes a search for `x` — is refused by the same predicate as every
    other call. A heredoc gets no derivation: cutting one at its `<<` would
    offer the channel a post with no body, and those refusals already name the
    shape they want.

    Neither does anything else the channel is reached with, whatever the
    operator: the body arrives on stdin however it was spelled, and `< body.md`
    is the form the reviewer's own skill lists, so a command cut at that `<` is
    the same post with the body gone. Most of the verbs would then die on
    `say: nothing on stdin`, spending the turn this exists to save; `review
    --approve` would not, because GitHub takes an approval with no body, and
    the offer would be a verdict with what was checked stripped out (#146).
    """
    if partition_unquoted(command, "<<")[1]:
        return None
    words = words_of(before_operator(command))
    if isinstance(words, str) or not words:
        return None
    if re.fullmatch(r"\.meta/say/[a-z]+", words[0]):
        return None
    form = form_of(words)
    if form:
        offset, _, allowed, takes_value = form
        while (i := refused_option(words[offset:], allowed, takes_value)) is not None:
            i += offset
            # An option with no `=` may own the word after it: `--repo other/repo`
            # goes whole, or the repository is left behind as a positional.
            owns = "=" not in words[i] and i + 1 < len(words) and not words[i + 1].startswith("-")
            words = words[:i] + words[i + (2 if owns else 1):]
    candidate = " ".join(requote(word) for word in words)
    return candidate if command_allowed(candidate) is None else None


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
            command = tool_input.get("command", "")
            problem = command_allowed(command)
            if problem:
                # The nearest command on the list goes last, because it is the
                # one to type and the end of a refusal is where that is looked
                # for (#144).
                plain = plain_form(command)
                return (f"Blocked: {problem}. The reviewer runs one plain command at a time: "
                        "`git log|show|diff|status|grep|ls-files` with plain options, `gh pr view|diff|checks`, "
                        "`python3 .meta/check_pr.py`, or a program of `.meta/say/` with a quoted heredoc. "
                        "No pipes, redirects, expansions or chaining."
                        + (f" This one would be taken as: {plain}" if plain else ""))
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
