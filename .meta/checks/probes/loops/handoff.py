"""`request-review`, `--watch` and the `unheld` sweep over the shapes a webhook should have carried (solorepo's DR-178).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import datetime
import subprocess
import sys
import types
from typing import Any

from checks import citations
from checks.collect import check
from checks.probes.harness import (
    FakeGitHub,
    WatchGitHub,
    load_channel,
    outcome,
    run_verb,
    stood_in,
    unanswered,
)

HUNG_LOGIN = "gh: `gh repo view` answered nothing within 60s"
"""What a hung login read raises, so the probe verifies the circuit breaker on login hangs."""


@check("handoff probes", pre=True)
def handoff_probes() -> list[str]:
    """`request-review` on a branch GitHub reports as `CONFLICTING`, `--watch` on one that becomes it, and the `unheld` sweep over the shapes a webhook should have carried.

    The two readings of solorepo's #195: a request made on a conflicting
    branch is held by GitHub and answered by nobody, since there is no merge
    ref and so `review.yml`'s `pull_request` trigger creates no run, and
    neither the verb nor the watch said so, which is why solorepo's #192 stood
    unreviewed. Both halves are a state GitHub reports and a sentence about
    it, so both are probed by standing GitHub in, as `probes/loops/advance.py`
    does: the state costs a merge on trunk to reach for real and is gone by the
    time anyone could look. `MERGEABILITY` is shortened to nothing first: what
    the cases hold is that the verb waits out an `UNKNOWN`, and the seconds it
    waits are GitHub's business.

    `request-review`: a conflicting branch is refused, nobody is requested,
    and the refusal names the branch and the base it is to be rebased onto,
    which is the pull request's own so that a layer is not sent to trunk; a
    branch GitHub can merge is requested and the read-back agrees; and
    `UNKNOWN`, which is GitHub still computing after the push the request
    follows, is waited out rather than refused on timing. Then the request
    already standing, eleven cases of it, since asking again is what fires
    `review_requested` and the run it starts is a second one on a head a run
    already stands on (solorepo's #950): a run on this head in progress and a
    run on this head queued, both left alone; a run on this head that finished
    with the Role's verdict at that head, left alone; and eight stale requests
    asked again — the run at this head finished without a verdict, the only run
    in flight is on the head the push moved off, no run is listed at all, the
    verdict at this head is another login's while the Role's names an older
    head, the Role's review at this head is the bodiless wrapper GitHub keeps
    around a raise, the Role's verdict at this head was dismissed, and the two
    listings the guard rests on refused one at a time, each seeded under the
    state that would otherwise withhold the handoff, so that a guard reading an
    unreadable listing as an answer reports.

    `--watch`, answered one poll at a time: a branch that goes conflicting
    under a standing request says so once, because the push that invalidated
    the answer reports `UNKNOWN` and then the value it already had, and
    neither is a change to the branch; one already conflicting when the watch
    starts is in the heading, since there is no change to report on a state
    that was true before the first poll, which is the shape solorepo's #192
    arrived in; and one begun while GitHub is still computing has no state in
    its heading, so the first answer is the first thing said about the
    branch, which is the ordinary case, because a request follows a push and
    a push sets `mergeable` computing.

    `unheld`, over one pull request at a time, each qualified by thirty
    minutes of silence so that a pass still running is not mistaken for one
    that stopped: an armed pull request holding an unresolved conversation,
    which auto-merge will not merge and no Job is standing to resolve
    (solorepo's DR-159), reported once idle and passed in silence while
    recent; an approved one on a conflicting branch; an unanswered request
    for changes on an idle loop branch; a green unreviewed one whose Challenge
    is at `human` or at `hard`, on a branch that merges and on one that
    conflicts, where the remedy is the rebase; an approved one with failing
    checks at `medium`, which the loop owns, and at `hard`, which the solo
    does; a review requested of the reviewer whose check failed without a
    verdict; an approved conflicting one at `hard`, where the loop stands
    down (solorepo's DR-167, solorepo's DR-178, solorepo's #316); and a
    reviewer's top-level comment nobody has answered, on a plan-only draft,
    which no other remedy reaches on silence alone, and on a loop branch, where
    the dispatch is named beside the answer (solorepo's DR-273). The Challenge's labels are
    answered by standing `check_pr.gh` in with the level each case names.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    channel.MERGEABILITY = (3, 0)
    check_pr = citations.load_check_pr()
    return (_request_review_cases(channel, move) + _watch_cases(check_pr)
            + _watch_failure_cases(check_pr) + _watch_recovery_cases(check_pr)
            + _unheld_armed_cases(check_pr) + _unheld_idle_cases(check_pr)
            + _unheld_comment_cases(check_pr))


def _pull_of(number: Any, title: Any, **fields: Any) -> dict[str, Any]:
    """A pull request on the loop's branch for `number`, based on trunk, not a draft, with no review requested, and `fields` over that."""
    return {"number": number, "title": title, "headRefName": f"claude/issue-{number}",
            "baseRefName": "main", "isDraft": False, "reviewRequests": [], **fields}


def _request_review_cases(channel: Any, move: Any) -> list[str]:
    """`request-review` refused on a conflicting branch, made on a mergeable one, made after waiting out `UNKNOWN`, and weighed against a request already standing."""
    problems = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "base": "claude/issue-6",
                           "mergeable": "CONFLICTING"}})
    said = run_verb(channel, fake, lambda: move.request_review("7", "reviewer"))
    if fake.pulls["7"].get("requested"):
        problems.append(f"request-review: a conflicting branch was requested of "
                        f"{fake.pulls['7']['requested']!r}, and no review can run on it")
    if not said or "claude/issue-6" not in said or "claude/issue-7" not in said or "no merge ref" not in said:
        problems.append(f"request-review: the refusal on a conflicting branch was {said!r}, "
                        "which does not name the rebase that lifts it")

    fake = FakeGitHub({8: {"behind": 0, "armed": False}})
    said = run_verb(channel, fake, lambda: move.request_review("8", "reviewer"))
    if fake.pulls["8"].get("requested") != ["o-r-reviewer"]:
        problems.append(f"request-review: a mergeable branch left GitHub holding "
                        f"{fake.pulls['8'].get('requested')!r}")
    if said:
        problems.append(f"request-review: the handoff it should have made exited with {said!r}")

    fake = FakeGitHub({9: {"behind": 0, "armed": False, "unknown": 2}})
    said = run_verb(channel, fake, lambda: move.request_review("9", "reviewer"))
    if fake.pulls["9"].get("requested") != ["o-r-reviewer"]:
        problems.append("request-review: it took the first `UNKNOWN` for an answer and left "
                        f"GitHub holding {fake.pulls['9'].get('requested')!r}")
    if said:
        problems.append(f"request-review: waiting out an `UNKNOWN` exited with {said!r}")

    return problems + _pending_request_cases(channel, move)


PENDING = ["o-r-reviewer"]
"""A review already requested of the reviewer: the state a re-request meets (solorepo's #950)."""


def _pending_request_cases(channel: Any, move: Any) -> list[str]:
    """A pending request a run on this head answers is left alone; a stale one is asked again.

    A case's `unreadable` is lifted out of the seed and onto the fake's store,
    where it marks the one call GitHub refuses rather than answers from the
    first read, so the two listings the guard rests on can be taken away one at
    a time from under a state that would otherwise withhold the handoff.
    """
    problems = []
    for number, pull, asked, why in (
            (10, {"runs": [("head10", "in_progress")]}, False,
             "a run on this head was already in progress"),
            (11, {"runs": [("head11", "queued")]}, False,
             "a run on this head was already queued"),
            (12, {"runs": [("head12", "completed")],
                  "reviewed": [("o-r-reviewer", "head12")]}, False,
             "the reviewer's verdict on this head already stands"),
            (13, {"runs": [("head13", "completed")]}, True,
             "the run on this head finished without a verdict"),
            (14, {"runs": [("older", "in_progress")]}, True,
             "the only run in flight is on a head the push moved off"),
            (15, {}, True, "no run has been listed on this head at all"),
            (16, {"runs": [("head16", "completed")],
                  "reviewed": [("o-r-solo", "head16"), ("o-r-reviewer", "older")]}, True,
             "the verdict at this head is another login's and the reviewer's names an older head"),
            (17, {"runs": [("head17", "completed")],
                  "reviewed": [("o-r-reviewer", "head17", "COMMENTED", "")]}, True,
             "the run raised a thread on this head and died before its verdict"),
            (18, {"runs": [("head18", "completed")],
                  "reviewed": [("o-r-reviewer", "head18", "DISMISSED", "asked for changes")]}, True,
             "the verdict at this head was dismissed to summon a fresh one"),
            (19, {"runs": [("head19", "completed")],
                  "reviewed": [("o-r-reviewer", "head19")],
                  "unreadable": "/reviews"}, True,
             "the verdicts on this head are a listing GitHub would not answer"),
            (20, {"runs": [("head20", "in_progress")],
                  "unreadable": "run list"}, True,
             "the runs on this branch are a listing GitHub would not answer")):
        seeded = dict(pull)
        refused = seeded.pop("unreadable", "")
        fake = FakeGitHub({number: {"behind": 0, "armed": False, "requested": list(PENDING),
                                    **seeded}})
        if refused:
            fake.git.unreadable[str(refused)] = 0
        def ask(n: int = number) -> None:
            """The verb under this case's GitHub."""
            move.request_review(str(n), "reviewer")

        with stood_in(channel, gh=fake):
            ended = outcome(ask)
        if ended.code:
            problems.append(f"request-review: a pending request where {why} exited with "
                            f"{ended.code!r}")
        if refused and "could not list" not in ended.out:
            problems.append(f"request-review: {why}, and the verb said {ended.out!r}, so a "
                            "guard that is off reads exactly like one that found nothing")
        if fake.edited and not asked:
            problems.append(f"request-review: {why}, and the request was withdrawn and made "
                            "again, which starts a second run on the same head")
        if asked and not fake.edited:
            problems.append(f"request-review: {why}, and the request was left as GitHub held "
                            "it, so a stale request is answered by nobody")
        if fake.pulls[str(number)].get("requested") != PENDING:
            problems.append(f"request-review: #{number} was left with GitHub holding "
                            f"{fake.pulls[str(number)].get('requested')!r}, not {PENDING!r}")
    return problems


def _watch_cases(check_pr: Any) -> list[str]:
    """`--watch` reporting the one change that produces no event: a branch going conflicting, headed by what it started on."""
    problems = []
    def watched(polls: list[tuple[str, str]]) -> list[str]:
        """What `--watch` printed on pull request 7, GitHub answering one poll at a time from `polls`."""
        with stood_in(check_pr.github, gh=WatchGitHub(polls)):
            lines: list[str] = outcome(lambda: check_pr.watch("7", every=0)).out.splitlines()
            return lines

    lines = watched([("OPEN", "MERGEABLE"), ("OPEN", "UNKNOWN"), ("OPEN", "MERGEABLE"),
                     ("OPEN", "CONFLICTING"), ("MERGED", "CONFLICTING")])
    changes = [line for line in lines[1:] if line.startswith("mergeable")]
    if len(changes) != 1 or "CONFLICTING" not in changes[0]:
        problems.append(f"watch: a branch that went conflicting reported {changes!r}")
    if "mergeable=MERGEABLE" not in lines[0]:
        problems.append(f"watch: the heading was {lines[0]!r}, and a watch that never says "
                        "what it started on cannot report a change from it")

    lines = watched([("OPEN", "CONFLICTING"), ("MERGED", "CONFLICTING")])
    if "mergeable=CONFLICTING" not in lines[0]:
        problems.append(f"watch: a watch begun on a conflicting branch headed itself {lines[0]!r}")

    lines = watched([("OPEN", "UNKNOWN"), ("OPEN", "CONFLICTING"), ("MERGED", "CONFLICTING")])
    changes = [line for line in lines[1:] if line.startswith("mergeable")]
    if len(changes) != 1 or "CONFLICTING" not in changes[0]:
        problems.append(f"watch: a watch headed `UNKNOWN` reported {changes!r}, and the answer "
                        "that followed is the only one it could have said")

    return problems


def _hung_subprocess(bounds: list[float | None]) -> Any:
    """As much of `subprocess` as `github.gh` uses, its `run` answering a call only when the call carries no bound.

    Each invocation records the `timeout=` it was given in `bounds`. A bounded
    call raises `TimeoutExpired`; an unbounded one returns successfully, so a
    `run` handed no bound never times out and the assertions below stop holding
    — which is what makes them assertions about the bound rather than about the
    handling of a timeout.
    """
    def run(*args: Any, **kwargs: Any) -> Any:
        bound = kwargs.get("timeout")
        bounds.append(bound)
        if bound is None:
            return subprocess.CompletedProcess(["gh"], 0, stdout="{}", stderr="")
        raise subprocess.TimeoutExpired(cmd=["gh"], timeout=bound)
    return types.SimpleNamespace(run=run, TimeoutExpired=subprocess.TimeoutExpired,
                                 CompletedProcess=subprocess.CompletedProcess)


def _watch_failure_cases(check_pr: Any) -> list[str]:
    """`--watch` failing fast on fatal environment errors, bounding a hung `gh` in the snapshot and in the evaluation, and tripping the circuit breaker."""
    problems: list[str] = []

    def fatal_gh(*args: Any) -> Any:
        sys.exit("gh: fatal: Unable to read current working directory: No such file or directory")

    with stood_in(check_pr.github, gh=fatal_gh):
        fatal_res = outcome(lambda: check_pr.watch("7", every=0))
    if not fatal_res.code or "fatal poll error" not in str(fatal_res.code):
        problems.append(f"watch: fatal poll error did not exit immediately: {fatal_res.code!r}")

    def transient_gh(*args: Any) -> Any:
        sys.exit("gh: GraphQL: connection timeout")

    with stood_in(check_pr.github, gh=transient_gh):
        breaker_res = outcome(lambda: check_pr.watch("7", every=0, max_retries=3))
    if not breaker_res.code or "circuit broken after 3 retries" not in str(breaker_res.code):
        problems.append(f"watch: circuit breaker did not trip after 3 retries: {breaker_res.code!r}")

    bounds: list[float | None] = []
    with stood_in(check_pr.github, subprocess=_hung_subprocess(bounds)):
        hung_call = outcome(lambda: check_pr.github.gh("pr", "view", "7"))
        given = bounds[0] if bounds else "no call at all"
        hung_watch = outcome(lambda: check_pr.watch("7", every=0, max_retries=2))
    if given != check_pr.github.GH_TIMEOUT:
        problems.append(f"gh: a call reached `subprocess.run` with timeout={given!r} rather "
                        f"than {check_pr.github.GH_TIMEOUT!r}, and an invocation carrying no "
                        "bound is the stall this exists to refuse")
    if not hung_call.code or "answered nothing within" not in str(hung_call.code):
        problems.append(f"gh: a call that never answered came to {hung_call.code!r}, "
                        "and a poll waiting on one stalls the watch it serves")
    if not hung_watch.code or "circuit broken after 2 retries" not in str(hung_watch.code):
        problems.append(f"watch: a hung `gh` came to {hung_watch.code!r}, and a hang that "
                        "persists is owed the exit a transient failure gets")

    def hung_login(_role: Any) -> Any:
        raise check_pr.github.GhTimeout(HUNG_LOGIN)

    with stood_in(check_pr.github, gh=WatchGitHub([]), role_login=hung_login):
        hung_eval = outcome(lambda: check_pr.watch("7", every=0, max_retries=2))
    if not hung_eval.code or "circuit broken after 2 retries" not in str(hung_eval.code):
        problems.append(f"watch: a hang reading the reviewer's login came to {hung_eval.code!r}, "
                        "and a poll that spends the bound and then classifies without a "
                        "reviewer is a watch that crawls without ever failing")

    return problems


def _watch_recovery_cases(check_pr: Any) -> list[str]:
    """`--watch` recovering from transient poll failures and resetting the retry counter."""
    problems: list[str] = []

    sequence: list[tuple[str, str] | None] = [
        None,
        ("OPEN", "MERGEABLE"),
        None,
        ("OPEN", "MERGEABLE"),
        None,
        ("OPEN", "MERGEABLE"),
        None,
        ("MERGED", "MERGEABLE"),
    ]

    def alternating_gh(*args: Any) -> Any:
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "o/r"}
        if args[:2] == ("pr", "view"):
            if args[-1] == "number":
                return {"number": 7}
            if not sequence:
                return {"number": 7, "state": "MERGED", "comments": [], "reviews": [], "mergeable": "MERGEABLE"}
            item = sequence.pop(0)
            if item is None:
                sys.exit("gh: temporary network glitch")
            state, mergeable = item
            return {"number": 7, "state": state, "comments": [], "reviews": [], "mergeable": mergeable}
        if args[0] == "api":
            return {"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": []}, "reviews": {"nodes": []}}}}}
        raise unanswered(args, "the gh fake")

    with stood_in(check_pr.github, gh=alternating_gh):
        alternating_res = outcome(lambda: check_pr.watch("7", every=0, max_retries=3))
    if alternating_res.code is not None or "pr MERGED" not in alternating_res.out:
        problems.append(
            f"watch: failures separated by successes tripped circuit breaker: code={alternating_res.code!r} out={alternating_res.out!r}"
        )
    if alternating_res.err.count("? poll skipped") != 4:
        problems.append(
            f"watch: alternating retry did not report expected 4 skipped polls: {alternating_res.err!r}"
        )

    return problems


def _unheld_armed_cases(check_pr: Any) -> list[str]:
    """`unheld` over an armed pull request: reported with unresolved threads, silent without them, and silent while it is recent."""
    problems = []
    armed = _pull_of(10, "Stuck armed PR", autoMergeRequest={"enabledAt": "2026-09-11"},
                    mergeable="MERGEABLE")
    with stood_in(check_pr.github, threads=lambda n: [{"id": "t1", "isResolved": False}]):
        owed = check_pr.unheld([armed], minutes=30, clean={10})
    if len(owed) != 1 or "unresolved conversation" not in owed[0]:
        problems.append(f"unheld: an armed PR with unresolved threads reported {owed!r}")

    with stood_in(check_pr.github, threads=lambda n: [{"id": "t1", "isResolved": True}]):
        clean_owed = check_pr.unheld([armed], minutes=30, clean={10})
        if clean_owed:
            problems.append(f"unheld: an armed PR with no unresolved threads reported {clean_owed!r}")

        recent = {**armed, "updatedAt": datetime.datetime.now(datetime.UTC).isoformat()}
        recent_owed = check_pr.unheld([recent], minutes=30, clean={10},
                                      unresolved={10: [{"id": "t1", "isResolved": False}]})
        if recent_owed:
            problems.append(f"unheld: recent armed PR reported {recent_owed!r} instead of passing in silence")
    return problems


def _unheld_idle_cases(check_pr: Any) -> list[str]:
    """`unheld` over each shape of idle pull request a webhook should have carried, the Challenge's labels answered by a `gh` stood in."""
    problems = []
    with stood_in(check_pr.github, threads=lambda n: [{"id": "t1", "isResolved": True}]):
        reviewer_name = check_pr.role_login("reviewer")
        approved = [{"author": {"login": reviewer_name}, "state": "APPROVED"}]
        changes_requested = [{"author": {"login": reviewer_name}, "state": "CHANGES_REQUESTED"}]
        approved_conflicting = check_pr.unheld(
            [_pull_of(11, "Approved conflicting PR", mergeable="CONFLICTING", latestReviews=approved)],
            minutes=30, clean={11})
        if len(approved_conflicting) != 1 or "approved, on a branch that conflicts" not in approved_conflicting[0]:
            problems.append(f"unheld: approved conflicting PR reported {approved_conflicting!r}")

        old_time = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=60)).isoformat()
        gate_failed = [{"name": "gate", "conclusion": "FAILURE", "startedAt": "2026-09-11T12:00:00Z"}]
        gate_passed = [{"name": "gate", "conclusion": "SUCCESS", "startedAt": "2026-09-11T12:00:00Z"}]
        idle: tuple[Any, ...] = (
            ("changes requested PR", "medium", set(),
             ("changes requested by reviewer, and unanswered",),
             _pull_of(12, "Changes requested PR", mergeable="MERGEABLE", statusCheckRollup=gate_failed,
                     latestReviews=changes_requested, updatedAt=old_time)),
            ("green PR with human challenge", "human", {13},
             (f"while #{'13'} is at human",),
             _pull_of(13, "Human challenge PR", mergeable="MERGEABLE", statusCheckRollup=gate_passed,
                     updatedAt=old_time)),
            ("green conflicting PR with human challenge", "human", {14},
             ("rebase claude/issue-14 onto main",),
             _pull_of(14, "Human conflicting PR", mergeable="CONFLICTING", statusCheckRollup=gate_passed,
                     updatedAt=old_time)),
            ("green PR with hard challenge", "hard", {15},
             (f"while #{'15'} is at hard",),
             _pull_of(15, "Hard challenge PR", mergeable="MERGEABLE", statusCheckRollup=gate_passed,
                     updatedAt=old_time)),
            ("approved failing loop PR", "medium", set(),
             ("approved, with failing checks", ".meta/say/move dispatch 16"),
             _pull_of(16, "Approved failing loop PR", mergeable="MERGEABLE", statusCheckRollup=gate_failed,
                     latestReviews=approved, updatedAt=old_time)),
            ("approved failing human PR", "hard", set(),
             ("approved, with failing checks", "fix the failing checks"),
             _pull_of(17, "Approved failing human PR", mergeable="MERGEABLE", statusCheckRollup=gate_failed,
                     latestReviews=approved, updatedAt=old_time)),
            ("stranded reviewer PR", "medium", set(),
             ("reviewer check failed without a verdict", ".meta/say/move request-review 18"),
             _pull_of(18, "Stranded reviewer PR", mergeable="MERGEABLE",
                     reviewRequests=[{"login": reviewer_name}],
                     statusCheckRollup=[{"name": "reviewer", "conclusion": "FAILURE",
                                         "startedAt": "2026-09-11T12:00:00Z"}],
                     updatedAt=old_time)),
            ("approved conflicting hard PR", "hard", set(),
             (f"Challenge #{'19'} is hard so the loop stands down",),
             _pull_of(19, "Approved conflicting hard PR", mergeable="CONFLICTING",
                     latestReviews=approved, updatedAt=old_time)),
        )
        for case, level, clean, phrases, pull in idle:
            with stood_in(check_pr.github, gh=lambda *a, level=level: {"state": "OPEN", "labels": [{"name": level}]}):
                owed = check_pr.unheld([pull], minutes=30, clean=clean)
            if len(owed) != 1 or any(phrase not in owed[0] for phrase in phrases):
                problems.append(f"unheld: {case} reported {owed!r}")
    return problems


def _unheld_comment_cases(check_pr: Any) -> list[str]:
    """`unheld` over a reviewer's top-level comment, on a plan-only draft and on a loop branch."""
    problems = []
    reviewer = check_pr.role_login("reviewer")
    coder = check_pr.role_login("coder")
    old_time = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=60)).isoformat()

    def said(n: int, login: str, text: str) -> dict[str, Any]:
        return {"id": f"IC_{n}", "databaseId": n, "author": {"login": login},
                "body": f"{text}\n\nActor: actor-{n}"}

    point = said(1, reviewer, "The plan reads the wrong file.")
    answer = said(2, coder, "Right, and a change to make (#issuecomment-1).")
    owed_nodes = check_pr.github.comment_threads([point], reviewer)
    answered_nodes = check_pr.github.comment_threads([point, answer], reviewer)

    def plan_of(**fields: Any) -> dict[str, Any]:
        return {"number": 20, "title": "Plan for a hard Challenge", "isDraft": True,
                "headRefName": "claude/plan-review-gates", "baseRefName": "main",
                "reviewRequests": [], "mergeable": "MERGEABLE", **fields}

    owed = check_pr.unheld([plan_of(updatedAt=old_time)], minutes=30, clean=set(),
                           unresolved={20: owed_nodes}, reviewer_login=reviewer)
    if len(owed) != 1 or ".meta/say/post comment 20" not in owed[0] or "draft" not in owed[0]:
        problems.append(f"unheld: a plan objection on a plan-only draft reported {owed!r}, "
                        "and a draft nothing reports is the stall solorepo's DR-248 refuses")

    now = datetime.datetime.now(datetime.UTC).isoformat()
    recent = check_pr.unheld([plan_of(updatedAt=now)], minutes=30, clean=set(),
                             unresolved={20: owed_nodes}, reviewer_login=reviewer)
    if recent:
        problems.append(f"unheld: a plan objection a run may still be answering reported "
                        f"{recent!r} instead of passing in silence")

    settled = check_pr.unheld([plan_of(updatedAt=old_time)], minutes=30, clean=set(),
                              unresolved={20: answered_nodes}, reviewer_login=reviewer)
    if settled:
        problems.append(f"unheld: an answered comment reported {settled!r}, and a point "
                        "settled by a link is owed nothing")

    loop_pull = _pull_of(21, "Loop PR with an owed comment", mergeable="MERGEABLE",
                         updatedAt=old_time)
    with stood_in(check_pr.github,
                  gh=lambda *a: {"state": "OPEN", "labels": [{"name": "medium"}]}):
        dispatched = check_pr.unheld([loop_pull], minutes=30, clean=set(),
                                     unresolved={21: check_pr.github.comment_threads(
                                         [point], reviewer)},
                                     reviewer_login=reviewer)
    if len(dispatched) != 1 or ".meta/say/move dispatch 21 --task review" not in dispatched[0]:
        problems.append(f"unheld: an owed comment on a loop branch reported {dispatched!r}, "
                        "which does not name the dispatch that answers it")
    return problems
