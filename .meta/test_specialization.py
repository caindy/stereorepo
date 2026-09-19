#!/usr/bin/env python3
"""Operational test runner for automated Specialization end-to-end verification (solorepo's DR-239, solorepo's DR-244).

Executes the 8-step Specialization Discipline into an isolated, temporary git repository
using pre-judged portfolio fixtures (solorepo's DR-026, solorepo's DR-204), validating that:
1. Inherited tooling, ontologies, and workflows assemble into a viable repository.
2. Workflow runner labels are successfully retargeted for external execution.
3. Template replacements and agent symlinks initialize cleanly.
4. Fixture tokens substitute with zero surviving placeholder tokens.
5. Language bootstrapping and assertion rendering succeed.
6. Scaffold-only paths remain strictly absent from the specialized tree.
7. The full portfolio gate passes cleanly across all initialized projects.

Usage:
    python3 .meta/test_specialization.py [--target <dir>] [--keep] [--lang <python>] [--verbose]
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence

try:
    import yaml
except ImportError:
    cmd = ["uvx", "--with", "pyyaml", "python", str(pathlib.Path(__file__).resolve()), *sys.argv[1:]]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

META = pathlib.Path(__file__).resolve().parent
ROOT = META.parent
FIXTURES_DIR = META / "fixtures" / "specialization"
DEFAULT_TOKENS_PATH = FIXTURES_DIR / "tokens.json"
TOKEN_RE = re.compile(r"__[A-Z0-9_]+__")
SCAFFOLD_ONLY_PATHS = ("SPECIALIZE.md", "template", "bootstraps")


def load_tokens(path: pathlib.Path) -> dict[str, str]:
    """Loads and validates the token substitution map from a JSON fixture.

    Parameters:
        path (pathlib.Path): Absolute path to the JSON tokens file.

    Returns:
        dict[str, str]: Mapping of placeholder tokens to synthetic portfolio values.

    Raises:
        ValueError: If the file is missing, invalid JSON, or contains non-string mappings.
    """
    if not path.is_file():
        raise ValueError(f"Tokens fixture file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse tokens fixture as JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Tokens fixture must be a JSON object, got {type(data).__name__}")
    tokens: dict[str, str] = {}
    for key, val in data.items():
        if not isinstance(key, str) or not isinstance(val, str):
            raise ValueError(f"Token key and value must be strings: {key!r}: {val!r}")
        tokens[key] = val
    return tokens


def normalize_tokens(tokens: dict[str, str]) -> dict[str, str]:
    """Ensures all token keys are framed with template placeholder double underscores.

    Parameters:
        tokens (dict[str, str]): Raw tokens dictionary from JSON fixture.

    Returns:
        dict[str, str]: Normalized mapping with placeholders formatted with surrounding double underscores.
    """
    return {
        (k if k.startswith("__") and k.endswith("__") else f"__{k}__"): v
        for k, v in tokens.items()
    }


def read_inherited_paths(disciplines_file: pathlib.Path) -> list[str]:
    """Parses inherited file and directory paths from disciplines.yaml.

    Parameters:
        disciplines_file (pathlib.Path): Path to disciplines.yaml assertion file.

    Returns:
        list[str]: Backtick path tokens declared in the Specialization discipline.
    """
    if not disciplines_file.is_file():
        return []
    data = yaml.safe_load(disciplines_file.read_text(encoding="utf-8")) or {}
    for discipline in data.get("disciplines") or []:
        if discipline.get("id") != "work:discipline/specialization":
            continue
        for step in discipline.get("steps") or []:
            if step.startswith("Copy what is inherited"):
                return re.findall(r"`([^`]+)`", step)
    return []


def retarget_workflows(workflows_dir: pathlib.Path) -> int:
    """Retargets ARC runner labels to public GitHub container runners in workflow YAMLs.

    Parameters:
        workflows_dir (pathlib.Path): Directory containing workflow YAML files.

    Returns:
        int: Total number of retargeted workflow files.
    """
    count = 0
    if not workflows_dir.is_dir():
        return count
    replacement = "runs-on: ubuntu-latest\n    container: ghcr.io/caindy/solorepo-runner:2.337.0-2"
    for wf in workflows_dir.glob("*.yml"):
        content = wf.read_text(encoding="utf-8")
        if "runs-on: arc-runner-set" in content:
            wf.write_text(content.replace("runs-on: arc-runner-set", replacement), encoding="utf-8")
            count += 1
    return count


def substitute_tokens(repo_dir: pathlib.Path, tokens: dict[str, str]) -> list[str]:
    """Replaces fixture tokens across repository files and asserts no placeholders survive.

    Parameters:
        repo_dir (pathlib.Path): Working tree root of the specialized repository.
        tokens (dict[str, str]): Mapping of token placeholders to substitution values.

    Returns:
        list[str]: List of paths containing surviving unreplaced placeholder tokens.
    """
    norm = normalize_tokens(tokens)
    surviving: list[str] = []
    for path in sorted(repo_dir.rglob("*")):
        if not path.is_file() or path.is_symlink() or ".git" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        modified = content
        for key, value in norm.items():
            if key in modified:
                modified = modified.replace(key, value)
        if modified != content:
            path.write_text(modified, encoding="utf-8")
        found = sorted(set(TOKEN_RE.findall(modified)))
        if found:
            surviving.append(f"{path.relative_to(repo_dir)}: {', '.join(found)}")
    return surviving


def run_command(cmd: Sequence[str], cwd: pathlib.Path, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    """Executes a subprocess command returning its exit code, stdout, and stderr.

    Parameters:
        cmd (Sequence[str]): Command argv arguments.
        cwd (pathlib.Path): Working directory for the process.
        env (dict[str, str] | None): Optional environment variables map.

    Returns:
        tuple[int, str, str]: Tuple of (exit_code, stdout, stderr).
    """
    proc_env = {**os.environ, **(env or {})}
    res = subprocess.run(cmd, cwd=str(cwd), env=proc_env, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def step_1_init_repo(target_path: pathlib.Path) -> int:
    """Initializes a fresh git repository at target destination with dummy commit user."""
    print(f"test-specialization: step 1 — initialize git repository in {target_path}")
    code, _, err = run_command(["git", "init", "-b", "main"], target_path)
    if code != 0:
        print(f"test-specialization: git init failed: {err}", file=sys.stderr)
        return code
    run_command(["git", "config", "user.name", "Specialization Test"], target_path)
    run_command(["git", "config", "user.email", "specialization-test@solorepo.local"], target_path)
    return 0


def step_2_copy_inherited(target_path: pathlib.Path, inherited_tokens: list[str], verbose: bool) -> int:
    """Copies all inherited files into the destination repository and retargets workflows."""
    print("test-specialization: step 2 — copy inherited scaffold files and retarget workflows")
    for token in inherited_tokens:
        src = ROOT / token if (ROOT / token).exists() else META / token
        if not src.exists():
            continue
        dest = target_path / token
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(src, dest)
        elif src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)

    retargeted = retarget_workflows(target_path / ".github" / "workflows")
    if verbose:
        print(f"test-specialization: retargeted {retargeted} workflow files to public container runner")
    return 0


def step_3_copy_template(target_path: pathlib.Path) -> int:
    """Copies template replacements to target repository and creates agent symlinks."""
    print("test-specialization: step 3 — copy template replacements and link agent entrypoints")
    template_dir = ROOT / "template"
    if not template_dir.is_dir():
        print("test-specialization: error — template/ directory missing from scaffold root", file=sys.stderr)
        return 1
    for src_file in sorted(template_dir.rglob("*")):
        if not src_file.is_file():
            continue
        rel = src_file.relative_to(template_dir)
        dest = target_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest)

    for link_name in ("CLAUDE.md", "GEMINI.md"):
        link_dest = target_path / link_name
        if link_dest.exists() or link_dest.is_symlink():
            link_dest.unlink()
        link_dest.symlink_to("AGENTS.md")
    return 0


def step_4_substitute_tokens(target_path: pathlib.Path, tokens: dict[str, str]) -> int:
    """Replaces fixture tokens and verifies that zero placeholders remain unreplaced."""
    print("test-specialization: step 4 — substitute portfolio fixture tokens")
    surviving = substitute_tokens(target_path, tokens)
    if surviving:
        print("test-specialization: error — surviving placeholders detected after substitution:", file=sys.stderr)
        for s in surviving:
            print(f"  {s}", file=sys.stderr)
        return 1
    return 0


def step_5_bootstrap_project(target_path: pathlib.Path, lang: str, verbose: bool) -> int:
    """Bootstraps a language project into the specialized portfolio using local template assets."""
    print(f"test-specialization: step 5 — bootstrap initial project ({lang})")
    bootstrap_staging = target_path / ".meta" / "bootstraps" / lang
    bootstrap_source = ROOT / "bootstraps" / lang
    if bootstrap_source.is_dir():
        bootstrap_staging.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(bootstrap_source, bootstrap_staging, dirs_exist_ok=True)

    bootstrap_cmd = [sys.executable, str(target_path / ".meta" / "bootstrap.py"), lang, "core-lib", "core_lib"]
    b_code, b_out, b_err = run_command(bootstrap_cmd, target_path)
    if b_code != 0:
        print(f"test-specialization: error — bootstrapping {lang} project failed (exit {b_code}):\n{b_out}\n{b_err}", file=sys.stderr)
        return b_code
    if verbose:
        print(b_out)

    if bootstrap_staging.parent.exists():
        shutil.rmtree(bootstrap_staging.parent)
    return 0


def step_6_render_portfolio(target_path: pathlib.Path) -> int:
    """Executes .meta/render.py inside the specialized repository to render recipes and docs."""
    print("test-specialization: step 6 — render portfolio assertions and recipes")
    r_code, r_out, r_err = run_command(["uvx", "--with", "pyyaml", "python", ".meta/render.py"], target_path)
    if r_code != 0:
        print(f"test-specialization: error — render failed (exit {r_code}):\n{r_out}\n{r_err}", file=sys.stderr)
        return r_code
    return 0


def step_7_verify_scaffold_paths(target_path: pathlib.Path) -> int:
    """Verifies that scaffold-only paths are absent and stages initial commit."""
    print("test-specialization: step 7 — verify scaffold-only paths absent")
    for prohibited in SCAFFOLD_ONLY_PATHS:
        prohibited_path = target_path / prohibited
        if prohibited_path.exists():
            print(f"test-specialization: error — prohibited scaffold path exists in portfolio: {prohibited}", file=sys.stderr)
            return 1

    run_command(["git", "add", "."], target_path)
    run_command(["git", "commit", "-m", "feat: specialize portfolio from solorepo scaffold"], target_path)
    return 0


def step_8_run_gate(target_path: pathlib.Path, verbose: bool) -> int:
    """Runs .meta/gate in the specialized repository and verifies zero failing steps."""
    print("test-specialization: step 8 — execute portfolio gate across all projects")
    gate_script = target_path / ".meta" / "gate"
    gate_proc = subprocess.run([str(gate_script)], cwd=str(target_path), capture_output=True, text=True)
    if verbose or gate_proc.returncode != 0:
        print(gate_proc.stdout)
        if gate_proc.stderr:
            print(gate_proc.stderr, file=sys.stderr)

    if gate_proc.returncode != 0:
        print(f"test-specialization: error — portfolio gate failed with exit code {gate_proc.returncode}", file=sys.stderr)
        return gate_proc.returncode

    gate_stdout = gate_proc.stdout
    if "\nx  " in gate_stdout:
        print("test-specialization: error — gate output contains failed steps", file=sys.stderr)
        return 1

    print("test-specialization: ok — 8 specialization steps and full portfolio gate completed cleanly")
    return 0


def execute_specialization_test(
    target_path: pathlib.Path,
    tokens_path: pathlib.Path = DEFAULT_TOKENS_PATH,
    lang: str = "python",
    verbose: bool = False,
) -> int:
    """Executes the 8-step specialization discipline in the specified target directory.

    Parameters:
        target_path (pathlib.Path): Destination path for the test repository.
        tokens_path (pathlib.Path): Path to substitution tokens JSON fixture.
        lang (str): Language bootstrap package to instantiate (default: python).
        verbose (bool): Whether to stream full command outputs.

    Returns:
        int: 0 if all steps and gate checks pass cleanly, non-zero otherwise.
    """
    tokens = load_tokens(tokens_path)
    disciplines_file = META / "assertions" / "disciplines.yaml"
    inherited_tokens = read_inherited_paths(disciplines_file)
    if not inherited_tokens:
        print("test-specialization: error — failed to load inherited paths from disciplines.yaml", file=sys.stderr)
        return 1

    code = step_1_init_repo(target_path)
    if code != 0:
        return code
    code = step_2_copy_inherited(target_path, inherited_tokens, verbose)
    if code != 0:
        return code
    code = step_3_copy_template(target_path)
    if code != 0:
        return code
    code = step_4_substitute_tokens(target_path, tokens)
    if code != 0:
        return code
    code = step_5_bootstrap_project(target_path, lang, verbose)
    if code != 0:
        return code
    code = step_6_render_portfolio(target_path)
    if code != 0:
        return code
    code = step_7_verify_scaffold_paths(target_path)
    if code != 0:
        return code
    return step_8_run_gate(target_path, verbose)


def build_parser() -> argparse.ArgumentParser:
    """Builds the argument parser for the specialization end-to-end verification CLI."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", type=pathlib.Path, default=None, help="directory to run specialization test inside")
    parser.add_argument("--keep", action="store_true", help="preserve temporary directory after run completes")
    parser.add_argument("--tokens", type=pathlib.Path, default=DEFAULT_TOKENS_PATH, help="path to custom tokens JSON")
    parser.add_argument("--lang", default="python", help="bootstrap language to test (default: python)")
    parser.add_argument("--verbose", "-v", action="store_true", help="stream verbose execution output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the specialization end-to-end test CLI tool."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.target:
        target = args.target.resolve()
        target.mkdir(parents=True, exist_ok=True)
        return execute_specialization_test(target, tokens_path=args.tokens.resolve(), lang=args.lang, verbose=args.verbose)

    if args.keep:
        temp_dir = tempfile.mkdtemp(prefix="solorepo-test-specialization-")
        target = pathlib.Path(temp_dir)
        print(f"test-specialization: retaining test directory at {target}")
        return execute_specialization_test(target, tokens_path=args.tokens.resolve(), lang=args.lang, verbose=args.verbose)

    with tempfile.TemporaryDirectory(prefix="solorepo-test-specialization-") as temp_dir:
        target = pathlib.Path(temp_dir)
        return execute_specialization_test(target, tokens_path=args.tokens.resolve(), lang=args.lang, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
