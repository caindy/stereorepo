"""`.meta/audit.py` run against stub gates and the Python standard (stereorepo's DR-353).
"""

import contextlib
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

CRASHED = 2
"""The audit's exit when the gate exited non-zero before reporting a step."""

CASES = (
    ("every step", FULL, 0, 0, ()),
    ("no mutants", tuple(line for line in FULL if line != "ok mutants"), 0, 1,
     ("python-stub-gate-mutants", "Observed Failure")),
    ("no orphans", tuple(line for line in FULL if line != "ok orphans"), 0, 1,
     ("python-stub-gate-orphans", "Literate Programming, Nothing Unconsumed")),
    ("a stray line", (*FULL, "running mutants..."), 0, 1,
     ("python-stub-gate-report-shape", "    running mutants...")),
    ("nothing", (), 0, 1, ("python-stub-gate-reports-nothing",)),
    ("twelve stray lines", (*FULL, *(f"noise {n}" for n in range(12))), 0, 1,
     ("python-stub-gate-report-shape", "    noise 9", "… and 2 more")),
    ("a crash", (), 3, CRASHED, ("audit: python-stub", "exited 3")),
    ("a stray line, then a crash", ("sccache: refused",), 3, CRASHED,
     ("audit: python-stub", "exited 3")),
    ("every step, exiting non-zero", FULL, 1, 0, ()),
)
"""Each case: its name, the lines the stub gate prints, the status the gate exits with, the
exit the audit must give, and the substrings it must print. A case expecting a gap expects
exactly one Issue carrying them; a case expecting `CRASHED` expects no Issue and the
substrings on standard error."""

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


def _stub(lines: tuple[str, ...], status: int) -> dict[str, str]:
    """A Project record whose gate prints `lines`, one to a line, and exits with `status`.

    With no lines the gate runs no `printf`, which given no argument would still
    print one empty line.
    """
    printed = "printf '%s\\n' " + " ".join(shlex.quote(line) for line in lines) + "; "
    return {"id": "work:project/python-stub",
            "gate": (printed if lines else "") + f"exit {status}"}


def _repository(root: pathlib.Path, project: str | None, lines: tuple[str, ...] = (),
                status: int = 0) -> None:
    """Makes `root` a repository asserting `project`, whose gate prints `lines` from a file.

    The gate is `cat report.txt; exit <status>`, and `report.txt` exists only in
    `root`, so the gate reports `lines` only when it runs from `root`. With no
    `project`, `root` gets no `structure.yaml`.
    """
    (root / "report.txt").write_text("".join(f"{line}\n" for line in lines))
    if project is None:
        return
    assertions = root / ".meta" / "assertions"
    assertions.mkdir(parents=True)
    structure = {"projects": [{"id": project, "gate": f"cat report.txt; exit {status}"}]}
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


def _judged(name: str, run: tuple[int | str, str, str], code: int,
            wanted: tuple[str, ...]) -> list[str]:
    """What is wrong with one case's run: its exit, how many Issues it printed, and what they say.

    Args:
        name: The case's name, as each problem names it.
        run: What the audit returned, or the message it exited with; what it
            printed; and what it printed on standard error.
        code: The exit the case expects.
        wanted: The substrings it must print: on standard error, with no Issue,
            when `code` is `CRASHED`; otherwise in its Issues, of which a case
            naming any expects one.

    Returns:
        list[str]: One line per departure, none when the run is as the case expects.
    """
    got, text, error = run
    problems = []
    if got != code:
        problems.append(f"audit: {name}: gave {got!r}, not {code}\n{text}{error}")
    issues = 0 if code == CRASHED else 1 if wanted else None
    if issues is not None and text.count(ISSUE) != issues:
        problems.append(
            f"audit: {name}: printed {text.count(ISSUE)} Issues, not {issues}\n{text}")
    where = error if code == CRASHED else text
    problems += [f"audit: {name}: printed no {part!r}\n{where}"
                 for part in wanted if part not in where]
    return problems


@check("audit probes", pre=True)
def audit_probes() -> list[str]:
    """`.meta/audit.py` passes a stub gate reporting every step the Python standard asks for.

    The stub is a Project record whose `gate` is a `printf` of fixed lines, so
    the audit's own runner, parser and comparison are what is exercised, and
    the Python standard is the record `bootstraps.yaml` holds. A step reported
    failing, or as unable to run, is reported; a step left out is one gap that
    names every Discipline it held; a line in no shape, and a gate that prints
    nothing and exits 0, are each a gap. A gate that exits non-zero having
    reported no step failed to run: the audit says so on standard error with
    the gate's exit code, prints no Issue and gives `CRASHED`, while a gate
    that reported its steps and exits non-zero is compared as usual
    (stereorepo's DR-359). A Project or Bootstrap name that is not asserted
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
    for name, lines, status, code, wanted in CASES:
        said, heard = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(heard):
            got = audit.audit(_stub(lines, status), python, out=said)
        problems += _judged(name, (got, said.getvalue(), heard.getvalue()), code, wanted)
        heard = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(heard):
            root = pathlib.Path(tmp).resolve()
            _repository(root, "work:project/python-stub", lines, status)
            got, text = _elsewhere(audit, root, "python-stub")
        problems += _judged(f"{name}, in another repository", (got, text, heard.getvalue()),
                            code, wanted)

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
