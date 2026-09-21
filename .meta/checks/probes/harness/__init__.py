"""What the probes stand in for, and the acts every probe repeats (solorepo's DR-209).

The channel loaded as modules; GitHub answered from a dict, for the verbs that
rebase, arm, hand off and dispatch; a watch answered from a list of polls; an
Issue answered from its labels; an obviation answered from what each number is;
a wiki page answered from a string. And the
small acts around a call: a script loaded without running its `main()`, an
attribute or an environment variable stood in for the length of a block, and
what a call exited with, read as text rather than allowed to end the step.

Nothing here is a step. A subject module imports what it needs from here and
registers its own, and this package imports no sibling under `probes/`, so the
package's import graph is a tree with this at its root, as `collect.py` is for
the gate (solorepo's DR-150). One module per kind of stand-in (solorepo's DR-218);
every name is re-exported here, so `from checks.probes.harness import ...` finds what
it did.
"""
from checks.probes.harness.acts import (
    Outcome,
    answered,
    environment,
    exit_of,
    outcome,
    run_verb,
    stood_in,
    unanswered,
    written,
)
from checks.probes.harness.fakes import (
    FakeFiling,
    FakeIssue,
    FakeObviation,
    FakeWikiPath,
)
from checks.probes.harness.github import FakeGitHub, WatchGitHub
from checks.probes.harness.loaders import load_channel, load_hook, load_module

__all__ = [
    "FakeFiling",
    "FakeGitHub",
    "FakeIssue",
    "FakeObviation",
    "FakeWikiPath",
    "Outcome",
    "WatchGitHub",
    "acts",
    "answered",
    "environment",
    "exit_of",
    "fakes",
    "github",
    "load_channel",
    "load_hook",
    "load_module",
    "loaders",
    "outcome",
    "run_verb",
    "stood_in",
    "unanswered",
    "written",
]
"""The module's whole surface, so every probe's `from checks.probes.harness import ...` still resolves."""
