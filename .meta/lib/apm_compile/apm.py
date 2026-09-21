"""The `apm` command line invoked over the compiled package: validate, pack, compile, and the pass-through operations.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

from lib.apm_compile import META, ROOT, primitives


def run_apm(args: list[str], meta_dir: pathlib.Path = META) -> int:
    """Runs the apm CLI inside meta_dir, passing args (solorepo's DR-201)."""
    apm_bin = shutil.which("apm")
    if not apm_bin:
        print(
            "apm is not installed. Install via 'brew install apm' or "
            "'curl -sSL https://aka.ms/apm-unix | sh'",
            file=sys.stderr,
        )
        return 1
    res = subprocess.run([apm_bin, *args], check=False, cwd=str(meta_dir))
    return res.returncode


def validate_apm(meta_dir: pathlib.Path = META, root_dir: pathlib.Path = ROOT) -> int:
    """Validates APM primitives against LinkML assertions and APM CLI schema (solorepo's DR-201, solorepo's DR-208)."""
    stale = primitives.check_primitives(meta_dir, root_dir)
    if stale:
        print("Internal assertion-to-primitive drift detected:", file=sys.stderr)
        for item in stale:
            print(f"  {item}", file=sys.stderr)
        return 1
    print("Internal assertion-to-primitive projection is up to date.")
    apm_bin = shutil.which("apm")
    if not apm_bin:
        print("Note: apm CLI is not installed; skipping downstream APM engine validation.")
        return 0
    code = run_apm(["compile", "--validate"], meta_dir=meta_dir)
    if code != 0:
        return code
    py_dir = root_dir / "bootstraps" / "python"
    if py_dir.is_dir() and (py_dir / "apm.yml").is_file():
        code = run_apm(["compile", "--validate"], meta_dir=py_dir)
    return code


def pack_apm(args: list[str], meta_dir: pathlib.Path = META) -> int:
    """Packs the APM project into distributable plugin/bundle artifacts (solorepo's DR-201)."""
    return run_apm(["pack", *args], meta_dir=meta_dir)


def compile_apm(args: list[str], meta_dir: pathlib.Path = META) -> int:
    """Compiles the APM project into target harness directories redirected to root (solorepo's DR-172, solorepo's DR-201)."""
    cmd_args = ["compile", "--root", ".."]
    if not any(a.startswith("-t") or a.startswith("--target") or a == "--all" for a in args):
        cmd_args.extend(["-t", "claude,gemini,copilot"])
    cmd_args.extend(args)
    return run_apm(cmd_args, meta_dir=meta_dir)
