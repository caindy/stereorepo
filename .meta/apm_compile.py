#!/usr/bin/env python3
"""Compiler and packager translating assertions into APM package primitives.

Compiles declarative assertions and bootstrap capabilities into Agent Package
Manager (APM) primitives and reconciles root agent harness configurations
(stereorepo's DR-325, stereorepo's DR-172, stereorepo's DR-333, stereorepo's DR-340,
stereorepo's DR-208).

History in apm_compile.history.md (stereorepo's DR-171).
"""
from __future__ import annotations

import pathlib
import sys

if __name__ == "__main__" and (
    "--reconcile" in sys.argv or "-h" in sys.argv or "--help" in sys.argv
):
    from lib.apm_compile import cli

    cli.main(__doc__)
    sys.exit(0)

try:
    import yaml  # noqa: F401  # reason: the import is the test of whether PyYAML is installed
except ImportError:
    if __name__ == "__main__":
        import subprocess
        cmd = ["uvx", "--python", "3.13", "--with", "pyyaml", "python",
               str(pathlib.Path(__file__).resolve()), *sys.argv[1:]]
        try:
            res = subprocess.run(cmd, check=False)
            sys.exit(res.returncode)
        except FileNotFoundError:
            sys.exit("apm_compile: PyYAML is not installed and uvx is not available in PATH.")

from lib.apm_compile import (
    BANNER,
    META,
    ROOT,
    harness,
)
from lib.apm_compile.harness import (
    check_root_symlinks,
    reconcile_harnesses,
    reconcile_root,
)

try:
    from lib.apm_compile import (
        agents,
        apm,
        bootstrap,
        cli,
        instructions,
        primitives,
        skills,
    )
    from lib.apm_compile.agents import agent_primitives
    from lib.apm_compile.apm import compile_apm, pack_apm, run_apm, validate_apm
    from lib.apm_compile.bootstrap import (
        python_bootstrap_instructions,
        python_bootstrap_manifest,
        python_bootstrap_primitives,
    )
    from lib.apm_compile.cli import main
    from lib.apm_compile.instructions import (
        apm_manifest,
        discipline_instructions,
        load_yaml,
        ubiquitous_language_instructions,
    )
    from lib.apm_compile.primitives import (
        check_primitives,
        rendered_primitives,
        write_primitives,
    )
    from lib.apm_compile.skills import hook_primitives, skill_primitives
except ImportError:
    pass

__all__ = [
    "BANNER",
    "META",
    "ROOT",
    "agent_primitives",
    "agents",
    "apm",
    "apm_manifest",
    "bootstrap",
    "check_primitives",
    "check_root_symlinks",
    "cli",
    "compile_apm",
    "discipline_instructions",
    "harness",
    "hook_primitives",
    "instructions",
    "load_yaml",
    "main",
    "pack_apm",
    "primitives",
    "python_bootstrap_instructions",
    "python_bootstrap_manifest",
    "python_bootstrap_primitives",
    "reconcile_harnesses",
    "reconcile_root",
    "rendered_primitives",
    "run_apm",
    "skill_primitives",
    "skills",
    "ubiquitous_language_instructions",
    "validate_apm",
    "write_primitives",
]
"""The script's whole surface, so `import apm_compile` still finds every name it did: the render
reads `check_root_symlinks` and `reconcile_root`, and the gate reads `python_bootstrap_primitives`
and `rendered_primitives`, through this module's name.

The modules are exported beside the names, none of them colliding with one, so a probe stands a
collaborator in at the module that defines it (stereorepo's DR-344)."""

if __name__ == "__main__":
    cli.main(__doc__)
