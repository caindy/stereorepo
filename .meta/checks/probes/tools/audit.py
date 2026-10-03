"""`.meta/audit.py` run against stub gates and the Python standard (stereorepo's DR-353).
"""

import io
import pathlib
import shlex
import tempfile
from typing import Any

import yaml

from checks.collect import META, check
from checks.probes.harness import load_module

FULL = ("ok lints — 3 files", "ok ruff", "x  types (2)", "     a.py:1 error",
        "     b.py:2 error", "?  doc: no tool", "ok test", "ok orphans", "ok evidence",
        "ok mutants", "ok render")
"""A stub gate reporting every step the Python standard's `held_by` lists name, one of them
failing with its problem lines and one unable to run: every step is reported all the same."""

CASES = (
    ("every step", FULL, 0, ()),
    ("no mutants", tuple(line for line in FULL if line != "ok mutants"), 1,
     ("python-stub-gate-mutants", "Observed Failure")),
    ("no orphans", tuple(line for line in FULL if line != "ok orphans"), 1,
     ("python-stub-gate-orphans", "Literate Programming, Nothing Unconsumed")),
    ("a stray line", (*FULL, "running mutants..."), 1,
     ("python-stub-gate-report-shape", "    running mutants...")),
    ("nothing", (), 1, ("python-stub-gate-reports-nothing",)),
    ("twelve stray lines", (*FULL, *(f"noise {n}" for n in range(12))), 1,
     ("python-stub-gate-report-shape", "    noise 9", "… and 2 more")),
)
"""Each case: its name, the lines the stub gate prints, the exit the audit must give, and the
substrings its printed Issues must carry. A case expecting a gap expects exactly one."""

UNKNOWN = (
    ("an unknown Project", ["audit.py", "no-such-project", "python"], None,
     ("no-such-project", "meta")),
    ("an unknown Bootstrap", ["audit.py", "meta", "no-such-bootstrap"], None,
     ("no-such-bootstrap", "python")),
    ("a Project with no gate", ["audit.py", "gateless", "python"],
     {"work:project/gateless": {"id": "work:project/gateless"}}, ("gateless", "no gate")),
)
"""Each case: its name, the arguments put to `main`, the Projects it is handed in place of the
asserted ones (`None` for those), and the substrings its exit message must carry, which are
the name refused and, for an unknown name, one that is asserted. None runs a gate."""

ELSEWHERE = (
    ("a repository with no structure.yaml", None, "python-stub", ("structure.yaml",)),
    ("a repository not asserting the Project", "work:project/other", "python-stub",
     ("python-stub", "other")),
)
"""Each case: its name, the one Project the target repository asserts (`None` for no
`structure.yaml` at all), the Project audited, and the substrings its exit message must carry
besides the target's path."""

ISSUE = "<!-- issues/backlog/"
"""What heads each Issue the audit prints, so counting it counts the gaps."""


def _stub(lines: tuple[str, ...]) -> dict[str, str]:
    """A Project record whose gate prints `lines`, one to a line, and nothing else."""
    command = "printf '%s\\n' " + " ".join(shlex.quote(line) for line in lines)
    return {"id": "work:project/python-stub", "gate": command if lines else "true"}


def _repository(root: pathlib.Path, project: str | None, lines: tuple[str, ...] = ()) -> None:
    """Makes `root` a repository asserting `project`, whose gate prints `lines` from a file.

    The gate is `cat report.txt`, and `report.txt` exists only in `root`, so the
    gate reports `lines` only when it runs from `root`. With no `project`,
    `root` gets no `structure.yaml`.
    """
    (root / "report.txt").write_text("".join(f"{line}\n" for line in lines))
    if project is None:
        return
    assertions = root / ".meta" / "assertions"
    assertions.mkdir(parents=True)
    structure = {"projects": [{"id": project, "gate": "cat report.txt"}]}
    (assertions / "structure.yaml").write_text(yaml.safe_dump(structure))


def _elsewhere(audit: Any, root: pathlib.Path, project: str) -> tuple[int | str, str]:
    """Audits `project` in the repository at `root` through `main`, against the Python standard.

    Returns:
        tuple[int | str, str]: What `main` returned, or the message it exited with,
            and what it printed.
    """
    said = io.StringIO()
    try:
        got = audit.main(["audit.py", project, "python", "--repository", str(root)], out=said)
    except SystemExit as stop:
        return str(stop.code), said.getvalue()
    return got, said.getvalue()


def _judged(name: str, got: int | str, text: str, code: int,
            wanted: tuple[str, ...]) -> list[str]:
    """What is wrong with one case's run: its exit, how many Issues it printed, and what they say.

    Args:
        name: The case's name, as each problem names it.
        got: What the audit returned, or the message it exited with.
        text: What it printed.
        code: The exit the case expects.
        wanted: The substrings its Issues must carry; a case naming any expects one Issue.

    Returns:
        list[str]: One line per departure, none when the run is as the case expects.
    """
    problems = []
    if got != code:
        problems.append(f"audit: {name}: gave {got!r}, not {code}\n{text}")
    if wanted and text.count(ISSUE) != 1:
        problems.append(f"audit: {name}: printed {text.count(ISSUE)} Issues, not 1\n{text}")
    problems += [f"audit: {name}: printed no {part!r}\n{text}"
                 for part in wanted if part not in text]
    return problems


@check("audit probes", pre=True)
def audit_probes() -> list[str]:
    """`.meta/audit.py` passes a stub gate reporting every step the Python standard asks for.

    The stub is a Project record whose `gate` is a `printf` of fixed lines, so
    the audit's own runner, parser and comparison are what is exercised, and
    the Python standard is the record `bootstraps.yaml` holds. A step reported
    failing, or as unable to run, is reported; a step left out is one gap that
    names every Discipline it held; a line in no shape, and a gate that prints
    nothing, are each a gap. A Project or Bootstrap name that is not asserted
    ends `main` with a message naming the ones that are, and so does a Project
    asserting no gate.

    Every case is run again through `main --repository` against a temporary
    repository whose gate prints the case's lines from a file only that
    repository holds, so it finds the same gaps only if the gate runs there. A
    target with no `structure.yaml`, or one not asserting the Project, ends
    `main` with a message naming the target.
    """
    try:
        audit = load_module(META / "audit.py", "audit")
    except Exception as exc:  # noqa: BLE001  # reason: names the failure, not a traceback
        return [f"audit: .meta/audit.py did not load — {type(exc).__name__}: {exc}"]
    records = yaml.safe_load((META / "assertions" / "bootstraps.yaml").read_text())["bootstraps"]
    python = next(b for b in records if b["id"] == "work:bootstrap/python")

    problems = []
    for name, lines, code, wanted in CASES:
        said = io.StringIO()
        got = audit.audit(_stub(lines), python, out=said)
        problems += _judged(name, got, said.getvalue(), code, wanted)
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            _repository(root, "work:project/python-stub", lines)
            got, text = _elsewhere(audit, root, "python-stub")
        problems += _judged(f"{name}, in another repository", got, text, code, wanted)

    for name, argv, projects, wanted in UNKNOWN:
        try:
            audit.main(argv, projects)
        except SystemExit as stop:
            message = str(stop.code)
            problems += [f"audit: {name}: exit message {message!r} carries no {part!r}"
                         for part in wanted if part not in message]
        else:
            problems.append(f"audit: {name}: main returned rather than exiting with a message")

    for name, asserted, project, wanted in ELSEWHERE:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            _repository(root, asserted)
            got, _ = _elsewhere(audit, root, project)
        if not isinstance(got, str):
            problems.append(f"audit: {name}: main returned {got} rather than exiting with a "
                            "message")
            continue
        problems += [f"audit: {name}: exit message {got!r} carries no {part!r}"
                     for part in (str(root), *wanted) if part not in got]
    return problems
