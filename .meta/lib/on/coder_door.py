"""Coder door lifecycle for `.meta/say/on` (solorepo's DR-217, DR-264)."""
import os
import sys
from collections.abc import Sequence
from typing import Any, NamedTuple

import channel
import check_pr
from lib.on import common

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

DEPTHS = {"rebase": ("claude-opus-5", "high", "60", "30"),
          "promote": ("claude-sonnet-5", "medium", "30", "15"),
          "medium": ("claude-opus-5", "high", "120", "60"),
          "easy": ("claude-sonnet-5", "medium", "60", "30")}
"""The model, effort, turn cap and minutes of a pass, by the pass or by the level it takes at."""

GEMINI_MODEL = "gemini-3.8-flash"
"""The model the Antigravity CLI fallback runs, on every coder pass."""

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


def coder_depth(task: str, level: str) -> None:
    """The model, effort, turn cap and minutes of the pass, as step outputs.

    `easy` is the smaller model and half an hour; `medium` the larger and
    the whole budget, and an answering pass takes it whatever the label was,
    since the threads it answers were written by the deeper reviewer. A
    rebase is bounded by what it is, the larger model at half the budget,
    because a conflict here is prose as often as code and a rebase taking an
    hour is not a rebase. Promotion on approval (solorepo's DR-159) is
    clerical transcription, the smaller model at a quarter of the whole. Claude
    Code's models run high extended thinking on every pass
    (solorepo's DR-186).
    """
    model, effort, turns, minutes = DEPTHS.get(task) or DEPTHS.get(level) or DEPTHS["easy"]
    common.emit(
        "GITHUB_OUTPUT", level=level, model=model, gemini_model=GEMINI_MODEL,
        effort=effort, turns=turns, minutes=minutes,
    )


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
        coder_depth(delivery.task, str(decided["level"]))
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
    coder_depth(delivery.task, "medium")
    if delivery.task == "promote":
        open_threads = [t for t in check_pr.github.threads(number) if not t.get("isResolved")]
        common.emit("GITHUB_OUTPUT", count=str(len(open_threads)))
        print(f"Found {len(open_threads)} unresolved thread(s) on approved #{number}")


BETWEEN_NOT_TAKE = ("::error::`between` reads what is open on the Challenge's branch, which only "
                    "the take pass has a prompt to say; it was asked on the {task} pass")
"""The refusal where `between` is asked on a pass whose prompt carries no resume clause."""

LEFT_OPEN = ("pull request #{number} is already open on #{issue}'s branch; the harness step that "
             "follows takes it up rather than opening again")
"""The line the run log gets where the branch already holds a pull request."""

LEFT_NOTHING = ("no pull request is open on #{issue}'s branch; the harness step that follows "
                "opens the one this Challenge is owed")
"""The line the run log gets where the branch holds nothing for the step that follows to resume."""


def coder_between(issue: str, delivery: Delivery) -> None:
    """The coder's door before the second harness step: what is open on the branch, as `resume`.

    The step runs immediately before the second harness step and on that
    step's own condition, which is met two ways: the first harness step
    failed, or the Challenge chose the harness that the second step runs and
    the first was skipped outright, making it the run's first harness rather
    than a fallback. On a failure, the turn cap is the common way to fail
    late — it lands after the work rather than before it, with the pull
    request already open and commits pushed. `before` read the branch once,
    ahead of both harness steps, so its `resume` says what was true at the
    start of the run: handed that, the step is told no run has taken this
    Issue and goes to open a second pull request on a branch that already owns
    one, which `move open` refuses. This reads the branch again, now, and the
    step's prompt takes its resume clause from here.

    It is the branch `sweep.hand_back` reads and the same `loop_pull`, but on
    `take`'s terms rather than the hand-back's: an empty listing as the
    default, so a listing GitHub refuses reads as no pull request instead of
    ending the process. The Challenge is still there to be taken, and a
    refusal is no reason to put a red step in the run log for a reading that
    only feeds a prompt.

    Parameters:
        issue (str): The Challenge.
        delivery (Delivery): What the workflow knows.

    Raises:
        SystemExit: Where the pass is not a take.
    """
    if delivery.task != "take":
        sys.exit(BETWEEN_NOT_TAKE.format(task=delivery.task))
    pull = check_pr.sweep.loop_pull(issue, "number", default=[])
    number = str(pull["number"]) if pull else ""
    common.emit("GITHUB_OUTPUT", resume=number)
    print(LEFT_OPEN.format(number=number, issue=issue) if number
          else LEFT_NOTHING.format(issue=issue))


class Ended(NamedTuple):
    """What the workflow knows about the coder's session that the door's `after` is handed.

    Attributes:
        claude: How the pass's Claude Code step ended: `success`, `failure`,
            `cancelled` or `skipped`.
        gemini: How its Antigravity CLI step ended, the same way.
        held: On a promotion, how many threads `before` found held.
        branch_prefix: The harness `before` chose, which names the loop's branch.
        execution: Where Claude Code wrote the pass's execution transcript, or
            the empty string where the step published no path.
    """

    claude: str | None
    gemini: str | None
    held: int | None
    branch_prefix: str
    execution: str = ""


OUTCOMES_NOT_SAID = ("the coder's `after` takes how the pass's two steps ended, --claude and "
                     "--gemini, and was handed claude={claude!r} gemini={gemini!r}: an outcome "
                     "that did not arrive is a red run, not a pass that was skipped")
"""The refusal where `after` is missing how the session's steps ended."""


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

NEITHER = ("::error::Neither Claude nor Gemini {task} pass succeeded (claude={claude}, "
           "gemini={gemini}).")
"""The finding where a pass ran and neither harness finished it."""


def coder(phase: str, number: str, delivery: Delivery, ended: Ended) -> None:
    """The coder's door at one phase of the session, for the pass `delivery` names.

    Parameters:
        phase (str): `before`, `between` the take pass's two harness steps, or `after`.
        number (str): The Challenge on a take, the pull request otherwise.
        delivery (Delivery): What the workflow knows.
        ended (Ended): How the session's steps ended, unread before it.
    """
    if phase == "before":
        coder_before(number, delivery)
    elif phase == "between":
        coder_between(number, delivery)
    else:
        from lib.on import handoff
        handoff.coder_after(number, delivery, ended)
