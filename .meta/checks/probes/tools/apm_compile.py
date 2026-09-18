"""`apm_compile.py`'s byte fallback for a skill file that is not UTF-8 text (solorepo's DR-208).
"""
import contextlib
import io
import pathlib
import tempfile

from collect import META, check
from probes.harness import load_module


@check("apm compile probes", pre=True)
def apm_compile_probes():
    """`apm_compile.python_bootstrap_primitives` over a skill file that is not UTF-8 text (solorepo's DR-208).

    One byte that does not decode — the shape a `__pycache__/*.pyc` beside a
    skill's script and a shipped diagram both take — used to end the compile
    in a traceback (solorepo's #450). Written two levels below `skills/`, so
    the check that only a nested file compiles still applies, the compiled
    entry for that file holds its own bytes unchanged, and the file is named
    on stderr rather than swapped in silently.
    """
    apm_compile = load_module(META / "apm_compile.py", "apm_compile_module", register=False)
    problems = []
    rel_path = "../bootstraps/python/.apm/skills/sample-skill/diagram.png"
    binary = b"\xf3\x00not valid utf-8"
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        skill_dir = root / "bootstraps" / "python" / "skills" / "sample-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "diagram.png").write_bytes(binary)
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr):
                prims = apm_compile.python_bootstrap_primitives(root)
        except UnicodeDecodeError as exc:
            return [f"apm_compile: a non-UTF-8 skill file raised {exc} instead of "
                    "being copied as bytes"]
    if prims.get(rel_path) != binary:
        problems.append(f"apm_compile: expected {rel_path} to hold the file's own bytes, "
                        f"got {prims.get(rel_path)!r}")
    if "diagram.png" not in stderr.getvalue():
        problems.append("apm_compile: expected the non-UTF-8 file named on stderr, "
                        f"got {stderr.getvalue()!r}")
    return problems
