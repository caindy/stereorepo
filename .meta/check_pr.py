#!/usr/bin/env python3
"""The GitHub half of the gate: A15, held against a live pull request, and the
quarter of A12 whose target is an Issue rather than a file.

`check.py` reads files and this repository's own commits, and reaches the remote
for one thing only — which Decision numbers are reserved, and only when the
record has a hole to explain (solorepo's DR-128). History in check_pr.history.md (solorepo's DR-171).
This reads GitHub for everything it does, so it is a separate command with a
separate lifecycle — it runs when a pull request opens or changes, and there is
nothing for it to say the rest of the time.

    python .meta/check_pr.py 12          # what CI runs
    python .meta/check_pr.py --file b.md # a body on disk, for watching it fail
    python .meta/check_pr.py 12 --watch  # one line per change, exiting on actionable events or when it closes

What a body must contain is **derived from the form**, never listed here. The
headings come out of the fence in `.meta/templates/pull-request.md`, which is
the same text GitHub renders into `.github/PULL_REQUEST_TEMPLATE.md`. Adding a
heading to the form makes it required by that act alone; a checker with its own
copy of the list would drift from the form the first time either moved, and the
drift would show up as a check that had quietly stopped asking for something.

A15 is the one Article in this area that is mechanically checkable. A13 and A14
are not — reasoning in a commit message is a judgement about a paragraph, and no
length check reaches it. What is checkable is narrower and still worth having:
every item under *what was noticed and not done* is a link, so the pull request
cannot close over an observation that has nowhere to live afterwards.

The same shape holds the other direction. Every item under *what it closes*
carries one of GitHub's closing keywords, so the merge closes the Challenge the
pull request finished and no one has to remember a second act (solorepo's DR-089).

`--all`, the sweep the gate workflow runs on the clock, asks one more thing that
is not the body's: who takes each open pull request next (solorepo's DR-129). A
handoff here is a review request, which GitHub holds and reports — so a pull
request with no request on it, and a request no workflow can answer, are the two
states nothing reports and nothing wakes on.

`--hand-back` answers that same question from the other side, for a run that is
about to die: whether anybody holds this Challenge's pull request yet, and
whether what is there is worth requesting a review of. Its reader is
`coder.yml`'s hand-back step, so the predicate lives here and not in that
step's shell (solorepo's DR-155).

`--handoff` is the one mode that reads the tree rather than GitHub, because what
it holds is about the branch: A18, and what a branch that changes the record owes
along with it — a render that is current, and a decision that names the artifacts
the branch edits while settling it (solorepo's DR-175).

`--unresolved-count` outputs the count of unresolved review threads for the
pull request, giving unattended workflows a first-class CLI query without
embedding inline Python in shell run steps (solorepo's DR-241).

This entry holds no logic (solorepo's DR-217): it exports the package's
submodules and the CLI entry point, so callers and test probes access verbs
and seams qualified by submodule (solorepo's #1028).
"""
from lib.check_pr import (
    META,
    ROOT,
    branch,
    cli,
    form,
    github,
    polling,
    remedies,
    review,
    state,
    sweep,
    verdict,
)
from lib.check_pr.cli import main

__all__ = [
    "META",
    "ROOT",
    "branch",
    "cli",
    "form",
    "github",
    "main",
    "polling",
    "remedies",
    "review",
    "state",
    "sweep",
    "verdict",
]


if __name__ == "__main__":
    cli.main(__doc__)
