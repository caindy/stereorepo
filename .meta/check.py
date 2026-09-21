#!/usr/bin/env python3
"""Gate orchestrator and semantic constraint checker for the .meta Project.

Validates semantic invariants across LinkML schema instances, graph relations,
prose citations, and code standards (solorepo's DR-029, solorepo's DR-150,
solorepo's DR-209). Sequentially executes registered prechecks, schema model
loaders, and step suites from `.meta/checks/`.

History in check.history.md (solorepo's DR-171).
"""
import io  # noqa: I001  # reason: the step imports below stand in registration order, not sorted order
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from checks import collect
from checks import files
from checks import citations  # noqa: F401  # reason: registers check steps
from checks import comments  # noqa: F401  # reason: registers check steps
from checks import graph  # noqa: F401  # reason: registers check steps
from checks import probes  # noqa: F401  # reason: registers check steps
from checks.collect import STEPS, views


def report(label: str, outcome: collect.StepOutcome | Sequence[str],
           unrunnable: list[str]) -> bool:
    """Formats and prints a single check step outcome adhering to Article 21 (solorepo's DR-092).

    Args:
        label: Descriptive identifier of the check step.
        outcome: Step result object (Passed, Found, CouldNotRun) or list of issues.
        unrunnable: Receives one `"<label>: <why>"` line per step that could not
            run, which `closing_block` renders again at the end of the run.

    Returns:
        bool: True if defects were detected, False otherwise.
    """
    if isinstance(outcome, collect.CouldNotRun):
        print(f"?  {label}: {outcome.why}")
        unrunnable.append(f"{label}: {outcome.why}")
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


def closing_block(unrunnable: Sequence[str],
                  environ: Mapping[str, str] = os.environ) -> tuple[list[str], bool]:
    """The block naming the steps that could not run, and whether they fail the run (Article 6, solorepo's DR-261).

    The block stands outside Article 21's three step shapes, and its detail
    lines are indented by two spaces rather than the five `.meta/gate` reads as
    a problem of the step above it, so the whole block reaches the operator on
    standard error together instead of being split by, or attributed to,
    whichever step happened to be last.

    Args:
        unrunnable: One `"<label>: <why>"` line per step that could not run, in
            the order the gate reported them.
        environ: The environment the `CI` variable is read from.

    Returns:
        tuple[list[str], bool]: The lines to print, which are the same text in
        every environment, and whether they fail the run. They fail where
        `environ` holds a non-empty `CI` and at least one step could not run;
        elsewhere the block is a report and does not fail the run. Empty
        `unrunnable` yields no lines and no failure.
    """
    if not unrunnable:
        return [], False
    lines = [f"?  steps that could not run ({len(unrunnable)}) — zero where a person runs "
             "the gate, non-zero under CI"]
    lines += [f"  {line}" for line in unrunnable]
    return lines, bool(environ.get("CI"))


def main() -> int:
    """Executes prechecks, schema collections, and registered verification steps.

    Catches execution exceptions per step to ensure failures report structured
    diagnostics rather than aborting prematurely (Article 6). Evaluates step
    sources on demand and tallies object indices. A step that could not run
    never ends the traversal, so one pass names every step the environment is
    short of and `closing_block` says whether they fail the run. Schemas that
    will not load are the one exception: every remaining step reads them, so
    the run says what it could not do and stops there, without the block.

    Returns:
        int: 0 where every registered step passed, and where steps that could
        not run were reported outside CI. 1 where any step failed, and where
        any step could not run and the process environment holds a non-empty
        `CI` (Article 6, solorepo's DR-261).
    """
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(line_buffering=True)
    failed = False
    unrunnable: list[str] = []
    for step in [s for s in STEPS if s.pre]:
        try:
            problems = step.run()
        except Exception as exc:
            problems = [f"the check itself could not run — {type(exc).__name__}: {exc}"]
        failed |= report(step.label, problems, unrunnable)
    rest = [s for s in STEPS if not s.pre]
    try:
        schemas = views()
        index, refs, skipped = collect.collect(schemas)
    except Exception as exc:
        print(f"?  schemas: could not load — {type(exc).__name__}: {exc}")
        print(f"     {len(rest)} steps did not run")
        return 1
    for name in skipped:
        failed |= report(name, collect.CouldNotRun("no container accepts its top-level keys"),
                         unrunnable)
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
            report(step.label,
                   collect.CouldNotRun("its source could not be built — "
                                       f"{type(exc).__name__}: {exc}"),
                   unrunnable)
            continue
        try:
            problems = step.run(*given)
        except Exception as exc:
            problems = [f"the check itself could not run — {type(exc).__name__}: {exc}"]
        failed |= report(step.label, problems, unrunnable)
    print(f"\n{len(index)} identified objects, {len(refs)} references")
    block, fatal = closing_block(unrunnable)
    if block:
        print("\n" + "\n".join(block))
    return 1 if failed or fatal else 0


if __name__ == "__main__":
    sys.exit(main())
