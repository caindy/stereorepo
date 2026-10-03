"""The tools beside the gate, run against the answers they exist to give (stereorepo's DR-342).

`dereference.py`'s scopes and report (stereorepo's DR-332, stereorepo's DR-336),
`search.py`'s index and benchmark (stereorepo's DR-103), `apm_compile.py`'s byte
fallback for a skill file that is not UTF-8 text (stereorepo's DR-208), `render.py`'s
writes under a sandbox that denies one of them (stereorepo's DR-302), and the
detectors of `comments.py` that the comment steps read through (stereorepo's DR-207),
and `.meta/gate`'s own runner, which every step of every Project reports through
(stereorepo's DR-092), `audit.py`'s comparison of a gate with a Bootstrap
(stereorepo's DR-353), with the specialization and brownfield runners, the comment
detectors, `bundle.py sync` (stereorepo's DR-315), and `release.py`
(stereorepo's DR-320). The scripts are ones no step of the gate runs, so a wrong
answer from one shows nowhere else; the detectors are read by those steps, so a wrong
answer from it shows as a wrong verdict rather than as a failure. Each is loaded and
asked one case at a time, and a failure names the case. The steps register here rather
than beside the tools they exercise, because the gate over assertions should not take
its imports from a test suite (stereorepo's DR-150). One module per probe,
imported in the order the steps report in (stereorepo's DR-345).
`test_brownfield` and `audit` are scaffold-only, so they are imported last and only where
present: a specialized portfolio has no adoption tool for the one to probe, and no Bootstrap
records for the other to audit against (stereorepo's DR-305, stereorepo's DR-353).
"""
import importlib  # noqa: I001  # reason: registration order is deliberate
import pathlib

import checks.probes.tools.dereference
import checks.probes.tools.search
import checks.probes.tools.apm_compile
import checks.probes.tools.render
import checks.probes.tools.terms
import checks.probes.tools.test_specialization
import checks.probes.tools.gate
import checks.probes.tools.comments
import checks.probes.tools.sync
import checks.probes.tools.release  # noqa: F401  # reason: registers check steps

SCAFFOLD_ONLY = ("test_brownfield", "audit")
"""The probes a specialized portfolio does not hold, imported after the rest where present."""

for _probe in SCAFFOLD_ONLY:
    if (pathlib.Path(__file__).parent / f"{_probe}.py").is_file():
        importlib.import_module(f"checks.probes.tools.{_probe}")
