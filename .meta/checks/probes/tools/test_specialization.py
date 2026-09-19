"""`test_specialization.py`'s fixture loading, path inheritance, and token substitution probes (solorepo's DR-239, solorepo's DR-244).
"""

from __future__ import annotations

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
            problems.append(f"test-specialization: missing or empty required token key {key} in fixture")
    return problems


def _check_fixture_error_handling(runner: Any, tmp: pathlib.Path) -> list[str]:
    """Validates that malformed JSON or non-string token structures raise ValueError."""
    problems: list[str] = []
    bad_json = tmp / "bad.json"
    bad_json.write_text("{not valid json", encoding="utf-8")
    try:
        runner.load_tokens(bad_json)
        problems.append("test-specialization: load_tokens accepted malformed JSON without raising ValueError")
    except ValueError:
        pass

    bad_type = tmp / "bad_type.json"
    bad_type.write_text(json.dumps({"KEY": 123}), encoding="utf-8")
    try:
        runner.load_tokens(bad_type)
        problems.append("test-specialization: load_tokens accepted non-string value without raising ValueError")
    except ValueError:
        pass
    return problems


def _check_retarget_and_substitute(runner: Any, tmp: pathlib.Path) -> list[str]:
    """Validates workflow runner retargeting and token substitution."""
    problems: list[str] = []
    wf_dir = tmp / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    sample_wf = wf_dir / "test.yml"
    sample_wf.write_text("jobs:\n  test:\n    runs-on: arc-runner-set\n", encoding="utf-8")
    retargeted_count = runner.retarget_workflows(wf_dir)
    if retargeted_count != 1:
        problems.append(f"test-specialization: expected retarget_workflows to retarget 1 file, got {retargeted_count}")
    retargeted_content = sample_wf.read_text(encoding="utf-8")
    if "runs-on: arc-runner-set" in retargeted_content or "solorepo-runner" not in retargeted_content:
        problems.append("test-specialization: retarget_workflows did not substitute runner configuration correctly")

    prefix = "_" + "_"
    test_token_placeholder = f"{prefix}PORTFOLIO_NAME{prefix}"
    unknown_placeholder = f"{prefix}UNKNOWN_TOKEN{prefix}"
    sub_file = tmp / "sample.txt"
    sub_file.write_text(f"Hello {test_token_placeholder}! Unhandled {unknown_placeholder} here.", encoding="utf-8")
    surviving = runner.substitute_tokens(tmp, {"PORTFOLIO_NAME": "World"})
    if not surviving:
        problems.append("test-specialization: substitute_tokens failed to report surviving unreplaced placeholder")
    sub_content = sub_file.read_text(encoding="utf-8")
    if "Hello World!" not in sub_content:
        problems.append(f"test-specialization: substitute_tokens failed to replace token: {sub_content!r}")
    return problems


def _check_inherited_paths(runner: Any) -> list[str]:
    """Validates that inherited path parsing retrieves expected scaffold assets."""
    problems: list[str] = []
    inherited = runner.read_inherited_paths(META / "assertions" / "disciplines.yaml")
    expected_inherited = (".meta/render.py", ".meta/gate", ".meta/check.py", ".github/workflows/coder.yml")
    for exp in expected_inherited:
        if exp not in inherited:
            problems.append(f"test-specialization: expected {exp} in inherited paths from disciplines.yaml")
    return problems


@check("test-specialization probes", pre=True)
def test_specialization_probes() -> list[str]:
    """`test_specialization.py` fixture loading, workflow retargeting, and placeholder substitution (solorepo's DR-239, solorepo's DR-244).

    Validates that:
    1. `tokens.json` contains all six expected template placeholder keys with non-empty strings.
    2. Malformed or non-existent token fixtures raise `ValueError`.
    3. `read_inherited_paths` extracts expected core paths from disciplines.yaml.
    4. `retarget_workflows` replaces ARC runner labels with public container runner syntax.
    5. `substitute_tokens` performs substitution and detects surviving placeholder tokens.
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
        problems.extend(_check_retarget_and_substitute(runner, tmp))

    problems.extend(_check_inherited_paths(runner))
    return problems
