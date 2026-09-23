"""Who takes each open pull request next, and what is owed where nobody does.

`unheld` composes one remedy per shape a webhook should have carried and did
not, each qualified by a span of silence so that a pass still running is not
mistaken for one that stopped (solorepo's DR-129, solorepo's DR-178). Four
readings of a pull request node live here too, for two different reasons.
`asked_of` and `green` are here because the hand-back in `sweep` calls them
both, asking the remedies' own question from the other side
(solorepo's DR-155). `is_approved_pull` and `is_changes_requested_pull` have no caller in
`sweep` at all: they travel with the remedies that read them, and reach their
other readers through `.meta/check_pr.py`'s re-export, which
`.meta/lib/move/pull_requests.py` binds and `move`'s `advance` and `challenges`
read when they decide whether a verdict lets a pull request go on.
"""
import datetime
import re
from collections.abc import Collection, Mapping, Sequence
from typing import Any, NamedTuple

from lib.check_pr import github, polling, review, state
from lib.check_pr.state import LOOP_LEVELS

LOOPS_BRANCH = re.compile(r"^(?:claude|gemini)/issue-(\d+)$")


def asked_of(pr: dict[str, Any]) -> list[str]:
    """Names or logins of reviewers currently requested on a pull request."""
    return [str(r.get("login") or r.get("name") or "someone") for r in pr["reviewRequests"]]


def green(pr: dict[str, Any]) -> bool:
    """Whether every check on the head has concluded and none of them failed."""
    raw_contexts = pr.get("statusCheckRollup") or []
    contexts = polling.deduplicate_checks(raw_contexts)
    _, all_green, _ = state.checks_summary(contexts)
    return bool(contexts) and all_green


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


def unanswered_comments_of(pr: dict[str, Any],
                           unresolved: Mapping[int, list[dict[str, Any]]] | None
                           ) -> list[Mapping[str, Any]] | None:
    """The reviewer's top-level comments on `pr` still owed an answer (solorepo's DR-273).

    The counterpart of `unresolved_of`, which leaves them out because they stop
    no merge. Read through `review.unaddressed_threads`, so that the sweep owes
    an answer to exactly what `just pr <n> --threads` and `watch` print as owed.

    Args:
        pr: Pull request metadata, of which only `number` is read.
        unresolved: The sweep's mapping of pull request number to its unresolved
            threads, or None to ask GitHub for this one's.

    Returns:
        list[Mapping[str, Any]] | None: The comment-shaped thread nodes owed an
            answer, and None where the mapping holds no entry for this pull
            request, as `unresolved_of` answers for the same absence.
    """
    found = (github.threads(str(pr["number"])) if unresolved is None
             else unresolved.get(pr["number"]))
    if found is None:
        return None
    return review.unaddressed_threads([t for t in found if t.get("comment")])


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


def unanswered_comment(standing: Standing, minutes: float,
                       unresolved: Mapping[int, list[dict[str, Any]]] | None) -> list[str]:
    """The remedy where a reviewer's top-level comment stands unanswered (solorepo's DR-273).

    Returns nothing until `minutes` of silence have passed, and appends the
    dispatch clause only where the branch names a Challenge that is open at a
    level the loop takes.
    """
    pr = standing.pr
    if standing.idle < minutes:
        return []
    owed = unanswered_comments_of(pr, unresolved)
    if not owed:
        return []
    remedy = (f"Answer each with .meta/say/post comment {pr['number']} linking it, which "
              f"is what settles one, GitHub having no resolve for it (solorepo's DR-273)")
    if standing.branch:
        try:
            issue_state, level = standing.challenge(LOOP_LEVELS)
        except SystemExit:
            issue_state, level = None, None
        if issue_state == "OPEN" and level:
            remedy += (f", or dispatch a run to answer it: .meta/say/move dispatch "
                       f"{pr['number']} --task review")
    idle_mins = int(standing.idle) if standing.idle != float("inf") else 0
    draft = (", and it is a draft, which no other remedy reaches on silence alone"
             if pr["isDraft"] else "")
    return [f"{standing.line()} — {len(owed)} top-level comment(s) from "
            f"{standing.reviewer_login} unanswered: no run is answering them and nothing "
            f"has moved on it for {idle_mins} minutes{draft}. {remedy}"]


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
    pull request whose checks are red; one that is green with nobody holding
    it; and a reviewer's top-level comment nobody has answered, which is the
    one shape reported on silence alone, and so the one that reaches a draft
    with nothing else wrong with it (solorepo's DR-273). Every one is qualified
    by `minutes` of silence, so a pass that is merely still running is not
    mistaken for one that stopped.
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
        out += unanswered_comment(standing, minutes, unresolved)
    return out

