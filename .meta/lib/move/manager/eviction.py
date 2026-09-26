"""Autonomous loop pull request eviction, draft demotion, and draft restoration (solorepo's DR-258).

The eviction half of the standing merge manager: detecting inactive or failing
autonomous loop runs, demoting stalled pull requests to draft to prevent
head-of-line blocking in the merge queue, restoring approved green drafts to
ready status, and managing signed merge refusal notices.
"""
import datetime
import sys
from collections.abc import Mapping, Sequence
from typing import Any

import channel
import check_pr
from lib.move import advance, challenges, common, drafts, pull_requests
from lib.move.actions import in_flight
from lib.move.manager import ranking

STALL_CHANGES_REQUESTED_THRESHOLD = 3
"""Number of changes-requested review rounds before an autonomous loop PR is
evicted to draft (solorepo's DR-258)."""

STALL_ESCALATION_MARKER = "<!-- solorepo:draft-escalation -->"
"""Marker on the first durable observation of an autonomous draft stall."""


def idle_minutes(obj: Mapping[str, Any], now: datetime.datetime,
                 field: str = "updatedAt") -> float:
    """Return the minutes since `field`, or infinity where GitHub omitted it."""
    moved = obj.get(field)
    if not moved:
        return float("inf")
    since = datetime.datetime.fromisoformat(str(moved).replace("Z", "+00:00"))
    return (now - since).total_seconds() / 60


def is_stalled_autonomous_pr(pull: common.Pull, reviewer_login: str) -> bool:
    """Whether an autonomous loop pull request has stalled beyond recovery
    thresholds (solorepo's DR-258).

    Exempts pull requests with standing APPROVED verdicts or in AWAITING_PROMOTION state.

    Parameters:
        pull (dict): The pull request metadata dictionary.
        reviewer_login (str): Expected login of the reviewer Role.

    Returns:
        bool: True if loop PR has exceeded changes-requested or rebase failure thresholds.
    """
    head = pull.get("headRefName") or ""
    if not pull_requests.LOOPS_BRANCH.match(head):
        return False
    if pull.get("mergeable") == "CONFLICTING" \
            and advance._find_advance_notice_comment(pull["number"]) is not None:
        return True
    if (check_pr.state.standing_verdict(pull, reviewer_login) == "APPROVED"
            or check_pr.classify_pr(pull, reviewer_login=reviewer_login)
            is check_pr.PullRequestState.AWAITING_PROMOTION):
        return False
    approved, _ = ranking.check_reviewer_approval(pull, reviewer_login)
    if approved:
        return False
    reviews = pull.get("reviews") or pull.get("latestReviews") or []
    cr_reviews = [
        r for r in reviews
        if (r.get("author") or {}).get("login") == reviewer_login
        and r.get("state") == "CHANGES_REQUESTED"
    ]
    if len(cr_reviews) < STALL_CHANGES_REQUESTED_THRESHOLD:
        return False
    last_cr = cr_reviews[-1]
    last_cr_oid = (last_cr.get("commit") or {}).get("oid")
    head_oid = pull.get("headRefOid")
    return not (head_oid and last_cr_oid and head_oid != last_cr_oid)


def _refusal_notice_body(exc_code: Any, head_oid: str = "") -> str:
    """Generate signed merge refusal diagnosis comment body with attribution trailers.

    Emits `head:<head_oid>` as a marker tag when provided, allowing
    `ranking.find_active_merge_refusal` to correlate the notice with the specific head commit.

    Parameters:
        exc_code: The refusal exit code or message.
        head_oid: The git commit SHA of the refused head commit.

    Returns:
        str: Attributed and signed markdown comment body.
    """
    oid_tag = f" head:{head_oid}" if head_oid else ""
    raw = (
        f"{ranking.MERGE_REFUSAL_MARKER}{oid_tag}\n\n"
        f"> Merge refusal: {exc_code}\n\n"
        f"Merge refusal diagnosis:\n\n{exc_code}"
    )
    return channel.signed(raw)


refusal_notice_body = _refusal_notice_body


def demote_to_draft(pull: common.Pull, action: str = "demote",
                    reason: str = "unmergeable", dry_run: bool = False) -> bool:
    """Demote a pull request to draft to prevent head-of-line blocking (solorepo's DR-258).

    In dry-run mode, logs the planned transition and returns True without mutating
    the pull metadata dictionary or issuing GitHub API mutations. In live execution,
    sets `pull["isDraft"] = True` locally before issuing the GitHub API mutation,
    leaving it set even if the remote mutation fails so in-memory queue evaluation
    reflects the demotion intent across subsequent checks.

    Parameters:
        pull (dict): The pull request metadata dictionary.
        action (str): Action verb for logging ('evict' or 'demote').
        reason (str): Reason description for logging.
        dry_run (bool): If True, log action without mutating GitHub state.

    Returns:
        bool: True if the pull request was demoted (or would be in dry run).
    """
    action_verb = "evict" if action == "evict" else "demote"
    action_past = "evicted" if action == "evict" else "demoted"
    if dry_run:
        print(f"merge-manager: dry run — would {action_verb} {reason} "
              f"PR #{pull['number']} to draft")
        return True
    pull["isDraft"] = True
    try:
        channel.gh("pr", "ready", str(pull["number"]), "--undo", parse=False)
        print(f"merge-manager: {action_past} {reason} PR #{pull['number']} to draft")
        return True
    except (SystemExit, *common.UNREACHED) as exc:
        print(f"warning: could not demote PR #{pull['number']} to draft: {exc}", file=sys.stderr)
        return False


def evict_stalled_autonomous_pr(pull: common.Pull, reviewer_login: str = "reviewer",
                                dry_run: bool = False) -> bool:
    """Demote stalled autonomous loop PR to draft to prevent head-of-line
    blocking (solorepo's DR-258).

    Parameters:
        pull (dict): The pull request metadata dictionary.
        reviewer_login (str): Expected login of the reviewer Role.
        dry_run (bool): If True, log action without mutating GitHub state.

    Returns:
        bool: True if the pull request was demoted (or would be in dry run).
    """
    if not is_stalled_autonomous_pr(pull, reviewer_login):
        return False
    return demote_to_draft(pull, action="evict", reason="stalled autonomous", dry_run=dry_run)


def draft_escalations(pulls: Sequence[common.Pull], reading: Any) -> list[Any]:
    """Return escalations owed on autonomous implementation drafts that remain stalled.

    The first qualified reconciliation writes an in-place observation tagged
    with the current head. A later reconciliation can hand the Challenge back
    only when that observation still names the unchanged draft, no GitHub
    Actions run answers it, and every other guard still holds. A conflict also
    needs the rebase run dispatched by the first phase to have completed.

    Parameters:
        pulls (Sequence[Pull]): The open pull requests in one reconciliation.
        reading (Reading): The reconciliation's cached Issues, times, and runs.

    Returns:
        list[Owed]: The Challenge hand-backs owed by qualifying drafts.
    """
    from lib.move import reconcile

    owed = []
    for pull in pulls:
        match = pull_requests.LOOPS_BRANCH.match(pull.get("headRefName") or "")
        if not match or not pull.get("isDraft") or not pull.get("changedFiles"):
            continue
        challenge = int(match.group(1))
        found = reconcile._challenge_reads(challenge, reading)
        if found is not check_pr.state.IssueState.RESUMABLE:
            continue
        idle = idle_minutes(pull, reading.now)
        head = str(pull.get("headRefName") or "")
        if idle < reading.bound or in_flight(reading.action_runs, branch=head):
            continue
        number = int(pull["number"])
        conflicting = str(pull.get("mergeable") or "").upper() == "CONFLICTING"
        rebase_finished = any(
            run.get("status") == "completed"
            and str(run.get("displayTitle") or "") == f"coder-issue-#{number}"
            for run in reading.coder_runs.recent or []
        )
        if conflicting and (not reading.coder_runs.listed or not rebase_finished):
            continue
        diagnosis = (
            f"Autonomous pull request #{number} on `{head}` remains a draft after "
            f"{int(idle)} inactive minutes with no queued or in-progress GitHub Actions run."
        )
        if conflicting:
            diagnosis += (" A dispatched rebase attempt completed, but GitHub still reports the "
                          "pull request conflicting.")
        else:
            diagnosis += " The soft draft demotion did not restore progress."
        observed = any(
            f"{STALL_ESCALATION_MARKER} head:{pull.get('headRefOid') or ''}"
            in str(comment.get("body") or "")
            for comment in pull.get("comments") or []
        )
        if not observed:
            body = (f"{STALL_ESCALATION_MARKER} head:{pull.get('headRefOid') or ''}\n"
                    f"**Draft stall observation.** {diagnosis}")
            owed.append(reconcile.Owed(
                "escalate", number, "first later reconciliation finding this autonomous draft "
                "stalled", title="observe", body=body,
            ))
            continue
        owed.append(reconcile.Owed(
            "escalate", challenge, f"#{number} remains an inactive autonomous draft after "
            "the soft demotion", body=diagnosis,
        ))
    return owed


def observe_draft_stall(pull: int, body: str) -> None:
    """Record the first later reconciliation that still finds a draft stalled."""
    advance.reconcile_notice(pull, STALL_ESCALATION_MARKER, channel.signed(body), body,
                             label="draft stall observation")


def settle_draft_escalation(number: int, observation: bool, body: str) -> None:
    """Record an observation or hand the associated Challenge back to the solo."""
    if observation:
        observe_draft_stall(number, body)
    else:
        challenges.stop(number, channel.signed(body))


def _restore_draft_if_ready(pull: common.Pull, reviewer_login: str, dry_run: bool) -> bool:
    """Mark an approved, green implementation pull request ready to merge.

    Parameters:
        pull: The pull request, as `MERGE_MANAGER_FIELDS` lists it.
        reviewer_login (str): The reviewer Role's login.
        dry_run (bool): If True, say what would be restored and mutate nothing.

    Returns:
        bool: True where this call took the pull request out of draft on GitHub,
        which is what `evaluate_open_pulls` reads to keep it out of this pass's
        merge candidates.
    """
    if not (pull.get("isDraft") and drafts.holds_changes(pull)):
        return False
    if ranking.find_active_merge_refusal(pull) is not None:
        return False
    approved, _ = ranking.check_reviewer_approval(pull, reviewer_login)
    if not approved:
        return False
    ok_green, _ = ranking.check_green(pull)
    if ok_green and pull.get("mergeable") != "CONFLICTING":
        if not dry_run:
            try:
                channel.gh("pr", "ready", str(pull["number"]), parse=False)
                pull["isDraft"] = False
                advance.reconcile_notice(
                    pull["number"], ranking.MERGE_REFUSAL_MARKER, None, None,
                    label="merge refusal",
                )
                print(f"merge-manager: marked approved and green PR #{pull['number']} "
                      "ready to merge")
                return True
            except (SystemExit, *common.UNREACHED) as exc:
                print(f"warning: could not mark PR #{pull['number']} ready: {exc}", file=sys.stderr)
        else:
            print(f"merge-manager: dry run — would mark PR #{pull['number']} ready to merge")
    return False


restore_draft_if_ready = _restore_draft_if_ready


def evaluate_open_pulls(
    pulls: Sequence[common.Pull],
    reviewer_login: str,
    owner: str,
    name: str,
    dry_run: bool = False,
) -> tuple[list[common.Pull], dict[int, tuple[bool, list[str]]]]:
    """Evict what has stalled, transition final approvals, and evaluate what remains.

    The eviction pass is this module's and the evaluation is `ranking`'s, so the
    two are joined here rather than in either: a pull request this pass took out
    of draft is named to `ranking.evaluate_candidates`, which refuses it.

    Parameters:
        pulls (list): All open pull requests in the repository.
        reviewer_login (str): Login of the reviewer Role.
        owner (str): Repository owner.
        name (str): Repository name.
        dry_run (bool): If True, do not mutate pull request state on GitHub.

    Returns:
        tuple[list[Pull], dict[int, tuple[bool, list[str]]]]: Pair of eligible PRs and evaluations.
    """
    restored: set[int] = set()
    for pull in pulls:
        if not pull.get("isDraft"):
            evict_stalled_autonomous_pr(pull, reviewer_login, dry_run=dry_run)
        elif _restore_draft_if_ready(pull, reviewer_login, dry_run=dry_run):
            restored.add(pull["number"])
    return ranking.evaluate_candidates(pulls, reviewer_login, owner, name, restored)


def _handle_refused_loop_branch(winner: common.Pull, exc_code: Any, dry_run: bool) -> None:
    """Demote autonomous loop PR to draft and hand back Challenge to human.

    Guards against mutating session or human-authored pull requests by inspecting
    `headRefName` against `pull_requests.LOOPS_BRANCH`; if the branch does not
    match autonomous loop naming conventions, returns immediately without mutation.

    When a candidate squash-merge fails at the final gate, repeating the merge
    mutation against an unchanged head commit cannot succeed and blocks queue
    throughput across scheduled runs. Following solorepo's DR-112 and
    solorepo's DR-258, the autonomous loop pull request is demoted to draft
    status via the shared mutation door `demote_to_draft`, and its associated
    Challenge is handed back to `human` via `challenges.stop` under an
    attributable signed trailer. This alerts a human maintainer to remediate
    the unmergeable branch rather than leaving the work silently parked in draft
    without an active semaphore.
    """
    match = pull_requests.LOOPS_BRANCH.match(winner.get("headRefName") or "")
    if not match:
        return
    demote_to_draft(winner, action="demote", reason="unmergeable", dry_run=dry_run)
    issue_num = match.group(1)
    if not dry_run:
        try:
            body = channel.signed(f"Merge refusal on #{winner['number']}:\n\n{exc_code}")
            challenges.stop(issue_num, body)
        except (SystemExit, *common.UNREACHED) as stop_err:
            print(f"warning: could not stop Challenge #{issue_num}: {stop_err}", file=sys.stderr)
    else:
        print(f"merge-manager: dry run — would hand back Challenge #{issue_num} to human")


handle_refused_loop_branch = _handle_refused_loop_branch
