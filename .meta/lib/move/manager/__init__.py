"""The standing merge manager: the gate over an open pull request, the mutual exclusion
the two workflows that run it hold it under, and the landing in order of leverage
(solorepo's DR-161, solorepo's DR-264, solorepo's DR-267).

Why a refusal over a running check is deferred. A pass that takes a pull request
out of draft starts a gate run on the same head, because `ready_for_review` is
one of the gate's triggers. The check states that pass is holding were read
before that run existed, so the pull request reads green on them, and the merge
the pass then asks for is one GitHub refuses while the run is in progress. That
refusal names a moment in a gate run rather than a branch that cannot land: the
same head merges once the run concludes. Demoting the pull request over it parks
the work instead, because the notice the demotion posts carries the current head
and `ranking.find_active_merge_refusal` then holds `_restore_draft_if_ready` off
the pull request until a new commit lands, which is the defect solorepo's #944
reports. So the refusal is deferred, and the next pass reads the same head with
the run concluded.

Two mechanisms carry that, and the order matters. `evaluate_open_pulls` names the
pull requests this pass restored to `ranking.evaluate_candidates`, which refuses
each before it can become a candidate, so the merge is never asked for.
`pull_requests.MergeDeferredError` carries the refusal GitHub gave where one was
asked for anyway, which is the case a pass did not start itself: the merge layer
classifies its own refusal, and this one catches the type rather than reading the
words back out of an exit message.

The package root is the eviction and the orchestration; `lock` is the mutual
exclusion and `ranking` is the reading each pass does before it evicts or
merges, the lease taken before any of it on a pass that merges and not at all
on a dry run, for the reason `merge_manager` gives below. The root imports both
as modules and neither imports a name out of the root (solorepo's DR-217 for
the route, the direction being this package's own constraint): the root is
mid-initialisation at the `from lib.move.manager import lock, ranking` line
below, so `from lib.move.manager import <name>` in a submodule would raise
`ImportError` on a name the root has not bound yet. That is why
`evaluate_open_pulls` stays here with the eviction rather than moving to
`ranking` with the rest of the reading — it is the one part of the reading that
calls `_restore_draft_if_ready`. A submodule still reaches the root
transitively, `ranking` importing `advance` which imports `manager`, and that
survives only on the terms `lib.move`'s own docstring sets: `from lib.move
import manager` answers out of `sys.modules` and nothing in the closure
dereferences an attribute at import time. `lock` imports nothing else in
`lib.move`: the lease is a compare-and-set over a git ref and is read by a probe
of its own, apart from the gate and the ranking. The ranking does not reach the
lease at all, and `merge_manager` here is the one thing that does."""
import sys
from collections.abc import Sequence
from typing import Any

import channel
import check_pr
from lib.move import advance, challenges, common, drafts, pull_requests
from lib.move.manager import lock, ranking

STALL_CHANGES_REQUESTED_THRESHOLD = 3
"""Number of changes-requested review rounds before an autonomous loop PR is evicted to draft (solorepo's DR-258)."""


MERGE_MANAGER_FIELDS = (
    "number,title,headRefName,baseRefName,headRefOid,isDraft,mergeable,"
    "mergeStateStatus,latestReviews,reviews,reviewRequests,closingIssuesReferences,"
    "additions,deletions,changedFiles,statusCheckRollup,body"
)


def is_stalled_autonomous_pr(pull: common.Pull, reviewer_login: str) -> bool:
    """Whether an autonomous loop pull request has stalled beyond recovery thresholds (solorepo's DR-258).

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
        if (r.get("author") or {}).get("login") == reviewer_login and r.get("state") == "CHANGES_REQUESTED"
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
    """Demote stalled autonomous loop PR to draft to prevent head-of-line blocking (solorepo's DR-258).

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
                    pull["number"], ranking.MERGE_REFUSAL_MARKER, None, None, label="merge refusal")
                print(f"merge-manager: marked approved and green PR #{pull['number']} ready to merge")
                return True
            except (SystemExit, *common.UNREACHED) as exc:
                print(f"warning: could not mark PR #{pull['number']} ready: {exc}", file=sys.stderr)
        else:
            print(f"merge-manager: dry run — would mark PR #{pull['number']} ready to merge")
    return False


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


def merge_manager(dry_run: bool = False, stranded: bool = True) -> None:
    """Take the merge manager's lock and manage the queue under it, or stand down.

    This is the way in: `merge.yml` and `reconcile.yml` both run the manager and
    are in concurrency groups of their own, so GitHub holds neither apart from
    the other and `lock.LOCK_REF` is what does (solorepo's DR-267). A dry run takes
    nothing, since it mutates nothing and would otherwise hold the queue for the
    length of a report.

    Parameters:
        dry_run (bool): If True, name the winner and merge nothing.
        stranded (bool): Whether a stranded pull request is rebased, as
            `_manage` reads it.

    Raises:
        SystemExit: With `_manage`'s code, the lock given back first.
    """
    if dry_run:
        _manage(dry_run=True, stranded=stranded)
        return
    held = lock.take_merge_lock()
    if held is None:
        return
    try:
        _manage(dry_run=False, stranded=stranded)
    finally:
        lock.drop_merge_lock(held)


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


def _manage(dry_run: bool = False, stranded: bool = True) -> None:
    """Evaluate open pull requests against semaphores, rank eligible candidates
    by leverage, assert choices, deferrals, and semaphore refusals out loud, and
    squash-merge the top candidate (solorepo's DR-161, solorepo's DR-258).

    The queue evaluation `merge_manager` runs under the merge manager's lock,
    and which takes no lock itself: call that rather than this, or two managers
    merge the same queue at once (solorepo's DR-267).

    Idle with nothing eligible, it hands the open pull requests to
    `advance_stranded`, so an approved one that has merely fallen behind trunk
    is rebased here rather than waiting for a push to `main` that may never come.

    A `SystemExit` from the winning candidate's `merge` is caught so that the
    failure isolates to its own candidate: `advance_stranded` runs when
    `stranded`, as on the idle branches above, and the queue's other work moves
    rather than waiting behind a candidate that cannot land. The code is then
    re-raised. A failed merge is an anomaly rather than a state only the solo
    can clear, so unlike `advance_stranded`'s own refusals it paints the
    scheduled run red, which is what surfaces a stall.

    A `pull_requests.MergeDeferredError` is the exception, and takes none of
    that: no diagnosis notice, no demotion to draft, no Challenge handed back,
    and no red run. A check still running is the state the next pass finds
    settled, so nothing is owed beyond saying that the candidate waits.

    Parameters:
        dry_run (bool): If True, name the winner and merge nothing.
        stranded (bool): If False, leave a stranded pull request alone. The
            caller passes False on the one event `advance.yml` also runs on, a
            push to `main`: the two workflows are in different concurrency
            groups, so nothing holds them apart, and `update-branch` returns
            before GitHub has performed the rebase, so both would issue one for
            the same branch.
    """
    owner, name, reviewer_login = ranking.repo_context()
    pulls = channel.gh("pr", "list", "--state", "open", "--limit", "100", "--json", MERGE_MANAGER_FIELDS)
    if not pulls:
        print("merge-manager: idle — no open pull requests")
        return

    eligible, evaluations = evaluate_open_pulls(pulls, reviewer_login, owner, name, dry_run=dry_run)
    if not eligible:
        print(f"merge-manager: idle — 0 of {len(pulls)} open pull request(s) eligible")
        ranking.report_refusals(pulls, evaluations)
        if stranded:
            advance.advance_stranded(pulls, evaluations, owner, name, dry_run)
        return

    uncontended, contention_deferred = ranking.partition_contention(
        eligible, pulls, reviewer_login, owner, name
    )
    if not uncontended:
        print(f"merge-manager: idle — 0 of {len(eligible)} eligible candidate(s) uncontended (held on review reservation)")
        ranking.report_contention_deferred(contention_deferred)
        ranking.report_refusals(pulls, evaluations)
        if stranded:
            advance.advance_stranded(pulls, evaluations, owner, name, dry_run)
        return

    winner, deferred, metrics = ranking.rank_by_leverage(uncontended, pulls, ranking.open_issues())
    ranking.report_evaluation_choices(winner, deferred, metrics, contention_deferred)
    ranking.report_refusals(pulls, evaluations)

    if dry_run:
        print(f"merge-manager: dry run — not merging #{winner['number']}")
        return

    is_stacked = bool(pull_requests.stacked(winner["number"]))
    print(f"merge-manager: merging #{winner['number']}...")
    try:
        pull_requests.merge(str(winner["number"]), stack=is_stacked, auto=False)
        advance.reconcile_notice(
            winner["number"], ranking.MERGE_REFUSAL_MARKER, None, None, label="merge refusal")
    except pull_requests.MergeDeferredError as deferral:
        print(f"merge-manager: could not merge #{winner['number']} — {deferral.refusal}")
        print(f"merge-manager: deferring #{winner['number']} — a required check is still "
              "running, which the next pass reads once it has concluded")
        if stranded:
            advance.advance_stranded(pulls, evaluations, owner, name, dry_run)
        return
    except SystemExit as exc:
        print(f"merge-manager: could not merge #{winner['number']} — {exc.code}")
        try:
            head_oid = winner.get("headRefOid") or ""
            advance.reconcile_notice(
                winner["number"],
                ranking.MERGE_REFUSAL_MARKER,
                lambda p: _refusal_notice_body(p, head_oid),
                str(exc.code),
                label="merge refusal",
            )
        except (SystemExit, *common.UNREACHED) as comment_err:
            print(f"warning: could not reconcile refusal diagnosis on #{winner['number']}: "
                  f"{comment_err}", file=sys.stderr)
        _handle_refused_loop_branch(winner, exc.code, dry_run)
        if stranded:
            advance.advance_stranded(pulls, evaluations, owner, name, dry_run)
        sys.exit(exc.code)
