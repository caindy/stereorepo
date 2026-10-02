#!/usr/bin/env python3
"""Operational test runner for automated Specialization end-to-end verification.

Cites DR-239 and DR-244.

Executes the 8-step Specialization Discipline into an isolated, temporary git repository
using pre-judged portfolio fixtures (DR-026, DR-204), validating that:
1. Inherited tooling and ontologies assemble into a viable repository.
2. Template replacements and agent symlinks initialize cleanly.
3. Fixture tokens substitute with zero surviving placeholder tokens.
4. Language bootstrapping and assertion rendering succeed.
5. Scaffold-only paths remain strictly absent from the specialized tree.
6. The full portfolio gate passes cleanly across all initialized projects.

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
from collections.abc import Callable, Sequence

from lib.bundle import Bundle, load_bundle

try:
    import yaml
except ImportError:
    cmd = ["uvx", "--python", "3.13", "--with", "pyyaml", "python",
           str(pathlib.Path(__file__).resolve()), *sys.argv[1:]]
    res = subprocess.run(cmd, check=False)
    sys.exit(res.returncode)

META = pathlib.Path(__file__).resolve().parent
ROOT = META.parent
FIXTURES_DIR = META / "fixtures" / "specialization"
DEFAULT_TOKENS_PATH = FIXTURES_DIR / "tokens.json"
TOKEN_RE = re.compile(r"__[A-Z0-9_]+__")
SCAFFOLD_ONLY_PATHS = ("SPECIALIZE.md", "template", "bootstraps", "pair", ".meta/adapt.py",
                       ".meta/lib/adapt", ".meta/checks/probes/tools/test_brownfield.py")
"""Paths the scaffold has and a portfolio does not, relative to the root; the same paths as
`checks.files.scaffold.SCAFFOLD_ONLY`, which spells a directory with a trailing slash."""

NO_FIXTURE = "Tokens fixture file not found: {path}"
"""What `load_tokens` raises where nothing is at the path it was given."""

UNPARSED_FIXTURE = "Failed to parse tokens fixture as JSON: {why}"
"""What `load_tokens` raises where the fixture will not parse as JSON."""

NOT_AN_OBJECT = "Tokens fixture must be a JSON object, got {got}"
"""What `load_tokens` raises where the fixture parses to something other than an object."""

NOT_A_STRING_PAIR = "Token key and value must be strings: {key!r}: {value!r}"
"""What `load_tokens` raises where a token's key or value is not a string."""


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
        raise ValueError(NO_FIXTURE.format(path=path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(UNPARSED_FIXTURE.format(why=exc)) from exc
    if not isinstance(data, dict):
        raise ValueError(NOT_AN_OBJECT.format(got=type(data).__name__))
    tokens: dict[str, str] = {}
    for key, val in data.items():
        if not isinstance(key, str) or not isinstance(val, str):
            raise ValueError(NOT_A_STRING_PAIR.format(key=key, value=val))
        tokens[key] = val
    return tokens


def normalize_tokens(tokens: dict[str, str]) -> dict[str, str]:
    """Ensures all token keys are framed with template placeholder double underscores.

    Parameters:
        tokens (dict[str, str]): Raw tokens dictionary from JSON fixture.

    Returns:
        dict[str, str]: Normalized mapping with placeholders formatted with surrounding
        double underscores.
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
            if step.get("name") == "Copy what is inherited":
                statement = step.get("statement", "")
                paths_clause = statement.split(". The channel")[0]
                return re.findall(r"`([^`]+)`", paths_clause)
    return []


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


def run_command(
    cmd: Sequence[str],
    cwd: pathlib.Path,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Executes a subprocess command returning its exit code, stdout, and stderr.

    Parameters:
        cmd (Sequence[str]): Command argv arguments.
        cwd (pathlib.Path): Working directory for the process.
        env (dict[str, str] | None): Optional environment variables map.

    Returns:
        tuple[int, str, str]: Tuple of (exit_code, stdout, stderr).
    """
    proc_env = {**os.environ, **(env or {})}
    res = subprocess.run(cmd, check=False, cwd=str(cwd), env=proc_env,
                         capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def _scaffold_only(path: pathlib.Path, root: pathlib.Path) -> bool:
    """Whether `path` is one of `SCAFFOLD_ONLY_PATHS` below `root`."""
    return path.is_relative_to(root) and path.relative_to(root).as_posix() in SCAFFOLD_ONLY_PATHS


def _copy_item(src: pathlib.Path, dest: pathlib.Path, root: pathlib.Path = ROOT) -> None:
    """Copies a file or tree to its destination, leaving out every scaffold-only path in it,
    such as `.meta/lib/adapt/` inside `.meta/lib/`."""
    if not src.exists() or _scaffold_only(src, root):
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        def left_out(where: str, names: list[str]) -> list[str]:
            return [name for name in names if _scaffold_only(pathlib.Path(where) / name, root)]
        shutil.copytree(src, dest, dirs_exist_ok=True, ignore=left_out)
    else:
        shutil.copy2(src, dest)


def step_1_init_repo(target_path: pathlib.Path) -> int:
    """Initializes a fresh git repository at target destination with dummy commit user."""
    print(f"test-specialization: step 1 — initialize git repository in {target_path}")
    code, _, err = run_command(["git", "init", "-b", "main"], target_path)
    if code != 0:
        print(f"test-specialization: git init failed: {err}", file=sys.stderr)
        return code
    run_command(["git", "config", "user.name", "Specialization Test"], target_path)
    run_command(["git", "config", "user.email", "test@stereorepo.local"], target_path)
    return 0


def step_2_copy_inherited(
    target_path: pathlib.Path,
    inherited_tokens: list[str],
    verbose: bool,
    bundle: Bundle | None = None,
) -> int:
    """Copies all inherited files into the destination repository."""
    print("test-specialization: step 2 — copy inherited scaffold files")
    if bundle is not None:
        for item in bundle.managed_items():
            _copy_item(ROOT / item.source_path(), target_path / item.dest_path())
    else:
        for token in inherited_tokens:
            src = ROOT / token if (ROOT / token).exists() else META / token
            _copy_item(src, target_path / token)
    return 0


def step_3_copy_template(target_path: pathlib.Path, bundle: Bundle | None = None) -> int:
    """Copies template replacements to target repository and creates agent symlinks."""
    print("test-specialization: step 3 — copy template replacements and link agent entrypoints")
    if bundle is not None:
        for item in bundle.template_items():
            _copy_item(ROOT / item.source_path(), target_path / item.dest_path())
        for item in bundle.symlink_items():
            dest = target_path / item.dest_path()
            dest.unlink(missing_ok=True)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.symlink_to(item.source_path())
        return 0

    template_dir = ROOT / "template"
    if not template_dir.is_dir():
        print(
            "test-specialization: error — template/ directory missing from scaffold root",
            file=sys.stderr,
        )
        return 1
    for src_file in sorted(template_dir.rglob("*")):
        if src_file.is_file():
            _copy_item(src_file, target_path / src_file.relative_to(template_dir))

    for name, target in (("CLAUDE.md", "AGENTS.md"), ("GEMINI.md", "AGENTS.md"),
                         (".github/copilot-instructions.md", "../AGENTS.md")):
        link = target_path / name
        link.unlink(missing_ok=True)
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
    return 0


def step_4_substitute_tokens(target_path: pathlib.Path, tokens: dict[str, str]) -> int:
    """Replaces fixture tokens and verifies that zero placeholders remain unreplaced."""
    print("test-specialization: step 4 — substitute portfolio fixture tokens")
    surviving = substitute_tokens(target_path, tokens)
    if surviving:
        print(
            "test-specialization: error — surviving placeholders detected after substitution:",
            file=sys.stderr,
        )
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

    bootstrap_cmd = [
        sys.executable,
        str(target_path / ".meta" / "bootstrap.py"),
        lang,
        "core-lib",
        "core_lib",
    ]
    b_code, b_out, b_err = run_command(bootstrap_cmd, target_path)
    if b_code != 0:
        print(
            f"test-specialization: error — bootstrapping {lang} project failed (exit {b_code}):\n"
            f"{b_out}\n{b_err}",
            file=sys.stderr,
        )
        return b_code
    if verbose:
        print(b_out)

    if bootstrap_staging.parent.exists():
        shutil.rmtree(bootstrap_staging.parent)
    return 0


def step_6_render_portfolio(target_path: pathlib.Path) -> int:
    """Executes .meta/render.py inside the specialized repository to render recipes and docs."""
    print("test-specialization: step 6 — render portfolio assertions and recipes")
    r_code, r_out, r_err = run_command(
        ["uvx", "--python", "3.13", "--with", "pyyaml", "python", ".meta/render.py"], target_path)
    if r_code != 0:
        print(
            f"test-specialization: error — render failed (exit {r_code}):\n{r_out}\n{r_err}",
            file=sys.stderr,
        )
        return r_code
    return 0


def step_7_verify_scaffold_paths(target_path: pathlib.Path) -> int:
    """Verifies that scaffold-only paths are absent and stages initial commit."""
    print("test-specialization: step 7 — verify scaffold-only paths absent")
    for prohibited in SCAFFOLD_ONLY_PATHS:
        prohibited_path = target_path / prohibited
        if prohibited_path.exists():
            print(
                f"test-specialization: error — prohibited scaffold path exists: {prohibited}",
                file=sys.stderr,
            )
            return 1

    run_command(["git", "add", "."], target_path)
    run_command(["git", "commit", "-m", "feat: specialize portfolio from stereorepo scaffold"],
                target_path)
    return 0


def step_8_run_gate(target_path: pathlib.Path, verbose: bool) -> int:
    """Runs .meta/gate in the specialized repository and verifies zero failing steps."""
    print("test-specialization: step 8 — execute portfolio gate across all projects")
    gate_script = target_path / ".meta" / "gate"
    gate_proc = subprocess.run([str(gate_script)], check=False, cwd=str(target_path),
                               capture_output=True, text=True)
    if verbose or gate_proc.returncode != 0:
        print(gate_proc.stdout)
        if gate_proc.stderr:
            print(gate_proc.stderr, file=sys.stderr)

    if gate_proc.returncode != 0:
        print(
            f"test-specialization: error — gate failed with exit code {gate_proc.returncode}",
            file=sys.stderr,
        )
        return gate_proc.returncode

    gate_stdout = gate_proc.stdout
    if "\nx  " in gate_stdout:
        print("test-specialization: error — gate output contains failed steps", file=sys.stderr)
        return 1

    print("test-specialization: ok — 8 steps and portfolio gate completed cleanly")
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
        print(
            "test-specialization: error — failed to load inherited paths from disciplines.yaml",
            file=sys.stderr,
        )
        return 1

    bundle: Bundle | None = None
    bundle_file = META / "bundle.yaml"
    if bundle_file.is_file():
        try:
            bundle = load_bundle(bundle_file, repo_root=ROOT)
        except (FileNotFoundError, ValueError, OSError) as exc:
            print(f"test-specialization: warning — failed to load bundle: {exc}", file=sys.stderr)

    steps: tuple[Callable[[], int], ...] = (
        lambda: step_1_init_repo(target_path),
        lambda: step_2_copy_inherited(target_path, inherited_tokens, verbose, bundle=bundle),
        lambda: step_3_copy_template(target_path, bundle=bundle),
        lambda: step_4_substitute_tokens(target_path, tokens),
        lambda: step_5_bootstrap_project(target_path, lang, verbose),
        lambda: step_6_render_portfolio(target_path),
        lambda: step_7_verify_scaffold_paths(target_path),
        lambda: step_8_run_gate(target_path, verbose),
    )
    for step in steps:
        code = step()
        if code != 0:
            return code
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Builds the argument parser for the specialization end-to-end verification CLI."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target", type=pathlib.Path, default=None,
        help="directory to run specialization test inside",
    )
    parser.add_argument(
        "--keep", action="store_true",
        help="preserve temporary directory after run completes",
    )
    parser.add_argument(
        "--tokens", type=pathlib.Path, default=DEFAULT_TOKENS_PATH,
        help="path to custom tokens JSON",
    )
    parser.add_argument(
        "--lang", default="python",
        help="bootstrap language to test (default: python)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="stream verbose execution output",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the specialization end-to-end test CLI tool."""
    args = build_parser().parse_args(argv)
    tokens = args.tokens.resolve()

    if args.target:
        target = args.target.resolve()
        target.mkdir(parents=True, exist_ok=True)
        return execute_specialization_test(
            target, tokens_path=tokens, lang=args.lang, verbose=args.verbose,
        )

    if args.keep:
        target = pathlib.Path(tempfile.mkdtemp(prefix="stereorepo-test-specialization-"))
        print(f"test-specialization: retaining test directory at {target}")
        return execute_specialization_test(
            target, tokens_path=tokens, lang=args.lang, verbose=args.verbose,
        )

    with tempfile.TemporaryDirectory(prefix="stereorepo-test-specialization-") as temp_dir:
        return execute_specialization_test(
            pathlib.Path(temp_dir), tokens_path=tokens, lang=args.lang, verbose=args.verbose,
        )


if __name__ == "__main__":
    sys.exit(main())
