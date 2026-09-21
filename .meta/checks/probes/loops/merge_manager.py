"""The merge manager's ranking and its one squash-merge per pass (solorepo's DR-161).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""

from typing import Any

from checks import citations
from checks.collect import META, check
from checks.probes.harness import (
    load_channel,
    load_module,
    outcome,
    stood_in,
)

GRAPHQL_OUTAGE = "GraphQL outage"
"""What a GraphQL stood in for to fail raises, so the probe reads a degraded answer."""

API_OUTAGE = "API outage"
"""What a `gh` stood in for to fail raises, so the probe reads a degraded answer."""

SIMULATED_NETWORK_FAILURE = "gh: simulated network failure marking ready"
"""What a stood-in `gh` raises to simulate a network failure marking a pull request ready."""


@check("merge manager probes", pre=True)
def merge_manager_probes() -> list[str]:
    """`merge-manager` against its semaphores and its leverage ranking (solorepo's DR-161).

    Each semaphore refuses in turn: a draft; checks pending on an empty
    rollup and checks failing; a conflicting branch and one behind its base;
    changes requested and no review; an unresolved thread; and a base that is
    not `main`. Beside them, a check run that failed and then passed under the
    same name is read as green by `check_green` and by `check_pr.green`
    alike, a `completedAt` of year one counting as no timestamp
    (solorepo's DR-167, solorepo's #316), and `check_threads` fails closed
    when GraphQL raises. With every semaphore satisfied the pull request is
    eligible. A mergeable read of `UNKNOWN` is waited out through
    `mergeability` rather than refusing the cycle on it; a branch the wait
    reveals as behind its base is refused as behind and nothing else, so
    `advance_stranded` still reaches it; and only a value still `UNKNOWN` once
    the wait is spent is refused, once and in words that say it was waited
    for, a settled `CONFLICTING` being the classifier's `NEEDS_REBASE`
    (solorepo's #784, solorepo's DR-264). The lifecycle refusals are the
    classifier's: a notice held at approval, read through the threads query
    the merge manager runs, is named as held for promotion; a thread owed an
    answer is counted once; a state nothing words names itself only where no
    other reason explains it; and a conflicting branch is refused once, in the
    classifier's words.

    The decision semaphore reads the diff (solorepo's DR-222): a diff adding
    an entry as `PROPOSED` or `RECOMMENDED` defers and is named in the reason
    (neither is yet in force), one adopting an entry or correcting an adopted
    entry's prose does not, an entry GitHub sends without a patch defers as
    unreadable, a file list that runs past the pages read defers with it, and
    the read fails closed when the API raises. Through `evaluate_pr`, a pull
    request every other semaphore clears is refused for the decision it
    carries.

    The end-to-end run answers GitHub from four pull requests and two Issues:
    a stack base, a dependent that waits on it, an unreviewed one and a layer
    based on the first. The base is chosen, the dependent deferred, and the
    unreviewed and layered candidates refused with their reasons; a dry run says
    so and merges nothing; the real run merges the base and nothing else. A
    winning candidate whose `merge` raises `SystemExit` sweeps the rest of the
    queue through `advance_stranded` and then exits on the merge's own code, so
    one failing candidate starves nothing and the run still goes red. Last,
    `issue_blockers` and `next.waits_on` prefer GitHub's native `blockedBy` over
    the body's prose and fall back to the prose, and `waits_on` returns a
    blocker that is not an Issue as the text it was (solorepo's DR-170).
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    return (_semaphores(move) + _rerun_reads_green(move) + _threads_fail_closed(channel, move)
            + _mergeable_unknown_is_waited_out(channel, move)
            + _lifecycle_is_the_classifiers(channel, move)
            + _eligible(channel, move) + _decisions_in_force(channel, move)
            + _end_to_end(channel, move) + _check_merge_failure_isolation(channel, move)
            + _blockers(move)
            + _check_contention_hold(channel, move)
            + _check_disjoint_bypass(channel, move)
            + _check_reservation_semantics(move)
            + _stall_eviction(channel, move))


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
    def broken_graphql(*args: Any, **kwargs: Any) -> Any:
        """A GraphQL that raises, whatever it is asked."""
        raise RuntimeError(GRAPHQL_OUTAGE)

    with stood_in(channel, graphql=broken_graphql):
        ok_th, msg_th = move.check_threads({"number": 99}, "owner", "repo")
    if ok_th or "could not read conversations" not in msg_th:
        problems.append(f"merge manager: check_threads did not fail closed on exception: {msg_th}")
    return problems


CLEARED = {"number": 1, "isDraft": False, "mergeable": "MERGEABLE", "baseRefName": "main",
           "statusCheckRollup": GREEN, "latestReviews": APPROVED,
           "reviewThreads": [{"isResolved": True}]}
"""A pull request every semaphore but the decision one clears."""

ENTRY = f".meta/assertions/decisions/DR-{299}.yaml"
"""The path of the Decision entry the decision semaphore's cases write.

`299` is a fixture number, not a Decision, so it is held out of the literal
here and at its two other uses below: written plainly it would read as a
citation and fail `cited_decisions` either way — unresolved as bare
`DR-299`, or, written `solorepo's DR-299`, resolved and still absent from
the index."""


def _diff_of(*changed: dict[str, Any]) -> Any:
    """A `gh` answering the pull request's files endpoint with `changed` on its first page and nothing after, and an empty dict to anything else."""
    def gh(*args: Any, **kwargs: Any) -> Any:
        """One `gh` call, answered as the enclosing function says."""
        if args[0] == "api" and "/files?per_page=" in str(args[-1]):
            return list(changed) if str(args[-1]).endswith("page=1") else []
        return {}
    return gh


def _settling_to(**settled: str) -> Any:
    """A `gh` answering every `pr view` with `settled`, and anything else the
    empty dict `_diff_of` would."""
    def gh(*args: Any, **kwargs: Any) -> Any:
        """One `gh` call, answered as the enclosing function says."""
        return dict(settled) if args[:2] == ("pr", "view") else {}
    return gh


def _mergeable_unknown_is_waited_out(channel: Any, move: Any) -> list[str]:
    """`check_mergeable_clean` waits an `UNKNOWN` mergeable read out through
    `mergeability` rather than refusing the cycle on it, refuses once and in
    words that say it was waited for once the wait is spent and the value
    never settles, with no second reason naming the review, and reads
    `mergeStateStatus` from the read that answered rather than from the one
    the wait was entered on (solorepo's #784)."""
    problems = []
    with stood_in(channel, MERGEABILITY=(2, 0)):
        with stood_in(channel, gh=_settling_to(mergeable="MERGEABLE")):
            ok, reasons = _evaluated(move, {**CLEARED, "mergeable": "UNKNOWN"})
        if not ok or reasons != ["eligible"]:
            problems.append(
                f"merge manager: UNKNOWN settling to MERGEABLE was refused: {reasons}")

        behind = _settling_to(mergeable="MERGEABLE", mergeStateStatus="BEHIND")
        with stood_in(channel, gh=behind):
            ok, reasons = _evaluated(
                move, {**CLEARED, "mergeable": "UNKNOWN", "mergeStateStatus": "UNKNOWN"})
        if ok or reasons != [move.BEHIND_BASE]:
            problems.append(
                f"merge manager: a branch the wait revealed as behind was not "
                f"refused as behind and nothing else: {reasons}")

        with stood_in(channel, gh=_settling_to(mergeable="UNKNOWN")):
            ok, msg = move.check_mergeable_clean({"number": 1, "mergeable": "UNKNOWN"})
        if ok or "waiting" not in msg:
            problems.append(
                f"merge manager: UNKNOWN outliving the wait was not refused as waited for: {msg}")
        with stood_in(channel, gh=_settling_to(mergeable="UNKNOWN")):
            ok, reasons = _evaluated(move, {**CLEARED, "mergeable": "UNKNOWN"})
        if ok or reasons != ["mergeable is still UNKNOWN after waiting"]:
            problems.append(
                f"merge manager: an approved pull request whose mergeability never settled "
                f"was refused as {reasons}, not once as waited for")
    return problems


def _lifecycle_is_the_classifiers(channel: Any, move: Any) -> list[str]:
    """The lifecycle is refused off the state `classify_pr` found (solorepo's DR-264).

    A notice held open at approval, read through `THREADS_QUERY` as the merge
    manager reads threads it was not handed, is named as held for promotion
    and not as a point owed; a thread left unresolved is refused once, as owed
    an answer, since the classifier reads it and nothing counts it a second
    time; a state nothing words names itself where no other reason explains
    it; and a branch that conflicts is refused once, in the classifier's
    words, rather than once by it and once by the mergeability check.
    """
    problems = []
    parked = [{"isResolved": False, "isOutdated": False,
               "comments": {"nodes": [{"author": {"login": REVIEWER},
                                       "body": "**Noticed and not done.** a thing"}]}}]

    def fetched(query: str, **_: Any) -> Any:
        """`THREADS_QUERY` answered as GitHub would, the comments only where selected."""
        nodes = parked if "comments" in query else [
            {key: value for key, value in thread.items() if key != "comments"} for thread in parked]
        return {"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": nodes}}}}}

    with stood_in(channel, gh=_diff_of(), graphql=fetched):
        ok, reasons = _evaluated(move, {**CLEARED, "reviewThreads": None})
    if ok or not any("held for promotion" in r for r in reasons):
        problems.append(f"merge manager: a notice held at approval was refused as {reasons}, "
                        "not as held for promotion")
    answered = [{"isResolved": False, "comments": {"nodes": [{"body": "Fixed in abc123."}]}}]
    with stood_in(channel, gh=_diff_of()):
        ok, reasons = _evaluated(move, {**CLEARED, "reviewThreads": answered})
    if ok or reasons != ["1 unresolved conversation(s) owed an answer"]:
        problems.append(f"merge manager: a thread left unresolved was refused as {reasons}, "
                        "not once as owed an answer")
    with stood_in(channel, gh=_diff_of()):
        ok, reasons = _evaluated(move, {**CLEARED, "mergeable": None})
    if ok or reasons != ["state is AWAITING_REVIEW, not READY_TO_MERGE"]:
        problems.append(f"merge manager: a state nothing words was refused as {reasons}, "
                        "not by naming itself")
    with stood_in(channel, gh=_diff_of()):
        ok, reasons = _evaluated(move, {**CLEARED, "mergeable": "CONFLICTING",
                                        "mergeStateStatus": "DIRTY"})
    if ok or reasons != ["branch conflicts with base"]:
        problems.append(f"merge manager: a conflicting branch was refused as {reasons}, "
                        "not once in the classifier's words")
    return problems


def _eligible(channel: Any, move: Any) -> list[str]:
    """With every semaphore satisfied, the decision one reading a diff that carries nothing, the pull request is eligible."""
    problems = []
    with stood_in(channel, gh=_diff_of()):
        ok, reasons = _evaluated(move, dict(CLEARED))
    if not ok or reasons != ["eligible"]:
        problems.append(f"merge manager: eligible PR failed evaluation: {reasons}")
    return problems


def _decisions_in_force(channel: Any, move: Any) -> list[str]:
    """The decision semaphore over the diffs it tells apart, failing closed when the API raises, and refusing through `evaluate_pr` a pull request every other semaphore clears (solorepo's DR-222)."""
    problems = []
    cases = (
        ("an entry proposed on the branch", False, f"DR-{299}",
         [{"filename": ENTRY, "additions": 40, "deletions": 0,
           "patch": "@@\n+  - id: work:decision/299\n+    status: PROPOSED\n"}]),
        ("an entry recommended on the branch", False, f"DR-{299}",
         [{"filename": ENTRY, "additions": 40, "deletions": 0,
           "patch": "@@\n+  - id: work:decision/299\n+    status: RECOMMENDED\n"}]),
        ("an entry the solo adopted on the branch", True, "only decisions in force",
         [{"filename": ENTRY, "additions": 1, "deletions": 1,
           "patch": "@@\n-    status: PROPOSED\n+    status: ADOPTED\n"}]),
        ("a correction to an entry's prose", True, "only decisions in force",
         [{"filename": ENTRY, "additions": 1, "deletions": 1,
           "patch": "@@\n-    context: as it was\n+    context: as it is\n"}]),
        ("a proposed status outside the record", True, "only decisions in force",
         [{"filename": ".meta/work/decisions.yaml", "additions": 1, "deletions": 0,
           "patch": "@@\n+    status: PROPOSED\n"}]),
        ("an entry GitHub sent no patch for", False, "could not read the diff",
         [{"filename": ENTRY, "additions": 40, "deletions": 0}]),
    )
    for case, expected, phrase, files in cases:
        with stood_in(channel, gh=_diff_of(*files)):
            ok, msg = move.check_decisions_in_force({"number": 1}, "owner", "repo")
        if ok != expected or phrase not in msg:
            problems.append(f"merge manager: {case} was read as {msg!r}")

    def broken_gh(*args: Any, **kwargs: Any) -> Any:
        """A `gh` that raises, whatever it is asked."""
        raise RuntimeError(API_OUTAGE)

    with stood_in(channel, gh=broken_gh):
        ok, msg = move.check_decisions_in_force({"number": 1}, "owner", "repo")
    if ok or "could not read the diff" not in msg:
        problems.append(f"merge manager: the decision semaphore did not fail closed: {msg}")

    def crowded_gh(*args: Any, **kwargs: Any) -> Any:
        """A `gh` whose every page of files is full, so the list never ends."""
        if args[0] == "api" and "/files?per_page=" in str(args[-1]):
            return [{"filename": "README.md", "additions": 1, "patch": "@@\n+a\n"}]
        return {}

    with stood_in(channel, gh=crowded_gh), stood_in(move, PER_PAGE=1, PAGES=2):
        ok, msg = move.check_decisions_in_force({"number": 1}, "owner", "repo")
    if ok or "over 2 files" not in msg:
        problems.append(f"merge manager: a file list past the pages read was not deferred: {msg}")

    carried = [{"filename": ENTRY, "additions": 40, "deletions": 0,
                "patch": "@@\n+    status: PROPOSED\n"}]
    with stood_in(channel, gh=_diff_of(*carried)):
        ok, reasons = _evaluated(move, dict(CLEARED))
    if ok or not any(f"DR-{299}" in reason for reason in reasons):
        problems.append(f"merge manager: PR carrying a proposed decision was reported as eligible: {reasons}")
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
    stack, the files endpoint answers an empty page, so no candidate carries a
    decision, and any other call answers an empty dict.
    """

    def __init__(self, pulls: Any, issues: Any) -> None:
        self.pulls, self.issues = pulls, issues
        self.merged: list[Any] = []

    def gh(self, *args: Any, parse: bool = True) -> Any:
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
        if args[0] == "api" and "/files?per_page=" in str(args[-1]):
            return []
        if len(args) >= 2 and args[0] == "api" and str(args[1]).endswith("/pulls/10"):
            return {"stack": {"id": "stack-1"}}
        return {}

    def repo(self) -> str:
        """`owner/repo`."""
        return "owner/repo"

    def graphql(self, query: str, **variables: Any) -> dict[str, Any]:
        """One resolved review thread, whatever is asked."""
        return {"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": [{"isResolved": True}]}}}}}


def _end_to_end(channel: Any, move: Any) -> list[str]:
    """The base is chosen, the dependent deferred, and the refused candidates named with their reasons; a dry run says so and merges nothing, and the real run merges the base and nothing else."""
    problems = []
    fake = ManagerFake(*_fixtures())
    with stood_in(channel, gh=fake.gh, repo=fake.repo, graphql=fake.graphql):
        text = outcome(lambda: move.merge_manager(dry_run=True)).out
        if f"chosen: #{'10'}" not in text:
            problems.append(f"merge manager: expected #{'10'} to be chosen as stack base, got:\n{text}")
        if f"deferred: #{'11'}" not in text:
            problems.append(f"merge manager: expected #{'11'} to be deferred, got:\n{text}")
        if f"  #{'12'} (unreviewed PR): no review from {REVIEWER}" not in text:
            problems.append(f"merge manager: expected #{'12'} refusal reason, got:\n{text}")
        if f"  #{'13'} (layered PR with non-main base): base is branch-a, not main" not in text:
            problems.append(f"merge manager: expected #{'13'} refusal reason, got:\n{text}")
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


def _check_merge_failure_isolation(channel: Any, move: Any) -> list[str]:
    """A winning candidate's `merge` raising `SystemExit` sweeps the queue
    through `advance_stranded` and then exits on the merge's own code, so the
    scheduled run goes red (solorepo's #776).

    `winner` is the stack base among `_fixtures`, which the leverage ranking
    chooses; `failing_merge` refuses it in the words `merge` itself uses.
    """
    problems = []
    fake = ManagerFake(*_fixtures())
    winner = 10
    refusal = f"say: #{winner} is open after the merge call; not deleting the branch"
    calls: list[Any] = []

    def failing_merge(pr: Any, stack: bool = False, auto: bool = False) -> None:
        """A `merge` that always refuses, as GitHub's own would on a candidate that never settles."""
        raise SystemExit(refusal)

    def recording_advance_stranded(*args: Any, **kwargs: Any) -> None:
        """An `advance_stranded` that records its call rather than sweeping anything."""
        calls.append(args)

    with stood_in(channel, gh=fake.gh, repo=fake.repo, graphql=fake.graphql), \
            stood_in(move, merge=failing_merge, advance_stranded=recording_advance_stranded):
        result = outcome(lambda: move.merge_manager(dry_run=False))

    if result.code != refusal:
        problems.append(
            f"merge manager: a failing merge did not exit on the merge's own code: {result.code}")
    if f"could not merge #{winner}" not in result.out:
        problems.append(f"merge manager: failing merge was not logged, got:\n{result.out}")
    if not calls:
        problems.append("merge manager: advance_stranded did not run after a failing merge")
    return problems


def _blockers(move: Any) -> list[str]:
    """`issue_blockers` reads GitHub's native `blockedBy` alone (solorepo's DR-213); `next.waits_on` reads native `blockedBy` for Issue blockers and returns a blocker that is not an Issue as text (solorepo's DR-170)."""
    problems = []
    native = {"number": 1, "body": f"**Waits on.** #{'99'}", "blockedBy": {"nodes": [{"number": 42}]}}
    if move.issue_blockers(native) != [42]:
        problems.append(f"issue_blockers did not read native blockedBy: {move.issue_blockers(native)}")
    prose = {"number": 2, "body": f"**Waits on.** #{'99'}", "blockedBy": {"nodes": []}}
    if move.issue_blockers(prose) != []:
        problems.append(f"issue_blockers read body prose as a blocker: {move.issue_blockers(prose)}")

    screen = load_module(META / "next.py", "next_screen", register=False)
    if screen.waits_on(native) != [42]:
        problems.append(f"next.waits_on did not prefer native blockedBy: {screen.waits_on(native)}")
    if screen.waits_on(prose) != []:
        problems.append(f"next.waits_on read unlinked numeric reference as a blocker: {screen.waits_on(prose)}")
    text_blocker = {"number": 3, "body": f"**Waits on.** Decision DR-{'041'}", "blockedBy": {"nodes": []}}
    if screen.waits_on(text_blocker) != f"Decision DR-{'041'}":
        problems.append(f"next.waits_on did not return non-issue blocker string: {screen.waits_on(text_blocker)}")
    return problems


def _check_contention_overlap(channel: Any, move: Any) -> list[str]:
    """Candidates sharing files with older reserving PRs are deferred under contention hold (solorepo's DR-258).

    Parameters:
        channel: The mock communication channel.
        move: The move module under test.

    Returns:
        list[str]: Identified probe violations.
    """
    problems = []
    pull_20 = {
        "number": 20, "title": "older in-review PR", "headRefName": "feat-20", "baseRefName": "main",
        "isDraft": False, "mergeable": "MERGEABLE", "statusCheckRollup": GREEN,
        "latestReviews": [], "reviewRequests": [{"login": REVIEWER}], "reviewThreads": [],
        "body": "", "additions": 10, "deletions": 5,
    }
    pull_21 = {
        "number": 21, "title": "contended newer PR", "headRefName": "feat-21", "baseRefName": "main",
        "isDraft": False, "mergeable": "MERGEABLE", "statusCheckRollup": GREEN,
        "latestReviews": APPROVED, "reviewThreads": [{"isResolved": True}],
        "body": "", "additions": 10, "deletions": 5,
    }
    merged_calls: list[str] = []

    def gh_contention(*args: Any, **kwargs: Any) -> Any:
        if args[:2] == ("repo", "view") or args[0] == "repo":
            return {"nameWithOwner": "owner/repo", "deleteBranchOnMerge": True}
        if args[:2] == ("pr", "list"):
            return [pull_20, pull_21]
        if args[:2] == ("issue", "list"):
            return []
        if args[:2] in (("pr", "merge"), ("stack", "merge")):
            merged_calls.append(str(args[2]))
            return {}
        if args[0] == "api" and "/files?per_page=" in str(args[-1]):
            return [{"filename": "shared.py"}]
        return {}

    with stood_in(channel, gh=gh_contention, repo=lambda: "owner/repo"):
        out = outcome(lambda: move.merge_manager(dry_run=True)).out
        if "contention hold" not in out or f"shares 1 file(s) with older #{'20'}" not in out:
            problems.append(f"merge manager: expected PR 21 to be held on contention, got:\n{out}")
        if merged_calls:
            problems.append(f"merge manager: attempted merge during contention hold: {merged_calls}")
    return problems


def _check_contention_unreadable(channel: Any, move: Any) -> list[str]:
    """Unreadable diffs assume maximal contention and defer candidates (solorepo's DR-258).

    Parameters:
        channel: The mock communication channel.
        move: The move module under test.

    Returns:
        list[str]: Identified probe violations.
    """
    problems = []
    pull_20 = {
        "number": 20, "title": "older in-review PR", "headRefName": "feat-20", "baseRefName": "main",
        "isDraft": False, "mergeable": "MERGEABLE", "statusCheckRollup": GREEN,
        "latestReviews": [], "reviewRequests": [{"login": REVIEWER}], "reviewThreads": [],
        "body": "", "additions": 10, "deletions": 5,
    }
    pull_21 = {
        "number": 21, "title": "contended newer PR", "headRefName": "feat-21", "baseRefName": "main",
        "isDraft": False, "mergeable": "MERGEABLE", "statusCheckRollup": GREEN,
        "latestReviews": APPROVED, "reviewThreads": [{"isResolved": True}],
        "body": "", "additions": 10, "deletions": 5,
    }

    def gh_unreadable(*args: Any, **kwargs: Any) -> Any:
        if args[:2] == ("repo", "view") or args[0] == "repo":
            return {"nameWithOwner": "owner/repo", "deleteBranchOnMerge": True}
        if args[:2] == ("pr", "list"):
            return [pull_20, pull_21]
        if args[:2] == ("issue", "list"):
            return []
        if args[0] == "api" and "/files?per_page=" in str(args[-1]):
            url = str(args[-1])
            if f"/pulls/{'21'}/" in url:
                return [{"filename": "cand.py"}]
            return [{"filename": f"file_{i}.py"} for i in range(100)]
        return {}

    with stood_in(channel, gh=gh_unreadable, repo=lambda: "owner/repo"):
        out_unreadable = outcome(lambda: move.merge_manager(dry_run=True)).out
        if "contention hold" not in out_unreadable or "unreadable file list (maximal contention assumed)" not in out_unreadable:
            problems.append(f"merge manager: expected PR 21 to be held on unreadable diff, got:\n{out_unreadable}")

    cache: dict[int, set[str] | None] = {21: None}
    cand_files = move.pr_changed_files(pull_21, "owner", "repo", cache)
    if cand_files is not None:
        problems.append("pr_changed_files: expected None when cached as unreadable")

    return problems


def _check_contention_hold(channel: Any, move: Any) -> list[str]:
    """Contention-aware queueing defers candidates sharing files with older reserving PRs (solorepo's DR-258).

    Parameters:
        channel: The mock communication channel.
        move: The move module under test.

    Returns:
        list[str]: Identified probe violations.
    """
    return _check_contention_overlap(channel, move) + _check_contention_unreadable(channel, move)


def _check_disjoint_bypass(channel: Any, move: Any) -> list[str]:
    """Disjoint diffs bypass the contention hold and merge cleanly (solorepo's DR-258).

    Parameters:
        channel: The mock communication channel.
        move: The move module under test.

    Returns:
        list[str]: Identified probe violations.
    """
    problems = []
    pull_20 = {
        "number": 20, "title": "older in-review PR", "headRefName": "feat-20", "baseRefName": "main",
        "isDraft": False, "mergeable": "MERGEABLE", "statusCheckRollup": GREEN,
        "latestReviews": [], "reviewRequests": [{"login": REVIEWER}], "reviewThreads": [],
        "body": "", "additions": 10, "deletions": 5,
    }
    pull_22 = {
        "number": 22, "title": "disjoint newer PR", "headRefName": "feat-22", "baseRefName": "main",
        "isDraft": False, "mergeable": "MERGEABLE", "statusCheckRollup": GREEN,
        "latestReviews": APPROVED, "reviewThreads": [{"isResolved": True}],
        "body": "", "additions": 10, "deletions": 5,
    }

    merged_calls: list[str] = []

    def gh_disjoint(*args: Any, **kwargs: Any) -> Any:
        if args[:2] == ("repo", "view") or args[0] == "repo":
            return {"nameWithOwner": "owner/repo", "deleteBranchOnMerge": True}
        if args[:2] == ("pr", "list"):
            return [pull_20, pull_22]
        if args[:2] == ("issue", "list"):
            return []
        if args[:2] in (("pr", "merge"), ("stack", "merge")):
            merged_calls.append(str(args[2]))
            return {}
        if args[:2] == ("pr", "view"):
            state = "MERGED" if merged_calls else "OPEN"
            return {"number": int(args[2]), "title": "disjoint newer PR", "state": state,
                    "mergeCommit": {"oid": "sha2222"}, "headRefName": "feat-22"}
        if args[0] == "api" and "/files?per_page=" in str(args[-1]):
            url = str(args[-1])
            if f"/pulls/{'20'}/" in url:
                return [{"filename": "a.py"}]
            if f"/pulls/{'22'}/" in url:
                return [{"filename": "b.py"}]
            return []
        return {}

    with stood_in(channel, gh=gh_disjoint, repo=lambda: "owner/repo"):
        out = outcome(lambda: move.merge_manager(dry_run=False)).out
        if "disjoint bypass" not in out or f"chosen: #{'22'}" not in out:
            problems.append(f"merge manager: expected PR 22 to bypass disjointly, got:\n{out}")
        if merged_calls != ["22"]:
            problems.append(f"merge manager: expected PR 22 to merge via disjoint bypass, got: {merged_calls}")
    return problems


def _check_reservation_semantics(move: Any) -> list[str]:
    """Active reservation window semantics for reviews and check rollups (solorepo's DR-258).

    Parameters:
        move: The move module under test.

    Returns:
        list[str]: Identified probe violations.
    """
    problems = []

    draft_pr = {"number": 1, "isDraft": True, "reviewRequests": [{"login": REVIEWER}]}
    if move.has_active_reservation(draft_pr, REVIEWER):
        problems.append("has_active_reservation: draft PR should not hold reservation")

    req_pr = {"number": 2, "isDraft": False, "reviewRequests": [{"login": REVIEWER}]}
    if not move.has_active_reservation(req_pr, REVIEWER):
        problems.append("has_active_reservation: PR with review request should hold reservation")

    pending_context_pr = {
        "number": 3, "isDraft": False,
        "statusCheckRollup": [{"context": "ci/test", "state": "PENDING"}],
    }
    if not move.has_active_reservation(pending_context_pr, REVIEWER):
        problems.append("has_active_reservation: PR with PENDING StatusContext should hold reservation")

    in_progress_pr = {
        "number": 4, "isDraft": False,
        "statusCheckRollup": [{"name": "gate", "status": "IN_PROGRESS"}],
    }
    if not move.has_active_reservation(in_progress_pr, REVIEWER):
        problems.append("has_active_reservation: PR with IN_PROGRESS check run should hold reservation")

    success_pr = {
        "number": 5, "isDraft": False,
        "statusCheckRollup": [{"context": "ci/test", "state": "SUCCESS"}],
    }
    if move.has_active_reservation(success_pr, REVIEWER):
        problems.append("has_active_reservation: PR with all green status contexts should not hold reservation")

    failed_pr = {
        "number": 6, "isDraft": False,
        "statusCheckRollup": [
            {"context": "ci/test", "state": "PENDING"},
            {"context": "ci/lint", "state": "FAILURE"},
        ],
    }
    if move.has_active_reservation(failed_pr, REVIEWER):
        problems.append("has_active_reservation: PR with failed check should forfeit reservation")

    dedup_pr = {
        "number": 7, "isDraft": False,
        "statusCheckRollup": [
            {"name": "gate", "status": "IN_PROGRESS", "startedAt": "2026-09-20T10:00:00Z"},
            {"name": "gate", "conclusion": "SUCCESS", "startedAt": "2026-09-20T10:05:00Z"},
        ],
    }
    if move.has_active_reservation(dedup_pr, REVIEWER):
        problems.append("has_active_reservation: deduplicated green rerun should not hold reservation")

    return problems


def _check_stall_thresholds(move: Any) -> list[str]:
    """Loop branches stall only after exceeding thresholds while session branches do not (solorepo's DR-258).

    Parameters:
        move: The move module under test.

    Returns:
        list[str]: Identified probe violations.
    """
    problems = []
    loop_pr_1_cr = {
        "number": 30, "headRefName": "gemini/issue-30", "isDraft": False,
        "reviews": [{"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"}],
        "latestReviews": [], "reviewRequests": [{"login": REVIEWER}],
        "mergeable": "MERGEABLE",
    }
    if move.is_stalled_autonomous_pr(loop_pr_1_cr, REVIEWER):
        problems.append("is_stalled_autonomous_pr: single CHANGES_REQUESTED should not stall loop PR")

    session_pr_3_cr = {
        "number": 30, "headRefName": "chris/issue-30", "isDraft": False,
        "reviews": [
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
        ],
        "latestReviews": [], "reviewRequests": [{"login": REVIEWER}],
        "mergeable": "MERGEABLE",
    }
    if move.is_stalled_autonomous_pr(session_pr_3_cr, REVIEWER):
        problems.append("is_stalled_autonomous_pr: non-loops session branch should not be marked stalled")

    stalled_loop_pr = {
        "number": 30, "headRefName": "gemini/issue-30", "isDraft": False,
        "reviews": [
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
        ],
        "latestReviews": [], "reviewRequests": [{"login": REVIEWER}],
        "mergeable": "MERGEABLE",
    }
    if not move.is_stalled_autonomous_pr(stalled_loop_pr, REVIEWER):
        problems.append("is_stalled_autonomous_pr: 3 CHANGES_REQUESTED reviews should stall loop PR")

    approved_loop_pr = {
        "number": 33, "headRefName": "claude/issue-33", "isDraft": False,
        "reviews": [
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "APPROVED"},
        ],
        "latestReviews": [{"author": {"login": REVIEWER}, "state": "APPROVED"}],
        "reviewRequests": [],
        "mergeable": "MERGEABLE",
    }
    if move.is_stalled_autonomous_pr(approved_loop_pr, REVIEWER):
        problems.append("is_stalled_autonomous_pr: approved loop PR with prior CRs should not be marked stalled")

    answered_loop_pr = {
        "number": 34, "headRefName": "claude/issue-34", "isDraft": False,
        "headRefOid": "new-head-oid",
        "reviews": [
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED", "commit": {"oid": "old-oid-1"}},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED", "commit": {"oid": "old-oid-2"}},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED", "commit": {"oid": "old-oid-3"}},
        ],
        "latestReviews": [],
        "reviewRequests": [{"login": REVIEWER}],
        "mergeable": "MERGEABLE",
    }
    if move.is_stalled_autonomous_pr(answered_loop_pr, REVIEWER):
        problems.append("is_stalled_autonomous_pr: answered loop PR with new head commit should not be marked stalled")

    re_requested_pr = {
        "number": 37, "headRefName": "gemini/issue-37", "baseRefName": "main", "isDraft": False,
        "latestReviews": APPROVED, "reviews": APPROVED, "reviewRequests": [{"login": REVIEWER}],
        "mergeable": "MERGEABLE", "statusCheckRollup": GREEN,
    }
    ok_app, reason = move.check_reviewer_approval(re_requested_pr, REVIEWER)
    if ok_app or "waiting on review" not in reason:
        problems.append(f"check_reviewer_approval: re-requested PR must not authorize approval: {reason}")

    return problems


def _check_stall_eviction_dry_run(channel: Any, move: Any) -> list[str]:
    """Stall eviction demotes to draft in real runs while leaving state untouched in dry runs (solorepo's DR-258).

    Parameters:
        channel: The mock communication channel.
        move: The move module under test.

    Returns:
        list[str]: Identified probe violations.
    """
    problems = []
    stalled_loop_pr = {
        "number": 30, "headRefName": "gemini/issue-30", "isDraft": False,
        "reviews": [
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
        ],
        "latestReviews": [], "reviewRequests": [{"login": REVIEWER}],
        "mergeable": "MERGEABLE",
    }
    demoted: list[str] = []

    def gh_evict(*args: Any, **kwargs: Any) -> Any:
        if args[:2] == ("pr", "ready") and "--undo" in args:
            demoted.append(str(args[2]))
            return {}
        if args[0] == "api" and "/comments" in str(args[-1]):
            return [{"body": f"{move.ADVANCE_NOTICE_MARKER}\nAdvance notice: branch has merge conflicts"}]
        return {}

    with stood_in(channel, gh=gh_evict, repo=lambda: "owner/repo"):
        evicted_dry = move.evict_stalled_autonomous_pr(stalled_loop_pr, reviewer_login=REVIEWER, dry_run=True)
        if not evicted_dry or demoted:
            problems.append(f"evict_stalled_autonomous_pr: dry run should not demote PR: {demoted}")

        evicted = move.evict_stalled_autonomous_pr(stalled_loop_pr, reviewer_login=REVIEWER, dry_run=False)
        if not evicted or demoted != ["30"]:
            problems.append(f"evict_stalled_autonomous_pr: expected PR 30 demoted, got: {demoted}")

        conflicting_loop_pr = {
            "number": 32, "headRefName": "gemini/issue-32", "isDraft": False,
            "mergeable": "CONFLICTING",
        }
        if not move.is_stalled_autonomous_pr(conflicting_loop_pr, REVIEWER):
            problems.append("is_stalled_autonomous_pr: conflicting loop PR with advance notice should stall")

    return problems


def _check_draft_restoration(channel: Any, move: Any) -> list[str]:
    """Draft loop pull requests are restored to ready when approved and green (solorepo's DR-258).

    Parameters:
        channel: The mock communication channel.
        move: The move module under test.

    Returns:
        list[str]: Identified probe violations.
    """
    problems = []
    restored: list[str] = []

    def gh_restore(*args: Any, **kwargs: Any) -> Any:
        if args[:2] == ("pr", "ready") and "--undo" not in args:
            restored.append(str(args[2]))
            return {}
        return {}

    draft_loop_pr = {
        "number": 31, "headRefName": "gemini/issue-31", "isDraft": True,
        "latestReviews": APPROVED, "statusCheckRollup": GREEN, "mergeable": "MERGEABLE",
    }
    with stood_in(channel, gh=gh_restore):
        move.evaluate_open_pulls([draft_loop_pr], reviewer_login=REVIEWER, owner="owner", name="repo", dry_run=True)
        if restored:
            problems.append(f"evaluate_open_pulls: dry run should not restore draft PR: {restored}")

        move.evaluate_open_pulls([draft_loop_pr], reviewer_login=REVIEWER, owner="owner", name="repo", dry_run=False)
        if restored != ["31"] or draft_loop_pr.get("isDraft") is not False:
            problems.append(f"evaluate_open_pulls: expected PR 31 restored to ready, got: {restored}")

    def gh_fail_restore(*args: Any, **kwargs: Any) -> Any:
        if args[:2] == ("pr", "ready") and "--undo" not in args:
            raise SystemExit(SIMULATED_NETWORK_FAILURE)
        return {}

    failing_draft_pr = {
        "number": 36, "headRefName": "gemini/issue-36", "isDraft": True,
        "latestReviews": APPROVED, "statusCheckRollup": GREEN, "mergeable": "MERGEABLE",
    }
    with stood_in(channel, gh=gh_fail_restore):
        move.evaluate_open_pulls([failing_draft_pr], reviewer_login=REVIEWER, owner="owner", name="repo", dry_run=False)
        if failing_draft_pr.get("isDraft") is not True:
            problems.append("evaluate_open_pulls: failed pr ready call must not clear isDraft in local dictionary")

    return problems


def _check_request_review_draft_restoration(channel: Any, move: Any) -> list[str]:
    """`request_review` restores loop drafts after conflict validation but leaves human drafts untouched (solorepo's DR-258).

    Parameters:
        channel: The mock communication channel.
        move: The move module under test.

    Returns:
        list[str]: Identified probe violations.
    """
    problems = []
    ready_calls: list[str] = []
    pull_data: dict[str, Any] = {}

    def gh_req(*args: Any, **kwargs: Any) -> Any:
        if args[:2] == ("pr", "view"):
            if "--json" in args and "reviewRequests" in args:
                return {"reviewRequests": [{"login": REVIEWER}]}
            return pull_data
        if args[:2] == ("pr", "ready"):
            ready_calls.append(str(args[2]))
            return {}
        if args[:2] == ("pr", "edit"):
            return {}
        return {}

    pull_data = {
        "number": 40, "headRefName": "gemini/issue-40", "baseRefName": "main",
        "state": "OPEN", "isDraft": True, "mergeable": "CONFLICTING",
    }
    with stood_in(channel, gh=gh_req, role_login=lambda r: REVIEWER):
        try:
            move.request_review(40, "reviewer")
            problems.append("request_review: expected conflicting branch to raise SystemExit")
        except SystemExit as exc:
            if "conflicts with its base" not in str(exc):
                problems.append(f"request_review: unexpected exit message: {exc}")
        if ready_calls:
            problems.append(f"request_review: undrafted conflicting branch before validation: {ready_calls}")

    ready_calls.clear()
    pull_data = {
        "number": 41, "headRefName": "session-feat", "baseRefName": "main",
        "state": "OPEN", "isDraft": True, "mergeable": "MERGEABLE",
    }
    with stood_in(channel, gh=gh_req, role_login=lambda r: REVIEWER):
        move.request_review(41, "reviewer")
        if ready_calls:
            problems.append(f"request_review: non-loop draft PR should not be undrafted: {ready_calls}")

    ready_calls.clear()
    pull_data = {
        "number": 42, "headRefName": "gemini/issue-42", "baseRefName": "main",
        "state": "OPEN", "isDraft": True, "mergeable": "MERGEABLE",
    }
    with stood_in(channel, gh=gh_req, role_login=lambda r: REVIEWER):
        move.request_review(42, "reviewer")
        if ready_calls != ["42"]:
            problems.append(f"request_review: expected loop draft PR 42 to be undrafted, got: {ready_calls}")

    return problems


def _check_stalled_pr_merge_manager_refusal(channel: Any, move: Any) -> list[str]:
    """A stalled loop PR is demoted to draft in-cycle and refused by merge_manager without merging (solorepo's DR-258).

    Parameters:
        channel: The mock communication channel.
        move: The move module under test.

    Returns:
        list[str]: Identified probe violations.
    """
    problems = []
    stalled_claude_pr = {
        "number": 35,
        "title": "stalled autonomous loop PR",
        "headRefName": "claude/issue-35",
        "baseRefName": "main",
        "headRefOid": "sha-stalled-35",
        "isDraft": False,
        "mergeable": "MERGEABLE",
        "statusCheckRollup": GREEN,
        "reviewThreads": [{"isResolved": True}],
        "reviews": [
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED", "commit": {"oid": "sha-stalled-35"}},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED", "commit": {"oid": "sha-stalled-35"}},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED", "commit": {"oid": "sha-stalled-35"}},
        ],
        "latestReviews": [],
        "reviewRequests": [],
        "body": "",
        "additions": 10,
        "deletions": 5,
    }

    demoted_calls: list[str] = []
    merged_calls: list[str] = []

    def gh_stalled(*args: Any, **kwargs: Any) -> Any:
        cmd = args[:2]
        if cmd == ("pr", "ready") and "--undo" in args:
            demoted_calls.append(str(args[2]))
        elif cmd in (("pr", "merge"), ("stack", "merge")):
            merged_calls.append(str(args[2]))
        elif cmd == ("pr", "list"):
            return [stalled_claude_pr]
        elif cmd in (("repo", "view"), ("repo",)):
            return {"nameWithOwner": "owner/repo", "deleteBranchOnMerge": True}
        elif cmd == ("pr", "view"):
            return {"number": int(args[2]), "state": "OPEN", "headRefName": "claude/issue-35"}
        elif args[0] == "api":
            return [{"filename": "lib/foo.py"}]
        return {}

    with stood_in(channel, gh=gh_stalled, repo=lambda: "owner/repo"):
        out = outcome(lambda: move.merge_manager(dry_run=False)).out
        if demoted_calls != ["35"]:
            problems.append(f"merge_manager: expected PR 35 demoted to draft on GitHub, got: {demoted_calls}")
        if stalled_claude_pr.get("isDraft") is not True:
            problems.append("merge_manager: stalled PR isDraft was not updated to True in local dictionary")
        if merged_calls:
            problems.append(f"merge_manager: stalled PR was merged despite draft demotion: {merged_calls}")
        if f"merging #{'35'}" in out:
            problems.append(f"merge_manager: log indicates attempt to merge stalled PR:\n{out}")

    return problems


def _stall_eviction(channel: Any, move: Any) -> list[str]:
    """Stalled autonomous PRs are demoted to draft, and answered green PRs restored (solorepo's DR-258).

    Parameters:
        channel: The mock communication channel.
        move: The move module under test.

    Returns:
        list[str]: Identified probe violations.
    """
    return (
        _check_stall_thresholds(move)
        + _check_stall_eviction_dry_run(channel, move)
        + _check_draft_restoration(channel, move)
        + _check_request_review_draft_restoration(channel, move)
        + _check_stalled_pr_merge_manager_refusal(channel, move)
    )

