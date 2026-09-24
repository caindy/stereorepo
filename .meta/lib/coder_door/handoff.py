"""Coder-door handoff and completion behavior for `.meta/coder_door.py`.

Enacts solorepo's DR-217, solorepo's DR-264, and solorepo's DR-284.

Defect history in .meta/coder_door.history.md (solorepo's DR-171).
"""

import json
import sys
from typing import Any

import agents
import channel
import check_pr
from lib.coder_door import coder_door


def outcome_of(ended: coder_door.Ended) -> str:
    """How the pass ended: the word of the last rung that ran, `skipped` where none did.

    A later rung runs only where the one before it failed, so the last rung
    that was not skipped is the one whose word the account names
    (solorepo's DR-257, solorepo's DR-281).
    """
    ran = [outcome for outcome in (ended.outcomes or ()) if outcome != "skipped"]
    return ran[-1] if ran else "skipped"


def transcript_entries(text: str) -> list[dict[str, Any]]:
    """Every JSON object a transcript holds, whether it is one document or a stream of lines.

    The file arrives in more than one shape. `claude-code-action` publishes a
    single JSON array, but a runner or a wrapper interleaves its own status
    lines into the same stream, and whole-document decoding has already
    failed on this file here: `agents.history.md` records `_from_ndjson`
    being established for it, `agents.parse_agents` tries the document, then
    the lines, then the raw log, and `detect_fallback.py` falls through to a
    text scan rather than answering nothing. So the document is tried first
    and the lines after, each unreadable line skipped rather than the
    reading abandoned.

    Parameters:
        text (str): What the transcript file held.

    Returns:
        list[dict[str, Any]]: The objects read, in the order they arrived.
    """
    try:
        whole = json.loads(text)
    except ValueError:
        pass
    else:
        return [
            entry
            for entry in (whole if isinstance(whole, list) else [whole])
            if isinstance(entry, dict)
        ]
    entries: list[dict[str, Any]] = []
    for line in text.splitlines():
        candidate = line.strip()
        if not (candidate.startswith("{") and candidate.endswith("}")):
            continue
        try:
            entry = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def cut_by_cap(execution: str) -> int | None:
    """The turns a take pass spent where its transcript says the turn cap cut it.

    Claude Code writes the session's messages to the file
    `claude-code-action` publishes as `execution_file`, and the result entry
    carries `subtype: error_max_turns` where the cap ended the session,
    beside the `num_turns` it spent. The step's conclusion is `success` in
    that case, the process having exited in an orderly way, so the
    transcript is the only place the reason is (solorepo's DR-277). A path
    the step never published, a file that cannot be read, and one holding no
    capped result entry all answer `None`, and the run log says which: a
    reading that cannot say the cap was hit is not one that says it was. A
    file the reader cannot decode whole is read by `transcript_entries` line
    by line rather than treated as a session that was never capped, and a
    capped entry whose `num_turns` is not a number answers `0`, the cap
    named and the turns not, rather than raising out of the door.

    Parameters:
        execution (str): Where the harness step wrote the transcript.

    Returns:
        int | None: The turns the capped session spent, `0` where the
            transcript counted none, and `None` where the cap did not cut it.
    """
    if not execution:
        return None
    try:
        text = agents.read_content(execution, quiet=True)
    except OSError as unreadable:
        print(f"the turn cap could not be read from {execution}: {unreadable}", file=sys.stderr)
        return None
    capped = [
        entry for entry in transcript_entries(text) if entry.get("subtype") == coder_door.CAPPED
    ]
    if not capped:
        return None
    try:
        return int(capped[-1].get("num_turns") or 0)
    except (TypeError, ValueError) as uncounted:
        print(
            f"the cap in {execution} counted no turns this could read: {uncounted}", file=sys.stderr
        )
        return 0


def cut_before(number: str) -> bool:
    """Whether the pull request already carries the account of a run cut by its turn cap.

    The account is the evidence, since a run holds nothing of the one before
    it and the pull request is what crosses the seam. The author is matched
    as well as the phrase: `coder_door.CAP_MARK` is a sentence in English, and the
    account invites a reviewer to quote it, so the phrase alone would read a
    quotation as a second cap. A read GitHub refuses answers `False`, the
    login it speaks as included, which offers the reviewer a second draft
    rather than handing the Challenge to the solo on a failed read: the
    first costs a review pass and the second strands work nobody is standing
    over.

    Parameters:
        number (str): The pull request the run left.
    """
    view = channel.gh("pr", "view", number, "--json", "comments", default=None)
    try:
        mine = channel.role_login("coder")
    except SystemExit as unreadable:
        print(f"who this door speaks as could not be read: {unreadable}", file=sys.stderr)
        return False
    comments = (view or {}).get("comments") or []
    return any(
        coder_door.CAP_MARK in str(comment.get("body") or "")
        and str((comment.get("author") or {}).get("login") or "") == mine
        for comment in comments
    )


def account_of(outcome: str, cap: int | None) -> str:
    """The account's first sentence: the cap where one cut the pass, else the step's own word."""
    if cap is None:
        return coder_door.DID_NOT_FINISH.format(outcome=outcome, run=coder_door.run_url())
    return coder_door.CUT_BY_CAP.format(
        spent=coder_door.TURNS_SPENT.format(turns=cap) if cap else "", run=coder_door.run_url()
    )


def what_run_left(issue: str) -> dict[str, Any] | None:
    """What the hand-back needs about the pull request the run left, or `None` where unreadable.

    A read that cannot answer is a reason to give the solo rather than the
    end of the handler: a handler that dies hands nothing back
    (solorepo's DR-155).
    """
    try:
        return dict(check_pr.sweep.hand_back(issue))
    except (SystemExit, Exception) as failed:  # noqa: BLE001  # reason: a failed read here is a reason to give the solo and not the end of the handler
        print(f"the hand-back could not read what the run left: {failed}", file=sys.stderr)
        return None


def stop_with(issue: str, outcome: str, branch: str, why: str, cap: int | None = None) -> None:
    """Hands the Challenge to the solo with the account and why the reviewer is not asked."""
    body = (
        account_of(outcome, cap)
        + coder_door.STAYS_OPEN.format(branch=branch)
        + coder_door.NOT_REQUESTED.format(why=why)
    )
    channel.sibling("move").stop(issue, channel.signed(body))


def hand_back(issue: str, outcome: str, prefix: str, cap: int | None = None) -> None:
    """Hands back a take that ended without saying where it stopped.

    Every way a run ends releases the claim or requests review, so that a
    Challenge is never left claimed behind a dead step. What the run left is
    read first, since somebody holding the pull request means the run
    finished and then ran out; then the Issue, since one GitHub has closed
    or one already at `human` is finished whatever the branch says; then
    whether the branch merged. Green and clean, the account is posted on the
    pull request before review is requested, since the request carries no
    words and the one thing the reviewer cannot otherwise know is that this
    is where a run stopped and not where one finished; the Issue stays
    claimed at its level (solorepo's DR-129). Otherwise the Challenge goes to the solo through
    `stop`, with why the reviewer was not asked, and a read that failed is
    one such reason rather than the end of the handler (solorepo's DR-155).

    A pass the turn cap cut is a run that stopped and reaches here alongside
    one whose step failed, its account naming the cap rather than the step's
    conclusion (solorepo's DR-277). The reviewer is offered such a draft
    once: a second cap on a pull request that already carries a cap account
    goes to the solo, since a Challenge that does not fit twice is not the
    loop's.

    Parameters:
        issue (str): The Challenge.
        outcome (str): How the take step ended.
        prefix (str): The harness's branch prefix, naming the branch where nothing was left.
        cap (int | None): The turns a capped pass spent, and `None` where the
            cap did not cut it.
    """
    left = what_run_left(issue)
    number = str(left["number"]) if left and left.get("number") else ""
    branch = str((left or {}).get("branch") or f"{prefix}/issue-{issue}")
    base = str((left or {}).get("base") or "main")
    if left and left.get("handed"):
        print(
            f"#{issue}'s pull request has its review requested; the run finished and then ran out"
        )
        return
    view = channel.gh("issue", "view", issue, "--json", "state,labels", default=None)
    if view is None:
        stop_with(issue, outcome, branch, coder_door.UNREADABLE_ISSUE.format(issue=issue), cap)
        return
    labels = check_pr.state.issue_labels(view)
    level = next((lvl for lvl in channel.sibling("move").DIFFICULTIES if lvl in labels), "")
    if view.get("state") != "OPEN":
        print(f"#{issue} is closed; a Challenge GitHub has closed has nothing to hand back")
        return
    if level == "human":
        print(f"#{issue} is already at human; the run handed it back itself")
        return
    merged = channel.gh(
        "pr", "list", "--state", "merged", "--head", branch, "--json", "number", default=None
    )
    if merged is None:
        stop_with(issue, outcome, branch, coder_door.UNREADABLE_MERGE.format(branch=branch), cap)
    elif merged:
        print(
            f"#{issue}'s pull request #{merged[0]['number']} has merged; the run finished and "
            "then ran out"
        )
    elif (
        number
        and left
        and left.get("green")
        and not left.get("conflicting")
        and not (cap is not None and cut_before(number))
    ):
        body = account_of(outcome, cap) + coder_door.WORTH_READING.format(issue=issue, level=level)
        channel.sibling("post").conversation_comment(number, channel.signed(body))
        channel.sibling("move").request_review(number, "reviewer")
    else:
        stop_with(issue, outcome, branch, not_requested(left, number, branch, base), cap)


def not_requested(left: dict[str, Any] | None, number: str, branch: str, base: str) -> str:
    """Why the reviewer is not asked, where the pull request the run left is no handoff.

    The order is the hand-back's own: a read that failed says so before
    anything is concluded from it, then a run that opened nothing, then a
    branch no review could run on, then a pull request that already carries
    the account of a turn cap, this being the second, and a red gate last,
    that being the ordinary case.

    Parameters:
        left (dict[str, Any] | None): What the run left, or `None` where unreadable.
        number (str): The pull request the run left, empty where it opened none.
        branch (str): The branch the run worked on.
        base (str): What that branch is based on.
    """
    if left is None:
        return coder_door.UNREADABLE_LEFT
    if not number:
        return "the run opened no pull request"
    if left.get("conflicting"):
        return coder_door.CONFLICTS.format(number=number, base=base, branch=branch)
    if left.get("green"):
        return coder_door.CUT_TWICE.format(number=number)
    return coder_door.NOT_GREEN.format(number=number)


def verify(task: str, ended: coder_door.Ended) -> None:
    """Ends the run red where a pass ran and no rung finished it.

    Raises:
        SystemExit: Where no rung succeeded and one failed; a pass that was
            cancelled, or never ran, is not a failure of the pass.
    """
    outcomes = ended.outcomes or ()
    if "success" not in outcomes and "failure" in outcomes:
        sys.exit(coder_door.NEITHER.format(task=task, outcomes=",".join(outcomes)))
    print(f"the {task} pass ended {','.join(outcomes)}")


def redeliver(number: str) -> None:
    """Redelivers the review pass where a rebase cleared a standing request for changes.

    A rebase pushes with `--force-with-lease`, which GitHub reports as
    `synchronize`, an event the coder's door does not listen for; where the
    reviewer had already requested changes no request is pending, so
    nothing fires and the pull request sits answered by nobody
    (solorepo's #777). `dispatch` reads the standing verdict and the pending
    request before deciding, and refuses where there is nothing to redeliver,
    which is said and not a failure.
    """
    try:
        channel.sibling("move").dispatch_pass(number, "review")
    except SystemExit as refused:
        print(f"nothing to redeliver on #{number}: {refused}")


def coder_after(number: str, delivery: coder_door.Delivery, ended: coder_door.Ended) -> None:
    """The coder's door after the session: what each pass owes once its steps have ended.

    A take that failed or was cancelled is handed back, and so is one whose
    transcript says the turn cap cut it, which the step conclusion reports as
    a success (solorepo's DR-277); a rebase that succeeded redelivers the
    review pass, and one that did not is verified; an answer is verified.
    Verification ends the run red where neither harness finished the pass.

    Parameters:
        number (str): The Challenge on a take, the pull request otherwise.
        delivery (coder_door.Delivery): What the workflow knew before the session.
        ended (coder_door.Ended): How the session's steps ended.
    """
    if ended.outcomes is None:
        sys.exit("::error::" + coder_door.OUTCOMES_NOT_SAID)
    if delivery.task == "take":
        outcome = outcome_of(ended)
        stopped = outcome in ("failure", "cancelled")
        cap = None if stopped else cut_by_cap(ended.execution)
        if stopped or cap is not None:
            hand_back(number, outcome, ended.branch_prefix, cap)
        else:
            print(f"the take pass ended {outcome}; nothing to hand back")
    elif delivery.task == "rebase":
        if "success" in (ended.outcomes or ()):
            redeliver(number)
        else:
            verify(delivery.task, ended)
    else:
        verify(delivery.task, ended)
