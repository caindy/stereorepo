#!/usr/bin/env -S uvx --python 3.13 --with pyyaml python
"""Audit of a Project's gate against a Bootstrap (stereorepo's DR-312, stereorepo's DR-353).

Takes a Project and a Bootstrap by the last segment of their ids, runs the
Project's gate as `.meta/assertions/structure.yaml` declares it, and compares
what the gate reports on standard output with what the Bootstrap asks: every
step named in the `held_by` list of an implemented Discipline, each reported in one of
Article 21's shapes (stereorepo's DR-092). Each gap is printed as the text of
an Issue for `issues/backlog/`, and the audit exits non-zero when there is
one. It compares step names and report shape only; whether a step passes, or
does what the Bootstrap's step does, is the gate's business and the
developer's.
"""
from __future__ import annotations

import dataclasses
import pathlib
import subprocess
import sys
from collections.abc import Iterable
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from typing import IO, Any

import yaml

META = pathlib.Path(__file__).resolve().parent
BOOTSTRAPS = META / "assertions" / "bootstraps.yaml"
DISCIPLINES = META / "assertions" / "imported" / "disciplines.yaml"

QUOTED = 10
"""How many lines out of shape an Issue quotes: enough to show what leaks, not the whole run."""

NO_SPEC = "no module spec for {path}"
"""What loading `.meta/gate` raises where `importlib` declines to describe it as a module."""

_LOADER = SourceFileLoader("meta_gate", str(META / "gate"))
_SPEC = spec_from_loader("meta_gate", _LOADER)
if _SPEC is None:
    raise ImportError(NO_SPEC.format(path=META / "gate"))
gate = module_from_spec(_SPEC)
"""`.meta/gate`, whose patterns are the contract's shapes and whose loader reads the Projects."""
_LOADER.exec_module(gate)


@dataclasses.dataclass(frozen=True)
class Gap:
    """One departure from the Bootstrap, as the Issue that would close it."""

    slug: str
    title: str
    body: str


def reported(lines: Iterable[str]) -> tuple[set[str], list[str]]:
    """Reads a gate's standard output into the steps it reported and the lines in no shape.

    A step counts whatever its mark: `ok`, `x` and `?` all report it. A
    five-space-indented problem line is in shape only beneath an `x` report or
    another problem line, as `.meta/gate` reads it. A blank line is neither.

    Args:
        lines: The gate's standard output, one line per item, newlines optional.

    Returns:
        tuple[set[str], list[str]]: The names of the reported steps, and the
            lines in none of Article 21's shapes, in the order printed.
    """
    steps: set[str] = set()
    stray: list[str] = []
    under_failure = False
    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip():
            under_failure = False
            continue
        if (m := gate.X.match(line)):
            steps.add(m["step"])
            under_failure = True
            continue
        if under_failure and gate.PROBLEM.match(line):
            continue
        under_failure = False
        if (m := gate.COULD_NOT.match(line) or gate.OK.match(line)):
            steps.add(m["step"])
        else:
            stray.append(line)
    return steps, stray


def held(bootstrap: dict[str, Any]) -> dict[str, list[str]]:
    """Maps each step the Bootstrap asks for to the Disciplines it holds.

    Args:
        bootstrap: A record from `.meta/assertions/bootstraps.yaml`.

    Returns:
        dict[str, list[str]]: Each step named in the `held_by` list of an
            implemented Discipline, in first-named order, to the ids of the
            Disciplines naming it. An exempt Discipline asks nothing and names none.
    """
    steps: dict[str, list[str]] = {}
    for implementation in bootstrap.get("discipline_implementations") or []:
        if implementation.get("status") != "implemented":
            continue
        for step in implementation.get("held_by") or []:
            steps.setdefault(step, []).append(implementation["discipline"])
    return steps


def discipline_names() -> dict[str, str]:
    """The display name of every Discipline, keyed by its id."""
    data = yaml.safe_load(DISCIPLINES.read_text()) or {}
    return {d["id"]: d["name"] for d in data.get("disciplines") or []}


def _named(ident: str, names: dict[str, str]) -> str:
    """A Discipline's display name, else its id's last segment in title case."""
    return names.get(ident) or gate.short(ident).replace("-", " ").title()


def gaps(
    project: dict[str, Any],
    bootstrap: dict[str, Any],
    lines: Iterable[str],
    names: dict[str, str] | None = None,
) -> list[Gap]:
    """Compares one run of a Project's gate with a Bootstrap.

    A gate that reported no step is one gap, and the steps it did not report
    are not listed besides: every one of them would be. Otherwise each step the
    Bootstrap asks for and the gate did not report is one gap, naming every
    Discipline it leaves unheld. The lines in no shape are one gap together,
    however many there are, quoting the first `QUOTED` of them.

    Args:
        project: A Project record, read for its id.
        bootstrap: A Bootstrap record, read for its id and its Disciplines.
        lines: The gate's standard output.
        names: Discipline display names by id; read from the assertions when omitted.

    Returns:
        list[Gap]: The gaps, missing steps first in the Bootstrap's order,
            then the lines out of shape.
    """
    names = discipline_names() if names is None else names
    who = gate.short(project["id"])
    standard = bootstrap.get("name") or gate.short(bootstrap["id"])
    steps, stray = reported(lines)
    found: list[Gap] = []
    if not steps:
        found.append(Gap(
            f"{who}-gate-reports-nothing",
            f"Make {who}'s gate report its steps",
            f"{standard} asks for steps that {who}'s gate cannot be seen to run: it printed "
            "no line in any of Article 21's three shapes, `ok <step>`, `x  <step> (<count>)` "
            "or `?  <step>: <why>` (stereorepo's DR-092).",
        ))
    else:
        for step, disciplines in held(bootstrap).items():
            if step in steps:
                continue
            serves = ", ".join(_named(d, names) for d in disciplines)
            found.append(Gap(
                f"{who}-gate-{step}",
                f"Add a `{step}` step to {who}'s gate",
                f"{standard} holds {serves} with a gate step named `{step}`, and "
                f"{who}'s gate does not report one. Add the step, or record why {who} holds "
                f"{serves} another way (stereorepo's DR-312).",
            ))
    if stray:
        listed = "\n".join(f"    {line}" for line in stray[:QUOTED])
        if len(stray) > QUOTED:
            listed += f"\n    … and {len(stray) - QUOTED} more"
        found.append(Gap(
            f"{who}-gate-report-shape",
            f"Bring {who}'s gate output into Article 21's shapes",
            f"{who}'s gate printed {len(stray)} line{'s' if len(stray) != 1 else ''} on standard "
            "output in none of Article 21's shapes (stereorepo's DR-092), which `.meta/gate` "
            f"cannot read as a step report:\n\n{listed}\n\nReport each step as `ok <step>`, "
            "`x  <step> (<count>)` with five-space-indented problems, or `?  <step>: <why>`, "
            "and send anything else to standard error.",
        ))
    return found


def issue(gap: Gap) -> str:
    """The text of the Issue that would close `gap`, headed by the comment naming its file."""
    return (f"<!-- issues/backlog/{gap.slug}.md -->\n# {gap.title}\n\n{gap.body}\n\n"
            "Found by `just audit` (stereorepo's DR-312, stereorepo's DR-353).\n")


def audit(project: dict[str, Any], bootstrap: dict[str, Any], out: IO[str] = sys.stdout) -> int:
    """Runs a Project's gate from the repository root and prints each gap as an Issue.

    The gate's standard error passes through, and its exit code is not read: a
    failing step is still a reported one.

    Args:
        project: A Project record carrying the `gate` command.
        bootstrap: The Bootstrap record to compare it with.
        out: Where the Issues are printed.

    Returns:
        int: 1 if there is a gap, otherwise 0.
    """
    run = subprocess.run(project["gate"], shell=True, cwd=gate.ROOT, text=True,
                         stdout=subprocess.PIPE, check=False)
    found = gaps(project, bootstrap, run.stdout.splitlines())
    out.write("\n".join(issue(gap) for gap in found))
    return 1 if found else 0


def main(argv: list[str], projects: dict[str, dict[str, Any]] | None = None) -> int:
    """CLI entrypoint: `audit.py <project> <bootstrap>`.

    Args:
        argv: The script name, then a Project's and a Bootstrap's name.
        projects: The asserted Projects keyed by id, as `.meta/gate` reads them;
            read from `structure.yaml` when omitted.

    Returns:
        int: 0 with no gap, 1 with one; an unknown name or a Project with no
            gate exits through `sys.exit` with a message.
    """
    if len(argv) != 3:
        sys.exit("usage: audit.py <project> <bootstrap>")
    asserted = gate.structure()[0] if projects is None else projects
    by_name = {gate.short(p["id"]): p for p in asserted.values()}
    data = yaml.safe_load(BOOTSTRAPS.read_text()) or {}
    bootstraps = {gate.short(b["id"]): b for b in data.get("bootstraps") or []}
    project, bootstrap = by_name.get(argv[1]), bootstraps.get(argv[2])
    if project is None:
        sys.exit(f"audit: no Project {argv[1]} is asserted; there are {', '.join(by_name)}")
    if bootstrap is None:
        sys.exit(f"audit: no Bootstrap {argv[2]} is asserted; there are {', '.join(bootstraps)}")
    if not project.get("gate"):
        sys.exit(f"audit: {argv[1]} asserts no gate, so there is nothing to audit")
    return audit(project, bootstrap)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
