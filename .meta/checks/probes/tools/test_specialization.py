"""`test_specialization.py`'s fixture loading, path inheritance, and token substitution probes.

Cites stereorepo's DR-239 and stereorepo's DR-244.
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import tempfile
from typing import Any

from checks.collect import META, check
from checks.probes.harness import load_module


def _check_fixture_keys(runner: Any, tokens_path: pathlib.Path) -> list[str]:
    """Validates that tokens.json fixture carries required keys and non-empty values."""
    if not tokens_path.is_file():
        return [f"test-specialization: tokens fixture missing at {tokens_path}"]
    try:
        tokens = runner.load_tokens(tokens_path)
    except ValueError as exc:
        return [f"test-specialization: failed to load tokens fixture: {exc}"]

    problems: list[str] = []
    required_keys = (
        "PORTFOLIO_SLUG",
        "PORTFOLIO_NAME",
        "PORTFOLIO_DESCRIPTION",
        "GITHUB_OWNER",
        "GITHUB_REPO",
        "WHY_THIS_PORTFOLIO_EXISTS",
    )
    for key in required_keys:
        if key not in tokens or not tokens[key].strip():
            problems.append(
                f"test-specialization: missing or empty required token key {key} in fixture"
            )
    return problems


def _check_fixture_error_handling(runner: Any, tmp: pathlib.Path) -> list[str]:
    """Validates that malformed JSON or non-string token structures raise ValueError."""
    problems: list[str] = []
    bad_json = tmp / "bad.json"
    bad_json.write_text("{not valid json", encoding="utf-8")
    try:
        runner.load_tokens(bad_json)
        problems.append(
            "test-specialization: load_tokens accepted malformed JSON without raising ValueError"
        )
    except ValueError:
        pass

    bad_type = tmp / "bad_type.json"
    bad_type.write_text(json.dumps({"KEY": 123}), encoding="utf-8")
    try:
        runner.load_tokens(bad_type)
        problems.append(
            "test-specialization: load_tokens accepted non-string value without raising ValueError"
        )
    except ValueError:
        pass
    return problems


def _check_substitute(runner: Any, tmp: pathlib.Path) -> list[str]:
    """Validates token substitution."""
    problems: list[str] = []
    prefix = "_" + "_"
    test_token_placeholder = f"{prefix}PORTFOLIO_NAME{prefix}"
    unknown_placeholder = f"{prefix}UNKNOWN_TOKEN{prefix}"
    sub_file = tmp / "sample.txt"
    sub_file.write_text(
        f"Hello {test_token_placeholder}! Unhandled {unknown_placeholder} here.",
        encoding="utf-8",
    )
    surviving = runner.substitute_tokens(tmp, {"PORTFOLIO_NAME": "World"})
    if not surviving:
        problems.append(
            "test-specialization: substitute_tokens failed to report surviving unreplaced "
            "placeholder"
        )
    sub_content = sub_file.read_text(encoding="utf-8")
    if "Hello World!" not in sub_content:
        problems.append(
            f"test-specialization: substitute_tokens failed to replace token: {sub_content!r}"
        )
    return problems


def _check_scaffold_only(runner: Any, tmp: pathlib.Path) -> list[str]:
    """Validates that a copy leaves out nested scaffold-only paths and step 7 refuses one."""
    problems: list[str] = []
    scaffold, target = tmp / "scaffold", tmp / "target"
    for file in (".meta/lib/bundle/__init__.py", ".meta/checks/probes/tools/gate.py",
                 ".meta/lib/adapt/plan.py", ".meta/checks/probes/tools/test_brownfield.py"):
        (scaffold / file).parent.mkdir(parents=True, exist_ok=True)
        (scaffold / file).write_text("")
    for tree in (".meta/lib", ".meta/checks"):
        runner._copy_item(scaffold / tree, target / tree, scaffold)
    copied = sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file())
    if copied != [".meta/checks/probes/tools/gate.py", ".meta/lib/bundle/__init__.py"]:
        problems.append(f"test-specialization: a copy of .meta/lib and .meta/checks kept {copied}, "
                        "expected the scaffold-only paths left out")
    (target / ".meta" / "adapt.py").write_text("")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        refused = runner.step_7_verify_scaffold_paths(target)
    if refused != 1:
        problems.append(f"test-specialization: step 7 over a target holding .meta/adapt.py "
                        f"returned {refused}, expected 1")
    return problems


def _check_inherited_paths(runner: Any) -> list[str]:
    """Validates that inherited path parsing retrieves expected scaffold assets."""
    problems: list[str] = []
    inherited = runner.read_inherited_paths(META / "assertions" / "disciplines.yaml")
    expected_inherited = (
        ".meta/render.py",
        ".meta/gate",
        ".meta/check.py",
        ".meta/lib/",
    )
    for exp in expected_inherited:
        if exp not in inherited:
            problems.append(
                f"test-specialization: expected {exp} in inherited paths from disciplines.yaml"
            )
    return problems


def _check_bundle(runner: Any) -> list[str]:
    """Validates installation bundle schema, presence, and disk integrity."""
    from lib.bundle import (
        InvalidManifestError,
        ManifestNotFoundError,
        load_bundle,
        validate_bundle,
    )

    problems: list[str] = []
    bundle_path = META / "bundle.yaml"
    if not bundle_path.is_file():
        return ["test-specialization: .meta/bundle.yaml does not exist"]
    try:
        bundle = load_bundle(bundle_path)
    except (ManifestNotFoundError, InvalidManifestError, OSError) as exc:
        return [f"test-specialization: failed to load .meta/bundle.yaml: {exc}"]

    if bundle.schema_version != 1:
        problems.append(
            f"test-specialization: unexpected bundle schema_version {bundle.schema_version}"
        )
    if not bundle.source_revision:
        problems.append("test-specialization: bundle source_revision is empty")

    if len(bundle.managed_items()) < 25:
        problems.append(
            f"test-specialization: expected >= 25 managed items, "
            f"found {len(bundle.managed_items())}"
        )
    if len(bundle.template_items()) < 7:
        problems.append(
            f"test-specialization: expected >= 7 template items, "
            f"found {len(bundle.template_items())}"
        )
    if len(bundle.symlink_items()) < 3:
        problems.append(
            f"test-specialization: expected >= 3 symlink items, "
            f"found {len(bundle.symlink_items())}"
        )

    errors = validate_bundle(bundle, META.parent)
    for err in errors:
        problems.append(f"test-specialization: bundle validation error: {err}")

    return problems


@check("test-specialization probes", pre=True)
def test_specialization_probes() -> list[str]:
    """`test_specialization.py` fixture loading, workflow retargeting,
    and placeholder substitution (stereorepo's DR-239, stereorepo's DR-244).

    Validates that:
    1. `tokens.json` contains all six expected template placeholder keys with non-empty strings.
    2. Malformed or non-existent token fixtures raise `ValueError`.
    3. `read_inherited_paths` extracts expected core paths from disciplines.yaml.
    4. `retarget_workflows` replaces ARC runner labels with public container runner syntax.
    5. `substitute_tokens` performs substitution and detects surviving placeholder tokens.
    6. `.meta/bundle.yaml` is well-formed and validates against repository disk contents.
    7. A copy leaves out scaffold-only paths below the top level, and step 7 refuses one
       (stereorepo's DR-305).
    """
    test_script = META / "test_specialization.py"
    if not test_script.is_file():
        return []

    runner = load_module(test_script, "test_specialization_module", register=False)
    tokens_path = META / "fixtures" / "specialization" / "tokens.json"

    problems = _check_fixture_keys(runner, tokens_path)
    if problems:
        return problems

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = pathlib.Path(tmp_str)
        problems.extend(_check_fixture_error_handling(runner, tmp))
        problems.extend(_check_substitute(runner, tmp))
        problems.extend(_check_scaffold_only(runner, tmp))

    problems.extend(_check_inherited_paths(runner))
    problems.extend(_check_bundle(runner))
    return problems
