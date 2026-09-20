#!/usr/bin/env python3
"""Gate orchestrator and semantic constraint checker for the .meta Project.

Validates semantic invariants across LinkML schema instances, graph relations,
prose citations, and code standards (solorepo's DR-029, solorepo's DR-150,
solorepo's DR-209). Sequentially executes registered prechecks, schema model
loaders, and step suites from `.meta/checks/`.

History in check.history.md (solorepo's DR-171).
"""
import sys  # noqa: I001  # reason: the step imports below stand in registration order, not sorted order
from collections.abc import Callable, Sequence
from typing import Any

from checks import collect
from checks import files
from checks import citations  # noqa: F401  # reason: registers check steps
from checks import comments  # noqa: F401  # reason: registers check steps
from checks import graph  # noqa: F401  # reason: registers check steps
from checks import probes  # noqa: F401  # reason: registers check steps
from checks.collect import STEPS, views


def report(label: str, outcome: collect.StepOutcome | Sequence[str]) -> bool:
    """Formats and prints a single check step outcome adhering to Article 21 (solorepo's DR-092).

    Args:
        label: Descriptive identifier of the check step.
        outcome: Step result object (Passed, Found, CouldNotRun) or list of issues.

    Returns:
        bool: True if defects were detected, False otherwise.
    """
    if isinstance(outcome, collect.CouldNotRun):
        print(f"?  {label}: {outcome.why}")
        return False
    elif isinstance(outcome, collect.Passed):
        print(f"ok {label}" + (f" — {outcome.scope}" if outcome.scope else ""))
        return False
    elif isinstance(outcome, collect.Found):
        problems = outcome.problems
    else:
        problems = outcome

    if problems:
        print(f"x  {label} ({len(problems)})")
        for p in problems:
            print(f"     {p}")
        return True
    else:
        print(f"ok {label}")
        return False


def main() -> int:
    """Executes prechecks, schema collections, and registered verification steps.

    Catches execution exceptions per step to ensure failures report structured
    diagnostics rather than aborting prematurely (Article 6). Evaluates step
    sources on demand and tallies object indices.

    Returns:
        int: 0 if all registered steps pass cleanly, 1 if any step fails.
    """
    failed = False
    for step in [s for s in STEPS if s.pre]:
        try:
            problems = step.run()
        except Exception as exc:
            problems = [f"the check itself could not run — {type(exc).__name__}: {exc}"]
        failed |= report(step.label, problems)
    rest = [s for s in STEPS if not s.pre]
    try:
        schemas = views()
        index, refs, skipped = collect.collect(schemas)
    except Exception as exc:
        print(f"?  schemas: could not load — {type(exc).__name__}: {exc}")
        print(f"     {len(rest)} steps did not run")
        return 1
    for name in skipped:
        print(f"?  {name}: no container accepts its top-level keys")
    failed |= bool(skipped)
    sources: dict[str, Callable[[], Any]] = {
        "index": lambda: index,
        "refs": lambda: refs,
        "views": lambda: schemas,
        "asked": lambda: files.rendering()[0].ASKED,
        "pages": lambda: files.rendering()[1],
    }
    for step in rest:
        try:
            given = [sources[name]() for name in step.sources]
        except Exception as exc:
            print(f"?  {step.label}: its source could not be built — "
                  f"{type(exc).__name__}: {exc}")
            failed = True
            continue
        failed |= report(step.label, step.run(*given))
    print(f"\n{len(index)} identified objects, {len(refs)} references")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
