#!/usr/bin/env python3
"""The gate for the .meta Project (solorepo's DR-029).

Invariants stated in the schemas and enforceable by none of them. Some cross a
path LinkML cannot traverse; one crosses a file boundary, because two tree roots
are two documents and references between them resolve to nothing a validator will
look at; and three are arithmetic over a list, which a rule cannot count.

    uvx --with linkml --with pyyaml python .meta/check.py

Run `linkml-validate` first — this checks what that cannot, and assumes the
documents are otherwise well formed. It also runs render.py's staleness check, so
one command is the whole gate.

This file is the run. The steps live in `.meta/checks/`, one module per subject
(solorepo's DR-150), and each registers itself at its definition with `@check`,
so there is no table here naming them. Importing a module is what puts its steps
in the registry, so the order of these imports is the order the steps register.
`main()` then prints every precheck first, whatever module it came from, and the
rest in that same registration order. What that comes to: `duplicate keys` and
the probes under `.meta/checks/probes/` (solorepo's DR-209), then the tree, then
what prose claims about it, then what its comments hold, then the graph.
The imports are written in dependency order so that the registration order is
the one stated here and not one a transitive import decided. History in
check.history.md (solorepo's DR-171).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "checks"))

import collect  # noqa: I001  # reason: sys.path modified above and registration order is deliberate
import files
import citations  # noqa: F401  # reason: registers check steps
import comments  # noqa: F401  # reason: registers check steps
import graph  # noqa: F401  # reason: registers check steps
import probes  # noqa: F401  # reason: registers check steps
from collect import STEPS, views


def report(label, outcome):
    """One step, one line, in the shape A21 names (solorepo's DR-092), and its problems or status."""
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


def main():
    """The prechecks, then the schemas, then every other step the registry holds.

    Nothing here dies where it can report instead: a step that cannot run says
    so, and says why, rather than printing a stack trace (Article 6). That
    holds three times over, once at each point where the gate is asked for
    something it may not be able to produce.

    A precheck exists so that one broken thing does not take the gate down
    before the step that names it runs, so a precheck that dies uncaught is
    that same failure with the roles swapped. A schema load that fails names
    how many steps did not run, counted off the registry, because a gate that
    stops early otherwise looks like one that passed. And a step's sources are
    built on first demand rather than up front: the render is the costly one
    and only the last steps read it, so a gate going red on the record does not
    pay for pages nothing asked about.
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
    sources = {"index": lambda: index, "refs": lambda: refs, "views": lambda: schemas,
               "asked": lambda: files.rendering()[0].ASKED,
               "pages": lambda: files.rendering()[1]}
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
