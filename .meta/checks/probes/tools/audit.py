"""`.meta/audit.py` run against stub gates and the Python standard (stereorepo's DR-353).
"""

import io
import shlex

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

ISSUE = "<!-- issues/backlog/"
"""What heads each Issue the audit prints, so counting it counts the gaps."""


def _stub(lines: tuple[str, ...]) -> dict[str, str]:
    """A Project record whose gate prints `lines`, one to a line, and nothing else."""
    command = "printf '%s\\n' " + " ".join(shlex.quote(line) for line in lines)
    return {"id": "work:project/python-stub", "gate": command if lines else "true"}


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
        text = said.getvalue()
        if got != code:
            problems.append(f"audit: {name}: exited {got}, not {code}\n{text}")
        if wanted and text.count(ISSUE) != 1:
            problems.append(f"audit: {name}: printed {text.count(ISSUE)} Issues, not 1\n{text}")
        problems += [f"audit: {name}: printed no {part!r}\n{text}"
                     for part in wanted if part not in text]

    for name, argv, projects, wanted in UNKNOWN:
        try:
            audit.main(argv, projects)
        except SystemExit as stop:
            message = str(stop.code)
            problems += [f"audit: {name}: exit message {message!r} carries no {part!r}"
                         for part in wanted if part not in message]
        else:
            problems.append(f"audit: {name}: main returned rather than exiting with a message")
    return problems
