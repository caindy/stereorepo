#!/usr/bin/env python3
"""What the workflows cost in time, on one screen, read from GitHub (solorepo's DR-157).

`just next`'s `loops()` answers whether a loop is idle. This answers what it
costs, which is the question nobody asks until they are waiting — and by then
the increment that caused it is several weeks back and inside the noise of the
one before.

    python3 .meta/timing.py              # every workflow, the last 20 runs each
    python3 .meta/timing.py gate.yml     # one workflow
    python3 .meta/timing.py --steps      # the slowest steps, and what they wait on

Two costs, reported apart, because they move for different reasons and only
one of them is the repository's to fix:

- **waiting** is what the run spent getting a runner: GitHub finding one, and
  for `arc-runner-set` a pod being scheduled and pulling its image. A change
  to this repository's own files does not move it; a change to the runner
  image or the scale set's ceiling does.
- **running** is what it spent working once it had one, which is what a step
  added to a workflow moves.

Both are read off the job that finished last, so they add up to the run —
see `critical`, which is where the arithmetic that looks obvious is wrong.

Reported together they are one number that goes up for two unrelated reasons,
which is the shape that gets attributed to whatever landed most recently.

**Read locally, never by CI.** This is an Actions read, and solorepo's DR-153 refused
`actions: read` in the gate workflows on the ground that a scaffold hands a
fresh clone whatever scope its gate declares. So this is a command the solo
runs with the solo's own token, and no workflow calls it. `next.py` already
degrades when its token cannot list runs; this would have nothing left to
print, so it says so rather than printing zeros.

**The figures are this repository's.** solorepo's runs on `arc-runner-set` and a
portfolio's on `ubuntu-latest` (Specialization's second step retargets every
`runs-on:`), so a number measured here means nothing there. Nothing here
carries a threshold for that reason: it reports, and what is too slow is read
by someone who knows what the work was.
"""
from lib.timing import cli
from lib.timing.arithmetic import at, clock, critical, pick, span
from lib.timing.cli import main
from lib.timing.github import (
    NOT_RUN,
    RUN_FIELDS,
    UNSET,
    WORKFLOWS,
    gh,
    jobs_of,
    runs_of,
)
from lib.timing.routing import (
    BOUNDARY_PATTERN,
    ISSUES_FETCHED,
    difficulty_of,
    model_of,
    stratify_run,
)
from lib.timing.screen import Window, row, screen, steps, subrow, summarise

__all__ = [
    "BOUNDARY_PATTERN",
    "ISSUES_FETCHED",
    "NOT_RUN",
    "RUN_FIELDS",
    "UNSET",
    "WORKFLOWS",
    "Window",
    "at",
    "cli",
    "clock",
    "critical",
    "difficulty_of",
    "gh",
    "jobs_of",
    "main",
    "model_of",
    "pick",
    "row",
    "runs_of",
    "screen",
    "span",
    "steps",
    "stratify_run",
    "subrow",
    "summarise",
]
"""The script's whole surface, so `timing probes` in `.meta/checks/probes/tools/timing.py`, which loads
this file by path, finds `pick` and `gh` where it did."""

if __name__ == "__main__":
    cli.main(__doc__)
