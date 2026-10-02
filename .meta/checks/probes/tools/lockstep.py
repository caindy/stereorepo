"""Each Python Project's gate package, in lockstep with `comments.py` (stereorepo's DR-305).

A Project's `uv run gate` keeps its own copy of the keep-exceptions,
suppression patterns and statement detectors, so that it and the root gate
give one verdict on one comment. The `comment probes` step asks every copy.
"""
import pathlib
import re
import tempfile
from typing import Any

import yaml

from checks.collect import ROOT, Found, Passed, StepOutcome
from checks.probes.harness import load_module

GATE_PACKAGE = pathlib.Path("gate") / "src" / "gate" / "__init__.py"
"""Where, below a Python Project's directory, its gate keeps a copy of `comments.py`'s detectors."""

AGREEING_GATE = (
    "from checks.comments import (CITATION, DIRECTIVE, NOQA, NOTICE, STATEMENTS, TYPE_IGNORE,\n"
    "                             keep_exception, python_code)\n"
)
"""A stub gate package in lockstep with `comments.py` by construction."""

DISAGREEING_GATE = AGREEING_GATE + "import re\nNOQA = re.compile('noqa')\n"
"""The stub with a `NOQA` pattern of its own, which the lockstep must catch."""

INCOMPLETE_GATE = "from checks.comments import CITATION, DIRECTIVE, NOQA, NOTICE, TYPE_IGNORE\n"
"""A stub gate package with the patterns and none of the detectors."""

PATTERNS = ("DIRECTIVE", "NOTICE", "CITATION", "NOQA", "TYPE_IGNORE")
"""The compiled patterns a gate package shares with `comments.py`, compared by source."""

DETECTORS = ("STATEMENTS", "keep_exception", "python_code")
"""The other names a gate package shares with `comments.py`, compared by value or by answer."""


def python_gates(root: pathlib.Path = ROOT) -> list[tuple[str, pathlib.Path]]:
    """The Python Projects that have a gate package, each with the package's `__init__.py`.

    Read from `structure.yaml` directly, since the step runs before the
    assertions load. A Project's `name` is its directory, and its `language`
    is exactly `Python`: the `meta` Project, whose language names Python
    among others, has no gate package of this shape.

    Args:
        root: The repository whose `.meta/assertions/structure.yaml` is read.

    Returns:
        list[tuple[str, pathlib.Path]]: `(Project name, gate package file)`, in
        the order `structure.yaml` asserts them.
    """
    structure = root / ".meta" / "assertions" / "structure.yaml"
    if not structure.is_file():
        return []
    projects = (yaml.safe_load(structure.read_text(encoding="utf-8")) or {}).get("projects") or []
    return [(project["name"], root / project["name"] / GATE_PACKAGE) for project in projects
            if project.get("language") == "Python" and project.get("name")
            and (root / project["name"] / GATE_PACKAGE).is_file()]


def lockstep(comments: Any, root: pathlib.Path) -> tuple[list[str], list[str]]:
    """What the Python Projects' gate packages disagree with `comments.py` on, and who was asked."""
    gates = python_gates(root)
    problems = [line for project, gate_file in gates
                for line in gate_sync(comments, project, gate_file)]
    return problems, [project for project, _ in gates]


def verdict(problems: list[str], projects: list[str]) -> StepOutcome:
    """What `comment probes` comes to: every problem found, or the Projects kept in lockstep."""
    if problems:
        return Found(problems)
    if not projects:
        return Passed("every detector; no Python Project has a gate package to keep in lockstep")
    return Passed(f"every detector, in lockstep with the gate of {', '.join(projects)}")


def lockstep_probes(comments: Any) -> list[str]:
    """The lockstep over two agreeing gate packages, one disagreeing, one incomplete, then none."""
    problems = []
    with tempfile.TemporaryDirectory() as tmp_str:
        root = pathlib.Path(tmp_str)
        (root / ".meta" / "assertions").mkdir(parents=True)
        (root / ".meta" / "assertions" / "structure.yaml").write_text(yaml.safe_dump({"projects": [
            {"name": "one", "language": "Python"}, {"name": "two", "language": "Python"},
            {"name": "crate", "language": "Rust"}, {"name": "bare", "language": "Python"}]}))
        for project in ("one", "two", "crate"):
            (root / project / GATE_PACKAGE).parent.mkdir(parents=True)
            (root / project / GATE_PACKAGE).write_text(AGREEING_GATE)

        synced, projects = lockstep(comments, root)
        if synced or projects != ["one", "two"]:
            problems.append(f"comment probes: two agreeing Python gates came to {synced!r} over "
                            f"{projects!r}, expected nothing over ['one', 'two']")
        shown = verdict(synced, projects)
        if not isinstance(shown, Passed) or "one, two" not in shown.scope:
            problems.append(f"comment probes: two agreeing Python gates came to {shown!r}, "
                            "expected a pass naming both")

        (root / "two" / GATE_PACKAGE).write_text(DISAGREEING_GATE)
        synced, _ = lockstep(comments, root)
        if not synced or not all("two's" in line and "one's" not in line for line in synced):
            problems.append(f"comment probes: a disagreeing gate in `two` came to {synced!r}, "
                            "expected failures naming `two` alone")

        (root / "two" / GATE_PACKAGE).write_text(INCOMPLETE_GATE)
        synced, _ = lockstep(comments, root)
        if synced != ["comment probes: two's gate is missing " + ", ".join(DETECTORS)]:
            problems.append(f"comment probes: a gate in `two` without the detectors came to "
                            f"{synced!r}, expected one failure naming `two` and what it lacks")

        for project in ("one", "two"):
            (root / project / GATE_PACKAGE).unlink()
        synced, projects = lockstep(comments, root)
        shown = verdict(synced, projects)
        if projects or not isinstance(shown, Passed) or "no Python Project" not in shown.scope:
            problems.append(f"comment probes: no Python gate package came to {shown!r} over "
                            f"{projects!r}, expected a pass saying there is none")
    return problems


def gate_sync(comments: Any, project: str, gate_file: pathlib.Path) -> list[str]:
    """Asserts that one Project's gate package matches comments.py, pattern for pattern.

    The package is loaded afresh from its file under a name of the Project's
    own, so one Project's `gate` never answers for another's. A package that
    will not load, or lacks one of the names compared, is a failure naming the
    Project rather than an error that stops the step.
    """
    try:
        gate: Any = load_module(gate_file, "lockstep_gate_" + re.sub(r"\W", "_", project))
    except (ImportError, SyntaxError) as error:
        return [f"comment probes: could not import {project}'s gate — {error}"]
    missing = [name for name in (*PATTERNS, *DETECTORS) if not hasattr(gate, name)]
    if missing:
        return [f"comment probes: {project}'s gate is missing {', '.join(missing)}"]
    problems = []
    for name in PATTERNS:
        meta_re = getattr(comments, name)
        gate_re = getattr(gate, name)
        if meta_re.pattern != gate_re.pattern:
            problems.append(
                f"comment probes: {project}'s gate {name}.pattern differs from comments.py: "
                f"{gate_re.pattern!r} != {meta_re.pattern!r}"
            )

    if gate.STATEMENTS != comments.STATEMENTS:
        problems.append(f"comment probes: {project}'s gate STATEMENTS differs from comments.py")

    for sample in (
        "x = compute(1)",
        "return None",
        "noqa: F401",
        "Copyright 2026 the author",
        "see stereorepo's DR-171",
        "narration inside body",
        "value = 1  # noqa",
    ):
        meta_keep = comments.keep_exception(sample)
        gate_keep = gate.keep_exception(sample)
        if meta_keep != gate_keep:
            problems.append(
                f"comment probes: {project}'s gate keep_exception({sample!r}) disagreed: "
                f"gate={gate_keep!r}, meta={meta_keep!r}"
            )
        meta_code = comments.python_code(sample)
        gate_code = gate.python_code(sample)
        if meta_code != gate_code:
            problems.append(
                f"comment probes: {project}'s gate python_code({sample!r}) disagreed: "
                f"gate={gate_code!r}, meta={meta_code!r}"
            )

    return problems
