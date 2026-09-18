"""`request-review`, `--watch` and the `unheld` sweep over the shapes a webhook should have carried (solorepo's DR-178).

One module for one probe, so a history log's receipt names the file holding it (solorepo's DR-209).
"""
import datetime
from typing import Any

import citations
from collect import check
from probes.harness import (
    FakeGitHub,
    WatchGitHub,
    load_channel,
    outcome,
    run_verb,
    stood_in,
)


@check("handoff probes", pre=True)
def handoff_probes():
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
    follows, is waited out rather than refused on timing.

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
    verdict; and an approved conflicting one at `hard`, where the loop stands
    down (solorepo's DR-167, solorepo's DR-178, solorepo's #316). The Challenge's
    labels are answered by standing `check_pr.gh` in with the level each case
    names.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    move.MERGEABILITY = (3, 0)
    check_pr = citations.load_check_pr()
    return (_request_review_cases(channel, move) + _watch_cases(check_pr)
            + _unheld_armed_cases(check_pr) + _unheld_idle_cases(check_pr))


def _pull_of(number: Any, title: Any, **fields) -> dict[str, Any]:
    """A pull request on the loop's branch for `number`, based on trunk, not a draft, with no review requested, and `fields` over that."""
    return {"number": number, "title": title, "headRefName": f"claude/issue-{number}",
            "baseRefName": "main", "isDraft": False, "reviewRequests": [], **fields}


def _request_review_cases(channel: Any, move: Any) -> list[str]:
    """`request-review` refused on a conflicting branch, made on a mergeable one, and made after waiting out `UNKNOWN`."""
    problems = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "base": "claude/issue-6",
                           "mergeable": "CONFLICTING"}})
    said = run_verb(channel, fake, lambda: move.request_review("7", "reviewer"))
    if fake.pulls["7"].get("requested"):
        problems.append(f"request-review: a conflicting branch was requested of "
                        f"{fake.pulls['7']['requested']!r}, and no review can run on it")
    if not said or "claude/issue-6" not in said or "no merge ref" not in said:
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
    return problems


def _watch_cases(check_pr: Any) -> list[str]:
    """`--watch` reporting the one change that produces no event: a branch going conflicting, headed by what it started on."""
    problems = []
    def watched(polls):
        """What `--watch` printed on pull request 7, GitHub answering one poll at a time from `polls`."""
        with stood_in(check_pr.github, gh=WatchGitHub(polls)):
            return outcome(lambda: check_pr.watch("7", every=0)).out.splitlines()

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
        idle = (
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
