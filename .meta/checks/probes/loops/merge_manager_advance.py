"""The merge manager advancing an approved pull request that fell behind trunk.

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
from typing import Any

from checks.collect import check
from checks.probes.harness import (
    FakeGitHub,
    load_channel,
    outcome,
    stood_in,
)


@check("merge manager advance probes", pre=True)
def merge_manager_advance_probes() -> list[str]:
    """The merge manager rebasing what only a stale branch holds back (solorepo's #459).

    An approved pull request that goes behind trunk while it is in review is
    reached by no event: `advance.yml` runs on a push to `main` and the
    approval is not one, so the manager reads `BEHIND`, calls the pull request
    ineligible and goes idle — and with nothing else eligible to move trunk,
    nothing ever pushes (solorepo's #452, stranded behind solorepo's #447).
    These cases run `merge_manager` over a GitHub where that is the state, and
    read the rebase off the branch rather than off the printed line.

    Five pull requests, none eligible: one approved and green whose only
    failing semaphore is the stale branch, which is rebased; one in the same
    state that is the base of another open pull request, which is refused,
    because rebasing it would rewrite commits the layer above is on
    (solorepo's DR-133); that layer itself, which is behind nothing and
    approved by nobody; one that is behind *and* red, which is not one rebase
    from landing and so is left alone; and one approved and green carrying an
    unresolved conversation, which is left alone too, because rebasing it would
    outdate the anchored comment PR First's *Reread the diff and notice* step parks work on. A
    refusal is printed and the verb still exits 0, since `merge.yml` runs on a
    fifteen-minute schedule and a stack base that stays behind would otherwise
    paint it red on the clock. Under `--dry-run` the same GitHub is named and
    not touched, and with `stranded=False` — what `merge.yml` passes on the push
    to `main` that `advance.yml` answers itself — nothing is named or touched.

    The conversations are read where production reads them, over GraphQL:
    `MERGE_MANAGER_FIELDS` does not ask `pr list` for `reviewThreads` and `gh`
    answers only the fields it is asked for, so a fixture injecting the field
    into the listing would take a branch no run of `merge.yml` takes.

    Both waits are shortened to nothing, as `probes/loops/advance.py` does and
    for the same reason: what the cases hold is that the rebase is read back, and
    the seconds it waits are GitHub's business.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    channel.SETTLES = (3, 0)
    channel.MERGEABILITY = (3, 0)
    return (_dry_run(channel, move) + _held_run(channel, move) + _real_run(channel, move)
            + _stall_eviction_exemptions(move) + _unresolved_conversations_carve_out(move))


REVIEWER = "o-r-reviewer"
GREEN = [{"name": "gate", "conclusion": "SUCCESS"}]
RED = [{"name": "gate", "conclusion": "FAILURE"}]
APPROVED = [{"author": {"login": REVIEWER}, "state": "APPROVED"}]
TALKING = {24}
"""The pull request whose conversation is unresolved."""
PARKED = {25}
"""The pull request holding a parked coder notice."""


def stranded(checks: Any = GREEN, reviews: Any = APPROVED, **fields: Any) -> dict[str, Any]:
    """The fields `merge_manager` reads of a pull request that is behind its base."""
    return {"isDraft": False, "mergeStateStatus": "BEHIND", "statusCheckRollup": checks,
            "latestReviews": reviews, **fields}


def conversations(query: Any, number: int = 0, **_: Any) -> Any:
    """The review threads GitHub answers for `number`: resolved, talking, or parked."""
    if number in PARKED:
        nodes = [{
            "isResolved": False,
            "comments": {
                "nodes": [{"author": {"login": REVIEWER}, "body": "**Noticed and not done.** wait"}]
            },
        }]
    elif number in TALKING:
        nodes = [{
            "isResolved": False,
            "comments": {"nodes": [{"author": {"login": REVIEWER}, "body": "active question"}]},
        }]
    else:
        nodes = [{"isResolved": True, "comments": {"nodes": []}}]
    return {"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": nodes}}}}}


def github() -> Any:
    """The six pull requests, fresh, so a dry run and a real run do not share a state."""
    return FakeGitHub({
        20: {"behind": 2, "armed": False, "verdicts": [(REVIEWER, "APPROVED")],
             "manager": stranded()},
        21: {"behind": 2, "armed": False, "verdicts": [(REVIEWER, "APPROVED")],
             "manager": stranded()},
        22: {"behind": 0, "armed": False, "base": "claude/issue-21",
             "manager": stranded(checks=[], reviews=[], mergeStateStatus=None)},
        23: {"behind": 2, "armed": False, "verdicts": [(REVIEWER, "APPROVED")],
             "manager": stranded(checks=RED)},
        24: {"behind": 2, "armed": False, "verdicts": [(REVIEWER, "APPROVED")],
             "manager": stranded()},
        25: {"behind": 2, "armed": False, "verdicts": [(REVIEWER, "APPROVED")],
             "manager": stranded()},
    })


def manager_github(fake: Any) -> Any:
    """`fake`, with the fields `merge_manager` reads added to its `pr list`.

    The manager and `advance` ask two different `pr list` questions of the
    same pull requests, and `FakeGitHub` answers only `advance`'s. Each pull
    request's `manager` dict is merged into its listing, so one object
    answers both and the rebase a case reads back is the one `advance`
    performed. `issue list` answers empty: leverage is not what these cases
    are about, and a manager that finds nothing eligible never asks.
    """
    def gh(*args: Any, parse: bool = True, **kwargs: Any) -> Any:
        """One `gh` call, as `fake` answers it, with `pr list` enriched."""
        if args[:2] == ("issue", "list"):
            return []
        answer = fake(*args, parse=parse, **kwargs)
        if args[:2] == ("pr", "list"):
            for listed in answer:
                listed.update(fake.pulls[str(listed["number"])].get("manager") or {})
        return answer
    return gh


def _dry_run(channel: Any, move: Any) -> list[str]:
    """A dry run names the stranded pull request and rebases nothing."""
    problems: list[str] = []
    fake = github()
    with stood_in(channel, gh=manager_github(fake), graphql=conversations):
        dry = outcome(lambda: move.merge_manager(dry_run=True))
    if f"dry run — not advancing #{'20'}" not in dry.out:
        problems.append(f"merge manager: a dry run did not name the stranded pull request:\n{dry.out}")
    if any(pull.get("rebased") for pull in fake.pulls.values()):
        problems.append("merge manager: a dry run rebased a branch")
    return problems


def _held_run(channel: Any, move: Any) -> list[str]:
    """With `stranded=False`, the event `advance.yml` answers itself, nothing is named or touched."""
    problems: list[str] = []
    fake = github()
    with stood_in(channel, gh=manager_github(fake), graphql=conversations):
        held = outcome(lambda: move.merge_manager(dry_run=False, stranded=False))
    if any(pull.get("rebased") for pull in fake.pulls.values()):
        problems.append("merge manager: it rebased a branch on the event advance.yml answers")
    if "advancing" in held.out:
        problems.append(f"merge manager: it named a stranded pull request it had left alone:\n{held.out}")
    return problems


def _real_run(channel: Any, move: Any) -> list[str]:
    """The real run rebases the approved pull request behind its base and leaves the stack base, the red one and the one still talking alone, naming each."""
    problems: list[str] = []
    fake = github()
    with stood_in(channel, gh=manager_github(fake), graphql=conversations):
        ran = outcome(lambda: move.merge_manager(dry_run=False))
    if ran.code is not None:
        problems.append(f"merge manager: a refused rebase ended the run — {ran.code}")
    if "idle" not in ran.out:
        problems.append(f"merge manager: nothing was eligible and it did not say so:\n{ran.out}")
    if not fake.pulls["20"].get("rebased"):
        problems.append("merge manager: an approved pull request behind its base was not rebased")
    if fake.pulls["20"]["behind"]:
        problems.append("merge manager: the rebase left the branch behind its base")
    if fake.pulls["21"].get("rebased"):
        problems.append("merge manager: it rebased the base of another open pull request")
    if f"could not advance #{'21'}" not in ran.out:
        problems.append(f"merge manager: the refused stack base was not named:\n{ran.out}")
    if fake.pulls["23"].get("rebased"):
        problems.append("merge manager: it rebased a pull request whose checks are failing")
    if fake.pulls["24"].get("rebased"):
        problems.append("merge manager: it rebased a pull request with an unresolved conversation")
    if f"not advancing #{'24'}" not in ran.out:
        problems.append(f"merge manager: the unresolved conversation was not named:\n{ran.out}")
    if not fake.pulls["25"].get("rebased"):
        problems.append("merge manager: approved PR holding parked notices was not rebased")
    if fake.pulls["25"]["behind"]:
        problems.append("merge manager: rebase of PR holding parked notices left branch behind")
    return problems


def _stall_eviction_exemptions(move: Any) -> list[str]:
    """Loop PRs with approval or in AWAITING_PROMOTION are exempt from stall (solorepo's DR-258)."""
    problems: list[str] = []
    re_requested_approved_pr = {
        "number": 37,
        "headRefName": "gemini/issue-37",
        "baseRefName": "main",
        "isDraft": False,
        "latestReviews": APPROVED,
        "reviews": [
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "APPROVED"},
        ],
        "reviewRequests": [{"login": REVIEWER}],
        "mergeable": "MERGEABLE",
        "statusCheckRollup": GREEN,
    }
    if move.is_stalled_autonomous_pr(re_requested_approved_pr, REVIEWER):
        problems.append(
            "is_stalled_autonomous_pr: standing APPROVED verdict must exempt loop PR from stall"
        )
    awaiting_promotion_pr = {
        "number": 38,
        "headRefName": "claude/issue-38",
        "baseRefName": "main",
        "isDraft": False,
        "latestReviews": APPROVED,
        "reviews": [
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"},
            {"author": {"login": REVIEWER}, "state": "APPROVED"},
        ],
        "reviewRequests": [],
        "reviewThreads": [
            {
                "isResolved": False,
                "comments": {"nodes": [{"body": "**Noticed and not done.** wait"}]},
            }
        ],
        "mergeable": "MERGEABLE",
        "statusCheckRollup": GREEN,
    }
    if move.is_stalled_autonomous_pr(awaiting_promotion_pr, REVIEWER):
        problems.append("is_stalled_autonomous_pr: AWAITING_PROMOTION PR must be exempt from stall")
    return problems


def _unresolved_conversations_carve_out(move: Any) -> list[str]:
    """Parked coder notices are carved out from conversation counts (solorepo's DR-159)."""
    problems: list[str] = []
    parked = [
        {
            "isResolved": False,
            "comments": {"nodes": [{"body": "**Noticed and not done.** parked notice"}]},
        }
    ]
    refusal = move.unresolved_conversations(parked)
    if refusal != "":
        problems.append(
            f"unresolved_conversations: expected empty string for parked notice, got: {refusal!r}"
        )
    owed = [
        {
            "isResolved": False,
            "comments": {"nodes": [{"body": "active question"}]},
        }
    ]
    refusal_owed = move.unresolved_conversations(owed)
    if refusal_owed != "1 unresolved conversation(s)":
        problems.append(
            f"unresolved_conversations: expected 1 conversation, got: {refusal_owed!r}"
        )
    return problems

