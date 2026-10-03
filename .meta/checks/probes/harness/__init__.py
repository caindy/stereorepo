"""What the probes stand in for, and the acts every probe repeats (stereorepo's DR-342).

A wiki page answered from a string, a script loaded without running its
`main()`, and what a call exited with, read as text rather than allowed to end
the step.

Nothing here is a step. A subject module imports what it needs from here and
registers its own, and this package imports no sibling under `probes/`, so the
package's import graph is a tree with this at its root, as `collect.py` is for
the gate (stereorepo's DR-150).
"""
from checks.probes.harness.acts import Outcome, outcome
from checks.probes.harness.fakes import FakeWikiPath
from checks.probes.harness.loaders import load_module

__all__ = [
    "FakeWikiPath",
    "Outcome",
    "acts",
    "fakes",
    "load_module",
    "loaders",
    "outcome",
]
"""The module's whole surface, so every probe's `from checks.probes.harness import ...` still resolves."""
