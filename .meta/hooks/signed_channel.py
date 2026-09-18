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

Exit 2 blocks the call and shows the message to the agent. The body is
`.meta/lib/signed_channel/`: `tables` holds every list and pattern named above,
`shell` takes a command line apart, `reach` judges each segment and holds the
predicate `blocked`, and `verdict` reads the event and exits with the judgement.
Each module's docstring carries the why of its part; this file is the contract a
harness invokes, and `reach.blocked` is the predicate, separate from the
plumbing so it can be watched failing without a harness.

History in signed_channel.history.md (solorepo's DR-171).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from lib.signed_channel import (
    reach,
    shell,
    tables,
    verdict,
)
from lib.signed_channel.reach import (
    blocked,
    reaches,
    runs_channel,
    writes,
)
from lib.signed_channel.shell import (
    bodies_after,
    past_prefix,
    program,
    run_by,
    runs_nothing,
    segments,
    shell_code,
    without_heredocs,
)
from lib.signed_channel.tables import (
    ASSIGNMENT,
    ENDPOINT,
    GH_WRITES,
    HEREDOC,
    NESTING,
    OPTION_VALUES,
    QUOTES,
    READING,
    READING_PAIRS,
    RUNS_CODE,
    SANCTIONED,
    SEPARATORS,
    SHELLS,
    SUBSTITUTION,
    TRANSPARENT,
    UNREADABLE,
    WHY,
    WRAPPERS,
)
from lib.signed_channel.verdict import main

__all__ = [
    "ASSIGNMENT",
    "ENDPOINT",
    "GH_WRITES",
    "HEREDOC",
    "NESTING",
    "OPTION_VALUES",
    "QUOTES",
    "READING",
    "READING_PAIRS",
    "RUNS_CODE",
    "SANCTIONED",
    "SEPARATORS",
    "SHELLS",
    "SUBSTITUTION",
    "TRANSPARENT",
    "UNREADABLE",
    "WHY",
    "WRAPPERS",
    "blocked",
    "bodies_after",
    "main",
    "past_prefix",
    "program",
    "reach",
    "reaches",
    "run_by",
    "runs_channel",
    "runs_nothing",
    "segments",
    "shell",
    "shell_code",
    "tables",
    "verdict",
    "without_heredocs",
    "writes",
]
"""The hook's whole surface: every public name of the package, and the four modules beside them.

`hook_probes` in `.meta/checks/probes/git/step.py` loads this file by path and
reads `blocked` off it; `main` and the rest are exported so that the surface is
the one the file had before the split. The modules are exported so a probe can
stand a collaborator in at the module that defines it (solorepo's DR-217)."""

if __name__ == "__main__":
    sys.exit(verdict.main())
