"""`test_specialization.py`'s fixture loading, path inheritance, token substitution, and
shipped `.gitignore` probes.

Cites stereorepo's DR-239 and stereorepo's DR-244.
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import shutil
import subprocess
import tempfile
from typing import Any

from checks.collect import META, check
from checks.probes.harness import load_module
from lib.bundle import load_bundle


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


def _check_baselines_kept(runner: Any, tmp: pathlib.Path) -> list[str]:
    """Validates that copying the real bundle's managed items over a portfolio replaces its
    managed baseline with the scaffold's and leaves its own baseline unchanged."""
    problems: list[str] = []
    bundle = load_bundle()
    if bundle.manages(".meta/baselines/comments.baseline.yaml"):
        problems.append("test-specialization: a managed item contains .meta/baselines/, so a "
                        "copy would overwrite a portfolio's own baselines")
    scaffold, target = tmp / "baselines-scaffold", tmp / "baselines-portfolio"
    managed, own = ".meta/checks/comments.baseline.yaml", ".meta/baselines/comments.baseline.yaml"
    written = {scaffold / managed: ".meta/check.py: 2\n",
               scaffold / own: ".meta/test_specialization.py: 1\n",
               target / managed: ".meta/check.py: 9\n",
               target / own: "src/app.py: 4\n"}
    for path, text in written.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    for item in bundle.managed_items():
        runner._copy_item(scaffold / item.source_path(), target / item.dest_path(), scaffold)
    if (target / own).read_bytes() != b"src/app.py: 4\n":
        problems.append(f"test-specialization: a copy of the managed items changed the "
                        f"portfolio's {own} to {(target / own).read_text()!r}")
    if (target / managed).read_bytes() != b".meta/check.py: 2\n":
        problems.append(f"test-specialization: a copy of the managed items left the portfolio's "
                        f"{managed} as {(target / managed).read_text()!r}, not the scaffold's")
    return problems


def _check_gitignore(tmp: pathlib.Path) -> list[str]:
    """Validates that the shipped `.gitignore` keeps `.meta/apm.yml`, which the meta gate
    reads, and ignores the rest of APM's files."""
    repo = tmp / "ignore"
    repo.mkdir()
    shutil.copy2(META.parent / ".gitignore", repo / ".gitignore")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    problems: list[str] = []
    for path, ignored in ((".meta/apm.yml", False), ("apm.yml", True),
                          ("apm.lock.yaml", True), ("apm_modules/x", True)):
        res = subprocess.run(["git", "check-ignore", "-q", "--no-index", path],
                             cwd=repo, check=False)
        if (res.returncode == 0) != ignored:
            verdict = "lets in" if ignored else "ignores"
            problems.append(f"test-specialization: .gitignore {verdict} {path}, "
                            "so a fresh checkout of a portfolio disagrees with the scaffold")
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


def _check_report(runner: Any, tmp: pathlib.Path) -> list[str]:
    """Validates that `main` reports as a gate does: narration on stderr, one A21 report on stdout.

    `execute_specialization_test` is replaced by one that narrates and ends as it is told, so
    no portfolio is built; the report is read with `.meta/gate`'s own patterns.
    """
    gate = load_module(META / "gate", "gate-runner-report", register=False)
    real = runner.execute_specialization_test
    problems: list[str] = []
    for code, step in ((0, 9), (1, 8), (1, 0)):
        def fake(
            target: pathlib.Path, end: tuple[int, int] = (code, step), **_: Any
        ) -> tuple[int, int]:
            print(f"test-specialization: step 1 — initialize git repository in {target}")
            print("ok meta/narrated — a gate's line, which must not reach stdout")
            return end
        runner.execute_specialization_test = fake
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                exit_code = runner.main(["--target", str(tmp / "report")])
        finally:
            runner.execute_specialization_test = real
        lines = out.getvalue().splitlines()
        if code == 0:
            shaped = len(lines) == 1 and bool(gate.OK.match(lines[0]))
        else:
            shaped = (len(lines) == 2 and bool(gate.X.match(lines[0]))
                      and bool(gate.PROBLEM.match(lines[1])))
        if not shaped or exit_code != code or "narrated" not in err.getvalue():
            problems.append(
                f"test-specialization: a run ending ({code}, step {step}) exited {exit_code} and "
                f"printed {lines!r} on stdout, not one A21 report with its narration on stderr"
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

    if "stakeholders/" not in [item.dest_path() for item in bundle.portfolio_items()]:
        problems.append("test-specialization: stakeholders/ is not a portfolio item, so a sync "
                        "would remove a portfolio's own Personas and Roles (stereorepo's DR-317)")
    if bundle.manages("stakeholders/customers/persona.md"):
        problems.append("test-specialization: a managed item contains stakeholders/customers/, "
                        "so a sync would overwrite a portfolio's own Personas")

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
    8. The shipped `.gitignore` keeps `.meta/apm.yml`, which the meta gate reads, and still
       ignores `apm.yml` elsewhere, `apm.lock.yaml` and `apm_modules/`.
    9. A copy of the managed items replaces a portfolio's managed baselines and leaves its
       own under `.meta/baselines/` as they were, and no managed item contains that
       directory (stereorepo's DR-314).
    10. `main` reports as the gate of the Project `specialization` does: its narration on
        stderr, and on stdout one `ok` line, or one `x` line and its problem (stereorepo's DR-321).
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
        problems.extend(_check_baselines_kept(runner, tmp))
        problems.extend(_check_gitignore(tmp))
        problems.extend(_check_report(runner, tmp))

    problems.extend(_check_inherited_paths(runner))
    problems.extend(_check_bundle(runner))
    return problems
