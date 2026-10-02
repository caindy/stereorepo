"""`files.scaffold.scaffold_only_lines` against a scaffold-only path named bare and qualified.

The step is run by the gate over the scaffold's inherited files, which name no
scaffold-only path, so a scan that reported nothing at all would pass there.
Here it is given a file written to a temporary directory: the bare reference
must be reported once, and the one that says it is stereorepo's must not be.

`SCAFFOLD_ONLY` has a second copy, `lib.bundle.SCAFFOLD_ONLY_PATHS`, which
`test_specialization.py` and the adoption planner read, and the two are asked
to name the same paths.
"""
import pathlib
import tempfile

from checks.collect import check
from checks.files import scaffold
from lib.bundle import SCAFFOLD_ONLY_PATHS

SAMPLE = (
    "Run the gate from `bootstraps/python/seed`.\n"
    "The seed lives at stereorepo's `bootstraps/python/seed`.\n"
)
"""Line 1 names a scaffold-only path bare; line 2 qualifies it with the scaffold's name."""


@check("scaffold-only path probes")
def scaffold_only_path_probes() -> list[str]:
    """`scaffold_only_lines` reports a bare scaffold-only path and passes over a qualified one.

    Returns:
        list[str]: One line per case the scan got wrong.
    """
    with tempfile.TemporaryDirectory() as tmp_str:
        root = pathlib.Path(tmp_str)
        sample = root / "skill.md"
        sample.write_text(SAMPLE)
        got = scaffold.scaffold_only_lines(sample, scaffold.SCAFFOLD_ONLY, root)
    want = ["skill.md:1 names 'bootstraps/', which a portfolio does not have"]
    problems = [f"scaffold-only paths: expected {want}, got {got}"] if got != want else []
    return problems + _lists_agree()


def _lists_agree() -> list[str]:
    """`SCAFFOLD_ONLY` and `lib.bundle.SCAFFOLD_ONLY_PATHS` name the same paths."""
    gate_side = {name.rstrip("/") for name in scaffold.SCAFFOLD_ONLY}
    runner_side = set(SCAFFOLD_ONLY_PATHS)
    if gate_side != runner_side:
        return [f"scaffold-only paths: SCAFFOLD_ONLY and SCAFFOLD_ONLY_PATHS differ by "
                f"{sorted(gate_side ^ runner_side)}"]
    return []
