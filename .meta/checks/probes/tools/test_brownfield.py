"""Brownfield repository adoption planning probes.

Validates path classification, collision detection, read-only invariants,
serialization formats, and CLI execution under stereorepo's DR-217.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile

import yaml

from checks.collect import META, CouldNotRun, Found, Passed, StepOutcome, check
from checks.probes.harness import load_module
from lib.adapt import (
    PathClassification,
    build_adoption_plan,
    load_product_config,
)
from lib.bundle import load_bundle


def _hash_directory(dir_path: pathlib.Path) -> dict[str, str]:
    """Computes SHA-256 hashes of all files in a directory tree."""
    hashes: dict[str, str] = {}
    if not dir_path.is_dir():
        return hashes
    for root, _, filenames in dir_path.walk():
        for filename in filenames:
            file_path = root / filename
            if file_path.is_symlink():
                target = str(file_path.readlink())
                hashes[str(file_path.relative_to(dir_path))] = f"symlink:{target}"
            elif file_path.is_file():
                content = file_path.read_bytes()
                digest = hashlib.sha256(content).hexdigest()
                hashes[str(file_path.relative_to(dir_path))] = digest
    return hashes


def _check_empty_target(scaffold_dir: pathlib.Path, tmp: pathlib.Path) -> list[str]:
    """Validates that an empty target plans all bundle items as CREATE."""
    problems: list[str] = []
    target_dir = tmp / "empty_target"
    target_dir.mkdir(parents=True)
    bundle_path = scaffold_dir / ".meta" / "bundle.yaml"

    try:
        plan = build_adoption_plan(
            target_dir=target_dir,
            bundle_path=bundle_path,
            scaffold_dir=scaffold_dir,
        )
    except Exception as exc:  # noqa: BLE001  # reason: probe diagnostic capture
        return [f"brownfield: failed to plan empty target: {exc}"]

    if plan.has_conflicts:
        problems.append("brownfield: empty target unexpectedly reported conflicts")

    bundle = load_bundle(bundle_path=bundle_path, repo_root=scaffold_dir)
    expected_creates = len({item.dest_path().rstrip("/") for item in bundle.items})
    create_actions = [a for a in plan.actions if a.classification == PathClassification.CREATE]
    if len(create_actions) != expected_creates:
        problems.append(
            f"brownfield: expected {expected_creates} CREATE actions for empty target, "
            f"got {len(create_actions)}"
        )
    return problems


def _check_retains_and_integrations(scaffold_dir: pathlib.Path, tmp: pathlib.Path) -> list[str]:
    """Validates classification of retained product files and default integrations."""
    problems: list[str] = []
    target_dir = tmp / "target_repo"
    target_dir.mkdir(parents=True)

    app_file = target_dir / "src" / "app.py"
    app_file.parent.mkdir(parents=True)
    app_file.write_text("print('hello world')\n", encoding="utf-8")

    agents_file = target_dir / "AGENTS.md"
    agents_file.write_text("# Existing product instructions\n", encoding="utf-8")

    readme_file = target_dir / "README.md"
    readme_file.write_text("# Existing product\n", encoding="utf-8")

    scaffold_readme = scaffold_dir / "template" / ".meta" / "README.md"
    meta_readme = target_dir / ".meta" / "README.md"
    meta_readme.parent.mkdir(parents=True)
    meta_readme.write_bytes(scaffold_readme.read_bytes())

    claude_symlink = target_dir / "CLAUDE.md"
    claude_symlink.symlink_to("AGENTS.md")

    plan = build_adoption_plan(
        target_dir=target_dir,
        bundle_path=scaffold_dir / ".meta" / "bundle.yaml",
        scaffold_dir=scaffold_dir,
    )

    action_map = {a.path: a for a in plan.actions}

    app_act = action_map.get("src/app.py")
    if not app_act or app_act.classification != PathClassification.RETAIN:
        problems.append("brownfield: src/app.py was not classified as RETAIN")

    agents_act = action_map.get("AGENTS.md")
    if not agents_act or agents_act.classification != PathClassification.INTEGRATE:
        problems.append("brownfield: AGENTS.md was not classified as INTEGRATE")

    readme_act = action_map.get("README.md")
    if not readme_act or readme_act.classification != PathClassification.INTEGRATE:
        problems.append("brownfield: README.md was not classified as INTEGRATE")

    meta_act = action_map.get(".meta/README.md")
    if not meta_act or meta_act.classification != PathClassification.RETAIN:
        problems.append("brownfield: matching .meta/README.md was not classified as RETAIN")

    claude_act = action_map.get("CLAUDE.md")
    if not claude_act or claude_act.classification != PathClassification.RETAIN:
        problems.append("brownfield: matching CLAUDE.md symlink was not classified as RETAIN")

    return problems


def _check_conflicts(scaffold_dir: pathlib.Path, tmp: pathlib.Path) -> list[str]:
    """Validates detection of content and type collision conflicts."""
    problems: list[str] = []
    target_dir = tmp / "conflict_target"
    target_dir.mkdir(parents=True)

    render_file = target_dir / ".meta" / "render.py"
    render_file.parent.mkdir(parents=True)
    render_file.write_text("Conflicting product render content\n", encoding="utf-8")

    gemini_file = target_dir / "GEMINI.md"
    gemini_file.write_text("Regular file instead of symlink\n", encoding="utf-8")

    struct_dir = target_dir / ".meta" / "assertions" / "structure.yaml"
    struct_dir.mkdir(parents=True)

    plan = build_adoption_plan(
        target_dir=target_dir,
        bundle_path=scaffold_dir / ".meta" / "bundle.yaml",
        scaffold_dir=scaffold_dir,
    )

    if not plan.has_conflicts:
        problems.append("brownfield: expected conflicts were not detected")

    action_map = {a.path: a for a in plan.actions}

    render_act = action_map.get(".meta/render.py")
    if not render_act or render_act.classification != PathClassification.CONFLICT:
        problems.append("brownfield: conflicting .meta/render.py not marked CONFLICT")

    gem_act = action_map.get("GEMINI.md")
    if not gem_act or gem_act.classification != PathClassification.CONFLICT:
        problems.append("brownfield: symlink-to-file GEMINI.md not marked CONFLICT")

    struct_act = action_map.get(".meta/assertions/structure.yaml")
    if not struct_act or struct_act.classification != PathClassification.CONFLICT:
        problems.append("brownfield: file-to-dir structure.yaml not marked CONFLICT")

    return problems


def _check_tracked_files(scaffold_dir: pathlib.Path, tmp: pathlib.Path) -> list[str]:
    """Validates that a git target is planned from its tracked files.

    The files are staged rather than committed: `ls-files` reads the index,
    and a commit would need an identity and would trigger the developer's
    signing configuration.
    """
    problems: list[str] = []
    target_dir = tmp / "git_target"
    target_dir.mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(target_dir), *args], check=True, capture_output=True, env=env
        )

    try:
        git("init", "-q")
        (target_dir / "src").mkdir()
        (target_dir / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
        (target_dir / "gone.py").write_text("deleted after staging\n", encoding="utf-8")
        (target_dir / ".gitignore").write_text("build/\n", encoding="utf-8")
        git("add", "src/app.py", "gone.py", ".gitignore")
    except (OSError, subprocess.CalledProcessError) as exc:
        return [f"brownfield: could not build the git target: {exc}"]
    (target_dir / "gone.py").unlink()
    (target_dir / "scratch.txt").write_text("untracked\n", encoding="utf-8")
    (target_dir / "build").mkdir()
    (target_dir / "build" / "out.txt").write_text("ignored\n", encoding="utf-8")
    (target_dir / ".meta").mkdir()
    (target_dir / ".meta" / "render.py").write_text("Untracked product render\n", encoding="utf-8")

    plan = build_adoption_plan(
        target_dir=target_dir,
        bundle_path=scaffold_dir / ".meta" / "bundle.yaml",
        scaffold_dir=scaffold_dir,
    )
    action_map = {a.path: a for a in plan.actions}

    app_act = action_map.get("src/app.py")
    if not app_act or app_act.classification != PathClassification.RETAIN:
        problems.append("brownfield: tracked src/app.py was not classified as RETAIN")
    for absent in ("gone.py", "scratch.txt", "build/out.txt"):
        if absent in action_map:
            problems.append(f"brownfield: untracked, ignored or deleted {absent} was planned")
    render_act = action_map.get(".meta/render.py")
    if not render_act or render_act.classification != PathClassification.CONFLICT:
        problems.append(
            "brownfield: untracked .meta/render.py at a scaffold path not marked CONFLICT"
        )
    gem_act = action_map.get("GEMINI.md")
    if not gem_act or gem_act.classification != PathClassification.CREATE:
        problems.append("brownfield: unoccupied GEMINI.md not marked CREATE in a git target")
    return problems


def _check_product_config(scaffold_dir: pathlib.Path, tmp: pathlib.Path) -> list[str]:
    """Validates ProductConfig overrides for retain, integrate, ignore, and tokens."""
    problems: list[str] = []
    target_dir = tmp / "config_target"
    target_dir.mkdir(parents=True)

    render_file = target_dir / ".meta" / "render.py"
    render_file.parent.mkdir(parents=True)
    render_file.write_text("Custom product render\n", encoding="utf-8")

    custom_merge = target_dir / "custom" / "merge.txt"
    custom_merge.parent.mkdir(parents=True)
    custom_merge.write_text("Custom merge target\n", encoding="utf-8")

    ignored_file = target_dir / "build_output" / "artifact.bin"
    ignored_file.parent.mkdir(parents=True)
    ignored_file.write_text("Binary data\n", encoding="utf-8")

    config_file = tmp / ".stereorepo.yaml"
    config_content = {
        "retain": [".meta/render.py"],
        "integrations": ["custom/merge.txt"],
        "ignore": ["build_output/**"],
        "tokens": {"PORTFOLIO_NAME": "TestPortfolio"},
    }
    config_file.write_text(yaml.dump(config_content), encoding="utf-8")

    config = load_product_config(config_file)
    plan = build_adoption_plan(
        target_dir=target_dir,
        bundle_path=scaffold_dir / ".meta" / "bundle.yaml",
        config=config,
        scaffold_dir=scaffold_dir,
    )

    action_map = {a.path: a for a in plan.actions}

    render_act = action_map.get(".meta/render.py")
    if not render_act or render_act.classification != PathClassification.RETAIN:
        problems.append("brownfield: retain override failed for render.py")

    merge_act = action_map.get("custom/merge.txt")
    if not merge_act or merge_act.classification != PathClassification.INTEGRATE:
        problems.append("brownfield: integrations override failed for custom/merge.txt")

    if "build_output/artifact.bin" in action_map:
        problems.append("brownfield: ignored path build_output/artifact.bin appeared in actions")

    return problems


def _check_readonly_invariant(scaffold_dir: pathlib.Path, tmp: pathlib.Path) -> list[str]:
    """Validates that build_adoption_plan does not modify the target repository."""
    problems: list[str] = []
    target_dir = tmp / "readonly_target"
    target_dir.mkdir(parents=True)

    (target_dir / "src").mkdir()
    (target_dir / "src" / "lib.py").write_text("x = 1\n", encoding="utf-8")
    (target_dir / "AGENTS.md").write_text("# Target instructions\n", encoding="utf-8")
    (target_dir / "CLAUDE.md").symlink_to("AGENTS.md")

    before_hashes = _hash_directory(target_dir)

    _ = build_adoption_plan(
        target_dir=target_dir,
        bundle_path=scaffold_dir / ".meta" / "bundle.yaml",
        scaffold_dir=scaffold_dir,
    )

    after_hashes = _hash_directory(target_dir)

    if before_hashes != after_hashes:
        problems.append(
            "brownfield: read-only invariant violated: target directory contents were mutated"
        )
    return problems


def _check_cli_and_formats(scaffold_dir: pathlib.Path, tmp: pathlib.Path) -> list[str]:
    """Validates serialization formats and CLI dispatcher execution."""
    adapt_mod = load_module(META / "adapt.py", "adapt_module", register=False)
    _cmd_plan = adapt_mod._cmd_plan

    problems: list[str] = []
    target_dir = tmp / "cli_target"
    target_dir.mkdir(parents=True)
    (target_dir / "file.txt").write_text("hello\n", encoding="utf-8")

    plan = build_adoption_plan(
        target_dir=target_dir,
        bundle_path=scaffold_dir / ".meta" / "bundle.yaml",
        scaffold_dir=scaffold_dir,
    )

    text_out = plan.to_text()
    if "Adoption plan for" not in text_out or "CREATE" not in text_out:
        problems.append("brownfield: to_text output missing expected headers or actions")

    json_out = plan.to_json()
    try:
        parsed_json = json.loads(json_out)
        if "actions" not in parsed_json or "summary" not in parsed_json:
            problems.append("brownfield: to_json output missing required top-level keys")
    except ValueError as exc:
        problems.append(f"brownfield: to_json produced invalid JSON: {exc}")

    yaml_out = plan.to_yaml()
    try:
        parsed_yaml = yaml.safe_load(yaml_out)
        if not isinstance(parsed_yaml, dict) or "actions" not in parsed_yaml:
            problems.append("brownfield: to_yaml output missing required structure")
    except Exception as exc:  # noqa: BLE001  # reason: probe diagnostic capture
        problems.append(f"brownfield: to_yaml produced invalid YAML: {exc}")

    clean_args = argparse.Namespace(
        target=str(target_dir),
        root=str(scaffold_dir),
        bundle=str(scaffold_dir / ".meta" / "bundle.yaml"),
        config=None,
        format="text",
        json=False,
        yaml=False,
        fail_on_conflict=True,
        quiet=True,
    )
    ret_clean = _cmd_plan(clean_args)
    if ret_clean != 0:
        problems.append(f"brownfield: CLI returned non-zero ({ret_clean}) on conflict-free target")

    conflict_dir = tmp / "cli_conflict"
    conflict_dir.mkdir(parents=True)
    (conflict_dir / ".meta").mkdir(parents=True)
    (conflict_dir / ".meta" / "render.py").write_text("conflict\n", encoding="utf-8")

    conflict_args = argparse.Namespace(
        target=str(conflict_dir),
        root=str(scaffold_dir),
        bundle=str(scaffold_dir / ".meta" / "bundle.yaml"),
        config=None,
        format="json",
        json=True,
        yaml=False,
        fail_on_conflict=True,
        quiet=True,
    )
    ret_conflict = _cmd_plan(conflict_args)
    if ret_conflict != 1:
        problems.append(
            f"brownfield: CLI with --fail-on-conflict expected exit code 1, got {ret_conflict}"
        )

    return problems


NO_TEMPLATE = "no template/ to adopt from: brownfield adoption is planned from the scaffold"
"""Why the step could not run in a repository without the scaffold's `template/`: a portfolio."""


def _check_without_template(tmp: pathlib.Path) -> list[str]:
    """Validates that the step reports it could not run, rather than passing, without template/."""
    bare = tmp / "no_template"
    bare.mkdir()
    shown = test_brownfield_probes(bare)
    if not isinstance(shown, CouldNotRun) or shown.why != NO_TEMPLATE:
        return [f"brownfield: a repository without template/ reported {shown!r}, "
                f"expected could-not-run {NO_TEMPLATE!r}"]
    return []


@check("brownfield adoption probes", pre=True)
def test_brownfield_probes(scaffold_dir: pathlib.Path = META.parent) -> StepOutcome:
    """Probes brownfield adoption planning and CLI dispatcher (stereorepo's DR-217).

    Validates that:
    1. Empty target repository plans all bundle entries as CREATE.
    2. Retained product files and default integrations are classified accurately.
    3. Content and filesystem type collisions are detected as CONFLICT.
    4. ProductConfig overrides (retain, integrations, ignore, tokens) are honoured.
    5. Target directory trees remain strictly unmodified (read-only invariant).
    6. Formats (text, JSON, YAML) and CLI execution exit codes adhere to specification.
    7. A repository without `template/` is reported as could-not-run.
    8. A git target is planned from its tracked files, not its working tree.

    The plan is drawn from the scaffold's `template/`. A specialized portfolio
    has no copy of this step (stereorepo's DR-305), but a repository adopted
    from a plan still does, without `template/`, so there the step could not
    run and says so rather than passing.

    Args:
        scaffold_dir: The repository whose bundle and `template/` the plans are drawn from.

    Returns:
        StepOutcome: `CouldNotRun` where `scaffold_dir` has no `template/`,
        otherwise `Found` with one line per failed case, or `Passed`.
    """
    if not (scaffold_dir / "template").is_dir():
        return CouldNotRun(NO_TEMPLATE)
    problems: list[str] = []

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = pathlib.Path(tmp_str)
        problems.extend(_check_empty_target(scaffold_dir, tmp))
        problems.extend(_check_retains_and_integrations(scaffold_dir, tmp))
        problems.extend(_check_conflicts(scaffold_dir, tmp))
        problems.extend(_check_product_config(scaffold_dir, tmp))
        problems.extend(_check_readonly_invariant(scaffold_dir, tmp))
        problems.extend(_check_cli_and_formats(scaffold_dir, tmp))
        problems.extend(_check_without_template(tmp))
        problems.extend(_check_tracked_files(scaffold_dir, tmp))

    return Found(problems) if problems else Passed("8 adoption cases")
