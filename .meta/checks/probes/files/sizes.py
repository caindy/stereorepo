"""The ceilings, against a path in each layer and a length on each side (solorepo's DR-217).

`files.python.ceiling` and `files.python.past_ceilings` are read by the `meta
file sizes` step rather than run beside it, so a wrong answer shows as a wrong
verdict rather than as a failure: a ceiling that reads `.meta/say/on` as an
ordinary module lets an entry point grow another hundred and fifty lines with
the gate green, and an arithmetic that fails a file sitting exactly on its
number turns the ceiling into a limit one line lower. The cases are a path from
each layer and a length on each side of each ceiling, and a failure names the
case. The step registers here rather than beside the check it exercises, because
the gate over assertions should not take its imports from a test suite
(solorepo's DR-150).
"""
import collections

from checks.collect import check
from checks.files import python

SizeCase = collections.namedtuple("SizeCase", "path length ceiling over")
"""One file's length put to `past_ceilings`.

Attributes:
    path: The repository-relative path, whose layer sets the ceiling.
    length: How many lines the file holds.
    ceiling: The ceiling that path is held to.
    over: How many lines past it the answer must report, `0` for a file that
        runs past none.
"""


SIZE_CASES = (
    SizeCase(".meta/say/move", 350, 350, 0),
    SizeCase(".meta/say/on", 351, 350, 1),
    SizeCase(".meta/render.py", 349, 350, 0),
    SizeCase(".meta/say/channel.py", 714, 350, 364),
    SizeCase(".meta/checks/files/python.py", 500, 500, 0),
    SizeCase(".meta/lib/move/manager.py", 501, 500, 1),
    SizeCase(".meta/checks/probes/loops/merge_manager.py", 1078, 500, 578),
    SizeCase(".meta/arc/deploy", 399, 500, 0),
    SizeCase(".meta/jules/client.py", 560, 500, 60),
)
"""Every length the ceilings are asked about, one per case. A path is here for
the layer it sits in and the length beside it is the case rather than a claim
about the tree, which moves. No path appears twice, since the cases are put to
`past_ceilings` as one mapping."""


@check("file size ceiling probes", pre=True)
def file_size_ceiling_probes() -> list[str]:
    """`files.python.ceiling` reads a path's layer and `past_ceilings` reports the lines past it.

    Two layers, because the entry ceiling is only worth the difference between
    them: a file directly under `.meta/` or `.meta/say/` is held to
    `ENTRY_CEILING` whether it is a suffixless verb, a top-level script or a
    module beside them, and anything deeper — a package of the gate, a package
    under `.meta/lib/`, a script under `.meta/arc/` — is held to
    `MODULE_CEILING`. A file sitting exactly on its ceiling is clean, one line
    past it is one line of debt, and a file that is failed names the ceiling it
    ran past, since the number is what the reader has to know to answer the
    failure.
    """
    problems = []
    counts, sites = python.past_ceilings({case.path: case.length for case in SIZE_CASES})
    for case in SIZE_CASES:
        held = python.ceiling(case.path)
        if held != case.ceiling:
            problems.append(f"file sizes: {case.path} is held to a ceiling of {held}, "
                            f"not {case.ceiling}")
        found = counts.get(case.path, 0)
        if found != case.over:
            problems.append(f"file sizes: {case.path} at {case.length} lines is reported "
                            f"{found} lines past its ceiling, not {case.over}")
        if case.over and not any(str(case.ceiling) in line for line in sites.get(case.path, [])):
            problems.append(f"file sizes: {case.path} is failed without naming "
                            "the ceiling it ran past")
    if python.ENTRY_CEILING >= python.MODULE_CEILING:
        problems.append("file sizes: the entry layer's ceiling is not the tighter of the two")
    return problems
