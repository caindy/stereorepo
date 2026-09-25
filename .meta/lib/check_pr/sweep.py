"""The sweep the gate runs on the clock, the hand-back a dying run asks for, and the take door.

Beyond the body, the sweep asks who takes each open pull request next, which
`remedies` answers for it (solorepo's DR-129); the hand-back asks whether
anybody holds a Challenge's pull request yet (solorepo's DR-155); and the take
door asks whether a delivery of a Challenge is the loop's to run, read through
the Issue classifier in `state` (solorepo's DR-264).
"""
import re
import sys
import time
from typing import Any, NamedTuple

from lib.check_pr import META, github, polling, remedies, state, verdict
from lib.check_pr.state import LOOP_LEVELS

CODER = META.parent / ".github" / "workflows" / "coder.yml"


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


# What the hand-back asks `gh pr list` for, which is everything except the
# rollup: those fields are a pull request's own and the step's token reads them
# at `pull-requests: read`, while the check states come through `ROLLUP` in
# `github`, whose scope is `checks: read` and nothing wider (solorepo's DR-155).
HANDBACK_FIELDS = ("number,headRefName,baseRefName,reviewRequests,autoMergeRequest,mergeable,"
                   "changedFiles,commits")


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
    for prefix in ("gemini", "claude"):
        found = github.gh("pr", "list", "--state", "open", "--head", f"{prefix}/issue-{issue}",
                          "--json", fields, default=default)
        if found:
            return dict(found[0])
    return None


def is_only_plan(pr: dict[str, Any]) -> bool:
    """Return whether the pull request branch contains only the initial plan commit."""
    if pr.get("changedFiles") != 0:
        return False
    commits = pr.get("commits") or []
    return not commits or all(
        "Record initial plan for Challenge" in (c.get("messageHeadline") or "") for c in commits
    )


def hand_back(issue: str | int) -> dict[str, Any]:
    """Provides pull request status metrics for challenge hand-back automation.

    Args:
        issue: Challenge issue number string or integer.

    Returns:
        dict[str, Any]: Status summary containing handed, green, conflicting,
            number, base, only_plan.
    """
    pr = loop_pull(issue, HANDBACK_FIELDS)
    if pr is None:
        return {"number": None, "branch": None, "handed": False, "green": False,
                "conflicting": False, "base": None, "only_plan": False}
    raw_contexts = github.rollup_of(pr["number"])
    pending = [c for c in raw_contexts if (c.get("conclusion") or c.get("state") or c.get("status") or "").upper() in state.UNCONCLUDED]
    if pending:
        raw_contexts = wait_for_checks(pr["number"], timeout=120, interval=5)
    pr["statusCheckRollup"] = polling.deduplicate_checks(raw_contexts)
    return {"number": pr["number"],
            "branch": pr.get("headRefName"),
            "handed": bool(remedies.asked_of(pr)) or pr.get("autoMergeRequest") is not None,
            "green": remedies.green(pr),
            "conflicting": pr.get("mergeable") == "CONFLICTING",
            "base": pr.get("baseRefName") or "main",
            "only_plan": is_only_plan(pr)}


ISSUE_DOOR = "issues"
"""The event a label delivers a Challenge on, where a claim with a pull request is a duplicate."""

UNNAMED = "on a branch that names no Challenge the loop holds"
"""Why a delivery on a branch of the loop's shape that names no Issue is not the loop's."""

UNREADABLE = "not an Issue this repository can read"
"""Why a delivery naming an Issue GitHub will not answer for is not the loop's."""


class Decision(NamedTuple):
    """The take door's outputs, as `--take` prints them.

    Attributes:
        by: A word for a delivery that must not run — `closed`, `held`, `blocked`,
            `stale`, `unnamed`, or the number of the pull request a standing run holds —
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
    read = github.gh("issue", "view", issue, "--json", "state,assignees,labels,blockedBy",
                     default=None)
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
    if found is state.IssueState.BLOCKED:
        return _decided("blocked", "has open blockers", state=found,
                        said=f"#{issue} has open blockers; this loop stands down")
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
        owed = remedies.unheld(found, minutes, clean, unresolved, reviewer_login=reviewer)
        print(f"{'x  ' if owed else 'ok '}hand-off — "
              + (f"{len(owed)} pull request(s) nobody can take up"
                 if owed else "every open pull request names who takes it next"))
        for o in owed:
            print(f"     {o}")
        failed |= bool(owed)
    return 1 if failed else 0
