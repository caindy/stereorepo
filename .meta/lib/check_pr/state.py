"""Pull request state classification and lifecycle predicates.

Defines the formal states of a pull request across autonomous GitHub Actions
loops and interactive local agent harnesses, and provides state classification
over pull request metadata, reviews, check rollups, and threads.
"""

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any

from lib.check_pr.review import unaddressed_threads as unaddressed_threads

GREEN: frozenset[str] = frozenset({"SUCCESS", "NEUTRAL", "SKIPPED"})
"""Check status values that signify concluded and passed checks."""

UNCONCLUDED: frozenset[str] = frozenset({
    "PENDING",
    "IN_PROGRESS",
    "QUEUED",
    "WAITING",
    "REQUESTED",
    "EXPECTED",
})
"""Check status values that signify checks currently running or queued."""


class PullRequestState(StrEnum):
    """Lifecycle states of a pull request.

    Attributes:
        DRAFT: Pull request is in draft mode.
        AWAITING_GATE: Status checks are pending, queued, or running, or initial checks are absent.
        GATE_FAILED: One or more status checks failed or were cancelled.
        AWAITING_REVIEW: Status checks are clean, and review has been requested or verdict is pending.
        CHANGES_REQUESTED: Reviewer requested changes, or approved with unaddressed threads owed an answer.
        NEEDS_REBASE: Branch conflicts with base (mergeable status is CONFLICTING).
        AWAITING_PROMOTION: Reviewer approved, but parked noticed-and-not-done threads remain open.
        READY_TO_MERGE: Reviewer approved, all checks green, zero unaddressed threads, and mergeable is clean.
        MERGED: Pull request is merged into base branch.
        CLOSED: Pull request is closed unmerged.
    """

    DRAFT = "DRAFT"
    AWAITING_GATE = "AWAITING_GATE"
    GATE_FAILED = "GATE_FAILED"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    NEEDS_REBASE = "NEEDS_REBASE"
    AWAITING_PROMOTION = "AWAITING_PROMOTION"
    READY_TO_MERGE = "READY_TO_MERGE"
    MERGED = "MERGED"
    CLOSED = "CLOSED"


CODER_ACTIONABLE_STATES = frozenset({
    PullRequestState.GATE_FAILED,
    PullRequestState.CHANGES_REQUESTED,
    PullRequestState.NEEDS_REBASE,
    PullRequestState.AWAITING_PROMOTION,
    PullRequestState.READY_TO_MERGE,
    PullRequestState.MERGED,
    PullRequestState.CLOSED,
})
"""Pull request states that require action from the coder Role to advance work toward merge."""


def latest_verdict(pr: Mapping[str, Any], reviewer_login: str | None = None) -> str:
    """The state of the designated reviewer's most recent review, upper-cased, or the empty string.

    Args:
        pr: Pull request metadata mapping.
        reviewer_login: Optional login of the designated reviewer.

    Returns:
        The upper-cased review state ('APPROVED', 'CHANGES_REQUESTED', etc.), or empty string.
    """
    reviews = pr.get("latestReviews") or pr.get("reviews") or []
    matching = [
        r for r in reviews
        if not reviewer_login or (r.get("author") or {}).get("login") == reviewer_login
    ]
    if not matching:
        return ""
    return str(matching[-1].get("state") or "").upper()


def is_review_requested(pr: Mapping[str, Any], reviewer_login: str | None = None) -> bool:
    """Determines if a review is currently requested on the pull request.

    Args:
        pr: Pull request metadata mapping.
        reviewer_login: Optional login of the designated reviewer.

    Returns:
        True if review is requested of the specified reviewer (or any reviewer), False otherwise.
    """
    requests = pr.get("reviewRequests") or []
    logins = [
        r.get("login") or r.get("name") or (r.get("requestedReviewer") or {}).get("login") or ""
        if isinstance(r, Mapping) else str(r)
        for r in requests
    ]
    return reviewer_login in logins if reviewer_login else bool(logins)


def deduplicate_checks(
    contexts: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Filters duplicate check runs sharing a name, retaining only the latest entry.

    When multiple check runs share a name (e.g. repeated runs, re-dispatches, or body
    revisions), keeps only the latest entry ordered by startedAt, completedAt, or createdAt.

    Args:
        contexts: Sequence of check context mappings (such as from statusCheckRollup).

    Returns:
        Deduplicated list of check context mappings preserving only the latest run per name.
    """
    def timestamp(c: Mapping[str, Any]) -> str:
        completed = c.get("completedAt") or ""
        if str(completed).startswith("0001"):
            completed = ""
        return str(c.get("startedAt") or completed or c.get("createdAt") or "")

    deduped: dict[str, Mapping[str, Any]] = {}
    for c in sorted(contexts, key=timestamp):
        name = str(c.get("name") or c.get("context") or "check")
        deduped[name] = c
    return list(deduped.values())


def checks_summary(
    checks: Mapping[str, tuple[str, str | None]] | Sequence[Mapping[str, Any]] | None,
) -> tuple[bool, bool, bool]:
    """Summarizes rollup check values into status flags.

    Args:
        checks: Optional mapping of check names to (conclusion, details_url) tuples,
            or sequence of check context mappings (such as from statusCheckRollup).

    Returns:
        A tuple of (has_failures, all_green, any_unconcluded).
    """
    if not checks:
        return False, False, True
    if isinstance(checks, Sequence):
        deduped = deduplicate_checks([c for c in checks if isinstance(c, Mapping)])
        values = [
            str(c.get("conclusion") or c.get("state") or c.get("status") or "PENDING").upper()
            for c in deduped
        ]
    elif isinstance(checks, Mapping):
        values = [
            v[0].upper() if isinstance(v, (tuple, list)) else str(v).upper()
            for v in checks.values()
        ]
    else:
        values = []

    if not values:
        return False, False, True

    has_failures = any(
        v not in GREEN and v not in UNCONCLUDED
        for v in values
    )
    all_green = all(v in GREEN for v in values)
    any_unconcluded = any(v in UNCONCLUDED for v in values)
    return has_failures, all_green, any_unconcluded


def _threads_from_pr(
    pr: Mapping[str, Any],
    threads: Sequence[Mapping[str, Any]] | None,
) -> Sequence[Mapping[str, Any]]:
    """Extracts review thread nodes from pr mapping or provided threads sequence."""
    if threads is not None:
        return threads
    threads_val = pr.get("reviewThreads")
    raw_nodes: Any = None
    if isinstance(threads_val, Mapping):
        raw_nodes = threads_val.get("nodes")
    elif isinstance(threads_val, Sequence):
        raw_nodes = threads_val
    if isinstance(raw_nodes, Sequence):
        res: list[Mapping[str, Any]] = []
        for node in raw_nodes:
            if isinstance(node, Mapping):
                res.append(node)
        return res
    return []


def _approved_state(
    unaddressed_owed: bool,
    unaddressed_parked: bool,
    all_green: bool,
    mergeable: str,
) -> PullRequestState | None:
    """Computes state transition when reviewer verdict is APPROVED."""
    if unaddressed_owed:
        return PullRequestState.CHANGES_REQUESTED
    if unaddressed_parked:
        return PullRequestState.AWAITING_PROMOTION
    if all_green and mergeable == "MERGEABLE":
        return PullRequestState.READY_TO_MERGE
    return None


def classify_pr(
    pr: Mapping[str, Any],
    checks: Mapping[str, tuple[str, str | None]] | Sequence[Mapping[str, Any]] | None = None,
    threads: Sequence[Mapping[str, Any]] | None = None,
    reviewer_login: str | None = None,
) -> PullRequestState:
    """Classifies a pull request into its current PullRequestState.

    Args:
        pr: Pull request metadata mapping from GitHub.
        checks: Optional mapping of check names to (conclusion, details_url) tuples,
            or sequence of check context mappings. If None, uses pr.get("statusCheckRollup").
        threads: Optional sequence of review thread node mappings. If None,
            uses pr.get("reviewThreads") or empty sequence.
        reviewer_login: Optional login of the designated reviewer Role.

    Returns:
        PullRequestState: The classified lifecycle state.
    """
    state_str = str(pr.get("state", "OPEN")).upper()
    if state_str in ("MERGED", "CLOSED"):
        return PullRequestState(state_str)

    if pr.get("isDraft"):
        return PullRequestState.DRAFT

    mergeable = str(pr.get("mergeable") or "UNKNOWN").upper()
    if mergeable == "CONFLICTING":
        return PullRequestState.NEEDS_REBASE

    if checks is None:
        checks = pr.get("statusCheckRollup")

    has_failures, all_green, any_unconcluded = checks_summary(checks)
    if has_failures:
        return PullRequestState.GATE_FAILED

    thread_nodes = _threads_from_pr(pr, threads)
    unaddressed_owed = unaddressed_threads(thread_nodes, parked=False)
    unaddressed_parked = unaddressed_threads(thread_nodes, parked=True)
    review_requested = is_review_requested(pr, reviewer_login)

    verdict = latest_verdict(pr, reviewer_login)
    if verdict == "CHANGES_REQUESTED" and (unaddressed_owed or not review_requested):
        return PullRequestState.CHANGES_REQUESTED

    if verdict == "APPROVED":
        st = _approved_state(bool(unaddressed_owed), bool(unaddressed_parked), all_green, mergeable)
        if st is not None:
            return st

    if any_unconcluded:
        return PullRequestState.AWAITING_GATE

    if is_review_requested(pr, reviewer_login) or all_green:
        return PullRequestState.AWAITING_REVIEW

    return PullRequestState.AWAITING_GATE
