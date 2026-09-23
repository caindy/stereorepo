"""The sweep the gate runs on the clock, the hand-back a dying run asks for, and the take door.

Beyond the body, the sweep asks who takes each open pull request next
(solorepo's DR-129); the hand-back asks whether anybody holds a Challenge's pull
request yet (solorepo's DR-155); and the take door asks whether a delivery of a
Challenge is the loop's to run, read through the Issue classifier in `state`
(solorepo's DR-264).
"""
import datetime
import re
import sys
import time
from collections.abc import Collection, Mapping, Sequence
from typing import Any, NamedTuple

from lib.check_pr import META, github, polling, state, verdict
from lib.check_pr.state import LOOP_LEVELS

CODER = META.parent / ".github" / "workflows" / "coder.yml"

LOOPS_BRANCH = re.compile(r"^(?:claude|gemini|codex)/issue-(\d+)$")

# The fields the hand-off reader needs, added to the sweep's own list so that
# one fetch answers both. The rollup is not among them: `gh` answers that one
# field with a query the gate's token cannot run, so it is fetched by name
# alongside (solorepo's DR-153).
SWEEP_FIELDS = ("number,title,headRefOid,headRefName,baseRefName,isDraft,updatedAt,"
                "reviewRequests,autoMergeRequest,mergeable,latestReviews")


def longest_run() -> int | None:
    """Reads the maximum job timeout in minutes configured for the coder workflow.

    Returns:
        int | None: Configured timeout in minutes, or None if unreadable.
    """
    if not CODER.exists():
        print(f"?  no {CODER.name} in this checkout; who holds each pull request is unchecked")
        return None
    found = re.search(r"^    timeout-minutes: (\d+)\s*$", CODER.read_text(), re.M)
    if not found:
        print(f"?  no job timeout in {CODER.name}; who holds each pull request is unchecked")
        return None
    return int(found.group(1))


def asked_of(pr: dict[str, Any]) -> list[str]:
    """Names or logins of reviewers currently requested on a pull request."""
    return [str(r.get("login") or r.get("name") or "someone") for r in pr["reviewRequests"]]


def green(pr: dict[str, Any]) -> bool:
    """Whether every check on the head has concluded and none of them failed."""
    raw_contexts = pr.get("statusCheckRollup") or []
    contexts = polling.deduplicate_checks(raw_contexts)
    _, all_green, _ = state.checks_summary(contexts)
    return bool(contexts) and all_green


# What the hand-back asks `gh pr list` for, which is everything except the
# rollup: those fields are a pull request's own and the step's token reads them
# at `pull-requests: read`, while the check states come through `ROLLUP` below,
# whose scope is `checks: read` and nothing wider (solorepo's DR-155).
HANDBACK_FIELDS = "number,headRefName,baseRefName,reviewRequests,autoMergeRequest,mergeable"


def wait_for_checks(pr_number: int, timeout: int = 120,
                    interval: int = 5) -> list[dict[str, Any]]:
    """Wait for in-progress or queued checks on the head to conclude."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        raw = github.rollup_of(pr_number)
        if not raw:
            return []
        pending = [c for c in raw if (c.get("conclusion") or c.get("state") or c.get("status") or "").upper() in state.UNCONCLUDED]
        if not pending:
            return raw
        time.sleep(interval)
    return github.rollup_of(pr_number)


def loop_pull(issue: str | int, fields: str,
              default: Any = github.UNSET) -> dict[str, Any] | None:
    """The open pull request on a Challenge's loop branch under any harness's prefix, or None.

    Asked by head, one prefix at a time, rather than listed whole and filtered:
    `gh pr list --head` is one indexed read where the listing is every open
    pull request. The prefixes are the shapes `coder.yml` cuts.

    Args:
        issue: Challenge Issue number.
        fields: The `--json` fields the caller reads off the pull request.
        default: What a listing GitHub refuses answers with, as `github.gh`
            takes it. Omitted, the refusal ends the process, which is the
            hand-back's reading; `take` passes an empty listing, so that a
            refused read is no pull request rather than a red job on a door
            where a red job is a verdict answered by nobody.

    Returns:
        dict[str, Any] | None: The pull request's fields, or None where no
            prefix has an open pull request on that Issue's branch.
    """
    for prefix in ("gemini", "claude", "codex"):
        found = github.gh("pr", "list", "--state", "open", "--head", f"{prefix}/issue-{issue}",
                          "--json", fields, default=default)
        if found:
            return dict(found[0])
    return None


def hand_back(issue: str | int) -> dict[str, Any]:
    """Provides pull request status metrics for challenge hand-back automation.

    Args:
        issue: Challenge issue number string or integer.

    Returns:
        dict[str, Any]: Status summary containing handed, green, conflicting, number, base.
    """
    pr = loop_pull(issue, HANDBACK_FIELDS)
    if pr is None:
        return {"number": None, "branch": None, "handed": False, "green": False,
                "conflicting": False, "base": None}
    raw_contexts = github.rollup_of(pr["number"])
    pending = [c for c in raw_contexts if (c.get("conclusion") or c.get("state") or c.get("status") or "").upper() in state.UNCONCLUDED]
    if pending:
        raw_contexts = wait_for_checks(pr["number"], timeout=120, interval=5)
    pr["statusCheckRollup"] = polling.deduplicate_checks(raw_contexts)
    return {"number": pr["number"],
            "branch": pr.get("headRefName"),
            "handed": bool(asked_of(pr)) or pr.get("autoMergeRequest") is not None,
            "green": green(pr),
            "conflicting": pr.get("mergeable") == "CONFLICTING",
            "base": pr.get("baseRefName") or "main"}


ISSUE_DOOR = "issues"
"""The event a label delivers a Challenge on, where a claim with a pull request is a duplicate."""

UNNAMED = "on a branch that names no Challenge the loop holds"
"""Why a delivery on a branch of the loop's shape that names no Issue is not the loop's."""

UNREADABLE = "not an Issue this repository can read"
"""Why a delivery naming an Issue GitHub will not answer for is not the loop's."""


class Decision(NamedTuple):
    """The take door's outputs, as `--take` prints them.

    Attributes:
        by: A word for a delivery that must not run — `closed`, `held`, `stale`,
            `unnamed`, or the number of the pull request a standing run holds —
            and empty for one that does. The one field every branch writes, so
            that it is never empty by accident.
        why: Why the delivery must not run, beside a `by` that says so.
        resume: The open pull request a hand-back left, for the run to take up.
        level: The label the run takes the Challenge at.
        state: The `IssueState` the decision was read off; empty where no Issue
            was read, which is a name that is not a number or one GitHub would
            not answer for.
        said: The line the run log gets.
    """

    by: str
    why: str = ""
    resume: str = ""
    level: str = ""
    state: str = ""
    said: str = ""


def _decided(by: str, why: str = "", **rest: str) -> dict[str, Any]:
    """A `Decision` as the mapping `--take` prints, `rest` being its remaining fields by name."""
    return Decision(by, why, **rest)._asdict()


def take(issue: str, door: str) -> dict[str, Any]:
    """What the coder's take door decides about a delivery, read through the Issue classifier.

    `by` carries a word for every delivery that must not run — `closed`,
    `held`, `stale`, `unnamed`, or the number of the pull request a standing
    run already holds — and is empty for one that does; `resume` is the open
    pull request a hand-back left, `level` the label the run takes the
    Challenge at, `state` the `IssueState` the decision was read off, empty
    where no Issue was read, and `said` the line the run log gets. A pull
    request listing GitHub refuses reads as no pull request on every door,
    which is what the shell this replaced read off a failed pipeline, since
    the door must not go red where a red job is a verdict answered by nobody.
    The door decides one reading only: a
    claim with a pull request open is a duplicate where the delivery is the
    label's own event, and the ordinary standing of a run where the delivery
    arrived on that pull request (solorepo's DR-142).

    Args:
        issue: What the delivery names, which on the label's door is an Issue
            number and on the others is read off a branch by prefix.
        door: The event the delivery arrived on, as `github.event_name` names it.

    Returns:
        dict[str, Any]: `by`, `why`, `resume`, `level`, `state` and `said`.

    Raises:
        SystemExit: On the label's door, an Issue that is not a number or that
            GitHub will not answer for: the delivery is not taken, and the Issue
            is there to be delivered again. On the other doors both are a word
            rather than a failure, since a red job there is a verdict answered
            by nobody.
    """
    if not (issue.isascii() and issue.isdigit()):
        if door == ISSUE_DOOR:
            sys.exit(f"take: {issue!r} is not an Issue number")
        return _decided("unnamed", UNNAMED,
                        said=f"'{issue}' is not an Issue number; the branch is not the loop's "
                             "shape, and this delivery is not its")
    read = github.gh("issue", "view", issue, "--json", "state,assignees,labels", default=None)
    if read is None:
        if door == ISSUE_DOOR:
            sys.exit(f"take: #{issue} could not be read")
        return _decided("unnamed", UNREADABLE,
                        said=f"#{issue} cannot be read; the branch names no Challenge the "
                             "loop holds, and this delivery is not its")
    pull = loop_pull(issue, "number,headRefName", default=[])
    number = str(pull["number"]) if pull else ""
    coder = github.role_login("coder")
    found = state.classify_issue(read, coder, pull is not None)
    if found is state.IssueState.TAKEN and door != ISSUE_DOOR:
        found = state.classify_issue(read, None, pull is not None)
    labels = ", ".join(state.issue_labels(read))
    if found is state.IssueState.CLOSED:
        return _decided("closed", "closed", state=found,
                        said=f"#{issue} is closed now; this delivery is stale")
    if found is state.IssueState.TAKEN:
        return _decided(number, state=found,
                        said=f"#{issue} is claimed by {coder} and has open pull request "
                             f"#{number}; this delivery is a duplicate")
    if found is state.IssueState.HELD:
        return _decided("held", "labelled hard", state=found,
                        said=f"#{issue} is hard now: the solo's, with a session beside him; "
                             "this loop stands down")
    if found in state.NOT_TAKEN_STATES:
        shown = f"'{labels}'" if labels else "nothing"
        return _decided("stale", f"labelled {labels or 'nothing'} now, which no loop takes",
                        state=found,
                        said=f"#{issue} is labelled {shown} now; a Challenge at neither easy "
                             "nor medium is not this loop's, on any door but the solo's own "
                             "dispatch")
    level = next((lvl for lvl in LOOP_LEVELS if lvl in state.issue_labels(read)), "")
    said = (f"#{issue} has open pull request #{number} and no claim: a hand-back, taken up again"
            if number else "")
    return _decided("", resume=number, level=level, state=found, said=said)


def is_approved_pull(pr: dict[str, Any], reviewer_login: str | None = None) -> bool:
    """Whether the reviewer's most recent review on this pull request is an approval."""
    reviews = pr.get("latestReviews") or pr.get("reviews")
    if not reviews:
        return False
    if reviewer_login is None:
        reviewer_login = github.role_login("reviewer")
    verdict = state.latest_verdict(pr, reviewer_login)
    return verdict == "APPROVED"


def is_changes_requested_pull(pr: dict[str, Any],
                              reviewer_login: str | None = None) -> bool:
    """Whether the reviewer's most recent review on this pull request requests changes."""
    reviews = pr.get("latestReviews") or pr.get("reviews")
    if not reviews:
        return False
    if reviewer_login is None:
        reviewer_login = github.role_login("reviewer")
    verdict = state.latest_verdict(pr, reviewer_login)
    return verdict == "CHANGES_REQUESTED"


class Standing(NamedTuple):
    """One open pull request as `unheld` reads it: the request on it, the loop's branch match, how long it has sat, and the reviewer's login."""

    pr: dict[str, Any]
    asked: list[str]
    branch: re.Match[str] | None
    idle: float
    reviewer_login: str

    def line(self) -> str:
        """`#<number> <title>`, the head of every remedy."""
        return f"#{self.pr['number']} {self.pr['title'][:60]}"

    def challenge(self, levels: Collection[str]) -> tuple[str | None, str | None]:
        """The branch's Challenge as `(state, level)`, the level being the first of `levels` among its labels, or None.

        `(None, None)` where the branch names no Challenge, which every caller
        reads as it reads a Challenge that is closed or unlabelled.
        """
        if self.branch is None:
            return None, None
        issue = github.gh("issue", "view", self.branch.group(1), "--json", "state,labels")
        level = next((lbl["name"] for lbl in issue["labels"] if lbl["name"] in levels), None)
        return str(issue["state"]), level


def unresolved_of(pr: dict[str, Any],
                  unresolved: Mapping[int, list[dict[str, Any]]] | None
                  ) -> list[dict[str, Any]] | None:
    """The unresolved conversations of `pr`, a reviewer's comment being none (solorepo's DR-273)."""
    found = (github.threads(str(pr["number"])) if unresolved is None
             else unresolved.get(pr["number"]))
    return None if found is None else [t for t in found if not (t["isResolved"] or t.get("comment"))]


def waiting_on_conflict(standing: Standing) -> list[str]:
    """The remedy where a request, an arming or an approval waits on a branch that conflicts, and nothing where none does."""
    pr = standing.pr
    waiting: list[str] = []
    stuck: list[str] = []
    if standing.asked:
        waiting.append(f"requested of {', '.join(standing.asked)}")
        stuck.append("GitHub builds no merge ref, so the review workflow has nothing "
                     "to check out and the request cannot be answered")
    if pr.get("autoMergeRequest"):
        waiting.append("armed")
        stuck.append("GitHub will not merge it and will not update the branch, so the "
                     "arming waits on an act nothing performs")
    if is_approved_pull(pr, reviewer_login=standing.reviewer_login):
        waiting.append("approved")
        stuck.append("GitHub will not merge it and will not update the branch, so the "
                     "approval waits on a rebase nothing performs")
    if not waiting or pr.get("mergeable") != "CONFLICTING":
        return []
    hard_remedy = ""
    if standing.branch:
        try:
            _, level = standing.challenge(("human", "hard"))
        except SystemExit:
            level = None
        if level:
            number = standing.branch.group(1)
            hard_remedy = (f". Challenge #{number} is {level} so the loop stands down "
                           f"(solorepo's DR-142): rebase by hand, or dispatch with "
                           f".meta/say/move dispatch {pr['number']} --task rebase, or "
                           f".meta/say/move difficulty {number} medium")
    return [f"{standing.line()} — {' and '.join(waiting)}, on a "
            f"branch that conflicts: {'; and '.join(stuck)}. Rebase "
            f"{pr['headRefName']} onto {pr['baseRefName']}{hard_remedy}"]


def armed_over_conversations(standing: Standing, minutes: float,
                             unresolved: Mapping[int, list[dict[str, Any]]] | None) -> list[str]:
    """The remedy where an arming waits on unresolved conversations nobody is standing to resolve (solorepo's DR-159)."""
    pr = standing.pr
    if not (pr.get("autoMergeRequest") and pr.get("mergeable") != "CONFLICTING" and standing.idle >= minutes):
        return []
    threads_unresolved = unresolved_of(pr, unresolved)
    if not threads_unresolved:
        return []
    return [f"{standing.line()} — armed, with "
            f"{len(threads_unresolved)} unresolved conversation(s): GitHub will "
            f"not merge it while conversations are unresolved, and no Job is "
            f"standing to resolve them (solorepo's DR-159). Promote surviving "
            f"notices with .meta/say/post promote, resolve threads whose link or "
            f"answer is already posted with .meta/say/post resolve, or answer with "
            f".meta/say/post answer"]


def stranded_request(standing: Standing, minutes: float) -> list[str]:
    """The remedy where a review is requested of the reviewer whose check failed without a verdict (solorepo's DR-178)."""
    pr = standing.pr
    if not (standing.reviewer_login in standing.asked and not pr["isDraft"]
            and pr.get("mergeable") != "CONFLICTING" and standing.branch and standing.idle >= minutes):
        return []
    contexts = polling.deduplicate_checks(pr.get("statusCheckRollup") or [])
    reviewer_check = next((c for c in contexts if c.get("name") == "reviewer"), None)
    if not (reviewer_check and (reviewer_check.get("conclusion") or "").upper() == "FAILURE"):
        return []
    return [f"{standing.line()} — review requested of {standing.reviewer_login}, "
            f"but reviewer check failed without a verdict: no run is answering it and "
            f"nothing has moved on it for {int(standing.idle)} minutes. Re-request review with "
            f".meta/say/move request-review {pr['number']}"]


def unanswered_changes(standing: Standing, minutes: float,
                       unresolved: Mapping[int, list[dict[str, Any]]] | None) -> list[str]:
    """The remedy where the reviewer's request for changes stands unanswered on a Challenge the loop holds."""
    pr = standing.pr
    if not (is_changes_requested_pull(pr, reviewer_login=standing.reviewer_login) and not standing.asked
            and standing.branch and standing.idle >= minutes):
        return []
    if not (unresolved_of(pr, unresolved) or not green(pr)):
        return []
    state, level = standing.challenge(LOOP_LEVELS)
    if state != "OPEN" or not level:
        return []
    return [f"{standing.line()} — changes requested by "
            f"reviewer, and unanswered: no run is answering it and nothing "
            f"has moved on it for {int(standing.idle)} minutes, while #{standing.branch.group(1)} "
            f"is still {level}. A review event was dropped or a run ended "
            f"without answering: .meta/say/move dispatch {pr['number']} --task review"]


def approved_and_failing(standing: Standing, minutes: float) -> list[str]:
    """The remedy where an approved pull request's checks went red after the approval and no Job is standing to fix them."""
    pr = standing.pr
    if not (is_approved_pull(pr, reviewer_login=standing.reviewer_login) and not standing.asked
            and not pr["isDraft"] and not green(pr) and pr.get("mergeable") != "CONFLICTING"
            and standing.branch and standing.idle >= minutes):
        return []
    state, level = standing.challenge((*LOOP_LEVELS, "human", "hard"))
    if state != "OPEN" or not level:
        return []
    if level in LOOP_LEVELS:
        remedy = f".meta/say/move dispatch {pr['number']} --task review"
    else:
        remedy = f"fix the failing checks (or move difficulty {standing.branch.group(1)} medium)"
    idle_mins = int(standing.idle) if standing.idle != float("inf") else 0
    return [f"{standing.line()} — approved, with failing checks: "
            f"no review requested, no merge armed, and nothing has moved on it for "
            f"{idle_mins} minutes, while #{standing.branch.group(1)} is still {level}. "
            f"A check failed after approval, and no Job is standing to fix it: {remedy}"]


def green_and_unheld(standing: Standing, minutes: float,
                     clean: Collection[int]) -> list[str]:
    """The remedy where a green pull request on a loop's branch has no request, no arming and nobody holding it."""
    pr = standing.pr
    if (standing.asked or pr.get("autoMergeRequest") or pr["isDraft"] or not green(pr)
            or pr["number"] not in clean or not standing.branch or standing.idle < minutes):
        return []
    state, level = standing.challenge((*LOOP_LEVELS, "human", "hard"))
    if state != "OPEN" or not level:
        return []
    number = standing.branch.group(1)
    conflicting = pr.get("mergeable") == "CONFLICTING"
    if level in ("human", "hard"):
        remedy = (f"while #{number} is at {level} and its branch conflicts: "
                  f"rebase {pr['headRefName']} onto {pr['baseRefName']}, then "
                  f".meta/say/move request-review {pr['number']} "
                  f"(or move difficulty {number} medium)" if conflicting else
                  f"while #{number} is at {level} (a run stopped before checks were green): "
                  f".meta/say/move request-review {pr['number']} "
                  f"(or move difficulty {number} medium)")
        return [f"{standing.line()} — green, and unreviewed: "
                f"no review requested, no merge armed, and nothing has moved on it for "
                f"{int(standing.idle)} minutes, {remedy}"]
    remedy = (f"and its branch conflicts, so a review requested on it now could not "
              f"be answered: rebase {pr['headRefName']} onto "
              f"{pr['baseRefName']}, then "
              f".meta/say/move request-review {pr['number']}" if conflicting else
              f"and nobody has: .meta/say/move request-review {pr['number']}")
    return [f"{standing.line()} — green, and nobody holds it: "
            f"no review requested, no merge armed, and nothing has moved on it for "
            f"{int(standing.idle)} minutes, while #{number} is still {level}. "
            f"A run ended without handing it over, {remedy}"]


def unheld(prs: Sequence[dict[str, Any]], minutes: float, clean: Collection[int],
           unresolved: Mapping[int, list[dict[str, Any]]] | None = None,
           reviewer_login: str | None = None) -> list[str]:
    """Identifies open pull requests lacking an active owner, review request, or remediation.

    Args:
        prs: Sequence of pull request metadata dictionaries from GitHub.
        minutes: Inactivity threshold in minutes before flagging unheld work.
        clean: Set of pull request numbers verified as passing gate checks in the current run.
        unresolved: Optional mapping of pull request numbers to unresolved review threads.
        reviewer_login: Optional reviewer handle; defaults to the configured reviewer role.

    Returns:
        list[str]: Remediation messages for each unheld or stalled pull request.

    Each shape reported here is one a webhook should have carried and did not:
    the event was spent, or the run that took it ended without answering. A
    review requested of the reviewer whose check failed with no verdict
    (solorepo's DR-178); a request for changes nobody is answering; an approved
    pull request whose checks are red; and one that is green with nobody
    holding it. Every one is qualified by `minutes` of silence, so a pass that
    is merely still running is not mistaken for one that stopped.
    """
    if reviewer_login is None:
        reviewer_login = github.role_login("reviewer")
    now = datetime.datetime.now(datetime.UTC)
    out: list[str] = []
    for pr in prs:
        moved = (datetime.datetime.fromisoformat(pr["updatedAt"].replace("Z", "+00:00"))
                 if pr.get("updatedAt") else None)
        standing = Standing(pr, asked_of(pr), LOOPS_BRANCH.match(pr["headRefName"]),
                            (now - moved).total_seconds() / 60 if moved else float("inf"), reviewer_login)
        out += waiting_on_conflict(standing)
        out += armed_over_conversations(standing, minutes, unresolved)
        out += stranded_request(standing, minutes)
        out += unanswered_changes(standing, minutes, unresolved)
        out += approved_and_failing(standing, minutes)
        out += green_and_unheld(standing, minutes, clean)
    return out


def sweep_all(publishing: bool) -> int:
    """Evaluates gate checks and ownership across all open pull requests.

    Args:
        publishing: Whether to publish check runs to GitHub for each pull request.

    Returns:
        int: 0 if all checks succeed or no PRs are open; 1 if any check or fetch failed.

    A pull request GitHub would not answer for — the listing that failed, or
    the one missing from the rollup — is reported as unread and keeps the
    verdict its last push left. It is not passed on to `unheld`, where an empty
    check suite is indistinguishable from a green one, and a run that could not
    ask would otherwise report the whole tree as clean.
    """
    try:
        found = github.gh("pr", "list", "--state", "open", "--json", SWEEP_FIELDS)
        rolled = github.rollups()
    except SystemExit as unreachable:
        print("x  sweep — could not ask GitHub for the open pull requests, so no "
              "verdict was published and every one keeps the verdict its last "
              f"push left: {unreachable.code}")
        return 1
    if not found:
        print("ok sweep — no open pull requests")
        return 0
    unfetched = [pr for pr in found if pr["number"] not in rolled]
    if unfetched:
        print(f"x  sweep — GitHub answered for {len(rolled)} open pull request(s) "
              "and not for "
              + ", ".join(f"#{pr['number']}" for pr in unfetched)
              + ", which are left unread and keep the verdict their last push left")
    found = [pr for pr in found if pr["number"] in rolled]
    for pr in found:
        pr["statusCheckRollup"] = rolled[pr["number"]]
    failed = bool(unfetched)
    clean: set[int] = set()
    unresolved: dict[int, list[dict[str, Any]]] = {}
    for pr in found:
        number = str(pr["number"])
        pr_threads = github.threads(number)
        unresolved[pr["number"]] = [t for t in pr_threads if not t["isResolved"]]
        problems = verdict.gate(number, thread_nodes=pr_threads)
        print(f"{'x  ' if problems else 'ok '}#{number} {pr['title'][:60]}"
              + (f" ({len(problems)})" if problems else ""))
        for p in problems:
            print(f"     {p}")
        if publishing:
            verdict.publish(number, pr["headRefOid"], problems)
        if not problems:
            clean.add(pr["number"])
        failed |= bool(problems)

    minutes = longest_run()
    if minutes is not None:
        reviewer = github.role_login("reviewer")
        owed = unheld(found, minutes, clean, unresolved, reviewer_login=reviewer)
        print(f"{'x  ' if owed else 'ok '}hand-off — "
              + (f"{len(owed)} pull request(s) nobody can take up"
                 if owed else "every open pull request names who takes it next"))
        for o in owed:
            print(f"     {o}")
        failed |= bool(owed)
    return 1 if failed else 0
