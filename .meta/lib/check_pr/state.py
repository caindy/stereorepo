"""Lifecycle states of a pull request and of an Issue, and the classification over each.

`classify_pr` reads a pull request off its metadata, reviews, check rollup and
threads, for the autonomous loops and the local harnesses alike.
`classify_issue` reads an Issue off its state, labels and assignees and the
pull request on its loop branch. The Issue half is the first seam of
solorepo's DR-264: the coder's take door reads through it, in `sweep.take`,
while `just next` and `.meta/say/move` still read an Issue's labels for
themselves until the seams that move them land.
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
        CHANGES_REQUESTED: Reviewer requested changes, approved with unaddressed threads owed an
            answer, or left a comment verdict with threads owed and no request standing
            (solorepo's DR-265).
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


class IssueState(StrEnum):
    """Lifecycle states of an Issue.

    The order the states are decided in is the take door's: a closed Issue is
    finished whatever else is
    true of it; a claim with a pull request open is a run standing, whatever
    the level; `hard` is the solo's; a Challenge at no level a loop takes is
    nobody's to take; and only then does the claim or the pull request say
    whether a loop starts, resumes, or is already standing.

    Attributes:
        CLOSED: Closed, by a merge or by hand; finished work.
        UNLABELLED: Neither `challenge` nor `roadmap`; nothing offers it.
        ROADMAP: Intended and deferred; never taken.
        UNREAD: A Challenge with no level; no reviewer has read it (solorepo's DR-230).
        HANDED_BACK: `human`; the solo's, and no Job's.
        HELD: `hard`; the solo's with a session beside them, and a loop stands down.
        TAKEN: Claimed by the coder with its pull request open; a run is standing.
        CLAIMED: Claimed by the coder with no pull request; a run that has not
            opened yet, or one that ended holding the claim.
        RESUMABLE: At a level a loop takes, its pull request open and no claim;
            a hand-back the solo has answered, taken up again.
        OFFERED: At a level a loop takes, unclaimed, no pull request; the
            loop's the moment the label landed.
    """

    CLOSED = "CLOSED"
    UNLABELLED = "UNLABELLED"
    ROADMAP = "ROADMAP"
    UNREAD = "UNREAD"
    HANDED_BACK = "HANDED_BACK"
    HELD = "HELD"
    TAKEN = "TAKEN"
    CLAIMED = "CLAIMED"
    RESUMABLE = "RESUMABLE"
    OFFERED = "OFFERED"


LOOP_LEVELS: tuple[str, ...] = ("easy", "medium")
"""The levels a loop takes the moment the label lands, which is what makes a Challenge a
loop's and not the solo's (solorepo's DR-112); `human` and `hard` are the solo's, and so is
a pull request on their Challenge."""

NOT_TAKEN_STATES = frozenset({
    IssueState.UNLABELLED,
    IssueState.ROADMAP,
    IssueState.UNREAD,
    IssueState.HANDED_BACK,
})
"""Issue states at no level a loop takes, which the take door calls stale."""


def issue_labels(issue: Mapping[str, Any]) -> list[str]:
    """The label names on an Issue, as `gh issue view --json labels` lists them."""
    return [str(lbl.get("name") or "") for lbl in issue.get("labels") or []
            if isinstance(lbl, Mapping)]


def classify_issue(
    issue: Mapping[str, Any],
    coder_login: str | None,
    open_pull: bool,
) -> IssueState:
    """Classifies an Issue into its current IssueState.

    Args:
        issue: Issue metadata mapping from GitHub, carrying `state`, `labels`
            and `assignees` as `gh issue view --json` lists them.
        coder_login: The coder Role's login, whose assignment is the claim; None
            reads the Issue as if nobody held it, which is how the doors a run
            arrives at with its own pull request read it.
        open_pull: Whether a pull request is open on the Issue's loop branch.

    Returns:
        IssueState: The classified lifecycle state.
    """
    if str(issue.get("state", "OPEN")).upper() != "OPEN":
        return IssueState.CLOSED
    labels = issue_labels(issue)
    claimed = bool(coder_login) and any(
        isinstance(a, Mapping) and a.get("login") == coder_login
        for a in issue.get("assignees") or []
    )
    if claimed and open_pull:
        return IssueState.TAKEN
    if "hard" in labels:
        return IssueState.HELD
    level = next((lvl for lvl in LOOP_LEVELS if lvl in labels), None)
    if level is None:
        if "human" in labels:
            return IssueState.HANDED_BACK
        if "challenge" in labels:
            return IssueState.UNREAD
        if "roadmap" in labels:
            return IssueState.ROADMAP
        return IssueState.UNLABELLED
    if claimed:
        return IssueState.CLAIMED
    if open_pull:
        return IssueState.RESUMABLE
    return IssueState.OFFERED


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


def is_verdict(review: Mapping[str, Any]) -> bool:
    """Whether a review is a verdict rather than the record GitHub keeps around an inline thread.

    Args:
        review: A review mapping carrying `state` and `body`.

    Returns:
        True where the review approves, requests changes, or comments with a
        body; False for a comment review with no body.
    """
    return str(review.get("state") or "").upper() != "COMMENTED" or bool(review.get("body"))


def standing_verdict(pr: Mapping[str, Any], reviewer_login: str | None = None) -> str:
    """The state of the reviewer's most recent verdict, upper-cased, or the empty string.

    Both of GitHub's review listings are read, `reviews` before
    `latestReviews`, and the first to yield a verdict answers. `reviews` is the
    whole history; `latestReviews` is one review per author and holds the
    newest whatever it is, so the bodiless record GitHub keeps around a reply
    on a thread displaces the verdict standing beneath it there and nowhere
    else. Reading `latestReviews` alone returns the empty string for a pull
    request whose reviewer requested changes and has since replied on a
    thread, which is the shape a cancelled review run leaves
    (solorepo's DR-265). `latestReviews` remains the fallback for a caller
    that asked GitHub for it alone.

    Args:
        pr: Pull request metadata mapping.
        reviewer_login: Optional login of the designated reviewer.

    Returns:
        The upper-cased state of the newest review `is_verdict` admits and
        GitHub has not dismissed ('APPROVED', 'CHANGES_REQUESTED',
        'COMMENTED'), or the empty string where the reviewer left none.
    """
    for listing in ("reviews", "latestReviews"):
        matching = [
            r for r in pr.get(listing) or []
            if (not reviewer_login or (r.get("author") or {}).get("login") == reviewer_login)
            and is_verdict(r) and str(r.get("state") or "").upper() != "DISMISSED"
        ]
        if matching:
            return str(matching[-1].get("state") or "").upper()
    return ""


def verdicts_given(pr: Mapping[str, Any], reviewer_login: str) -> int:
    """How many verdicts the reviewer has submitted on the pull request, on any head.

    A verdict is what `is_verdict` admits, a review GitHub has since dismissed
    included: the count is of what was submitted, and a dismissal changes a
    review rather than adding one.

    Args:
        pr: Pull request metadata mapping carrying `reviews`.
        reviewer_login: The login whose verdicts are counted.

    Returns:
        The count.
    """
    return sum(1 for r in pr.get("reviews") or []
               if (r.get("author") or {}).get("login") == reviewer_login and is_verdict(r))


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

    if (unaddressed_owed and not review_requested
            and standing_verdict(pr, reviewer_login) == "COMMENTED"):
        return PullRequestState.CHANGES_REQUESTED

    if verdict == "APPROVED" and not review_requested:
        st = _approved_state(bool(unaddressed_owed), bool(unaddressed_parked), all_green, mergeable)
        if st is not None:
            return st

    if any_unconcluded:
        return PullRequestState.AWAITING_GATE

    if is_review_requested(pr, reviewer_login) or all_green:
        return PullRequestState.AWAITING_REVIEW

    return PullRequestState.AWAITING_GATE
