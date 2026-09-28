"""The gate's own steps, run against the answers they exist to give (stereorepo's DR-209).

The invariants under `checks/files/` are run by the gate, so a wrong answer
from one shows as a failure. What this package holds are the answers those
steps read rather than run — `files/python.py`'s ceilings on how long a file
under `.meta/` may run (stereorepo's DR-217). A wrong answer from one shows as a wrong
verdict instead. Each is asked one case at a time, and a failure names
the case. The steps register here rather than beside the checks they exercise,
because the gate over assertions should not take its imports from a test suite
(stereorepo's DR-150). One module per probe, re-exported in the order the steps
report in (stereorepo's DR-218); the re-export is what imports the module and so
what registers its step, which is why this package suppresses nothing.
"""
from checks.probes.files.rendered import rendered_artifact_probes
from checks.probes.files.sizes import SIZE_CASES, SizeCase, file_size_ceiling_probes

__all__ = [
    "SIZE_CASES",
    "SizeCase",
    "file_size_ceiling_probes",
    "rendered_artifact_probes",
]
"""The package's whole surface, so `from checks.probes import files` finds every probe's cases."""
