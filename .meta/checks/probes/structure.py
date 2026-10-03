"""Probes for Structure ontology invariants over assertion datasets (stereorepo's DR-342).

Validates that structure graph checks correctly enforce domain invariants across
registered Bootstraps and project bindings (Article 7). Probes sit in their own
module under `.meta/checks/probes/` by subject under test (stereorepo's DR-150).

History in graph.history.md (stereorepo's DR-171).
"""
from typing import Any

from checks import graph
from checks.collect import check


@check("bootstrap discipline coverage probes", pre=True)
def bootstrap_discipline_coverage_probes() -> list[str]:
    """Verify that bootstrap_discipline_coverage enforces coverage invariants (Article 7).

    Pins clean conformance of fully populated and exempt declarations, detection of missing
    disciplines, empty gate step lists, missing exemption reasons, disallowed portfolio_scoped
    declarations on project-binding disciplines, and duplicate declarations.

    Returns:
        list[str]: Findings naming cases whose diagnostic output did not match expectations.
    """
    valid_impls: list[dict[str, Any]] = [
        {
            "discipline": "work:discipline/literate-programming",
            "status": "implemented",
            "held_by": ["doc", "test", "orphans"],
        },
        {
            "discipline": "work:discipline/ratchet",
            "status": "implemented",
            "held_by": ["lints", "ruff", "types"],
        },
        {
            "discipline": "work:discipline/observed-failure",
            "status": "implemented",
            "held_by": ["mutants"],
        },
        {
            "discipline": "work:discipline/nothing-unconsumed",
            "status": "implemented",
            "held_by": ["orphans", "evidence"],
        },
        {
            "discipline": "work:discipline/seeded-artifacts",
            "status": "implemented",
            "held_by": ["render"],
        },
        {
            "discipline": "work:discipline/written-decisions",
            "status": "exempt",
            "exemption_reason": "Verified by portfolio gate.",
        },
    ]

    problems: list[str] = []

    clean_index: dict[str, Any] = {
        "work:bootstrap/clean": (
            "Bootstrap",
            {"discipline_implementations": valid_impls},
            "bootstraps.yaml",
        )
    }
    findings = graph.bootstrap_discipline_coverage(clean_index)
    if findings:
        problems.append(
            f"bootstrap discipline coverage: clean case expected no findings, got {findings!r}"
        )

    missing_impls: list[dict[str, Any]] = [
        e for e in valid_impls if e["discipline"] != "work:discipline/ratchet"
    ]
    missing_index: dict[str, Any] = {
        "work:bootstrap/missing": (
            "Bootstrap",
            {"discipline_implementations": missing_impls},
            "bootstraps.yaml",
        )
    }
    findings = graph.bootstrap_discipline_coverage(missing_index)
    expected_missing = (
        "work:bootstrap/missing: missing discipline entry for 'work:discipline/ratchet'"
    )
    if expected_missing not in findings:
        problems.append(
            f"bootstrap discipline coverage: expected missing ratchet finding, got {findings!r}"
        )

    empty_held_by_impls: list[dict[str, Any]] = [
        {**e, "held_by": []} if e["discipline"] == "work:discipline/ratchet" else dict(e)
        for e in valid_impls
    ]
    empty_held_by_index: dict[str, Any] = {
        "work:bootstrap/empty_held_by": (
            "Bootstrap",
            {"discipline_implementations": empty_held_by_impls},
            "bootstraps.yaml",
        )
    }
    findings = graph.bootstrap_discipline_coverage(empty_held_by_index)
    expected_empty = (
        "work:bootstrap/empty_held_by: discipline 'work:discipline/ratchet' is implemented "
        "but names no gate steps in 'held_by'"
    )
    if expected_empty not in findings:
        problems.append(
            f"bootstrap discipline coverage: expected empty held_by finding, got {findings!r}"
        )

    no_reason_impls: list[dict[str, Any]] = [
        {**e, "exemption_reason": ""}
        if e["discipline"] == "work:discipline/written-decisions"
        else dict(e)
        for e in valid_impls
    ]
    no_reason_index: dict[str, Any] = {
        "work:bootstrap/no_reason": (
            "Bootstrap",
            {"discipline_implementations": no_reason_impls},
            "bootstraps.yaml",
        )
    }
    findings = graph.bootstrap_discipline_coverage(no_reason_index)
    expected_reason = (
        "work:bootstrap/no_reason: discipline 'work:discipline/written-decisions' is exempt "
        "but carries no 'exemption_reason'"
    )
    if expected_reason not in findings:
        problems.append(
            f"bootstrap discipline coverage: expected missing exemption finding, got {findings!r}"
        )

    portfolio_scoped_impls: list[dict[str, Any]] = [
        {**e, "status": "portfolio_scoped"}
        if e["discipline"] == "work:discipline/ratchet"
        else dict(e)
        for e in valid_impls
    ]
    portfolio_scoped_index: dict[str, Any] = {
        "work:bootstrap/portfolio_scoped": (
            "Bootstrap",
            {"discipline_implementations": portfolio_scoped_impls},
            "bootstraps.yaml",
        )
    }
    findings = graph.bootstrap_discipline_coverage(portfolio_scoped_index)
    expected_scoped = (
        "work:bootstrap/portfolio_scoped: project-binding discipline 'work:discipline/ratchet' "
        "cannot be marked 'portfolio_scoped'"
    )
    if expected_scoped not in findings:
        problems.append(
            f"bootstrap discipline coverage: expected rejected scoped finding, got {findings!r}"
        )

    dup_impls: list[dict[str, Any]] = [*valid_impls, valid_impls[0]]
    dup_index: dict[str, Any] = {
        "work:bootstrap/duplicate": (
            "Bootstrap",
            {"discipline_implementations": dup_impls},
            "bootstraps.yaml",
        )
    }
    findings = graph.bootstrap_discipline_coverage(dup_index)
    expected_dup = (
        "work:bootstrap/duplicate: discipline 'work:discipline/literate-programming' "
        "declared more than once"
    )
    if expected_dup not in findings:
        problems.append(
            f"bootstrap discipline coverage: expected duplicate finding, got {findings!r}"
        )

    return problems
