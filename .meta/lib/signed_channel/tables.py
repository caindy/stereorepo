"""What the hook knows by name: the endpoint however it is spelled, the verbs of the GitHub CLI that write, the programs the channel sanctions, the wrappers and shells that run another program, the programs that only print what they are given, the shell's own syntax (its separators, quotes, heredocs, substitutions and assignments, and the nesting it is read to), and the two refusals it can say.
"""
import re

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
