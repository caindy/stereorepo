"""Coder door lifecycle for `.meta/say/on` (solorepo's DR-217, DR-264)."""
import os
import sys
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

import channel
import check_pr
from lib.on import common, routing

CODER_HARNESSES = ("gemini", "claude")
"""The harnesses the coder's door chooses among, in the order asked: Antigravity CLI
by label or as the fallback (solorepo's DR-245), and Claude Code by default."""

PASSES = ("take", "rebase", "answer", "promote")
"""The coder's four passes (solorepo's DR-133, solorepo's DR-159), as `--pass` names them."""

NO_JOB = ("closed", "stale", "unnamed", "held")
"""The words `take` decides with where a verdict's delivery is nobody's to answer: the loop
stands down on `closed`, `stale` and `unnamed`, and on `held` the Issue is the solo's at `hard`,
where a session may have ended before the review landed, so the sign is one more line alerting
them (solorepo's DR-142)."""

RUN_LEFT = ("A run before this one stopped and left pull request #{number} open on that branch: "
            "check the branch out and continue under it, and do not branch or open again.")
"""The take prompt's resume clause, where `before` found a pull request on the branch."""

RUN_LEFT_NOTHING = "No run has taken this Issue before."
"""The take prompt's resume clause, where `before` found nothing on the branch."""

HARNESS_LEFT = ("A harness before this one left pull request #{number} open on that branch: "
                "check the branch out and continue under it, and do not branch or open again.")
"""The take prompt's resume clause on a later rung, where `between` found a pull request."""

HARNESS_LEFT_NOTHING = "No harness has left a pull request on that branch."
"""The take prompt's resume clause on a later rung, where `between` found nothing."""

STOP_ISSUE = "`.meta/say/move stop {issue}` with why on stdin."
"""How the answering prompt says to stop, where the branch names a Challenge to hand back."""

STOP_COMMENT = ("say why on the pull request with `.meta/say/post comment {number}`, this branch "
                "naming no Challenge to hand back.")
"""How the answering prompt says to stop, where the branch names no Challenge."""

UNNAMED_REBASE = ("::error::#{n} is on {branch}, which names no Challenge, so a rebase pass that "
                  "could not finish would have nothing to hand back. Rebase it by hand.")
"""The refusal of a rebase dispatched for a branch that is not the loop's shape."""

NO_JOB_SAID = ("No run takes this up: #{issue} is {why}, so what stands on this pull request is "
               "the solo's. What decided that is in the run log, {run}.")
"""The sign the verdict's door leaves where the loop stood down (solorepo's DR-142)."""


class Delivery(NamedTuple):
    """What the workflow knows about a coder delivery before the session.

    Attributes:
        task: Which pass the event opened: `take`, `rebase`, `answer` or `promote`.
        event: The event the delivery arrived on, as `github.event_name` names it.
        harness: The harness a dispatch asked for, or the empty string.
    """

    task: str
    event: str
    harness: str


def loop_issue(branch: str) -> str:
    """The Challenge a loop branch names, or empty where the shape is not the loop's.

    `<harness>/issue-<n>` is the only shape the loop cuts; what follows
    `issue-` is taken whole, so `claude/issue-169-followup` names
    `169-followup`, which the take door reads as no Challenge the loop holds.
    """
    prefix, cut, rest = branch.partition("/issue-")
    return rest if cut and prefix in CODER_HARNESSES else ""


def labelled(labels: Sequence[str], among: Sequence[str]) -> str | None:
    """The harness a `harness:` label among `labels` names, first of `among` taken, or `None`."""
    return next((name for name in among if f"harness:{name}" in labels), None)


def coder_harness(delivery: Delivery, labels: Sequence[str]) -> str:
    """Which harness runs the coder's pass.

    On a take the Challenge's own label wins over a dispatch's input, whose
    default is never empty, and the input wins where the label names no
    harness, so an explicit ask still decides over silence; on the other
    passes the input wins, then the pull request's label. Claude Code where
    nothing says.

    Parameters:
        delivery (Delivery): What the workflow knows.
        labels (Sequence[str]): The Challenge's labels on a take, the pull request's otherwise.
    """
    named = labelled(labels, CODER_HARNESSES)
    if delivery.task == "take":
        return named or delivery.harness or "claude"
    return delivery.harness or named or "claude"


def coder_depth(task: str, level: str, harness: str, fields: Mapping[str, str]) -> None:
    """The pass's depth and its chain as step outputs, and the first rung's prompt written.

    The depth is the routing policy's, by the pass first and the level after
    (solorepo's DR-281); Claude Code's models run high extended thinking on
    every pass (solorepo's DR-186). The chain is emitted as `tier_<n>_*` for
    each rung from the primary, which the ladder of attempt steps reads by
    number. The chain and the fields go
    under `.review/` for `between` to read, with the first rung's prompt,
    after the tree is checked for tracking anything there: on every pass but
    a take the pull request's branch is checked out by now, and a branch that
    tracks a symlink under `.review/` would turn the write into one onto its
    target.

    Parameters:
        task (str): The pass.
        level (str): The level a take is at; `medium` on every other pass.
        harness (str): The primary, by label, input or default.
        fields (Mapping[str, str]): What the prompt's form is filled with.
    """
    common.emit("GITHUB_OUTPUT", level=level)
    tiers = routing.coder_chain(harness, task, level)
    common.name_tiers(tiers)
    common.refuse_tracked_scratch()
    common.write_routing("coder", task, tiers, fields)


def pull_fields(number: str, pull: Mapping[str, Any], issue: str, task: str) -> dict[str, str]:
    """What a pass on a pull request fills its prompt with: the pull request, its branches, the
    Challenge, and on the answering pass how to stop, which depends on whether one is named."""
    fields = {"number": number, "repository": channel.repo(),
              "branch": str(pull.get("headRefName") or ""),
              "base": str(pull.get("baseRefName") or ""), "issue": issue}
    if task == "answer":
        fields["stop"] = STOP_ISSUE.format(issue=issue) if issue \
            else STOP_COMMENT.format(number=number)
    return fields


def run_url() -> str:
    """This run's page, from the environment a run has."""
    return (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
            f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/"
            f"{os.environ.get('GITHUB_RUN_ID', '')}")


def taken(issue: str, delivery: Delivery) -> dict[str, Any]:
    """Whether the delivery is still the loop's, read through the take door.

    A dispatch of a review pass is the solo's own word and is not read
    against; every other delivery is, on the label's door and on the
    verdict's alike (solorepo's DR-142), and `by` carries a word for each
    that must not run.
    """
    if delivery.task == "answer" and delivery.event == "workflow_dispatch":
        decided = check_pr.sweep.Decision("")._asdict()
    else:
        door = check_pr.sweep.ISSUE_DOOR if delivery.task == "take" else delivery.event
        decided = check_pr.sweep.take(issue, door)
    common.emit(
        "GITHUB_OUTPUT", by=decided["by"], why=decided["why"],
        resume=decided["resume"], level=decided["level"],
    )
    if decided["said"]:
        print(decided["said"])
    return decided


def find_pull(number: str, delivery: Delivery) -> dict[str, Any] | None:
    """The pull request a pass answers: its branch, base, and Challenge, and the branch checked out.

    The base is read and not assumed to be `main`, since a layer is based on
    the layer below. The Challenge is the branch's own name, because a pass
    that cannot finish hands that Challenge back and has nothing else to
    name, so a rebase of a branch that names none is refused. A pull request
    merged or closed already is nothing for the run to do, said as `by`.
    The promotion pass tolerates a checkout that fails, since it reads
    GitHub and writes nothing in the tree.

    Returns:
        dict[str, Any] | None: The pull request, or `None` where it is finished.
    """
    view: dict[str, Any] = channel.gh("pr", "view", number, "--json",
                                      "state,headRefName,baseRefName,labels")
    branch, base = str(view.get("headRefName") or ""), str(view.get("baseRefName") or "")
    issue = loop_issue(branch)
    if delivery.task == "rebase" and not issue:
        sys.exit(UNNAMED_REBASE.format(n=number, branch=branch))
    common.emit("GITHUB_OUTPUT", number=number, branch=branch, base=base, issue=issue)
    if view.get("state") in ("MERGED", "CLOSED"):
        print(f"#{number} is {view['state']} already; nothing for this run to do")
        common.emit("GITHUB_OUTPUT", by="merged", why="merged")
        return None
    try:
        common.command(["git", "checkout", "--quiet", branch])
    except SystemExit:
        if delivery.task != "promote":
            raise
        print(f"{branch} could not be checked out; the promotion pass reads GitHub, not the tree")
    return view


def coder_before(number: str, delivery: Delivery) -> None:
    """The coder's door before the session: the pull request, the harness, whether taken, how deep.

    A take reads the Challenge; the other passes read the pull request and
    check its branch out, so the work continues where the last pass left it.
    The harness is chosen by label and input, named as every door names it.
    Whether the delivery is still the loop's is read now rather than off the
    frozen payload, since a level can move while a run waits in its
    concurrency group (solorepo's #117): a claim with a pull request open is
    a duplicate on the label's door, and a `hard` Issue's branch is the
    solo's on the verdict's door as on the first (solorepo's DR-142,
    solorepo's #168). Where the loop stands down on a request for changes,
    the sign is left on the pull request, the verdict's door being delivered
    once; the rebase door is delivered on every push to `main` while the
    branch conflicts, and `dispatch()` in `.meta/say/move` reads the Issue
    before it dispatches and names the branch it leaves alone in `advance`'s
    own log.
    The depth follows the pass and the level the Challenge holds now. On
    approval the unresolved threads are counted, since a pull request with
    none lands unattended (solorepo's DR-159, solorepo's DR-161).

    Parameters:
        number (str): The Challenge on a take, the pull request otherwise.
        delivery (Delivery): What the workflow knows.
    """
    common.emit("GITHUB_OUTPUT", **{"pass": delivery.task})
    if delivery.task == "take":
        view = channel.gh("issue", "view", number, "--json", "labels")
        harness = coder_harness(delivery, check_pr.state.issue_labels(view))
        common.name_harness(harness)
        common.emit("GITHUB_OUTPUT", branch_prefix=harness)
        decided = taken(number, delivery)
        left = str(decided["resume"] or "")
        coder_depth(delivery.task, str(decided["level"]), harness, {
            "number": number, "repository": channel.repo(), "level": str(decided["level"]),
            "branch_prefix": harness,
            "resume": RUN_LEFT.format(number=left) if left else RUN_LEFT_NOTHING,
        })
        return
    pull = find_pull(number, delivery)
    if pull is None:
        return
    harness = coder_harness(delivery, check_pr.state.issue_labels(pull))
    common.name_harness(harness)
    common.emit("GITHUB_OUTPUT", branch_prefix=harness)
    issue = loop_issue(str(pull.get("headRefName") or ""))
    decided = taken(issue, delivery)
    if delivery.task == "answer" and delivery.event == "pull_request_review" \
            and decided["by"] in NO_JOB:
        channel.sibling("post").conversation_comment(
            number, channel.signed(NO_JOB_SAID.format(issue=issue, why=decided["why"],
                                                      run=run_url())))
    coder_depth(delivery.task, "medium", harness, pull_fields(number, pull, issue, delivery.task))
    if delivery.task == "promote":
        open_threads = [t for t in check_pr.github.threads(number) if not t.get("isResolved")]
        common.emit("GITHUB_OUTPUT", count=str(len(open_threads)))
        print(f"Found {len(open_threads)} unresolved thread(s) on approved #{number}")


BETWEEN_NOT_TAKE = ("::error::`between` reads what is open on the Challenge's branch, which only "
                    "the take pass has a prompt to say; it was asked on the {task} pass and "
                    "named no rung")
"""The refusal where `between` is asked the two-step question on a pass whose prompt carries no
resume clause: with no rung named there is nothing else for it to answer."""

LEFT_OPEN = ("pull request #{number} is already open on #{issue}'s branch; the harness step that "
             "follows takes it up rather than opening again")
"""The line the run log gets where the branch already holds a pull request."""

LEFT_NOTHING = ("no pull request is open on #{issue}'s branch; the harness step that follows "
                "opens the one this Challenge is owed")
"""The line the run log gets where the branch holds nothing for the step that follows to resume."""


def coder_between(issue: str, delivery: Delivery, handed: common.Attempt) -> None:
    """The coder's door between two rungs: what is open on the branch, and whether the next runs.

    On a take the branch is read again, now, and the next rung's prompt
    takes its resume clause from here: `before` read the branch once, ahead
    of every rung, so its `resume` says what was true at the start of the
    run, and a rung told no run has taken this Issue goes to open a second
    pull request on a branch that already owns one, which `move open`
    refuses. A rung that failed late, at its turn cap, is the common case,
    the pull request already open and the commits pushed. The reading is on
    `take`'s terms rather than the hand-back's: an empty listing as the
    default, so a listing GitHub refuses reads as no pull request instead
    of ending the process, since a refusal is no reason to put a red step in
    the run log for a reading that only feeds a prompt.

    Where the workflow names the rung that ended and how, `run` says whether
    the next rung of the chain runs and its prompt is written where the
    attempt step reads it (solorepo's DR-281). Asked the older two-step
    question, with no rung named, the phase answers `resume` alone, and is
    refused on any pass but a take, whose prompt alone carries the clause.

    Parameters:
        issue (str): The Challenge on a take, the pull request otherwise.
        delivery (Delivery): What the workflow knows.
        handed (common.Attempt): Which rung ended and how, where the workflow said.

    Raises:
        SystemExit: Where no rung is named and the pass is not a take.
    """
    fields: dict[str, str] = {}
    if delivery.task == "take":
        pull = check_pr.sweep.loop_pull(issue, "number", default=[])
        number = str(pull["number"]) if pull else ""
        common.emit("GITHUB_OUTPUT", resume=number)
        print(LEFT_OPEN.format(number=number, issue=issue) if number
              else LEFT_NOTHING.format(issue=issue))
        fields["resume"] = HARNESS_LEFT.format(number=number) if number \
            else HARNESS_LEFT_NOTHING
    elif handed.attempt is None:
        sys.exit(BETWEEN_NOT_TAKE.format(task=delivery.task))
    if handed.attempt is not None:
        common.fallback(handed, fields)


class Ended(NamedTuple):
    """What the workflow knows about the coder's session that the door's `after` is handed.

    Attributes:
        outcomes: How each rung of the pass ended, in rung order: `success`,
            `failure`, `cancelled` or `skipped` each; `None` where the workflow
            did not say, which `after` refuses.
        held: On a promotion, how many threads `before` found held.
        branch_prefix: The harness `before` chose, which names the loop's branch.
        execution: Where Claude Code wrote the pass's execution transcript, or
            the empty string where no rung published a path.
    """

    outcomes: tuple[str, ...] | None
    held: int | None
    branch_prefix: str
    execution: str = ""


OUTCOMES_NOT_SAID = ("the coder's `after` takes how the pass's rungs ended, --outcomes, and was "
                     "handed none: an outcome that did not arrive is a red run, not a pass "
                     "that was skipped")
"""The refusal where `after` is missing how the session's rungs ended."""


OUTCOMES = ("success", "failure", "cancelled", "skipped")
"""How a step ends, as the workflow reports it: a step that never ran reports `skipped`, so an
empty string is none of these and is refused."""

DID_NOT_FINISH = ("This run ended without finishing and without saying where it stopped: its "
                  "step ended {outcome}. What it did is in the run log, {run}.")
"""The first sentence of a hand-back's account, where the step conclusion is what ended the pass."""

CAPPED = "error_max_turns"
"""The `subtype` Claude Code's result entry carries where the turn cap ended the session."""

CAP_MARK = "was cut by its turn cap"
"""What a cap account says, and so what a later run reads, with its author, to find one posted."""

CUT_BY_CAP = ("This run was cut by its turn cap{spent}, which the harness reports as a step that "
              "succeeded: it stopped where the cap fell and not where the work finished. What it "
              "did is in the run log, {run}.")
"""The first sentence of a hand-back's account, where the turn cap cut the pass."""

TURNS_SPENT = ", {turns} turns in"
"""What the cap account says of the turns, where the transcript counted them."""

CUT_TWICE = ("#{number} already carries the account of a run cut by its turn cap, so this is the "
             "second, and a Challenge that does not fit twice is not the loop's")
"""Why the reviewer is not asked where a second run on the same pull request hit the cap."""

STAYS_OPEN = (" The pull request it opened, if it opened one, is on `{branch}` and stays open "
              "for the run that takes this up again.")
"""What the account says of the branch, where the Challenge goes to the solo."""

NOT_REQUESTED = "\n\nNot requested of the reviewer: {why}."
"""The account's second paragraph, where the Challenge goes to the solo."""

WORTH_READING = ("\n\nEvery check on this head is green, so this is where a run stopped and not "
                 "where one finished, and review is requested on that basis: what is here is "
                 "worth reading, and whether it answers #{issue} is the review's question. "
                 "#{issue} stays claimed at `{level}`, and a request for changes comes back to "
                 "the coder as a new run.")
"""The account's second paragraph, where the pull request is green and review is requested."""

UNREADABLE_ISSUE = ("#{issue} could not be read, so whether it is still open and at what level "
                    "is unknown here; the run log above says why")
"""Why the reviewer is not asked where the Challenge cannot be read."""

UNREADABLE_MERGE = ("whether {branch}'s pull request has merged could not be read, so whether "
                    "the work already landed is unknown here; the run log above says why")
"""Why the reviewer is not asked where the merged listing cannot be read."""

UNREADABLE_LEFT = ("the hand-back could not read what this run left: whether a pull request is "
                   "open on this branch, and whether it is green, is unknown here; the run log "
                   "above says why")
"""Why the reviewer is not asked where the pull request's state cannot be read."""

CONFLICTS = ("#{number}'s branch conflicts with its base, {base}. GitHub builds no merge ref "
             "for one that does, review.yml runs on pull_request, and so a review requested on "
             "it would create no run and be answered by nobody. Rebase {branch} onto {base} and "
             "the request can be made")
"""Why the reviewer is not asked where the branch conflicts."""

NOT_GREEN = "the checks on #{number} have not all passed, and a red gate is not a handoff"
"""Why the reviewer is not asked where the gate is red."""

NEITHER = "::error::No rung of the {task} pass succeeded (outcomes={outcomes})."
"""The finding where a pass ran and no rung finished it."""


def coder(phase: str, number: str, delivery: Delivery, ended: Ended,
          handed: common.Attempt = common.NO_RUNG) -> None:
    """The coder's door at one phase of the session, for the pass `delivery` names.

    Parameters:
        phase (str): `before`, `between` two rungs of the pass's ladder, or `after`.
        number (str): The Challenge on a take, the pull request otherwise.
        delivery (Delivery): What the workflow knows.
        ended (Ended): How the session's steps ended, unread before it.
        handed (common.Attempt): Between two rungs, which ended and how; unread elsewhere.
    """
    if phase == "before":
        coder_before(number, delivery)
    elif phase == "between":
        coder_between(number, delivery, handed)
    else:
        from lib.on import handoff
        handoff.coder_after(number, delivery, ended)
