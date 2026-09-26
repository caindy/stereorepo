"""Queue coordination and merge execution for the standing merge manager
(solorepo's DR-161, solorepo's DR-258).

Why a refusal over a running check is deferred. A pass that takes a pull request
out of draft starts a gate run on the same head, because `ready_for_review` is
one of the gate's triggers. The check states that pass is holding were read
before that run existed, so the pull request reads green on them, and the merge
the pass then asks for is one GitHub refuses while the run is in progress. That
refusal names a moment in a gate run rather than a branch that cannot land: the
same head merges once the run concludes. Demoting the pull request over it parks
the work instead, because the notice the demotion posts carries the current head
and `ranking.find_active_merge_refusal` then holds `eviction._restore_draft_if_ready` off
the pull request until a new commit lands, which is the defect solorepo's #944
reports. So the refusal is deferred, and the next pass reads the same head with
the run concluded.

Two mechanisms carry that, and the order matters. `eviction.evaluate_open_pulls` names the
pull requests this pass restored to `ranking.evaluate_candidates`, which refuses
each before it can become a candidate, so the merge is never asked for.
`pull_requests.MergeDeferredError` carries the refusal GitHub gave where one was
asked for anyway, which is the case a pass did not start itself: the merge layer
classifies its own refusal, and this one catches the type rather than reading the
words back out of an exit message.
"""
import sys

import channel
from lib.move import advance, common, epics, pull_requests
from lib.move.manager import eviction, lock, ranking

MERGE_MANAGER_FIELDS = (
    "number,title,headRefName,baseRefName,headRefOid,isDraft,mergeable,"
    "mergeStateStatus,latestReviews,reviews,reviewRequests,closingIssuesReferences,"
    "additions,deletions,changedFiles,statusCheckRollup,body"
)


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
    _close_completed_epics(dry_run)
    owner, name, reviewer_login = ranking.repo_context()
    pulls = channel.gh(
        "pr", "list", "--state", "open", "--limit", "100", "--json", MERGE_MANAGER_FIELDS
    )
    if not pulls:
        print("merge-manager: idle — no open pull requests")
        return

    eligible, evaluations = eviction.evaluate_open_pulls(
        pulls, reviewer_login, owner, name, dry_run=dry_run
    )
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
        print(f"merge-manager: idle — 0 of {len(eligible)} eligible candidate(s) uncontended "
              "(held on review reservation)")
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
                lambda p: eviction._refusal_notice_body(p, head_oid),
                str(exc.code),
                label="merge refusal",
            )
        except (SystemExit, *common.UNREACHED) as comment_err:
            print(f"warning: could not reconcile refusal diagnosis on #{winner['number']}: "
                  f"{comment_err}", file=sys.stderr)
        eviction._handle_refused_loop_branch(winner, exc.code, dry_run)
        if stranded:
            advance.advance_stranded(pulls, evaluations, owner, name, dry_run)
        sys.exit(exc.code)


def _close_completed_epics(dry_run: bool) -> None:
    """Close completed parent Epics during a real manager pass."""
    if not dry_run:
        epics.close_completed()
