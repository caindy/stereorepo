"""`reconcile`: one act per owed state, none under a run, none unless live (solorepo's DR-264).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import datetime
from typing import Any

from checks.collect import check
from checks.probes.harness import load_channel, stood_in
from checks.probes.loops.bench import (
    ANSWERED,
    APPROVED,
    ASKED,
    CHANGES,
    CODER,
    COMMENT,
    MINUTES,
    OWED,
    PARKED,
    PASSER_BY,
    RED,
    REFUSED,
    REPLY,
    REVIEWER,
    REVIEWER_FAILED,
    _ago,
    _Bench,
    _GitHub,
    _notice,
    _pull,
)

FAILED_MERGE = f"say: #{9} is open after the merge call"
"""What a merge manager whose candidate did not land exits with."""


@check("reconcile probes", pre=True)
def reconcile_probes() -> list[str]:
    """The reconciler's two readers and its one pass (solorepo's DR-264).

    `classify_pr`, over the two arms that turn on the threads, since
    `owed_by_pull` reads the state and not the conditions under it: a
    comment verdict with a thread owed an answer and no request standing
    reads `CHANGES_REQUESTED`, and the same verdict with nothing owed, under
    a review request, bodiless, or left by an account that is not the
    reviewer's reads `AWAITING_REVIEW` (solorepo's DR-265); an approval with
    a notice parked reads `AWAITING_PROMOTION` and one with every thread
    answered `READY_TO_MERGE`, which is the pair no act tells apart
    (solorepo's DR-159).

    `owed_by_pull`, over the classifiers' states: a conflicting branch under
    a verdict owes a rebase pass and one under nothing owes none; changes
    requested with no request owes a review pass, and so does a comment
    verdict with a thread owed an answer and no request standing, which is the
    verdict that withholds approval in prose (solorepo's DR-265); an approval
    ready to merge but behind its base owes the rebase pass where the sweep's
    own advance notice stands on it and nothing where it does not, or where
    the branch is current with a notice the sweep has yet to clear — the same
    verdict owes nothing with nothing owed on it or with a request standing,
    and a bodiless comment review, which is what GitHub records around a reply
    on a thread, is no verdict and owes nothing either; an approval with a
    thread owed an answer owes a review pass, and one with a notice parked
    or every thread answered owes nothing; a failed gate under an approval
    owes one, and under a request whose reviewer check is the one that
    failed owes the request again; a pull request failing checks while behind
    base owes a rebase pass when trunk is green, to clear inherited breakage
    from a previous broken baseline (solorepo's #985); a green pull request
    with no verdict, request, or arming owes its first request, and armed owes
    nothing; a Challenge in any state but resumable is held, the claim read as
    nobody's so that `hard` under a claim is not swallowed by `TAKEN`; not free
    owes nothing.

    `owed_by_issue`, one case per state, ten in all: unread and quiet owes the
    door again and read or within the hour does not; offered and free owes
    the take, and blocked, under a run, or too soon does not; claimed past
    the longest run owes the release and within it does not; the rest owe
    nothing.

    `breaking`, over the title that says which break a heal Challenge stands
    for: the Challenge naming this commit is found and one naming another is
    not, and a green trunk looks for none.

    `owed_by_trunk`, over a green trunk and each state its heal Challenge can
    stand in: green owes nothing; a break no Challenge stands for owes the
    filing, with a title and a body `file_issue` takes; one offered to the loop
    owes the take pass, and one a run, a claim or a pull request stands on owes
    nothing; one read at `hard` or handed back already is held; and one filed
    longer ago than a coder run lasts owes the escalation, which names the red
    commit, where within that bound the loop is still answering it.

    `reconcile`, against a GitHub answered from a dict with timestamps read
    off the clock: the merge manager runs first and its exit is held to the
    end; one act is performed per owed state and none where a run is in
    flight; a Challenge whose pull request is in draft is counted as having
    one and not re-taken; a blocked one is not taken; a Challenge a triage
    run read is not re-delivered; without `--live` every act is reported and
    none performed; a conflict the listing answers `UNKNOWN` for is settled
    before it is read and owes the rebase pass, not the review pass; a
    comment verdict and an approval are each read against the threads the
    listing cannot carry, so one with a thread owed an answer is dispatched
    a review pass and one with every thread answered or a notice parked is
    owed nothing, the read made for those pull requests and no others — a
    conflicting branch and a failed gate are settled before the threads are
    reached — and a read GitHub refuses owes nothing and says so; runs
    GitHub will not list hold every act and say so; and a refused act is
    printed and the next is performed.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    return (_classifier_cases(move) + _pull_cases(move) + _issue_cases(move)
            + _breaking_cases(move) + _trunk_cases(move) + _pass_cases(channel, move))



def _classifier_cases(move: Any) -> list[str]:
    """`classify_pr` over the two arms that turn on the threads, one condition per case.

    `owed_by_pull` cannot pin these: it answers `None` for a pull request under
    a review request whatever state it was handed, and `None` for
    `AWAITING_PROMOTION` and `READY_TO_MERGE` alike, so a case reading the act
    alone stays green with a condition deleted. Each shape here removes one
    condition of an arm and asserts the state the classifier every reader asks
    reports for it (solorepo's DR-265, solorepo's DR-159).
    """
    states = move.check_pr.PullRequestState
    cases: list[tuple[str, dict[str, Any], Any]] = [
        ("a comment verdict with a thread owed", _pull(1, latestReviews=COMMENT,
                                                       reviewThreads=OWED),
         states.CHANGES_REQUESTED),
        ("a comment verdict with nothing owed", _pull(1, latestReviews=COMMENT),
         states.AWAITING_REVIEW),
        ("a comment verdict under a review request", _pull(1, latestReviews=COMMENT,
                                                           reviewThreads=OWED,
                                                           reviewRequests=ASKED),
         states.AWAITING_REVIEW),
        ("a reply on a thread, which is no verdict", _pull(1, latestReviews=REPLY,
                                                           reviewThreads=OWED),
         states.AWAITING_REVIEW),
        ("a comment verdict from a passer-by", _pull(1, latestReviews=PASSER_BY,
                                                     reviewThreads=OWED),
         states.AWAITING_REVIEW),
        ("an approval with a notice parked", _pull(1, latestReviews=APPROVED,
                                                   reviewThreads=PARKED),
         states.AWAITING_PROMOTION),
        ("an approval with every thread answered", _pull(1, latestReviews=APPROVED,
                                                         reviewThreads=ANSWERED),
         states.READY_TO_MERGE),
    ]
    problems = []
    for name, pull, expected in cases:
        found = move.check_pr.classify_pr(pull, move.deduplicate_checks(pull["statusCheckRollup"]),
                                          None, REVIEWER)
        if found is not expected:
            problems.append(f"classify_pr: {name} read {found!r}, not {expected!r}")
    return problems


def _pull_cases(move: Any) -> list[str]:
    """`owed_by_pull` over each shape the classifiers name, a held Challenge, and not free."""
    issues = move.check_pr.state.IssueState
    notice = _notice(move, 1)
    untagged = _notice(move, 1, tagged=False)
    cases: list[tuple[str, dict[str, Any], Any, bool, str | None]] = [
        ("conflicting under a verdict", _pull(1, mergeable="CONFLICTING", latestReviews=CHANGES),
         issues.RESUMABLE, True, "rebase"),
        ("conflicting under nothing", _pull(1, mergeable="CONFLICTING"), issues.RESUMABLE, True,
         "rebase"),
        ("changes requested, unanswered", _pull(1, latestReviews=CHANGES), issues.RESUMABLE,
         True, "review"),
        ("changes requested, review requested", _pull(1, latestReviews=CHANGES,
                                                       reviewRequests=ASKED),
         issues.RESUMABLE, True, None),
        ("comment verdict with a thread owed", _pull(1, latestReviews=COMMENT,
                                                     reviewThreads=OWED),
         issues.RESUMABLE, True, "review"),
        ("comment verdict with nothing owed", _pull(1, latestReviews=COMMENT),
         issues.RESUMABLE, True, None),
        ("comment verdict under a review request",
         _pull(1, latestReviews=COMMENT, reviewThreads=OWED, reviewRequests=ASKED),
         issues.RESUMABLE, True, None),
        ("a reply on a thread, which is no verdict",
         _pull(1, latestReviews=REPLY, reviewThreads=OWED), issues.RESUMABLE, True, None),
        ("approved with a thread owed", _pull(1, latestReviews=APPROVED, reviewThreads=OWED),
         issues.RESUMABLE, True, "review"),
        ("approved with a notice parked", _pull(1, latestReviews=APPROVED, reviewThreads=PARKED),
         issues.RESUMABLE, True, "request"),
        ("approved with a notice parked under a review request",
         _pull(1, latestReviews=APPROVED, reviewThreads=PARKED, reviewRequests=ASKED),
         issues.RESUMABLE, True, None),
        ("approved with every thread answered",
         _pull(1, latestReviews=APPROVED, reviewThreads=ANSWERED), issues.RESUMABLE, True, None),
        ("approved and behind with a replay refused on this head",
         _pull(1, latestReviews=APPROVED, reviewThreads=ANSWERED,
               mergeStateStatus="BEHIND", comments=notice),
         issues.RESUMABLE, True, "rebase"),
        ("approved and behind with no finding, which is the sweep's to bring current",
         _pull(1, latestReviews=APPROVED, reviewThreads=ANSWERED, mergeStateStatus="BEHIND"),
         issues.RESUMABLE, True, None),
        ("approved and behind under a finding that is not a refused replay",
         _pull(1, latestReviews=APPROVED, reviewThreads=ANSWERED,
               mergeStateStatus="BEHIND", comments=untagged), issues.RESUMABLE, True, None),
        ("approved and behind under a finding against a head it no longer has",
         _pull(1, latestReviews=APPROVED, reviewThreads=ANSWERED,
               mergeStateStatus="BEHIND", comments=_notice(move, 99)),
         issues.RESUMABLE, True, None),
        ("approved and current with a finding the sweep has not cleared",
         _pull(1, latestReviews=APPROVED, reviewThreads=ANSWERED,
               mergeStateStatus="CLEAN", comments=notice),
         issues.RESUMABLE, True, None),
        ("approved with failing checks", _pull(1, latestReviews=APPROVED, statusCheckRollup=RED),
         issues.RESUMABLE, True, "review"),
        ("requested, reviewer check failed", _pull(1, reviewRequests=ASKED,
                                                    statusCheckRollup=REVIEWER_FAILED),
         issues.RESUMABLE, True, "request"),
        ("requested, checks pending", _pull(1, reviewRequests=ASKED,
                                             statusCheckRollup=[{"name": "gate",
                                                                 "status": "IN_PROGRESS"}]),
         issues.RESUMABLE, True, None),
        ("green and nobody holds it", _pull(1), issues.RESUMABLE, True, "request"),
        ("green and armed", _pull(1, autoMergeRequest={"enabledAt": "x"}), issues.RESUMABLE,
         True, None),
        ("held", _pull(1), issues.HELD, True, "hold"),
        ("held and not free", _pull(1), issues.HELD, False, "hold"),
        ("approved and conflicting with challenge handed back",
         _pull(1, mergeable="CONFLICTING", latestReviews=APPROVED),
         issues.HANDED_BACK, True, "rebase"),
        ("approved and behind with refused replay with challenge handed back",
         _pull(1, latestReviews=APPROVED, reviewThreads=ANSWERED,
               mergeStateStatus="BEHIND", comments=notice),
         issues.HANDED_BACK, True, "rebase"),
        ("approved with thread owed and challenge handed back",
         _pull(1, latestReviews=APPROVED, reviewThreads=OWED),
         issues.HANDED_BACK, True, "hold"),
        ("conflicting under nothing with challenge handed back",
         _pull(1, mergeable="CONFLICTING"),
         issues.HANDED_BACK, True, "hold"),
        ("read as the coder's, which a claim at hard would be", _pull(1), issues.TAKEN, True,
         "hold"),
        ("unread", _pull(1), issues.UNREAD, True, "hold"),
        ("failing checks while behind green trunk",
         _pull(1, statusCheckRollup=RED, mergeStateStatus="BEHIND"),
         issues.RESUMABLE, move.Constraints(free=True, trunk_green=True), "rebase"),
        ("failing checks while behind red trunk",
         _pull(1, statusCheckRollup=RED, mergeStateStatus="BEHIND"),
         issues.RESUMABLE, move.Constraints(free=True, trunk_green=False), None),
        ("failing checks while current on green trunk",
         _pull(1, statusCheckRollup=RED, mergeStateStatus="CLEAN"),
         issues.RESUMABLE, move.Constraints(free=True, trunk_green=True), None),
        ("approved with failing checks while behind green trunk",
         _pull(1, latestReviews=APPROVED, statusCheckRollup=RED, mergeStateStatus="BEHIND"),
         issues.RESUMABLE, move.Constraints(free=True, trunk_green=True), "rebase"),
        ("failing checks while behind green trunk in stack above conflicting layer",
         _pull(2, baseRefName="claude/issue-1", statusCheckRollup=RED, mergeStateStatus="BEHIND"),
         issues.RESUMABLE,
         move.Constraints(free=True, trunk_green=True,
                          pulls=[_pull(1, mergeable="CONFLICTING"),
                                 _pull(2, baseRefName="claude/issue-1", statusCheckRollup=RED,
                                       mergeStateStatus="BEHIND")]),
         "hold"),
        ("failing checks while behind green trunk not free",
         _pull(1, statusCheckRollup=RED, mergeStateStatus="BEHIND"),
         issues.RESUMABLE, move.Constraints(free=False, trunk_green=True), None),
        ("no open Challenge", _pull(1), None, True, None),
        ("not free", _pull(1, latestReviews=CHANGES), issues.RESUMABLE, False, None),
    ]
    problems = []
    for name, pull, found, free, expected in cases:
        state = move.check_pr.classify_pr(pull, move.deduplicate_checks(pull["statusCheckRollup"]),
                                          None, REVIEWER)
        act = move.owed_by_pull(pull, found, state, REVIEWER, free)
        kind = act.kind if act else None
        if kind != expected:
            problems.append(f"owed_by_pull: {name} owed {kind!r}, not {expected!r}")
    return problems


TRUNK = {"branch": "main", "commit": "abc1234", "checks": "gate", "longest": 75.0}
"""A red trunk as `Break` carries one, over which each case names what stands beside it."""


def _trunk_cases(move: Any) -> list[str]:
    """`owed_by_trunk` over a green trunk and each state the heal Challenge can stand in.

    The bound is `longest`, the coder workflow's job timeout, read against the
    time since the Challenge was filed: within it the loop is still answering
    the break, past it the loop was offered it and opened nothing. Both arms
    stand on `OFFERED`, so an unread Challenge past the bound owes nothing here
    however long it has stood — a level never landed, so no loop was offered
    anything, and the re-delivery that wakes the reviewer's door is
    `owed_by_issue`'s.
    """
    states = move.check_pr.state.IssueState
    standing = {**TRUNK, "challenge": 50, "idle": 10.0}
    cases: list[tuple[str, dict[str, Any], str | None]] = [
        ("green", {**TRUNK, "checks": ""}, None),
        ("red with no Challenge for the commit", TRUNK, "file"),
        ("offered, and within the longest run", {**standing, "found": states.OFFERED}, "take"),
        ("offered under a coder run", {**standing, "found": states.OFFERED, "busy": True}, None),
        ("its pull request open", {**standing, "found": states.RESUMABLE}, None),
        ("claimed", {**standing, "found": states.CLAIMED}, None),
        ("taken", {**standing, "found": states.TAKEN}, None),
        ("read at hard", {**standing, "found": states.HELD}, "hold"),
        ("handed back already", {**standing, "found": states.HANDED_BACK}, "hold"),
        ("unread within the longest run", {**standing, "found": states.UNREAD}, None),
        ("unread past the longest run, which is the reviewer's door and not an escalation",
         {**standing, "found": states.UNREAD, "idle": 600.0}, None),
        ("offered past the longest run", {**standing, "found": states.OFFERED, "idle": 600.0},
         "escalate"),
        ("past the longest run under a coder run",
         {**standing, "found": states.OFFERED, "idle": 600.0, "busy": True}, None),
    ]
    problems = []
    for name, fields, expected in cases:
        act = move.owed_by_trunk(move.Break(**fields))
        kind = act.kind if act else None
        if kind != expected:
            problems.append(f"owed_by_trunk: {name} owed {kind!r}, not {expected!r}")
        if kind == "file" and (not act.title or not act.body.startswith("**Waits on.**")):
            problems.append(f"owed_by_trunk: the heal Challenge would be filed as {act.title!r} "
                            f"with a body opening {act.body[:20]!r}, where `file_issue` takes a "
                            "title and a body opening on `**Waits on.**`")
        if kind == "escalate" and TRUNK["commit"] not in act.body:
            problems.append(f"owed_by_trunk: the escalation says {act.body!r}, where what the "
                            "solo is handed names the commit that is red")
    return problems


def _reading(move: Any) -> Any:
    """A pass's shared reading with nothing standing in it, for the readers that take one."""
    empty = move.Runs([], [])
    return move.Reading(now=datetime.datetime.now(datetime.UTC), bound=MINUTES, longest=75.0,
                        coder=CODER, reviewer_login=REVIEWER, owner="o", name="r",
                        by_number={}, named=set(), coder_runs=empty, review_runs=empty,
                        triage_runs=empty)


def _trunk(move: Any, failing: list[str], oid: str = "abc1234def") -> Any:
    """Trunk's HEAD rollup as `report_trunk` answers with one, red where `failing` names a check."""
    return move.cli.reconcile.actions.Trunk(
        ref="main", oid=oid, headline="the commit that landed",
        checks=[{"name": name} for name in failing], failing=failing, pending=False)


def _breaking_cases(move: Any) -> list[str]:
    """`breaking`: one heal Challenge per broken commit, found by the title naming it."""
    reading = _reading(move)
    issues = [{"number": 50,
               "title": move.HEAL_TITLE.format(branch="main", commit=TRUNK["commit"]),
               "labels": [{"name": "challenge"}, {"name": "medium"}], "assignees": [],
               "createdAt": _ago(10)}]
    problems = []
    found = move.breaking(_trunk(move, ["gate", "python seed"]), issues, reading)
    if found.challenge != 50 or found.checks != "gate, python seed" \
            or found.found is not move.check_pr.state.IssueState.OFFERED:
        problems.append(f"breaking: a break a Challenge already stands for read {found}, where "
                        "the Challenge whose title names the commit is the one standing for it "
                        "and both failing checks are named")
    again = move.breaking(_trunk(move, ["gate"], oid="def5678abcdef"), issues, reading)
    if again.challenge is not None:
        problems.append(f"breaking: a second break read #{again.challenge} as its Challenge, "
                        "where a title naming another commit stands for another break")
    green = move.breaking(_trunk(move, []), issues, reading)
    if green.checks or green.challenge is not None:
        problems.append(f"breaking: a green trunk read {green}, where nothing failed and no "
                        "Challenge is looked for")
    return problems


def _issue_cases(move: Any) -> list[str]:
    """`owed_by_issue` over all ten states, each bound within and past, blocked, and under a run."""
    states = move.check_pr.state.IssueState
    quiet = move.Quiet(True, True, True, False, 600.0)
    cases: list[tuple[str, Any, Any, str | None]] = [
        ("unread and quiet", states.UNREAD, quiet, "reread"),
        ("unread, read or within the hour", states.UNREAD,
         move.Quiet(True, False, True, False, 600.0), None),
        ("offered and free", states.OFFERED, quiet, "take"),
        ("offered under a run, or too soon", states.OFFERED,
         move.Quiet(False, True, True, False, 5.0), None),
        ("offered and blocked", states.OFFERED, move.Quiet(True, True, True, True, 600.0), None),
        ("claimed past the longest run", states.CLAIMED, quiet, "release"),
        ("claimed within the longest run", states.CLAIMED,
         move.Quiet(True, True, False, False, 40.0), None),
        ("held", states.HELD, quiet, None),
        ("handed back", states.HANDED_BACK, quiet, None),
        ("taken", states.TAKEN, quiet, None),
        ("resumable", states.RESUMABLE, quiet, None),
        ("roadmap", states.ROADMAP, quiet, None),
        ("unlabelled", states.UNLABELLED, quiet, None),
        ("closed", states.CLOSED, quiet, None),
    ]
    problems = []
    for name, found, when, expected in cases:
        act = move.owed_by_issue({"number": 5}, found, when)
        kind = act.kind if act else None
        if kind != expected:
            problems.append(f"owed_by_issue: {name} owed {kind!r}, not {expected!r}")
    return problems


def _check_reconcile_draft_demotions(fake: _GitHub) -> list[str]:
    """Verify that conflicting PRs were demoted to draft while maintenance rebases were not."""
    problems: list[str] = []
    p2 = next(p for p in fake.pulls if p["number"] == 2)
    p29 = next(p for p in fake.pulls if p["number"] == 29)
    p30 = next(p for p in fake.pulls if p["number"] == 30)
    if not p2.get("isDraft"):
        problems.append("reconcile: conflicting pull request 2 was not demoted to draft "
                        "before rebase dispatch")
    if not p29.get("isDraft"):
        problems.append("reconcile: approved pull request 29 with failing checks "
                        "was not demoted to draft before review dispatch")
    if p30.get("isDraft"):
        problems.append("reconcile: non-conflict maintenance rebase pull request 30 "
                        "was demoted to draft")
    return problems


def _pass_cases(channel: Any, move: Any) -> list[str]:
    """`reconcile` end to end: each act once live, reported otherwise, none under a run."""
    bench = _Bench(channel, move)
    problems = _edge_cases(bench)
    fake = _GitHub(bench.pulls, bench.issues, {})
    ended = bench.run(fake, live=True)
    expected = {("merge_manager", None), ("review", 1), ("rebase", 2), ("request", 3),
                ("relabel", (4, ("remove",))), ("relabel", (4, ("add",))), ("release", 6),
                ("rebase", 13), ("rebase", 15), ("rebase", 17), ("review", 24), ("review", 26),
                ("request", 28), ("review", 29), ("rebase", 30)}
    acted = bench.acted
    if ended.code is not None or set(acted) != expected or len(acted) != len(expected):
        problems.append(f"reconcile: live over the fixtures performed {acted} with exit "
                        f"{ended.code!r}, not one act per owed state {sorted(expected)}: the "
                        "root of a conflicting stack, a conflicting branch nobody holds, and a "
                        "layer whose root is clean are each owed a rebase, the layer above "
                        "a conflicting root none, a comment verdict and an approval each with "
                        "a thread owed an answer a review pass, where one with every thread "
                        "answered owes nothing, an approval with a notice parked owes a "
                        "request pass, an approval with a failed gate the review pass its checks "
                        "owe, and an approval behind its base with a replay refused on its head "
                        "the rebase pass, where the layer of that shape above a conflicting root "
                        "is held")
    if sorted(fake.queried) != [24, 25, 26, 27, 28, 30, 31]:
        problems.append(f"reconcile: the threads read were those of {sorted(fake.queried)}, "
                        "where the listing carries none and the read is owed to the pull "
                        "requests standing with no request under a comment verdict or an "
                        "approval, and to no other: a conflicting branch and a failed gate "
                        "are settled before the threads are reached")
    problems.extend(_check_reconcile_draft_demotions(fake))
    if f"holding #{12}" not in ended.out:
        problems.append(f"reconcile: a claimed Challenge at hard behind an open pull request was "
                        f"not held: {ended.out!r}")
    if f"holding #{14}" not in ended.out or "is rebased first" not in ended.out:
        problems.append(f"reconcile: the layer above a conflicting root was not held saying "
                        f"why: {ended.out!r}")
    if f"holding #{19}" not in ended.out or "in draft" not in ended.out \
            or "solo's to resolve" not in ended.out:
        problems.append(f"reconcile: the layer above a conflicting draft was not held naming "
                        f"the solo as the mover: {ended.out!r}")
    if f"holding #{21}" not in ended.out or "not the loop's branch" not in ended.out:
        problems.append(f"reconcile: the layer above a conflicting root on the solo's own "
                        f"branch was not held naming the solo as the mover: {ended.out!r}")
    if f"holding #{23}" not in ended.out or "its Challenge reads" not in ended.out:
        problems.append(f"reconcile: the layer above a conflicting root whose Challenge is "
                        f"claimed at hard was not held naming the solo as the mover: "
                        f"{ended.out!r}")
    taken = sorted(a[a.index("-f") + 1] for a in fake.dispatched)
    if taken != ["issue=11", "issue=5"]:
        problems.append(f"reconcile: the takes dispatched were {taken}, where the offered "
                        "Challenge and the one that never moved are owed one each, and the "
                        "blocked one and the one behind a draft none")

    ended = bench.run(fake, live=False)
    if ended.code is not None or acted != [("merge_manager", None)] or fake.dispatched:
        problems.append(f"reconcile: not live performed {acted} and dispatched "
                        f"{fake.dispatched}, where every act should have been reported")
    if f"would dispatch a review pass for #{1}" not in ended.out:
        problems.append(f"reconcile: not live did not say what it would do: {ended.out!r}")

    busy = {"coder.yml": [{"displayTitle": f"coder-issue-#{1}", "status": "in_progress",
                           "headBranch": "claude/issue-1"},
                          {"displayTitle": f"coder-issue-#{5}", "status": "queued",
                           "headBranch": "main"}],
            "review.yml": [{"displayTitle": "review", "status": "in_progress",
                            "headBranch": "claude/issue-3"}],
            "triage.yml": [{"displayTitle": f"triage-issue-#{4}", "status": "completed",
                            "conclusion": "success", "headBranch": "main"}]}
    ended = bench.run(_GitHub(bench.pulls, bench.issues, busy), live=True)
    left = {a for a in acted if a[0] != "merge_manager"}
    if left != {("rebase", 2), ("release", 6), ("rebase", 13), ("rebase", 15), ("rebase", 17),
                ("review", 24), ("review", 26), ("request", 28), ("review", 29), ("rebase", 30)}:
        problems.append(f"reconcile: with runs in flight, and a triage run that read, it "
                        f"performed {sorted(left)}, where only the rebases of the branches "
                        "no run answers, the release, the request pass for the parked notice, "
                        "and the review passes for the comment verdict, the approval with a "
                        "thread owed, and the approval with a failed gate were owed")
    return problems


def _refusing(pr: Any, task: str) -> None:
    """A dispatch GitHub refuses, in the words the channel exits with."""
    raise SystemExit(REFUSED)


def _failing(**_: Any) -> None:
    """A merge manager whose candidate failed to land."""
    raise SystemExit(FAILED_MERGE)


def _edge_cases(bench: _Bench) -> list[str]:
    """An `UNKNOWN` off the listing, unlistable runs, a refused dispatch, a failed merge,
    and a green trunk re-dispatching stranded pull requests.
    """
    problems = []
    unknown = _pull(7, mergeable="UNKNOWN", latestReviews=CHANGES)
    settling = _GitHub([unknown], [], {}, views={7: {**unknown, "mergeable": "CONFLICTING"}})
    with stood_in(bench.channel, MERGEABILITY=(2, 0)):
        bench.run(settling, live=True)
    if ("rebase", 7) not in bench.acted or ("review", 7) in bench.acted:
        problems.append(f"reconcile: a conflict the listing answered UNKNOWN for was owed "
                        f"{[a for a in bench.acted if a[1] == 7]}, not the rebase pass the "
                        "settled read shows")

    root = _pull(7, mergeable="UNKNOWN")
    layer = _pull(9, baseRefName="claude/issue-7", mergeable="CONFLICTING", latestReviews=APPROVED)
    with stood_in(bench.channel, MERGEABILITY=(2, 0)):
        ended = bench.run(_GitHub([root, layer], [], {}), live=True)
    if ("rebase", 9) not in bench.acted or f"holding #{9}" in ended.out:
        problems.append(f"reconcile: a layer above a root still UNKNOWN when the bound ran out "
                        f"was owed {[a for a in bench.acted if a[1] == 9]}, where only a "
                        "conflict below holds it and the next pass reads the root settled")

    talking = _pull(40, latestReviews=COMMENT, reviews=COMMENT)
    unreadable = _GitHub([talking], [], {}, threads={40: OWED})
    unreadable.unreadable = True
    ended = bench.run(unreadable, live=True)
    left = [a for a in bench.acted if a[0] != "merge_manager"]
    if left or "could not be read" not in ended.out:
        problems.append(f"reconcile: a comment verdict whose threads GitHub would not read was "
                        f"owed {left} and said {ended.out!r}, where nothing is owed on a read "
                        "that failed and the log says it failed")

    green_trunk = _trunk(bench.move, [])
    stranded = _pull(45, statusCheckRollup=RED, mergeStateStatus="BEHIND")
    dry_pass = bench.run(_GitHub([stranded], [bench.issue(45, "medium")], {}),
                         {"report_trunk": lambda *_: green_trunk}, live=False)
    if ("rebase", 45) in [a for a in bench.acted if a[0] != "merge_manager"] \
            or f"would dispatch a rebase pass for #{45}" not in dry_pass.out:
        problems.append(f"reconcile: not live did not report rebase for stranded PR: "
                        f"{dry_pass.out!r}")

    bench.run(_GitHub([stranded], [bench.issue(45, "medium")], {}),
              {"report_trunk": lambda *_: green_trunk}, live=True)
    if ("rebase", 45) not in bench.acted:
        problems.append(f"reconcile: a stranded pull request behind green trunk was not rebased: "
                        f"{bench.acted}")

    unlistable = _GitHub(bench.pulls, bench.issues, {})
    unlistable.unlistable = True
    ended = bench.run(unlistable, live=True)
    held = [a for a in bench.acted if a[0] != "merge_manager"]
    if held or unlistable.dispatched or "could not be listed" not in ended.out:
        problems.append(f"reconcile: with runs GitHub would not list it performed {held} and "
                        f"dispatched {unlistable.dispatched}, and said {ended.out!r}, where "
                        "every act is held and the log says why")

    got = bench.run(_GitHub(bench.pulls, bench.issues, {}), {"run_coder": _refusing}, live=True)
    if got.code is not None or ("request", 3) not in bench.acted or "not dispatch" not in got.out:
        problems.append(f"reconcile: a refused dispatch ended the pass with {got.code!r} and "
                        f"{bench.acted}, where the refusal is printed and the next act performed")

    ended = bench.run(_GitHub(bench.pulls, bench.issues, {}), {"merge_manager": _failing},
                      live=True)
    if ended.code != FAILED_MERGE or ("review", 1) not in bench.acted:
        problems.append(f"reconcile: a failed merge ended with {ended.code!r} after "
                        f"{bench.acted}, where the reading goes on and the merge's code is "
                        "the exit")
    return problems
