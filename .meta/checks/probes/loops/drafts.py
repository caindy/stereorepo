"""The plan-only draft and its review (solorepo's DR-273).

A plan-only pull request is a draft while the reviewer checks its plan, and
its empty commit must not merge on that approval. Every way out of draft asks
one check, whatever the branch is named; `watch` still wakes on a verdict on a
draft; and the reviewer's top-level comment, which is all a pull request with
no lines can carry, reads as a thread owed an answer.
"""
from typing import Any

from checks import citations
from checks.collect import check
from checks.probes.harness import load_channel, outcome, stood_in, unanswered

REVIEWER = "owner-repo-reviewer"
GREEN = [{"conclusion": "SUCCESS"}]
APPROVED = [{"author": {"login": REVIEWER}, "state": "APPROVED"}]


@check("draft probes", pre=True)
def draft_probes() -> list[str]:
    """`move ready`, both automatic ways out of draft, `watch` on a draft, and comment threads."""
    channel, _, programs = load_channel()
    move = programs["move"]
    check_pr = citations.load_check_pr()
    return (_ready_cases(channel, move) + _restore_cases(channel, move)
            + _watch_cases(check_pr) + _comment_cases(check_pr))


def _ready_cases(channel: Any, move: Any) -> list[str]:
    """`move ready` refuses a draft whose branch changes no file, and readies one that does."""
    problems = []
    ready_calls: list[str] = []
    pull: dict[str, Any] = {}

    def gh(*args: Any, **kwargs: Any) -> Any:
        if args[:2] == ("pr", "view"):
            return {"isDraft": not ready_calls} if args[-1] == "isDraft" else pull
        if args[:2] == ("pr", "ready"):
            ready_calls.append(str(args[2]))
        return {}

    pull = {"number": 50, "headRefName": "claude/plan", "baseRefName": "main",
            "state": "OPEN", "isDraft": True, "changedFiles": 0}
    with stood_in(channel, gh=gh):
        said = outcome(lambda: move.drafts.ready(50)).code
    if "stays a draft" not in str(said) or ready_calls:
        problems.append(f"ready: a plan-only draft exited {said!r} and was readied "
                        f"{ready_calls!r}, where it should be refused and left a draft")

    pull = {**pull, "number": 51, "changedFiles": 3}
    with stood_in(channel, gh=gh):
        move.drafts.ready(51)
    if ready_calls != ["51"]:
        problems.append(f"ready: a draft holding changes was not readied, got {ready_calls!r}")
    return problems


def _restore_cases(channel: Any, move: Any) -> list[str]:
    """Neither `request-review` nor the merge manager lifts a loop draft that changes no file."""
    problems = []
    ready_calls: list[str] = []
    pull: dict[str, Any] = {}

    def gh(*args: Any, **kwargs: Any) -> Any:
        if args[:2] == ("pr", "view"):
            if "reviewRequests" in args:
                return {"reviewRequests": [{"login": REVIEWER}]}
            return pull
        if args[:2] == ("pr", "ready"):
            ready_calls.append(str(args[2]))
        return {}

    pull = {"number": 43, "headRefName": "claude/issue-43", "baseRefName": "main",
            "state": "OPEN", "isDraft": True, "mergeable": "MERGEABLE", "changedFiles": 0}
    with stood_in(channel, gh=gh, role_login=lambda r: REVIEWER):
        move.request_review(43, "reviewer")
    if ready_calls:
        problems.append("request-review: a loop-shaped draft that changes no file was taken "
                        f"out of draft by its branch name alone: {ready_calls!r}")

    plan = {"number": 37, "headRefName": "gemini/issue-37", "isDraft": True, "changedFiles": 0,
            "latestReviews": APPROVED, "statusCheckRollup": GREEN, "mergeable": "MERGEABLE"}
    with stood_in(channel, gh=gh):
        move.evaluate_open_pulls([plan], reviewer_login=REVIEWER, owner="owner", name="repo",
                                 dry_run=False)
    if ready_calls or plan.get("isDraft") is not True:
        problems.append("merge manager: an approved draft that changes no file was restored, "
                        f"so a plan's approval could merge it: {ready_calls!r}")
    return problems


def _watch_cases(check_pr: Any) -> list[str]:
    """`--watch` begun on a draft holding a request for changes exits on its first poll."""
    verdict = [{"id": "R1", "author": {"login": "o-r-reviewer"}, "state": "CHANGES_REQUESTED"}]
    polls = [0]

    def gh(*args: Any) -> Any:
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "o/r"}
        if args[:2] == ("pr", "view"):
            if args[-1] == "number":
                return {"number": 7}
            polls[0] += 1
            return {"number": 7, "state": "OPEN" if polls[0] < 3 else "MERGED", "isDraft": True,
                    "mergeable": "MERGEABLE", "comments": [], "reviews": verdict,
                    "latestReviews": verdict, "reviewRequests": []}
        if args[0] == "api":
            return {"data": {"repository": {"pullRequest": {
                "reviewThreads": {"nodes": []}, "reviews": {"nodes": []}, "commits": {"nodes": [
                    {"commit": {"statusCheckRollup": {"contexts": {"nodes": [
                        {"name": "files", "status": "COMPLETED", "conclusion": "SUCCESS"}]}}}}]}}}}}
        raise unanswered(args)

    problems = []
    with stood_in(check_pr.github, gh=gh, role_login=lambda role: f"o-r-{role}"):
        lines: list[str] = outcome(lambda: check_pr.watch("7", every=0)).out.splitlines()
    if polls[0] != 1 or not any("CHANGES_REQUESTED" in line for line in lines):
        problems.append(f"watch: a draft carrying a request for changes was polled {polls[0]} "
                        f"times and printed {lines!r}, so a restarted watch sleeps through it")

    verdict[:] = [{"id": "R2", "author": {"login": "o-r-reviewer"}, "state": "APPROVED"}]
    polls[0] = 0
    with stood_in(check_pr.github, gh=gh, role_login=lambda role: f"o-r-{role}"):
        lines = outcome(lambda: check_pr.watch("7", every=0)).out.splitlines()
    if not any("plan approved" in line for line in lines) or any(
            "READY_TO_MERGE" in line for line in lines):
        problems.append(f"watch: an approved plan-only draft printed {lines!r}, where it is a "
                        "plan approved and not a pull request ready to merge")
    return problems


def _comment_cases(check_pr: Any) -> list[str]:
    """The reviewer's top-level comments read as threads, owed until another party answers."""
    def said(n: int, login: str, text: str) -> dict[str, Any]:
        return {"id": f"IC_{n}", "databaseId": n, "author": {"login": login},
                "body": f"{text}\n\nActor: actor-{n}"}

    point = said(1, "o-r-reviewer", "point")
    problems = []
    unanswering = {
        "an aside from another account": said(2, "o", "aside"),
        "the reviewer's own next run": said(3, "o-r-reviewer", "see #issuecomment-1 again"),
        "a coder comment that links nothing": said(4, "o-r-coder", "answered above"),
    }
    for case, later in unanswering.items():
        shaped = check_pr.github.comment_threads([point, later], "o-r-reviewer")
        if len(shaped) < 1 or shaped[0]["isResolved"] or not check_pr.review.unaddressed(shaped):
            problems.append(f"comment threads: {case} settled the reviewer's point: {shaped!r}")
    answer = said(5, "o-r-coder", "Right, and a change to make (#issuecomment-1).")
    shaped = check_pr.github.comment_threads([point, answer], "o-r-reviewer")
    if len(shaped) != 1 or not shaped[0]["isResolved"] or check_pr.review.unaddressed(shaped):
        problems.append(f"comment threads: a linked answer did not settle the point: {shaped!r}")
    if check_pr.review.unanswered(shaped):
        problems.append("comment threads: an answered reviewer comment fails A16's check")
    owed = check_pr.github.comment_threads([point], "o-r-reviewer")
    if check_pr.sweep.unresolved_of({"number": 1}, {1: owed}):
        problems.append("comment threads: `sweep` counts a reviewer comment among the "
                        "conversations that stop GitHub merging")
    if check_pr.review.where_of(shaped[0]) != check_pr.review.COMMENT_WHERE:
        problems.append("comment threads: a reviewer comment is printed as a thread to resolve")
    return problems
