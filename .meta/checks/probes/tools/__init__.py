"""The tools beside the gate, run against the answers they exist to give (solorepo's DR-209).

`timing.py`'s percentile and its degrade (solorepo's DR-157), `depth.py`'s
four layers (solorepo's DR-188), `agents.py`'s count against the fan-out
ceiling (solorepo's DR-191), `dereference.py`'s scopes and report
(solorepo's DR-134, solorepo's DR-192), `search.py`'s index and benchmark
(solorepo's DR-103), `apm_compile.py`'s byte fallback for a skill file that
is not UTF-8 text (solorepo's DR-208), and the detectors of `comments.py`
that the comment steps read through (solorepo's DR-207). Six are scripts
under `.meta/` that no step of the gate runs, so a wrong answer from one
shows nowhere else; the seventh is read by those steps, so a wrong answer
from it shows as a wrong verdict rather than as a failure. Each is loaded
and asked one case at a time, and a failure names the case. The steps
register here rather than beside the tools they exercise, because the gate
over assertions should not take its imports from a test suite
(solorepo's DR-150). One module per probe, imported in the order the steps report in
(solorepo's DR-218).
"""
import probes.tools.timing  # noqa: I001  # reason: registration order is deliberate
import probes.tools.depth
import probes.tools.agents
import probes.tools.dereference
import probes.tools.search
import probes.tools.apm_compile
import probes.tools.comments  # noqa: F401  # reason: registers check steps
