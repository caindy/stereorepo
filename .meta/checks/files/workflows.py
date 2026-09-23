"""
What the workflows and the scaffold owe each other: no scaffold-only path in an
inherited file, and the two gate workflows held equal.

Where a workflow is, is stated once here. `WORKFLOWS`, `REVIEW_WORKFLOW` and
`workflow_files()` are read by the families registered after this one —
`control_plane`, `harness`, `reviewer` and `inline_python` — so that a family
added later finds the workflows rather than gathering them again
(solorepo's DR-218).

History in files.history.md (solorepo's DR-171).
"""

import pathlib
from collections.abc import Sequence
from typing import Any

import yaml

from checks.collect import (
    META,
    ROOT,
    TEMPLATE,
    CouldNotRun,
    Found,
    Passed,
    StepOutcome,
    check,
)
from checks.files import sources

SCAFFOLD_ONLY = ("template/", "SPECIALIZE.md", "bootstraps/")


WORKFLOWS = ROOT / ".github" / "workflows"
"""Where this repository's workflows live, the loops among them."""


REVIEW_WORKFLOW = WORKFLOWS / "review.yml"
"""The reviewer workflow, which restores the control plane from trunk before a reviewer reads anything."""


def workflow_files() -> set[pathlib.Path]:
    """Every GitHub Actions workflow and composite action file the tree holds.

    Three directories can hold one: this repository's own workflows, the
    workflows a Specialization seeds, and the composite actions under
    `.meta/actions/`. A directory the tree does not have is skipped rather than
    reported, so a portfolio that seeds no workflows still scans its own.

    Returns:
        set[pathlib.Path]: Each `.yml` or `.yaml` file under those directories,
        unordered; the callers sort what they report.
    """
    files: set[pathlib.Path] = set()
    candidate_dirs = (WORKFLOWS, TEMPLATE / ".github" / "workflows", META / "actions")
    for directory in candidate_dirs:
        if directory.is_dir():
            files.update(path for path in directory.rglob("*")
                         if path.suffix in (".yml", ".yaml") and path.is_file())
    return files


@check("scaffold-only paths")
def scaffold_only_paths() -> StepOutcome:
    """Validate that documentation and workflows copied during Specialization contain no scaffold-only paths.

    Ensures that inherited files do not reference paths unique to solorepo (`template/`,
    `SPECIALIZE.md`, `bootstraps/`) unless explicitly qualified with a `solorepo` owner reference (solorepo's DR-036, solorepo's DR-115).

    Returns:
        Passed | Found | CouldNotRun: Validation result listing occurrences of scaffold-only paths.
    """
    problems: list[str] = []
    scanned: set[pathlib.Path] = set()

    def scan(paths: Sequence[pathlib.Path], names: Sequence[str]) -> None:
        for path in paths:
            if path.suffix not in (".md", ".yaml", ".yml") or not path.is_file():
                continue
            scanned.add(path)
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if "solorepo" in line.lower():
                    continue
                for name in names:
                    if name in line:
                        problems.append(f"{path.relative_to(ROOT)}:{number} names "
                                        f"'{name}', which a portfolio does not have")

    for token in sources.inherited():
        base = ROOT / token if (ROOT / token).exists() else META / token
        paths = [base] if base.is_file() else sorted(base.rglob("*")) if base.is_dir() else []
        scan(paths, SCAFFOLD_ONLY)
    scan(sorted(TEMPLATE.rglob("*")), tuple(n for n in SCAFFOLD_ONLY if n != "template/"))

    if not scanned:
        return CouldNotRun("no inherited paths or template/ to scan")
    if problems:
        return Found(problems)
    return Passed(f"{len(scanned)} file{'s' if len(scanned) != 1 else ''}")


# The half the two gate workflows share, by job (solorepo's DR-119): each of these is in
# both files and equal across them. The seed's own job is `gate` (solorepo's DR-115), and
# the scaffold's seed jobs are its alone.
SHARED_JOBS = ("pull-request", "sweep")


SEED_OWN_JOBS = ("gate",)


# Except where the job runs (solorepo's DR-140). This repository's gate runs on a
# self-hosted scale set that exists on one machine; a fresh clone has no cluster
# and every runner GitHub will give it. That is a fact about the machine each
# repository has, not about what the job does, and holding it equal would force
# one of the two to name a runner it does not have.
NOT_SHARED = ("runs-on",)


def _first_difference(a: Any, b: Any, path: str) -> tuple[str, str] | None:
    """Where two loaded YAML values first differ, as a dotted path, or None."""
    if isinstance(a, dict) and isinstance(b, dict):
        for key in list(a) + [k for k in b if k not in a]:
            if key not in a or key not in b:
                return f"{path}.{key}", "only on one side"
            found = _first_difference(a[key], b[key], f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(a, list) and isinstance(b, list):
        for i, (x, y) in enumerate(zip(a, b, strict=False)):
            found = _first_difference(x, y, f"{path}[{i}]")
            if found:
                return found
        if len(a) != len(b):
            return f"{path}[{min(len(a), len(b))}]", "only on one side"
        return None
    return None if a == b else (path, f"{a!r} against {b!r}")


@check("gate workflows agree")
def gate_workflows_agree() -> StepOutcome:
    """Validate that the root gate workflow and seeded template workflow agree on shared jobs.

    Verifies structural and semantic parity across triggers, permissions, and shared jobs
    (`pull-request`, `sweep`) between `.github/workflows/gate.yml` and `template/.github/workflows/gate.yml` (solorepo's DR-115, solorepo's DR-119, solorepo's DR-140).

    Returns:
        Passed | Found | CouldNotRun: Validation result detailing any discrepancy between shared workflow halves.

    The `on` key is read under the boolean `True` before its own name: YAML 1.1
    reads a bare `on` as a boolean and pyyaml is a 1.1 parser, so a workflow
    written the ordinary way arrives with `True` for a key.
    """
    ours = ROOT / ".github" / "workflows" / "gate.yml"
    seed = TEMPLATE / ".github" / "workflows" / "gate.yml"
    if not (ours.is_file() and seed.is_file()):
        return CouldNotRun("either ours or template workflow is absent")
    a = yaml.safe_load(ours.read_text()) or {}
    b = yaml.safe_load(seed.read_text()) or {}
    shared: dict[str, tuple[Any, Any]] = {
        "on": (a.get(True, a.get("on")), b.get(True, b.get("on"))),
        "permissions": (a.get("permissions"), b.get("permissions"))}
    jobs_a, jobs_b = a.get("jobs") or {}, b.get("jobs") or {}
    problems = []
    for name in SHARED_JOBS:
        for path, jobs in ((ours, jobs_a), (seed, jobs_b)):
            if name not in jobs:
                problems.append(f"jobs.{name}: not in {path.relative_to(ROOT)}, "
                                "and it is a job both gate workflows define")
        if name in jobs_a and name in jobs_b:
            halves = [{k: v for k, v in jobs[name].items() if k not in NOT_SHARED}
                      for jobs in (jobs_a, jobs_b)]
            shared[f"jobs.{name}"] = (halves[0], halves[1])
    for name in jobs_b:
        if name not in SHARED_JOBS + SEED_OWN_JOBS:
            problems.append(f"jobs.{name}: in {seed.relative_to(ROOT)} and neither shared "
                            f"nor the seed's own; the seed's jobs are {', '.join(SEED_OWN_JOBS)} "
                            f"and the shared {', '.join(SHARED_JOBS)}")
    for label, (x, y) in shared.items():
        found = _first_difference(x, y, label)
        if found:
            where, how = found
            problems.append(f"{where}: {how} — {ours.relative_to(ROOT)} and "
                            f"{seed.relative_to(ROOT)} share this half, and it is held equal")
    if problems:
        return Found(problems)
    return Passed(f"{ours.relative_to(ROOT)} and {seed.relative_to(ROOT)} agree")
