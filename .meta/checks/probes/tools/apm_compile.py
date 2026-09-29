"""`apm_compile.py` byte fallback (stereorepo's DR-208)
and worktree skill projection.
"""
import contextlib
import io
import pathlib
import shutil
import subprocess
import tempfile

from checks.collect import META, check
from checks.probes.harness import load_module


@check("apm compile probes", pre=True)
def apm_compile_probes() -> list[str]:
    """`apm_compile.python_bootstrap_primitives` over a skill file that is not UTF-8 text (stereorepo's DR-208).

    One byte that does not decode — the shape a `__pycache__/*.pyc` beside a
    skill's script and a shipped diagram both take — used to end the compile
    in a traceback. Written two levels below `skills/`, so
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


@check("worktree projection probes", pre=True)
def worktree_projection_probes() -> list[str]:
    """Worktree skill projection under constrained environments and hook error reporting.

    Enacts stereorepo's DR-172 and stereorepo's DR-201.
    Verifies that .meta/hooks/post-checkout materializes skills into .agents/skills/
    under constrained execution environments without APM CLI or ambient PyYAML,
    and reports failures to stderr instead of masking them to /dev/null.
    """
    problems: list[str] = []
    hook_path = META / "hooks" / "post-checkout"

    with tempfile.TemporaryDirectory() as tmp:
        tpath = pathlib.Path(tmp)
        subprocess.run(
            ["git", "init", str(tpath)],
            capture_output=True,
            cwd=str(tpath),
            check=False,
        )
        shutil.copytree(META, tpath / ".meta")
        shutil.copy(META.parent / "AGENTS.md", tpath / "AGENTS.md")
        env = {"PATH": "/usr/bin:/bin", "HOME": str(tpath)}
        res = subprocess.run(
            ["bash", str(tpath / ".meta" / "hooks" / "post-checkout"), "0", "0", "1"],
            cwd=str(tpath),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            problems.append(f"constrained post-checkout failed ({res.returncode}): {res.stderr}")
        if not (tpath / ".agents" / "skills" / "search" / "SKILL.md").is_file():
            problems.append("constrained post-checkout did not project the search skill")

    with tempfile.TemporaryDirectory() as tmp:
        tpath = pathlib.Path(tmp)
        subprocess.run(
            ["git", "init", str(tpath)],
            capture_output=True,
            cwd=str(tpath),
            check=False,
        )
        meta = tpath / ".meta"
        meta.mkdir()
        failing_code = (
            "import sys\n"
            "sys.stderr.write('mock compiler error\\n')\n"
            "sys.exit(2)\n"
        )
        (meta / "apm_compile.py").write_text(failing_code)
        hooks = meta / "hooks"
        hooks.mkdir()
        shutil.copy(hook_path, hooks / "post-checkout")
        res = subprocess.run(
            ["bash", str(hooks / "post-checkout"), "0", "0", "1"],
            cwd=str(tpath),
            capture_output=True,
            text=True,
            check=False,
        )
        if "failed to reconcile harness cognitive assets" not in res.stderr:
            problems.append(
                f"post-checkout did not report failure header to stderr: got {res.stderr!r}"
            )
        if "mock compiler error" not in res.stderr:
            problems.append(
                f"post-checkout did not include compiler output in stderr: got {res.stderr!r}"
            )
        if "exit code 2" not in res.stderr:
            problems.append(
                f"post-checkout did not include exit code in stderr: got {res.stderr!r}"
            )

    return problems
