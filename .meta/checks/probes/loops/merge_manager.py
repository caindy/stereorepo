"""The merge manager's ranking and its one squash-merge per pass (solorepo's DR-161).

One module for one probe, so a history log's receipt names the file holding it (solorepo's DR-209).
"""

from typing import Any

import citations
from collect import META, check
from probes.harness import (
    load_channel,
    load_module,
    outcome,
    stood_in,
)


@check("merge manager probes", pre=True)
def merge_manager_probes():
    """`merge-manager` against its semaphores and its leverage ranking (solorepo's DR-161).

    Each semaphore refuses in turn: a draft; checks pending on an empty
    rollup and checks failing; a conflicting branch and one behind its base;
    changes requested and no review; an unresolved thread; and a base that is
    not `main`. Beside them, a check run that failed and then passed under the
    same name is read as green by `check_green` and by `check_pr.green`
    alike, a `completedAt` of year one counting as no timestamp
    (solorepo's DR-167, solorepo's #316), and `check_threads` fails closed
    when GraphQL raises. With every semaphore satisfied the pull request is
    eligible.

    The end-to-end run answers GitHub from four pull requests and two Issues:
    a stack base, a dependent that waits on it, an unreviewed one and a layer
    based on the first. The base is chosen and the dependent deferred; a dry
    run says so and merges nothing; the real run merges the base and nothing
    else. Last, `issue_blockers` and `next.waits_on` prefer GitHub's native
    `blockedBy` over the body's prose and fall back to the prose, and
    `waits_on` returns a blocker that is not an Issue as the text it was
    (solorepo's DR-170).
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    return (_semaphores(move) + _rerun_reads_green(move) + _threads_fail_closed(channel, move)
            + _eligible(move) + _end_to_end(channel, move) + _blockers(move))


REVIEWER = "owner-repo-reviewer"
GREEN = [{"conclusion": "SUCCESS"}]
APPROVED = [{"author": {"login": REVIEWER}, "state": "APPROVED"}]


def _evaluated(move: Any, pull: Any) -> Any:
    """`evaluate_pr` of `pull` as the reviewer's account over `owner/repo`."""
    return move.evaluate_pr(pull, REVIEWER, "owner", "repo")


def _semaphores(move: Any) -> list[str]:
    """Each semaphore refuses in turn: a draft, then the eight shapes of `refused`."""
    problems = []
    ok, reasons = _evaluated(move, {"number": 1, "isDraft": True})
    if ok or "draft" not in reasons:
        problems.append("merge manager: draft PR was reported as eligible")

    refused = (
        ("PR with empty checks rollup", "checks pending",
         {"mergeable": "MERGEABLE", "statusCheckRollup": []}),
        ("PR with failing check", "checks failing",
         {"mergeable": "MERGEABLE", "statusCheckRollup": [{"name": "gate", "conclusion": "FAILURE"}]}),
        ("conflicting PR", "conflicts",
         {"mergeable": "CONFLICTING", "statusCheckRollup": GREEN}),
        ("behind PR", "behind",
         {"mergeable": "MERGEABLE", "mergeStateStatus": "BEHIND", "statusCheckRollup": GREEN}),
        ("PR with changes requested", "changes requested",
         {"mergeable": "MERGEABLE", "statusCheckRollup": GREEN,
          "latestReviews": [{"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"}]}),
        ("unreviewed PR", "no review",
         {"mergeable": "MERGEABLE", "statusCheckRollup": GREEN, "latestReviews": []}),
        ("PR with unresolved threads", "unresolved",
         {"mergeable": "MERGEABLE", "statusCheckRollup": GREEN, "latestReviews": APPROVED,
          "reviewThreads": [{"isResolved": False}]}),
        ("PR targeting non-main branch", "base is feature-branch, not main",
         {"mergeable": "MERGEABLE", "baseRefName": "feature-branch", "statusCheckRollup": GREEN,
          "latestReviews": APPROVED, "reviewThreads": [{"isResolved": True}]}),
    )
    for case, phrase, pull in refused:
        ok, reasons = _evaluated(move, {"number": 1, "isDraft": False, **pull})
        if ok or not any(phrase in r for r in reasons):
            problems.append(f"merge manager: {case} was reported as eligible")
    return problems


def _rerun_reads_green(move: Any) -> list[str]:
    """A check run that failed and then passed under the same name is green to `check_green` and `check_pr.green` alike, a year-one `completedAt` counting as none (solorepo's DR-167, solorepo's #316)."""
    problems = []
    rerun = [
        {"name": "gate", "conclusion": "FAILURE", "startedAt": "2026-09-11T12:00:00Z",
         "completedAt": "2026-09-11T12:05:00Z"},
        {"name": "gate", "conclusion": "SUCCESS", "startedAt": "2026-09-11T12:10:00Z",
         "completedAt": "2026-09-11T12:15:00Z"},
    ]
    ok_dedup, reasons_dedup = move.check_green({"statusCheckRollup": rerun})
    if not ok_dedup:
        problems.append(f"merge manager: check_green did not deduplicate check runs: {reasons_dedup}")
    ok_zero, _ = move.check_green({"statusCheckRollup": [
        rerun[0],
        {"name": "gate", "conclusion": "SUCCESS", "completedAt": "0001-01-01T00:00:00Z",
         "createdAt": "2026-09-11T12:10:00Z"},
    ]})
    if not ok_zero:
        problems.append("merge manager: check_green did not handle 0001-01-01 completedAt timestamp")
    if not citations.load_check_pr().green({"statusCheckRollup": rerun}):
        problems.append("check_pr.green did not deduplicate check runs")
    return problems


def _threads_fail_closed(channel: Any, move: Any) -> list[str]:
    """`check_threads` fails closed when GraphQL raises."""
    problems = []
    def broken_graphql(*args, **kwargs):
        """A GraphQL that raises, whatever it is asked."""
        raise RuntimeError("GraphQL outage")

    with stood_in(channel, graphql=broken_graphql):
        ok_th, msg_th = move.check_threads({"number": 99}, "owner", "repo")
    if ok_th or "could not read conversations" not in msg_th:
        problems.append(f"merge manager: check_threads did not fail closed on exception: {msg_th}")
    return problems


def _eligible(move: Any) -> list[str]:
    """With every semaphore satisfied the pull request is eligible."""
    problems = []
    ok, reasons = _evaluated(move, {"number": 1, "isDraft": False, "mergeable": "MERGEABLE",
                             "baseRefName": "main", "statusCheckRollup": GREEN,
                             "latestReviews": APPROVED, "reviewThreads": [{"isResolved": True}]})
    if not ok or reasons != ["eligible"]:
        problems.append(f"merge manager: eligible PR failed evaluation: {reasons}")
    return problems


def _fixtures() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The four pull requests and two Issues the end-to-end run answers GitHub from: a stack base, a dependent that waits on it, an unreviewed one and a layer based on the first."""
    pulls = [
        {"number": 10, "title": "stack base PR", "headRefName": "branch-a", "baseRefName": "main",
         "isDraft": False, "mergeable": "MERGEABLE", "statusCheckRollup": GREEN,
         "latestReviews": APPROVED, "reviewThreads": [{"isResolved": True}],
         "body": "implements base", "additions": 100, "deletions": 20},
        {"number": 11, "title": "dependent PR", "headRefName": "branch-b", "baseRefName": "main",
         "isDraft": False, "mergeable": "MERGEABLE", "statusCheckRollup": GREEN,
         "latestReviews": APPROVED, "reviewThreads": [{"isResolved": True}],
         "body": f"**Waits on.** #{'10'}", "additions": 500, "deletions": 100},
        {"number": 12, "title": "unreviewed PR", "headRefName": "branch-c", "baseRefName": "main",
         "isDraft": False, "mergeable": "MERGEABLE", "statusCheckRollup": GREEN,
         "latestReviews": [], "body": ""},
        {"number": 13, "title": "layered PR with non-main base", "headRefName": "branch-d",
         "baseRefName": "branch-a", "isDraft": False, "mergeable": "MERGEABLE",
         "statusCheckRollup": GREEN, "latestReviews": APPROVED,
         "reviewThreads": [{"isResolved": True}], "body": ""},
    ]
    issues = [
        {"number": 50, "body": f"**Waits on.** #{'10'}", "title": "blocked issue"},
        {"number": 51, "body": "**Waits on.** Nothing", "title": "natively blocked issue",
         "blockedBy": {"nodes": [{"number": 10}]}},
    ]
    return pulls, issues


class ManagerFake:
    """As much of GitHub as `merge_manager` asks about, over `owner/repo`: the `pulls` and `issues` given, every review thread resolved, and the merges asked for, recorded in `merged`.

    `pr view` answers `MERGED` once anything has been merged, `api
    .../pulls/10` answers a `stack` object so the winner is merged as a
    stack, and any other call answers an empty dict.
    """

    def __init__(self, pulls, issues):
        self.pulls, self.issues, self.merged = pulls, issues, []

    def gh(self, *args, parse=True):
        """One `gh` call, answered as the class docstring says."""
        head = args[:2]
        if head == ("repo", "view") or args[0] == "repo":
            return {"nameWithOwner": "owner/repo", "deleteBranchOnMerge": True}
        if head == ("pr", "list"):
            return list(self.pulls)
        if head == ("issue", "list"):
            return list(self.issues)
        if head in (("pr", "merge"), ("stack", "merge")):
            self.merged.append(args[2])
            return {}
        if head == ("pr", "view"):
            state = "MERGED" if self.merged else "OPEN"
            return {"number": int(args[2]), "title": "merged pr", "state": state,
                    "mergeCommit": {"oid": "sha1234"}, "headRefName": "branch"}
        if len(args) >= 2 and args[0] == "api" and str(args[1]).endswith("/pulls/10"):
            return {"stack": {"id": "stack-1"}}
        return {}

    def repo(self):
        """`owner/repo`."""
        return "owner/repo"

    def graphql(self, query, **variables):
        """One resolved review thread, whatever is asked."""
        return {"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": [{"isResolved": True}]}}}}}


def _end_to_end(channel: Any, move: Any) -> list[str]:
    """The base is chosen and the dependent deferred; a dry run says so and merges nothing, and the real run merges the base and nothing else."""
    problems = []
    fake = ManagerFake(*_fixtures())
    with stood_in(channel, gh=fake.gh, repo=fake.repo, graphql=fake.graphql):
        text = outcome(lambda: move.merge_manager(dry_run=True)).out
        if f"chosen: #{'10'}" not in text:
            problems.append(f"merge manager: expected #{'10'} to be chosen as stack base, got:\n{text}")
        if f"deferred: #{'11'}" not in text:
            problems.append(f"merge manager: expected #{'11'} to be deferred, got:\n{text}")
        if "dry run — not merging" not in text:
            problems.append("merge manager: dry run message missing")
        if fake.merged:
            problems.append(f"merge manager: dry run executed merges: {fake.merged}")

        text = outcome(lambda: move.merge_manager(dry_run=False)).out
        if f"merging #{'10'}" not in text:
            problems.append(f"merge manager: did not attempt merging #{'10'}, got:\n{text}")
        if fake.merged != ["10"]:
            problems.append(f"merge manager: expected merge of #{'10'}, got: {fake.merged}")
    return problems


def _blockers(move: Any) -> list[str]:
    """`issue_blockers` and `next.waits_on` prefer GitHub's native `blockedBy` over the body's prose, fall back to it, and return a blocker that is not an Issue as text (solorepo's DR-170)."""
    problems = []
    native = {"number": 1, "body": f"**Waits on.** #{'99'}", "blockedBy": {"nodes": [{"number": 42}]}}
    if move.issue_blockers(native) != [42]:
        problems.append(f"issue_blockers did not prefer native blockedBy: {move.issue_blockers(native)}")
    prose = {"number": 2, "body": f"**Waits on.** #{'99'}", "blockedBy": {"nodes": []}}
    if move.issue_blockers(prose) != [99]:
        problems.append(f"issue_blockers did not fall back to prose: {move.issue_blockers(prose)}")

    screen = load_module(META / "next.py", "next_screen", register=False)
    if screen.waits_on(native) != [42]:
        problems.append(f"next.waits_on did not prefer native blockedBy: {screen.waits_on(native)}")
    if screen.waits_on(prose) != [99]:
        problems.append(f"next.waits_on did not fall back to prose: {screen.waits_on(prose)}")
    text_blocker = {"number": 3, "body": f"**Waits on.** Decision DR-{'041'}", "blockedBy": {"nodes": []}}
    if screen.waits_on(text_blocker) != f"Decision DR-{'041'}":
        problems.append(f"next.waits_on did not return non-issue blocker string: {screen.waits_on(text_blocker)}")
    return problems
