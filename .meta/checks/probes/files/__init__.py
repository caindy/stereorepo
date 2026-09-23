"""The gate's own steps, run against the answers they exist to give (solorepo's DR-209).

The invariants under `checks/files/` are run by the gate, so a wrong answer
from one shows as a failure. What this package holds are the answers those
steps read rather than run — `files/python.py`'s ceilings on how long a file
under `.meta/` may run (solorepo's DR-217) — and the steps the gate runs on
almost no branch, where a failure would otherwise wait for the evening
somebody coins a word (solorepo's DR-276). A wrong answer from either shows as
a wrong verdict instead. Each is asked one case at a time, and a failure names
the case. The steps register here rather than beside the checks they exercise,
because the gate over assertions should not take its imports from a test suite
(solorepo's DR-150). One module per probe, re-exported in the order the steps
report in (solorepo's DR-218); the re-export is what imports the module and so
what registers its step, which is why this package suppresses nothing.
"""
from checks.probes.files.arc import GUARD_CASES, IMAGE_CASES, ImageCase, runner_image_probes
from checks.probes.files.mints import ADVERTISED, vocabulary_mint_probes
from checks.probes.files.sizes import SIZE_CASES, SizeCase, file_size_ceiling_probes

__all__ = [
    "ADVERTISED",
    "GUARD_CASES",
    "IMAGE_CASES",
    "SIZE_CASES",
    "ImageCase",
    "SizeCase",
    "file_size_ceiling_probes",
    "runner_image_probes",
    "vocabulary_mint_probes",
]
"""The package's whole surface, so `from checks.probes import files` finds every probe's cases."""
