"""The sweep the gate workflow runs on the clock, and the hand-back a dying run asks for.

Beyond the body, the sweep asks who takes each open pull request next
(solorepo's DR-129); the hand-back asks whether anybody holds a Challenge's pull
request yet (solorepo's DR-155).
"""
import datetime
import re
import time
from typing import NamedTuple

from lib.check_pr import META, github, polling, verdict

CODER = META.parent / ".github" / "workflows" / "coder.yml"

LOOPS_BRANCH = re.compile(r"^(?:claude|gemini|codex)/issue-(\d+)$")

# The difficulties a loop takes, which is what makes a Challenge a loop's and
# not the solo's. `human` and `hard` are the solo's, and so is a pull request
# on their Challenge.
TAKEN = ("easy", "medium")

# The fields the hand-off reader needs, added to the sweep's own list so that
# one fetch answers both. The rollup is not among them: `gh` answers that one
# field with a query the gate's token cannot run, so it is fetched by name
# alongside (solorepo's DR-153).
SWEEP_FIELDS = ("number,title,headRefOid,headRefName,baseRefName,isDraft,updatedAt,"
                "reviewRequests,autoMergeRequest,mergeable,latestReviews")


def longest_run():
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


def asked_of(pr):
    """Names or logins of reviewers currently requested on a pull request."""
    return [r.get("login") or r.get("name") or "someone" for r in pr["reviewRequests"]]


def green(pr):
    """Whether every check on the head has concluded and none of them failed."""
    contexts = polling.deduplicate_checks(pr.get("statusCheckRollup") or [])
    states = [c.get("conclusion") or c.get("state") or c.get("status")
              for c in contexts]
    return bool(states) and all(s in polling.GREEN for s in states)


# What the hand-back asks `gh pr list` for, which is everything except the
# rollup: those fields are a pull request's own and the step's token reads them
# at `pull-requests: read`, while the check states come through `ROLLUP` below,
# whose scope is `checks: read` and nothing wider (solorepo's DR-155).
HANDBACK_FIELDS = "number,headRefName,baseRefName,reviewRequests,autoMergeRequest,mergeable"


def wait_for_checks(pr_number, timeout=120, interval=5):
    """Wait for in-progress or queued checks on the head to conclude."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        raw = github.rollup_of(pr_number)
        if not raw:
            return []
        pending = [c for c in raw if (c.get("conclusion") or c.get("state") or c.get("status") or "").upper() in polling.UNCONCLUDED]
        if not pending:
            return raw
        time.sleep(interval)
    return github.rollup_of(pr_number)


def hand_back(issue):
    """Provides pull request status metrics for challenge hand-back automation.

    Args:
        issue: Challenge issue number string or integer.

    Returns:
        dict[str, Any]: Status summary containing handed, green, conflicting, number, base.
    """
    found = []
    for prefix in ("gemini", "claude", "codex"):
        found = github.gh("pr", "list", "--state", "open", "--head", f"{prefix}/issue-{issue}",
                   "--json", HANDBACK_FIELDS)
        if found:
            break
    if not found:
        return {"number": None, "branch": None, "handed": False, "green": False,
                "conflicting": False, "base": None}
    pr = found[0]
    raw_contexts = github.rollup_of(pr["number"])
    pending = [c for c in raw_contexts if (c.get("conclusion") or c.get("state") or c.get("status") or "").upper() in polling.UNCONCLUDED]
    if pending:
        raw_contexts = wait_for_checks(pr["number"], timeout=120, interval=5)
    pr["statusCheckRollup"] = polling.deduplicate_checks(raw_contexts)
    return {"number": pr["number"],
            "branch": pr.get("headRefName"),
            "handed": bool(asked_of(pr)) or pr.get("autoMergeRequest") is not None,
            "green": green(pr),
            "conflicting": pr.get("mergeable") == "CONFLICTING",
            "base": pr.get("baseRefName") or "main"}


def is_approved_pull(pr, reviewer_login=None):
    """Whether the reviewer's most recent review on this pull request is an approval."""
    if not (pr.get("latestReviews") or pr.get("reviews")):
        return False
    if reviewer_login is None:
        reviewer_login = github.role_login("reviewer")
    revs = [r for r in pr.get("latestReviews") or pr.get("reviews") or []
            if (r.get("author") or {}).get("login") == reviewer_login]
    return bool(revs and revs[-1].get("state") == "APPROVED")


def is_changes_requested_pull(pr, reviewer_login=None):
    """Whether the reviewer's most recent review on this pull request requests changes."""
    if not (pr.get("latestReviews") or pr.get("reviews")):
        return False
    if reviewer_login is None:
        reviewer_login = github.role_login("reviewer")
    revs = [r for r in pr.get("latestReviews") or pr.get("reviews") or []
            if (r.get("author") or {}).get("login") == reviewer_login]
    return bool(revs and revs[-1].get("state") == "CHANGES_REQUESTED")


class Standing(NamedTuple):
    """One open pull request as `unheld` reads it: the request on it, the loop's branch match, how long it has sat, and the reviewer's login."""

    pr: dict
    asked: list
    branch: re.Match | None
    idle: float
    reviewer_login: str

    def line(self):
        """`#<number> <title>`, the head of every remedy."""
        return f"#{self.pr['number']} {self.pr['title'][:60]}"

    def challenge(self, levels):
        """The branch's Challenge as `(state, level)`, the level being the first of `levels` among its labels, or None."""
        issue = github.gh("issue", "view", self.branch.group(1), "--json", "state,labels")
        level = next((lbl["name"] for lbl in issue["labels"] if lbl["name"] in levels), None)
        return issue["state"], level


def unresolved_of(pr, unresolved):
    """The unresolved threads of `pr`, from `unresolved` where the caller read them and from GitHub otherwise."""
    if unresolved is not None:
        return unresolved.get(pr["number"])
    return [t for t in github.threads(str(pr["number"])) if not t["isResolved"]]


def waiting_on_conflict(standing):
    """The remedy where a request, an arming or an approval waits on a branch that conflicts, and nothing where none does."""
    pr = standing.pr
    waiting, stuck = [], []
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


def armed_over_conversations(standing, minutes, unresolved):
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


def stranded_request(standing, minutes):
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


def unanswered_changes(standing, minutes, unresolved):
    """The remedy where the reviewer's request for changes stands unanswered on a Challenge the loop holds."""
    pr = standing.pr
    if not (is_changes_requested_pull(pr, reviewer_login=standing.reviewer_login) and not standing.asked
            and standing.branch and standing.idle >= minutes):
        return []
    if not (unresolved_of(pr, unresolved) or not green(pr)):
        return []
    state, level = standing.challenge(TAKEN)
    if state != "OPEN" or not level:
        return []
    return [f"{standing.line()} — changes requested by "
            f"reviewer, and unanswered: no run is answering it and nothing "
            f"has moved on it for {int(standing.idle)} minutes, while #{standing.branch.group(1)} "
            f"is still {level}. A review event was dropped or a run ended "
            f"without answering: .meta/say/move dispatch {pr['number']} --task review"]


def approved_and_failing(standing, minutes):
    """The remedy where an approved pull request's checks went red after the approval and no Job is standing to fix them."""
    pr = standing.pr
    if not (is_approved_pull(pr, reviewer_login=standing.reviewer_login) and not standing.asked
            and not pr["isDraft"] and not green(pr) and pr.get("mergeable") != "CONFLICTING"
            and standing.branch and standing.idle >= minutes):
        return []
    state, level = standing.challenge((*TAKEN, "human", "hard"))
    if state != "OPEN" or not level:
        return []
    if level in TAKEN:
        remedy = f".meta/say/move dispatch {pr['number']} --task review"
    else:
        remedy = f"fix the failing checks (or move difficulty {standing.branch.group(1)} medium)"
    idle_mins = int(standing.idle) if standing.idle != float("inf") else 0
    return [f"{standing.line()} — approved, with failing checks: "
            f"no review requested, no merge armed, and nothing has moved on it for "
            f"{idle_mins} minutes, while #{standing.branch.group(1)} is still {level}. "
            f"A check failed after approval, and no Job is standing to fix it: {remedy}"]


def green_and_unheld(standing, minutes, clean):
    """The remedy where a green pull request on a loop's branch has no request, no arming and nobody holding it."""
    pr = standing.pr
    if (standing.asked or pr.get("autoMergeRequest") or pr["isDraft"] or not green(pr)
            or pr["number"] not in clean or not standing.branch or standing.idle < minutes):
        return []
    state, level = standing.challenge((*TAKEN, "human", "hard"))
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


def unheld(prs, minutes, clean, unresolved=None, reviewer_login=None):
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
    out = []
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


def sweep_all(publishing):
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
    clean = set()
    unresolved = {}
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
