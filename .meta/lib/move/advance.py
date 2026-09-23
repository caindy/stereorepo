"""The advance sweep on a push to trunk and the passes it dispatches (solorepo's DR-133,
solorepo's DR-264)."""
import datetime
import re
import sys
from collections.abc import Sequence
from typing import Any

import channel
import check_pr
from lib.move import common, manager, pull_requests


def run_coder(pr: str | int, task: str) -> None:
    """Start one of `coder.yml`'s passes on a pull request: the dispatch itself.

    Written once because it has two callers — `dispatch` below, on the merge
    that stranded a review request, and `dispatch_pass`, where a person makes
    the same act — and for the reason the task is passed at all: `coder.yml`
    defaults the input to `review`, so a dispatch that dropped it would run the
    pass that answers threads on a branch whose problem is a conflict.
    Passes `harness=claude` explicitly to ensure unattended dispatch routes to
    the subscription harness rather than a metered one (solorepo's DR-240).
    """
    channel.gh("workflow", "run", "coder.yml", "-f", f"pull_request={pr}",
               "-f", f"task={task}", "-f", "harness=claude", parse=False)


_UNSET = object()
"""Sentinel distinguishing an unsupplied Challenge state from an unreadable one."""


def _is_autonomous_challenge(challenge: str, action: str, pull: common.Pull,
                             found: Any = _UNSET) -> bool:
    """Verify associated Challenge is open and easy/medium for loop action.

    An Issue deleted or transferred under its branch fails this read the same
    way on every push to trunk. This check avoids repeated red sweeps.

    Parameters:
        challenge: Identifier of the Challenge associated with the branch.
        action: Descriptive loop action name printed on refusal.
        pull: Pull request mapping being evaluated.
        found: Pre-resolved Issue state, or `_UNSET` to read it live.
            When omitted or `_UNSET`, parses `challenge` as an integer and
            reads its state live, refusing if the branch is not numeric.
            When `None`, treats the Challenge as already read and unreadable,
            refusing and logging the notice. When an `IssueState` value, uses
            the state directly, verifying it is `RESUMABLE` and refusing if
            closed or at a non-autonomous level.

    Returns:
        True if the Challenge is open and at an autonomous level; False otherwise.
    """
    from lib.move import reconcile
    if found is _UNSET:
        try:
            challenge_number = int(challenge)
        except ValueError:
            return False
        found = reconcile._challenge_reads(challenge_number)
    if found is None:
        print(f"left #{pull['number']} alone: #{challenge} cannot be read, so the {action} "
              f"is the solo's, and the sweep names it — {pull['title']}")
        return False
    if found is not check_pr.state.IssueState.RESUMABLE:
        state_str = "closed" if found is check_pr.state.IssueState.CLOSED else "at a level no loop takes"
        print(f"left #{pull['number']} alone: #{challenge} is {state_str}, "
              f"so the {action} is the solo's, and the sweep names it — {pull['title']}")
        return False
    return True


def _retry_stranded_reviewer(number: str, pull: common.Pull, asked: list[str],
                             merges: str, reviewer_login: str) -> tuple[bool, str | None, str | None]:
    """Retry review request if reviewer check failed without a verdict (solorepo's DR-178).

    Returns:
        tuple[bool, str | None, str | None]: (handled, failed_msg, refused_msg)
    """
    if reviewer_login not in asked or pull.get("isDraft") or merges == "CONFLICTING":
        return False, None, None
    checks = pull.get("statusCheckRollup")
    if checks is None:
        try:
            view_res = channel.gh("pr", "view", number, "--json", "statusCheckRollup")
            checks = view_res.get("statusCheckRollup") if isinstance(view_res, dict) else []
        except SystemExit:
            checks = []
    contexts = manager.deduplicate_checks(checks or [])
    reviewer_check = next((c for c in contexts if c.get("name") == "reviewer"), None)
    if reviewer_check and (reviewer_check.get("conclusion") or "").upper() == "FAILURE":
        try:
            pull_requests.request_review(number, "reviewer")
        except pull_requests.RequestRefused as exc:
            return True, None, f"#{number} has a review request stranded and the reviewer could not be re-requested for it — {exc.code}"
        except SystemExit as exc:
            return True, f"#{number} review request stranded and could not be re-requested — {exc.code}", None
        return True, None, None
    return False, None, None


def _dispatch_conflicting(pull: common.Pull, waiting: list[str],
                          pulls: Sequence[common.Pull], challenge: str,
                          reviewer_login: str) -> tuple[bool, str | None]:
    """Dispatch coder rebase pass for conflicting pull request if eligible.

    A layer above a conflicting lower layer is left alone and named, since a
    stack is resolved from the bottom (solorepo's DR-133); the root, and a
    layer whose lower layers are clean, is any loop branch's rebase.

    Returns:
        tuple[bool, str | None]: (handled, refused_msg)
    """
    from lib.move import reconcile
    number = str(pull["number"])
    try:
        challenge_number = int(challenge)
    except ValueError:
        challenge_number = None

    found = reconcile._challenge_reads(challenge_number) if challenge_number is not None else None
    act = reconcile.owed_by_pull(pull, found, check_pr.PullRequestState.NEEDS_REBASE,
                                 reviewer_login=reviewer_login,
                                 constraints=reconcile.Constraints(pulls=pulls, held_only=True))
    if act is not None and act.kind == "hold" and act.lower is not None:
        print(f"left #{number} alone: it is {act.why} — {pull['title']}")
        return True, None
    if not _is_autonomous_challenge(challenge, "conflict", pull, found=found):
        return True, None
    waits = " and ".join(waiting)
    try:
        run_coder(number, "rebase")
    except SystemExit as exc:
        return True, f"#{number} is {waits} and the coder could not be dispatched for it — {exc.code}"
    print(f"dispatched the coder for #{number}: {waits}, and conflicting with "
          f"{pull['baseRefName']}, so GitHub builds no merge ref and will not update "
          f"the branch — {pull['title']}")
    return True, None


def _dispatch_approved_or_redeliver(pull: common.Pull, merges: str,
                                    challenge: str, reviewer_login: str,
                                    redeliver: bool) -> tuple[bool, str | None]:
    """Dispatch review pass for approved PR with failing checks or redeliver changes requested."""
    number = str(pull["number"])
    if pull_requests.is_approved_pull(pull, reviewer_login=reviewer_login) \
            and not pull.get("isDraft") and merges != "CONFLICTING":
        checks = pull.get("statusCheckRollup")
        if checks is None:
            try:
                view_res = channel.gh("pr", "view", number, "--json", "statusCheckRollup")
                checks = view_res.get("statusCheckRollup") if isinstance(view_res, dict) else []
            except SystemExit:
                checks = []
        ok, msg = manager.check_green({"statusCheckRollup": checks})
        if not ok and "failing" in msg:
            if not _is_autonomous_challenge(challenge, "review", pull):
                return True, None
            try:
                run_coder(number, "review")
            except SystemExit as exc:
                return True, f"#{number} is approved with failing checks and the coder could not be dispatched for it — {exc.code}"
            print(f"dispatched the coder for #{number}: approved, with failing checks ({msg}) — {pull['title']}")
            return True, None
    elif redeliver and merges != "CONFLICTING":
        if not _is_autonomous_challenge(challenge, "review", pull):
            return True, None
        try:
            run_coder(number, "review")
        except SystemExit as exc:
            return True, f"#{number} has changes requested and the coder could not be dispatched for it — {exc.code}"
        print(f"dispatched the coder for #{number}: changes requested by reviewer, re-delivering pass — {pull['title']}")
        return True, None
    return False, None


def _dispatch_single_pull(pull: common.Pull, pulls: Sequence[common.Pull], reviewer_login: str,
                          minutes: int, now: datetime.datetime) -> tuple[str | None, str | None]:
    """Evaluate and dispatch coder passes for a single pull request."""
    number = str(pull["number"])
    challenge = re.sub(r"^(?:claude|gemini)/issue-", "", pull["headRefName"])
    asked = [r.get("login") or r.get("name") or "someone"
             for r in pull.get("reviewRequests") or []]
    moved = (datetime.datetime.fromisoformat(pull["updatedAt"].replace("Z", "+00:00"))
             if pull.get("updatedAt") else None)
    idle = (now - moved).total_seconds() / 60 if moved else float("inf")
    waiting = [f"requested of {', '.join(asked)}"] if asked else []
    if pull.get("autoMergeRequest"):
        waiting.append("armed")
    if pull_requests.is_approved_pull(pull, reviewer_login=reviewer_login):
        waiting.append("approved")
    redeliver = (pull_requests.is_changes_requested_pull(pull, reviewer_login=reviewer_login)
                 and idle >= minutes)
    if redeliver:
        waiting.append("awaiting the coder's answer to a request for changes")
    if not waiting and not redeliver:
        return None, None
    try:
        merges = pull_requests.mergeability(pull) or "UNKNOWN"
    except SystemExit as exc:
        return f"#{number} was left where it stands: GitHub would not say whether it still merges — {exc.code}", None

    handled, f_msg, r_msg = _retry_stranded_reviewer(number, pull, asked, merges, reviewer_login)
    if handled:
        return f_msg, r_msg

    if waiting and merges == "CONFLICTING":
        _, r_msg = _dispatch_conflicting(pull, waiting, pulls, challenge, reviewer_login)
        return None, r_msg

    _, r_msg = _dispatch_approved_or_redeliver(pull, merges, challenge, reviewer_login, redeliver)
    return None, r_msg


def dispatch(pulls: Sequence[common.Pull]) -> tuple[list[str], list[str]]:
    """Dispatch coder rebase passes for pull requests left conflicting by recent merges.

    Identifies loop-owned pull requests in CONFLICTING merge state that are waiting on
    something a conflict holds up — a review requested, an arming, an approval, or a request
    for changes the coder has not answered (solorepo's DR-237) — excluding a layer above a
    conflicting one, since a stack is resolved from the bottom — and triggers workflow dispatch
    for rebase passes (solorepo's DR-129, solorepo's DR-133, solorepo's DR-149).

    The two writes the sweep makes on a pull request's behalf are answered for
    separately from the rest. `gh workflow run coder.yml` fails identically
    whichever pull request asked for it — the credential without the Actions
    write, `coder.yml` disabled on the repository. The `pr edit` behind
    `request_review` fails identically too, for the credential without the
    repository write or a reviewer who is not a collaborator, which is why
    `RequestRefused` marks it apart from the reads around it. Neither is one
    pull request's weather, and a failure of the sweep reached through a
    per-pull-request arm is an arm catching too much, which is the falsifier
    solorepo's DR-238 wrote for itself; so the sweep's exit code answers for
    both. The sweep still reads every remaining pull request before the exit,
    since reading them is what its colour claims.

    A refused read of whether the branch still merges is the opposite case, and
    is one pull request's line: `mergeability` re-reads GitHub whenever the
    answer in hand is `UNKNOWN`, which is what GitHub answers while it computes
    a merge ref and so is routine on the push to trunk this runs on. The read
    happens once for each pull request any arm below could act on, so a refusal
    leaves that one where it stands and the pull requests behind it in the list
    are still dispatched for.

    Parameters:
        pulls (list[dict]): Open pull request objects returned from GitHub API view.

    Returns:
        tuple[list[str], list[str]]: What each pull request reported about
            itself, and the refused writes that belong to the sweep.
    """
    failed: list[str] = []
    refused: list[str] = []
    reviewer_login = channel.role_login("reviewer")
    minutes = check_pr.longest_run() or 30
    now = datetime.datetime.now(datetime.UTC)
    for pull in pulls:
        if not pull_requests.LOOPS_BRANCH.match(pull["headRefName"]):
            continue
        f_msg, r_msg = _dispatch_single_pull(pull, pulls, reviewer_login, minutes, now)
        if f_msg:
            failed.append(f_msg)
        if r_msg:
            refused.append(r_msg)

    return failed, refused


# The two states of a review that decide something in GitHub's own word for
# it, which is what `reconcile` reads a conflicting branch as held by. A
# `COMMENTED` review with no body is what every reply on a thread is submitted
# under and says nothing about the pull request; one with a body is a verdict
# that withholds approval, which `check_pr.state.standing_verdict` reads and
# the review pass answers (solorepo's DR-265). A `DISMISSED` one is a verdict
# GitHub has already taken back.
VERDICTS = ("APPROVED", "CHANGES_REQUESTED")


def _check_dispatch_rebase(pr: str | int, pull: common.Pull) -> None:
    """Validate preconditions before dispatching a coder rebase pass.

    Checks branch shape first because it is free, then whether a layer below
    the branch still conflicts, and finally checks mergeability against base.
    """
    from lib.move import reconcile
    head = str(pull.get("headRefName") or "")
    if not pull_requests.LOOPS_BRANCH.match(head):
        sys.exit(f"say: #{pr} is on {head}, which is not a loop branch "
                 "`(claude|gemini)/issue-<n>`. The rebase pass reads the Challenge it would "
                 "hand back to off the branch name, so on any other shape a pass that could not "
                 "settle the conflict has nowhere to stop. `coder.yml` holds that refusal already "
                 "and holds it after the dispatch, where it is a red run attached to no check; "
                 "a name that only nearly fits, `claude/issue-<n>-followup`, does not reach even "
                 "that — the guard reads it as naming no Challenge, the rebase is skipped, "
                 "and the run ends green having done nothing. Rebase it by hand.")
    open_now = channel.gh("pr", "list", "--state", "open", "--limit", "100", "--json",
                          "number,headRefName,baseRefName,mergeable")
    act = reconcile.owed_by_pull(pull, check_pr.state.IssueState.RESUMABLE,
                                 check_pr.PullRequestState.NEEDS_REBASE, "",
                                 reconcile.Constraints(pulls=open_now))
    if act is not None and act.kind == "hold" and act.lower is not None:
        sys.exit(f"say: #{pr} is a layer above #{act.lower}, which conflicts with its "
                 "own base, and rebasing a layer before the layers below it are clean "
                 "carries their unresolved commits as its own (solorepo's DR-133). A "
                 "conflicting stack is resolved from the bottom: dispatch the rebase for "
                 f"#{act.lower} first, or let the reconciler, which dispatches it on "
                 "its next pass and this one after.")
    merges = pull_requests.mergeability(pull) or "UNKNOWN"
    if merges != "CONFLICTING":
        base = pull.get("baseRefName")
        sys.exit(f"say: GitHub reports #{pr} as {merges} against "
                 f"{base}, not CONFLICTING, and the rebase pass is for a "
                 "branch GitHub builds no merge ref for — which is the state where no "
                 "review of the head can run and nothing but authoring can fix it. One "
                 "that has merely fallen behind is waiting on nothing and needs no Job: "
                 "its merge ref exists, so a review runs on the head as it stands, and "
                 "the branch comes onto its base when it is armed — `merge --auto` "
                 "advances before it arms, and `advance` sweeps up an armed one on the "
                 "next push to trunk.")


def _check_dispatch_review(pr: str | int, pull: common.Pull) -> None:
    """Validate preconditions before dispatching a coder review pass.

    The verdict read is `check_pr.state.standing_verdict`'s, so a comment
    verdict is a request for changes here as it is in the classifier
    (solorepo's DR-265). The classifier asks for a thread owed an answer
    before it moves a pull request unasked; this asks for none, on the same
    terms as the rebase pass above — the solo dispatching has decided there is
    a verdict to answer, and a comment verdict that left no thread left its
    ask in the body.
    """
    reviewer = channel.role_login("reviewer")
    if reviewer in [r.get("login") for r in pull.get("reviewRequests") or []]:
        sys.exit(f"say: GitHub shows a review of #{pr} requested of {reviewer} and not yet "
                 "given, so what stands on it is the reviewer's. The review pass answers a "
                 "verdict; a verdict answered and handed back is not one to answer again.")
    verdict = check_pr.state.standing_verdict(pull, reviewer)
    if verdict == "APPROVED":
        checks = pull.get("statusCheckRollup")
        if checks is None:
            try:
                view_res = channel.gh("pr", "view", str(pr), "--json", "statusCheckRollup")
                checks = view_res.get("statusCheckRollup") if isinstance(view_res, dict) else []
            except SystemExit:
                checks = []
        ok, msg = manager.check_green({"statusCheckRollup": checks})
        if not (not ok and "failing" in msg):
            sys.exit(f"say: the last verdict {reviewer} left on #{pr} is APPROVED, "
                     "and the review pass is for a verdict that withholds approval or an "
                     f"approved PR with failing checks ({msg})")
    elif verdict not in ("CHANGES_REQUESTED", "COMMENTED"):
        sys.exit(f"say: the last verdict {reviewer} left on #{pr} is "
                 f"{verdict or 'nothing'}, and the review pass is for a verdict that withholds "
                 f"approval — a request for changes or a comment verdict — or an approved pull "
                 f"request with failing checks: `move request-review "
                 f"{pr}` asks for a verdict; this dispatches the pass that answers one.")


def dispatch_pass(pr: str | int, task: str | None) -> None:
    """Start a coder pass on a pull request by hand: the act PR First's
    *Raise a Challenge with the form* step names, as a verb rather than
    as a command typed at GitHub.

    `coder.yml`'s events do not reach everything the coder is for. A verdict a
    session leaves behind is delivered once and to nobody, because moving the
    Issue back down fires the Issue door and re-delivers no review
    (solorepo's DR-142); and the rebase pass has no event of its own at all,
    which is why `advance` dispatches it above on the merge that caused it
    (solorepo's DR-133). Both gaps were named as the solo's to dispatch by hand,
    and by hand meant `gh workflow run coder.yml`, typed with whatever
    credential `gh` holds and refused by nothing: `GH_WRITES` in
    `.meta/hooks/signed_channel.py` named the CLI's writing verbs one by one and
    this was not among them. Starting a Job is an act GitHub records against an
    account, like a merge (solorepo's DR-075), so it belongs here — and the
    verb is only half of that pattern, which is why the hook now names the raw
    spelling too (solorepo's DR-151). The machine's dispatch was the channel's
    already; now a person's is, and there is no longer a shorter way.

    **The solo's, and the pull request is all that is read.**
    solorepo's DR-142 puts one guard on both of `coder.yml`'s doors and exempts
    exactly one delivery — the dispatch of a review pass, because the solo
    dispatching is the solo deciding. So nothing here reads the Challenge's
    level or its claim, and this verb does not become a second guard in front
    of the door that deliberately has none.

    **What it does refuse** (solorepo's DR-116). A pass with nothing to do, and
    a rebase pass that would do harm — which together are the whole of what the
    pull request can answer.

    The review pass reads the threads and answers a verdict that withholds
    approval, so it needs one standing: the newest verdict the reviewer's
    account left is a request for changes or a comment verdict
    (solorepo's DR-265), and no review is outstanding of that account — a
    request pending is the coder having answered already and handed back, which
    is the reviewer's turn and not a pass to run again.

    The rebase pass takes three, and each of them is one `advance`'s own
    dispatch takes, for the reason solorepo's DR-133 gave it there. What is
    not here is the other thing that filter reads, a review
    request outstanding: that is what makes the machine's dispatch necessary
    rather than what makes a rebase pass sensible, and the solo dispatching has
    decided the branch needs one already. The
    branch must be one GitHub reports as `CONFLICTING`: that is the state with
    no merge ref, where no review of the head can run and where `gh pr
    update-branch` is refused. A branch that has merely fallen behind is
    waiting on nothing — its merge ref exists, so the review runs on the head
    as it stands, and the branch is brought onto its base when it is armed, by
    `merge --auto` before the arming or by `advance` on the next push to trunk.
    The branch must be `claude/issue-<n>`, because that name is how the pass
    finds the Challenge it would hand back to: `coder.yml` refuses the rest
    itself, but after the dispatch, where the refusal is a red run attached to
    no check — and a name that is nearly the shape, `claude/issue-<n>-followup`,
    does not reach even that: the guard reads it as naming no Challenge, the
    rebase step is skipped, and the run ends green having done nothing at all.
    And the pull request must not be a layer above one that conflicts with
    its own base. Rebasing it first would carry the lower layer's unresolved
    commits as its own, so a conflicting stack is resolved from the bottom:
    the lower layer's rebase is dispatched first, by this verb or by the
    reconciler on its next pass, and this one's once the layers below it are
    clean. The root, and a layer whose lower layers are clean, is any loop
    branch's rebase.

    **What stands in for the read-back.** Starting a run is asynchronous and returns no immediate run ID, so there is nothing to verify on the remote in the moment: a dispatch returns no content and
    the run is created afterwards, so a `run list` a moment later asks about a
    run that may not exist yet. `coder.yml` groups both passes by pull request
    with `cancel-in-progress: false`, and the review pass takes the verdict's
    own key, so a dispatch that was one too many waits behind the run already
    going rather than racing it. What is printed is where the run will appear.
    """
    pull = channel.gh("pr", "view", str(pr), "--json", f"{pull_requests.ADVANCE},reviews")
    if task is None:
        task = "rebase" if pull.get("mergeable") == "CONFLICTING" else "review"
    if task == "rebase":
        _check_dispatch_rebase(pr, pull)
    else:
        _check_dispatch_review(pr, pull)
    run_coder(pr, task)
    print(f"dispatched the coder's {task} pass for #{pr} — {pull['title']}. GitHub creates the "
          "run after it answers the dispatch, so there is nothing to read back yet: "
          "`gh run list --workflow coder.yml` names it once it exists.")


def _advance_stack_layers(pull: common.Pull, all_open: Sequence[common.Pull],
                          advanced_stacks: set[str]) -> tuple[bool, int, list[str], list[str]]:
    """Advance linked stack layers if pull is part of a stack.

    Returns:
        tuple: (handled, moved_count, failed_list, refused_list)
    """
    root = pull_requests.stack_root(pull, all_open)
    root_number = str(root["number"])
    if root_number in advanced_stacks:
        return True, 0, [], []
    stack = pull_requests.stacked(root_number)
    if not stack:
        return False, 0, [], []
    advanced_stacks.add(root_number)
    layers = pull_requests.stack_layers(root, all_open)
    before_and_behind = [pull_requests.head_now(str(layer["number"])) for layer in layers]
    before = {str(layer["number"]): current
              for layer, (current, _) in zip(layers, before_and_behind, strict=True)}
    was_behind = {str(layer["number"]): behind
                  for layer, (_, behind) in zip(layers, before_and_behind, strict=True)}
    if any(pull_requests.mergeability(current) == "CONFLICTING" for current in before.values()):
        print(f"left #{root_number}'s stack alone: GitHub reports a layer conflicting "
              "with its base, and a stack is resolved from the bottom by the reconciler's "
              "rebase passes before it advances")
        return True, 0, [], []
    if not any(was_behind.values()):
        return True, 0, [], []
    must_move: dict[str, bool] = {}
    seen_behind = False
    for layer, (_, behind) in zip(layers, before_and_behind, strict=True):
        seen_behind = seen_behind or bool(behind)
        must_move[str(layer["number"])] = seen_behind
    errors, stack_refused = pull_requests.advance_stack(layers, before, must_move)
    moved = 1 if not errors and not stack_refused else 0
    return True, moved, errors, stack_refused


def _advance_single_pull(pull: common.Pull, pr: int | str | None,
                         bases: set[str]) -> tuple[int, int, list[str]]:
    """Advance a single non-stacked pull request onto its base branch.

    Returns:
        tuple: (moved_count, left_count, failed_list)
    """
    number = str(pull["number"])
    if pull["headRefName"] in bases:
        if pr is not None:
            sys.exit(f"say: #{pr} is the base of another open pull request; "
                     "it is not linked as a GitHub stack and cannot advance atomically (solorepo's DR-243)")
        return 0, 0, []
    before, behind = pull_requests.head_now(number)
    if not behind:
        return 0, 0, []
    if pr is None and pull_requests.mergeability(pull) == "CONFLICTING":
        print(f"left #{number} to the dispatch below: {behind} commit(s) behind "
              f"{pull['baseRefName']} and conflicting with it, which GitHub "
              f"will not rebase — {pull['title']}")
        return 0, 1, []
    before, behind = pull_requests.head_now(number)
    if not behind:
        return 0, 0, []
    channel.gh("pr", "update-branch", number, "--rebase", parse=False)
    print(f"advanced #{number}: {behind} commit(s) behind {pull['baseRefName']} — {pull['title']}")
    failed: list[str] = []
    before_oid = before["headRefOid"]
    after = channel.settled(lambda: channel.gh("pr", "view", number, "--json",
                                               pull_requests.ADVANCE),
                            lambda now: now["headRefOid"] != before_oid)
    if after["headRefOid"] == before_oid:
        failed.append(f"#{number} is on the head it was before the update and "
                      "GitHub has not moved it within the wait, so whether the "
                      "rebase drops the arming is unread — and dropped, it is "
                      "out of reach of every later sweep")
    elif pull_requests.behind_by(after):
        failed.append(f"#{number} is still behind {pull['baseRefName']} after the update")
    if pull.get("autoMergeRequest") and not after.get("autoMergeRequest") and after.get("state") != "MERGED":
        pull_requests.arm(number, f"{pull['title']} (#{number})")
        now = channel.settled(lambda: channel.gh("pr", "view", number, "--json",
                                                 pull_requests.ADVANCE),
                              lambda seen: seen.get("autoMergeRequest") or seen["state"] == "MERGED")
        if now["state"] == "MERGED":
            print(f"merged #{number}: re-armed after the update, and green")
        elif not now.get("autoMergeRequest"):
            failed.append(f"#{number} lost its arming to the update and GitHub "
                          "does not show it armed after the call that re-armed it")
        else:
            print(f"armed #{number} again: moving the head had dropped it")
    return 1, 0, failed


def _is_advance_candidate(pull: common.Pull, pr: int | str | None, bases: set[str],
                          heads: set[str], reviewer_login: str) -> bool:
    """Check if an open pull request is candidate for advance."""
    if pull.get("autoMergeRequest"):
        return True
    if pull_requests.is_approved_pull(pull, reviewer_login=reviewer_login):
        return True
    return bool(pr is not None and pull.get("headRefName") in bases and pull.get("baseRefName") not in heads)


ADVANCE_NOTICE_MARKER = "<!-- solorepo:advance-finding -->"
"""HTML comment marker identifying an in-place advance finding notice (solorepo's DR-255)."""


def _advance_notice_body(problem: str) -> str:
    """Generate signed advance finding notice comment body with attribution trailers."""
    raw = (
        f"{ADVANCE_NOTICE_MARKER}\n"
        "**Advance sweep finding.** `advance` could not update this branch on push to `main` (solorepo's DR-255):\n"
        f"> {problem}\n\n"
        "This in-place notice will be updated or removed automatically when the branch advances cleanly."
    )
    return channel.signed(raw)


def find_notice_comments(pr: str | int, marker: str) -> list[dict[str, Any]]:
    """Find all existing notice comments on a pull request matching marker."""
    try:
        comments = channel.gh(
            "api", "--paginate", f"repos/{channel.repo()}/issues/{pr}/comments",
            tolerate_fail=True,
        )
    except common.UNREACHED:
        return []
    if not isinstance(comments, list):
        return []
    return [c for c in comments if isinstance(c, dict) and marker in (c.get("body") or "")]


def find_notice_comment(pr: str | int, marker: str) -> dict[str, Any] | None:
    """Find primary notice comment on a pull request matching marker, or None."""
    matches = find_notice_comments(pr, marker)
    return matches[0] if matches else None


def _find_advance_notice_comment(pr: str | int) -> dict[str, Any] | None:
    """Find existing advance notice comment on a pull request, or None."""
    return find_notice_comment(pr, ADVANCE_NOTICE_MARKER)


def reconcile_notice(pr: str | int, marker: str, body_or_fn: Any,
                     problem: str | None, label: str = "notice") -> None:
    """Reconcile in-place failure notice on a pull request (solorepo's DR-255).

    Enforces a single standing notice comment per marker. Callers owe an attributed
    and signed comment body satisfying Article 19 and solorepo's DR-233.

    Parameters:
        pr: Pull request number to inspect and mutate.
        marker: HTML comment marker string identifying the notice class.
        body_or_fn: Callable taking `problem` and returning a signed markdown body,
            or a string coerced via `str()`.
        problem: Finding or diagnostic text. If non-empty, posts or updates the notice
            in place. If None, deletes any standing notices matching `marker`.
        label: Prefix for status logging and warning messages (default "notice").
    """
    try:
        if problem and not channel.speaker():
            print(f"{label}: skipping notice on #{pr} (no actor session in environment)",
                  file=sys.stderr)
            return
        matches = find_notice_comments(pr, marker)
        if problem:
            desired = body_or_fn(problem) if callable(body_or_fn) else str(body_or_fn)
            if matches:
                existing = matches[0]
                existing_body = existing.get("body") or ""
                head_match = re.search(r"head:(\S+)", desired)
                head_tag = head_match.group(0) if head_match else None
                needs_update = (
                    problem not in existing_body
                    or (head_tag is not None and head_tag not in existing_body)
                )
                if needs_update:
                    comment_id = existing.get("id")
                    channel.gh("api", f"repos/{channel.repo()}/issues/comments/{comment_id}",
                               "-X", "PATCH", "-f", f"body={desired}",
                               parse=False, tolerate_fail=True)
                    print(f"{label}: updated notice on #{pr}")
                for surplus in matches[1:]:
                    channel.gh("api", f"repos/{channel.repo()}/issues/comments/{surplus.get('id')}",
                               "-X", "DELETE", parse=False, tolerate_fail=True)
            else:
                channel.gh("api", f"repos/{channel.repo()}/issues/{pr}/comments",
                           "-f", f"body={desired}",
                           parse=False, tolerate_fail=True)
                print(f"{label}: posted notice on #{pr}")
        elif matches:
            for standing in matches:
                comment_id = standing.get("id")
                channel.gh("api", f"repos/{channel.repo()}/issues/comments/{comment_id}",
                           "-X", "DELETE", parse=False, tolerate_fail=True)
            print(f"{label}: cleared notice on #{pr}")
    except (SystemExit, *common.UNREACHED) as exc:
        print(f"warning: could not reconcile {label} on #{pr}: {exc}", file=sys.stderr)


def reconcile_advance_notice(pr: str | int, problem: str | None) -> None:
    """Reconcile in-place advance failure notice on a pull request (solorepo's DR-255).

    When `problem` is non-empty:
        Posts a signed notice comment if none exists, or updates the existing
        notice comment in place if the problem text has changed.
    When `problem` is None:
        Deletes any standing advance notice comment left from a prior run.
    """
    reconcile_notice(pr, ADVANCE_NOTICE_MARKER, _advance_notice_body, problem, label="advance")


def _report_advance_sweep(open_now: Sequence[common.Pull], failed: list[str], refused: list[str],
                          evaluated: Sequence[common.Pull] | None = None) -> None:
    """Run sweep dispatch and report pull request problems."""
    reported, dispatch_refused = dispatch(open_now)
    failed += reported
    refused.extend(dispatch_refused)
    if failed:
        print(f"advance: {len(failed)} pull request(s) "
              "reported a problem of their own, "
              "which the next push to trunk asks about again:")
        for problem in failed:
            print(f"  {problem}")
    problems_by_pr: dict[str, str] = {}
    for problem in failed:
        m = re.match(r"^#(\d+)\b", problem)
        if m:
            problems_by_pr[m.group(1)] = problem
    candidates = evaluated if evaluated is not None else open_now
    for pull in candidates:
        number = str(pull.get("number"))
        reconcile_advance_notice(number, problems_by_pr.get(number))
    if refused:
        sys.exit("say: " + "; ".join(refused))


def advance(pr: int | str | None = None, held: bool = False) -> None:
    """Rebase armed or approved pull requests or linked stacks onto their base branch.

    Rebases armed or approved pull requests that are behind their base branch,
    verifying that the update settles and that auto-merge status is preserved
    (solorepo's DR-113, solorepo's DR-158). Advances a linked stack as one
    operation, bottom layer first, when GitHub reports the layers as a stack,
    no layer conflicts with its base and at least one layer is behind; a
    conflicting stack is left for the solo, and a branch that is another pull
    request's base without being a linked layer is refused when named and passed
    over in a sweep (solorepo's DR-133, solorepo's DR-243). When invoked as a
    general sweep (pr=None), delegates conflicting branches to autonomous coder
    dispatch passes.

    A sweep succeeds when it reads every open pull request, whatever those pull
    requests report: one branch's failed rebase or stranded review request is
    printed under `advance: ... reported a problem of their own` and leaves the
    exit code at zero (solorepo's DR-238). A named pull request keeps its
    refusal in the exit code, because the caller asked about that one.

    Parameters:
        pr (int or str, optional): Specific pull request number to advance. When None,
            sweeps all open pull requests.
        held (bool): If True, bypasses the armed/approved check for the caller's held branch.

    Raises:
        SystemExit: If an explicit pull request cannot be advanced, if a read the
            sweep itself depends on — the list of open pull requests, the reviewer's
            login — is refused, the requested stack is not linear or linked, or if
            GitHub refused a write the sweep makes on a pull request's behalf: a
            `coder.yml` dispatch, or the re-request of a stranded or stack-dropped
            review. No pull request's own state causes either.
    """
    if pr is not None:
        open_now = [channel.gh("pr", "view", str(pr), "--json", pull_requests.ADVANCE)]
        all_open = channel.gh("pr", "list", "--state", "open", "--json", pull_requests.ADVANCE)
    else:
        open_now = channel.gh("pr", "list", "--state", "open", "--json", pull_requests.ADVANCE)
        all_open = open_now
    bases = {p.get("baseRefName") for p in all_open if p.get("baseRefName")}
    heads = {p.get("headRefName") for p in all_open if p.get("headRefName")}
    reviewer_login = channel.role_login("reviewer")
    found = open_now if held else [
        p for p in open_now if _is_advance_candidate(p, pr, bases, heads, reviewer_login)
    ]
    moved, left = 0, 0
    failed: list[str] = []
    refused: list[str] = []
    advanced_stacks: set[str] = set()
    if not found:
        if pr is not None:
            sys.exit(f"say: #{pr} is not armed or approved; nothing has asked it to land")
        print("advance: nothing armed or approved is open")
    else:
        for pull in found:
            number = str(pull["number"])
            try:
                if pull.get("headRefName") in bases or pull.get("baseRefName") in heads:
                    handled, stack_moved, errors, stack_refused = _advance_stack_layers(
                        pull, all_open, advanced_stacks
                    )
                    if handled:
                        moved += stack_moved
                        failed += errors
                        refused += stack_refused
                        continue
                single_moved, single_left, single_failed = _advance_single_pull(pull, pr, bases)
                moved += single_moved
                left += single_left
                failed += single_failed
            except SystemExit as exc:
                failed.append(f"#{number}: {exc.code}")
        if not moved and not failed and len(found) > left:
            print(f"advance: {len(found) - left} pull request(s) current with their base")
    if pr is None:
        _report_advance_sweep(open_now, failed, refused, evaluated=found)
        return
    problem = "; ".join(failed + refused) if (failed or refused) else None
    reconcile_advance_notice(pr, problem)
    if problem:
        sys.exit("say: " + problem)


def advance_stranded(pulls: list[dict[str, Any]],
                     evaluations: dict[int, tuple[bool, list[str]]],
                     owner: str, name: str,
                     dry_run: bool = False) -> None:
    """Rebase the approved pull requests that nothing but a stale branch holds back.

    Read when no open pull request is eligible, and on no event `advance.yml`
    already answers. A pull request whose only failing semaphore is
    `BEHIND_BASE` is approved and green, and with its conversations resolved it
    is one rebase from landing — and until this the rebase had a single trigger,
    `advance.yml` on a push to `main` (solorepo's DR-113). A pull request
    approved *after* the push that put it behind is reached by no event at all,
    so with nothing else eligible to move trunk the repository sat idle holding
    work that was approved and green (solorepo's #452, stranded behind
    solorepo's #447). `merge.yml` reaches this on its schedule and on a gate or
    review completion, so the rebase no longer waits on an unrelated merge
    (solorepo's DR-161).

    Two filters decide a candidate, and they have different owners. The
    readiness one is this function's. A reason list of exactly `[BEHIND_BASE]`
    is what keeps out a pull request that is behind *and* red, since a second
    failure puts a second reason in the list and `advance`'s own filter reads
    no check run. The conversations are read here too: `evaluate_pr` consults
    them only while nothing else has failed, so `BEHIND_BASE` arrives with the
    threads unread, and `MERGE_MANAGER_FIELDS` does not ask `pr list` for them.
    Rebasing on an unresolved conversation outdates the anchored comment
    PR First's *Reread the diff and notice* step parks work on, and a pull request holding one
    cannot merge until it is resolved anyway.

    The branch-safety refusals are `advance`'s, because this calls that verb by
    number rather than repeating its filter: an unlinked branch that is the
    base of another open pull request is refused, and one that is neither
    armed nor approved is refused. A branch that conflicts never reaches
    here, since `classify_pr` reads it as `NEEDS_REBASE` and `lifecycle_refusal`
    gives that its own reason, which this reads for the one; a branch both
    behind and conflicting collects `BEHIND_BASE` and the conflict reason,
    and two reasons fail the exact-list test as one did. A refusal is printed
    rather than exited on:
    `merge.yml` runs on a fifteen-minute schedule, and a stack base that stays
    behind would otherwise paint the workflow red on the clock over a state
    only the solo settles.

    Parameters:
        pulls (list): The open pull requests `merge_manager` evaluated.
        evaluations (dict): Pull request number to the `(eligible, reasons)`
            pair `evaluate_pr` answered with.
        owner (str): The repository's owner, for the conversations query.
        name (str): The repository's name, for the conversations query.
        dry_run (bool): If True, name what would be rebased and rebase nothing.
    """
    for pull in pulls:
        if evaluations[pull["number"]][1] != [manager.BEHIND_BASE]:
            continue
        number = str(pull["number"])
        threads_ok, threads_msg = manager.check_threads(pull, owner, name)
        if not threads_ok:
            print(f"merge-manager: not advancing #{number} — {threads_msg}")
            continue
        if dry_run:
            print(f"merge-manager: dry run — not advancing #{number} — {pull.get('title', '')[:50]}")
            continue
        try:
            advance(number)
        except SystemExit as exc:
            print(f"merge-manager: could not advance #{number} — {exc.code}")
