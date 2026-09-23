"""What has happened on a pull request since: continuously under `watch`, once under `resume`.

`watch` prints one line per change and exits on an actionable event or when
the pull request closes. `resume` reads what GitHub holds once and prints the
briefing an arriving Job needs. A snapshot keys checks by name, reduced to the
latest run of each, so a re-run concluding as its predecessor did is still a
change. A third mode answering the same question belongs here.
"""
import sys
from collections.abc import Mapping
from typing import Any

from lib.check_pr import github, review
from lib.check_pr.state import (
    CODER_ACTIONABLE_STATES,
    GREEN,
    UNCONCLUDED,
    PullRequestState,
    classify_pr,
)
from lib.check_pr.state import (
    deduplicate_checks as deduplicate_checks,
)

Snapshot = tuple[int, str, dict[str, Any], dict[str, Any], dict[str, Any],
                 dict[str, tuple[str, str | None]], str, dict[str, Any]]
"""One reading of a pull request: number, state, comments, reviews and threads each by id,
checks by name paired with the run that answered, mergeability, and the raw pull mapping."""


def snapshot(ref: str | int) -> Snapshot:
    """Queries pull request metadata, comments, reviews, threads, and check rollups.

    Args:
        ref: Pull request number, URL, or head branch reference.

    Returns:
        tuple: (number, state, comments_dict, reviews_dict, threads_dict, checks_dict, mergeable).

    Checks are keyed by name, so the several runs a name accumulates — a
    repeated dispatch, a cancelled run — are reduced to the latest by
    `deduplicate_checks` before the key is taken. Each answers with its
    conclusion and the URL of the run that reached it: a rerun concluding as
    its predecessor did is otherwise indistinguishable from no rerun at all,
    and the watcher would sit on it.
    """
    pr = github.gh(
        "pr",
        "view",
        str(ref),
        "--json",
        "number,state,comments,reviews,latestReviews,mergeable,isDraft,reviewRequests",
    )
    comments = {c["id"]: c for c in pr.get("comments") or []}
    reviews = {r["id"]: r for r in pr.get("reviews") or []}
    threads_ = {t["id"]: t for t in github.threads(ref)}
    sorted_checks = deduplicate_checks(github.rollup_of(pr["number"]))
    checks = {
        str(c.get("name") or c.get("context") or "check"): (
            str(c.get("conclusion") or c.get("state") or c.get("status") or "PENDING"),
            c.get("detailsUrl") or c.get("targetUrl"),
        )
        for c in sorted_checks
    }
    return (
        int(pr["number"]),
        str(pr["state"]),
        comments,
        reviews,
        threads_,
        checks,
        str(pr.get("mergeable") or "UNKNOWN"),
        pr,
    )


def where_of(thread: dict[str, Any]) -> str:
    """The path and line a thread is anchored to, or `the pull request` for one on the conversation."""
    if thread.get("comment"):
        return review.COMMENT_WHERE
    return str(thread["path"] or "the pull request") + (f":{thread['line']}" if thread.get("line") else "")


def new_comments(comments: Mapping[str, Any], before: Mapping[str, Any]) -> list[str]:
    """Print each comment not in `before` that is not this Actor's own; the actionable line for each."""
    actionable: list[str] = []
    for cid in comments.keys() - before.keys():
        c = comments[cid]
        if not review.mine(c["body"]):
            print(f"comment by {c['author']['login']}: {review.said(c['body'])}", flush=True)
            actionable.append(f"comment by {c['author']['login']}")
    return actionable


def new_reviews(reviews: Mapping[str, Any], before: Mapping[str, Any]) -> list[str]:
    """Print each review not in `before` that is not this Actor's own; the actionable line for each."""
    actionable: list[str] = []
    for rid in reviews.keys() - before.keys():
        r = reviews[rid]
        if not review.mine(r.get("body", "")):
            print(f"review by {r['author']['login']}: {r['state']} {review.said(r.get('body', ''))}",
                  flush=True)
            actionable.append(f"review by {r['author']['login']} ({r['state']})")
    return actionable


def new_threads(threads_: Mapping[str, Any], before: Mapping[str, Any]) -> list[str]:
    """Print each thread not in `before` with its opening comment; the actionable line for each."""
    actionable: list[str] = []
    for tid in threads_.keys() - before.keys():
        t = threads_[tid]
        nodes = t["comments"]["nodes"]
        first_author = (nodes[0]["author"] or {}).get("login", "someone") if nodes else "someone"
        first_body = nodes[0]["body"] if nodes else ""
        print(f"new thread on {where_of(t)} by {first_author}: {review.said(first_body)}", flush=True)
        actionable.append(f"new thread on {where_of(t)}")
    return actionable


def thread_activity(threads_: Mapping[str, Any], before: Mapping[str, Any]) -> list[str]:
    """Print each thread that grew by a comment not this Actor's own, and each thread resolved since `before`; the actionable line for each comment."""
    actionable: list[str] = []
    for tid, t in threads_.items():
        was = before.get(tid)
        nodes = t["comments"]["nodes"]
        was_len = len(was["comments"]["nodes"]) if was else 0
        if was is None or len(nodes) > was_len:
            last = nodes[-1] if nodes else None
            if last and not review.mine(last["body"]):
                who = (last["author"] or {}).get("login", "someone")
                print(f"thread {tid} on {where_of(t)} by {who}: {review.said(last['body'])}", flush=True)
                actionable.append(f"thread comment by {who}")
        if was is not None and t["isResolved"] and not was["isResolved"]:
            by = (t.get("resolvedBy") or {}).get("login", "someone")
            print(f"thread {tid} on {where_of(t)} resolved by {by}", flush=True)
    return actionable


def check_changes(checks: Mapping[str, tuple[str, str | None]],
                  before: Mapping[str, tuple[str, str | None]]) -> list[str]:
    """Print each check whose value changed or that ran again since `before`; the actionable line for each that failed."""
    actionable: list[str] = []
    for name, (value, run) in checks.items():
        was = before.get(name)
        is_failure = value not in GREEN and value not in UNCONCLUDED and value != "CANCELLED"
        if was is None or was[0] != value:
            print(f"check {name}: {value}", flush=True)
        elif was[1] != run:
            print(f"check {name}: {value} again, from a re-run", flush=True)
        else:
            continue
        if is_failure:
            actionable.append(f"check {name} ({value})")
    return actionable


def changes_since(current: Snapshot, previous: Snapshot, merges: str | None) -> list[str]:
    """Print every change from `previous` to `current` and answer the actionable lines among them; `merges` is the last mergeability GitHub answered."""
    _, _, comments, reviews, threads_, checks, mergeable = current[:7]
    _, _, p_comments, p_reviews, p_threads, p_checks, _ = previous[:7]
    actionable = (new_comments(comments, p_comments) + new_reviews(reviews, p_reviews)
                  + new_threads(threads_, p_threads) + thread_activity(threads_, p_threads)
                  + check_changes(checks, p_checks))
    if mergeable != "UNKNOWN" and mergeable != merges:
        print(f"mergeable: {mergeable}" + (
            " — GitHub builds no merge ref for a branch that conflicts, so no review "
            "of this head can run" if mergeable == "CONFLICTING" else ""), flush=True)
    return actionable


FATAL_POLL_PATTERNS: tuple[str, ...] = (
    "unable to read current working directory",
    "no such file or directory",
    "could not resolve to a repository",
    "could not resolve to a pullrequest",
    "pull request not found",
    "repository not found",
    "authentication required",
    "bad credentials",
    "must authenticate",
    "command not found",
    "permission denied",
)


def is_fatal_poll_error(exc: SystemExit) -> bool:
    """Matches a subprocess failure against known fatal stderr strings in FATAL_POLL_PATTERNS.

    Performs a case-insensitive substring search of `str(exc)` against
    `FATAL_POLL_PATTERNS`. Because `github.gh` raises `SystemExit` containing
    the raw stderr of `gh`, this is a heuristic over CLI and remote API prose
    outside local control; any fatal error reworded upstream will not match and
    will fall back to the transient retry loop.

    Args:
        exc: Subprocess exit exception from `github.gh`.

    Returns:
        bool: True if the exception message contains any pattern in `FATAL_POLL_PATTERNS`.
    """
    msg = str(exc).lower()
    return any(pattern in msg for pattern in FATAL_POLL_PATTERNS)


def _report_exit(
    number: int,
    state: str,
    pr_state: PullRequestState,
    detail: str = "",
    draft: bool = False,
) -> None:
    """Formats and prints the termination message when watch exits.

    An approved draft is not ready to merge: it is a plan-only pull request
    whose plan passed, and its next step is the implementation and `move ready`.
    """
    if pr_state in (PullRequestState.MERGED, PullRequestState.CLOSED):
        print(f"pr {state}", flush=True)
    elif draft and pr_state is PullRequestState.READY_TO_MERGE:
        print(f"watch exiting on #{number}: plan approved on a draft — push the "
              "implementation, then `.meta/say/move ready`", flush=True)
    else:
        suffix = f" ({detail})" if detail else ""
        print(f"watch exiting on #{number}: {pr_state.value}{suffix}", flush=True)


def _evaluate_poll(
    current: Snapshot,
    previous: Snapshot | None,
    merges: str | None,
) -> tuple[bool, Snapshot, str | None]:
    """Evaluates pull request state and deltas for a single watch polling turn.

    A draft is classified as if it were not one. A plan-only pull request is a
    draft while its plan is argued, and a verdict, an owed comment or a
    conflict on it is still the coder's to act on (solorepo's DR-273). This is
    local to `watch`: `classify_pr` and `sweep` read the real flag.

    Returns:
        tuple[bool, Snapshot, str | None]: (should_exit, current_snapshot, merges).

    Raises:
        github.GhTimeout: The reviewer's login could not be read because `gh`
            answered nothing. Every other failure of that read degrades to an
            unknown reviewer, which costs the classification one distinction; a
            hang costs the poll its whole interval, so it is raised for `watch`
            to retry rather than absorbed here.
    """
    number, state, _, _, threads_, checks, mergeable = current[:7]
    pr_data = current[7] if len(current) > 7 else {
        "number": number,
        "state": state,
        "comments": list(current[2].values()),
        "reviews": list(current[3].values()),
        "mergeable": mergeable,
    }
    reviewer_login = github.role_login("reviewer")

    pr_state = classify_pr({**pr_data, "isDraft": False}, checks, list(threads_.values()),
                           reviewer_login)

    if previous is None:
        owed = len(review.unaddressed(list(threads_.values())))
        print(f"watching #{number}: {owed} thread(s) owed an answer, mergeable={mergeable}, "
              + ", ".join(f"{k}={v}" for k, (v, _) in checks.items()), flush=True)
        if pr_state in CODER_ACTIONABLE_STATES:
            _report_exit(number, state, pr_state, draft=bool(pr_data.get("isDraft")))
            return True, current, merges
        return False, current, mergeable if mergeable != "UNKNOWN" else merges

    actionable = changes_since(current, previous, merges)
    if pr_state in CODER_ACTIONABLE_STATES:
        _report_exit(number, state, pr_state, ", ".join(actionable),
                     draft=bool(pr_data.get("isDraft")))
        return True, current, merges

    if actionable:
        print(f"watch exiting on #{number}: " + ", ".join(actionable), flush=True)
        return True, current, merges

    if state in ("MERGED", "CLOSED"):
        print(f"pr {state}", flush=True)
        return True, current, merges

    new_merges = mergeable if mergeable != "UNKNOWN" else merges
    return False, current, new_merges


def watch(ref: str | int, every: int = 60, max_retries: int = 5,
          max_backoff: int = 300) -> None:
    """Monitors a pull request for changes, printing events and exiting on actionable signals or fatal errors.

    Args:
        ref: Pull request number, URL, or head branch reference.
        every: Polling frequency in seconds (default: 60).
        max_retries: Maximum number of retry attempts after a failed poll before the circuit breaker trips (default: 5).
        max_backoff: Maximum exponential backoff delay in seconds between retries (default: 300).

    Raises:
        SystemExit: Non-zero exit when `snapshot` encounters an unrecoverable fatal error
            matched by `is_fatal_poll_error`, or when consecutive poll failures exhaust `max_retries`.

    Every `gh` call a poll makes is bounded by `github.GH_TIMEOUT`, so a hung
    invocation fails the poll it serves rather than stalling the watch: the
    failure is transient, so it is retried under backoff, and a hang that
    persists exhausts `max_retries` and exits, which is the signal a silent
    watch never sent (solorepo's #738). A poll is the snapshot and the
    evaluation of it together for exactly this reason: the reviewer's login is
    read during the evaluation, and a hang there costs the same interval and is
    owed the same retry as one in the snapshot.

    Mergeability is remembered as the last answer GitHub gave, apart from the
    snapshot, because `UNKNOWN` is not a state of the branch but GitHub
    computing one and every push sets it: compared snapshot to snapshot, a push
    would report `UNKNOWN` and then the value the branch already had, which is
    two lines for no change. Nothing said yet — including by the heading — is
    a change from nothing, and is printed.

    On every poll (including startup poll 0), the pull request is classified
    into PullRequestState (solorepo's DR-248). Whenever a state requiring
    coder action is reached — including conflict (NEEDS_REBASE), test failures
    (GATE_FAILED), changes requested, parked notices (AWAITING_PROMOTION),
    or readiness to merge (READY_TO_MERGE) — watch prints the transition and
    exits 0 as an active handoff semaphore.
    """
    import time
    previous: Snapshot | None = None
    merges: str | None = None
    retries: int = 0
    ref_name = f"#{str(ref).lstrip('#')}" if str(ref).lstrip("#").isdigit() else str(ref)
    while True:
        try:
            current = snapshot(ref)
            should_exit, nxt, nxt_merges = _evaluate_poll(current, previous, merges)
        except SystemExit as e:
            if is_fatal_poll_error(e):
                sys.exit(f"watch exiting on {ref_name}: fatal poll error: {e}")
            if retries >= max_retries:
                sys.exit(
                    f"watch exiting on {ref_name}: circuit broken after "
                    f"{retries} retries: {e}"
                )
            retries += 1
            delay = min(every * (2 ** (retries - 1)), max_backoff)
            print(
                f"? poll skipped ({retries}/{max_retries}): "
                f"{e} (retrying in {delay}s)",
                file=sys.stderr,
            )
            time.sleep(delay)
            continue
        retries = 0
        previous, merges = nxt, nxt_merges
        if should_exit:
            return
        time.sleep(every)


def resume(ref: str | int) -> str:
    """Formats pull request status, check rollups, reviews, and unaddressed threads for resuming work.

    Args:
        ref: Pull request number, URL, or head branch reference.

    Returns:
        str: Formatted briefing summary of pull request state.
    """
    pr = github.gh("pr", "view", str(ref), "--json", "number,title,body,headRefName")
    out = [f"#{pr['number']} {pr['title']}",
           f"branch: {pr['headRefName']}", "", "--- body ---", pr["body"] or "(empty)", ""]
    states = {c.get("name") or c.get("context"): c.get("conclusion") or c.get("state")
              for c in github.rollup_of(pr["number"])}
    out.append("checks: " + (", ".join(f"{k}={v}" for k, v in states.items()) or "none"))
    held = github.pull(ref)
    given = review.verdicts(held["reviews"]["nodes"])
    if given:
        out.append(f"--- {len(given)} verdict(s), newest first, each on the head GitHub recorded it against ---")
        out += given
    owed = review.unaddressed(held["reviewThreads"]["nodes"], limit=None)
    out.append(f"--- {len(owed)} thread(s) owed an answer ---")
    out += owed
    return "\n".join(out)
