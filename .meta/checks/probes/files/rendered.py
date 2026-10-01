"""`lib.render.targets` functions driven against invocation counts and orphan detection.

Observed Failure (Article 23) requires watching guardrails fail. The render check
pass evaluates target functions once into a snapshot, passing the shared snapshot to
`rendered()`, `unrendered()`, and `gitattributes()` to prevent repeated execution of
expensive target generators.
"""

from typing import Any

from checks.collect import check
from lib.render import targets


def _probe_invocations(calls: dict[str, int]) -> list[str]:
    problems: list[str] = []
    for target_name, count in calls.items():
        if count != 1:
            problems.append(
                f"render target {target_name!r} was called {count} times, expected exactly 1"
            )
    return problems


def _probe_rendered_pages(pages: dict[str, str]) -> list[str]:
    problems: list[str] = []
    if pages.get("probe_scalar.md") != "scalar content":
        problems.append("rendered pages missing scalar target output")
    if pages.get("probe_pkg/a.md") != "content a":
        problems.append("rendered pages missing expanded dict target probe_pkg/a.md")
    if pages.get("probe_pkg/b.md") != "content b":
        problems.append("rendered pages missing expanded dict target probe_pkg/b.md")
    if "probe_pkg" in pages:
        problems.append("rendered pages retained dict container key 'probe_pkg'")
    if "probe_orphan.md" in pages:
        problems.append("rendered pages included None target 'probe_orphan.md'")
    if "../.gitattributes" not in pages:
        problems.append("rendered pages missing '../.gitattributes'")
    return problems


def _probe_gitattributes(gitattr: str) -> list[str]:
    problems: list[str] = []
    if "/.meta/probe_scalar.md merge=union" not in gitattr:
        problems.append("gitattributes missing probe_scalar.md union entry")
    if "/.meta/probe_pkg/a.md merge=union" not in gitattr:
        problems.append("gitattributes missing probe_pkg/a.md union entry")
    if "probe_orphan.md" in gitattr:
        problems.append("gitattributes included None target probe_orphan.md")
    return problems


def _probe_unrendered() -> list[str]:
    problems: list[str] = []
    snap_orphan_test: dict[str, Any] = {
        "disciplines.md": None,
        "nonexistent_file_xyz.md": None,
        "charter.md": "existing content",
    }
    detected_orphans = targets.unrendered(snap_orphan_test)
    if detected_orphans != ["disciplines.md"]:
        problems.append(
            f"unrendered orphan detection returned {detected_orphans}, expected ['disciplines.md']"
        )
    return problems


def _probe_fallbacks() -> list[str]:
    problems: list[str] = []
    snap_default = targets.snapshot()
    if not isinstance(snap_default, dict) or not snap_default:
        problems.append("snapshot() returned empty or non-dict result")
    rendered_default = targets.rendered(None)
    if not rendered_default or "../.gitattributes" not in rendered_default:
        problems.append("rendered(None) fallback failed to render default targets")
    gitattr_default = targets.gitattributes(None)
    if "merge=union" not in gitattr_default:
        problems.append("gitattributes(None) fallback failed to generate union entries")
    return problems


def _probe_fallbacks_without_specialize() -> list[str]:
    """The fallbacks judged over default targets holding no `../SPECIALIZE.md`, as a portfolio's."""
    saved = targets.TARGETS
    targets.TARGETS = {"probe_page.md": lambda: "page", "../.gitattributes": targets.gitattributes}
    try:
        problems = _probe_fallbacks()
    finally:
        targets.TARGETS = saved
    return [f"without ../SPECIALIZE.md: {problem}" for problem in problems]


@check("rendered artifact probes", pre=True)
def rendered_artifact_probes() -> list[str]:
    """**Rendered artifact probes** verify single-evaluation snapshot reuse and orphan detection.

    Ensures that target functions are called exactly once across a render check pass,
    dict targets expand properly into individual files, None targets are excluded from
    rendered pages, and unrendered orphan files are detected without redundant calls.
    """
    calls = {"scalar": 0, "dict": 0, "none": 0}

    def mock_scalar() -> str:
        calls["scalar"] += 1
        return "scalar content"

    def mock_dict() -> dict[str, str]:
        calls["dict"] += 1
        return {"probe_pkg/a.md": "content a", "probe_pkg/b.md": "content b"}

    def mock_none() -> None:
        calls["none"] += 1

    mock_targets: dict[str, targets.TargetFn] = {
        "probe_scalar.md": mock_scalar,
        "probe_pkg": mock_dict,
        "probe_orphan.md": mock_none,
        "../.gitattributes": targets.gitattributes,
    }

    snap = targets.snapshot(mock_targets)
    pages = targets.rendered(snap)
    targets.unrendered(snap)
    gitattr = targets.gitattributes(snap)

    problems: list[str] = []
    problems.extend(_probe_invocations(calls))
    problems.extend(_probe_rendered_pages(pages))
    problems.extend(_probe_gitattributes(gitattr))
    problems.extend(_probe_unrendered())
    problems.extend(_probe_fallbacks())
    problems.extend(_probe_fallbacks_without_specialize())
    return problems
