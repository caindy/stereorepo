"""The tools beside the gate, run against the answers they exist to give (stereorepo's DR-209).

`dereference.py`'s scopes and report
(stereorepo's DR-134, stereorepo's DR-192), `search.py`'s index and benchmark
(stereorepo's DR-103), `apm_compile.py`'s byte fallback for a skill file that
is not UTF-8 text (stereorepo's DR-208), and the detectors of `comments.py`
that the comment steps read through (stereorepo's DR-207), and `.meta/gate`'s
own runner, which every step of every Project reports through
(stereorepo's DR-092), with the specialization and brownfield runners and the
comment detectors. The scripts are ones no step of the gate runs, so a wrong
answer from one shows nowhere else; the detectors are read by those steps, so a wrong answer
from it shows as a wrong verdict rather than as a failure. Each is loaded
and asked one case at a time, and a failure names the case. The steps
register here rather than beside the tools they exercise, because the gate
over assertions should not take its imports from a test suite
(stereorepo's DR-150). One module per probe, imported in the order the steps report in
(stereorepo's DR-218).
"""
import checks.probes.tools.dereference  # noqa: I001  # reason: registration order is deliberate
import checks.probes.tools.search
import checks.probes.tools.apm_compile
import checks.probes.tools.terms
import checks.probes.tools.test_specialization
import checks.probes.tools.test_brownfield
import checks.probes.tools.gate
import checks.probes.tools.comments  # noqa: F401  # reason: registers check steps
