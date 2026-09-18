"""The dispatch reading of `advance` and the by-hand `dispatch` against a GitHub stood in for (solorepo's DR-133).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import datetime

from checks.collect import check
from checks.probes.harness import (
    FakeGitHub,
    load_channel,
    run_verb,
)


def _conflicting_with_a_review_request_dispatches_rebase(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING"},
                       8: {"behind": 1, "armed": False, "requested": ["reviewer"]}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("7", "rebase")]:
        problems.append(f"advance: the conflicting one dispatched {fake.dispatched!r}")
    if fake.pulls["7"].get("rebased") or fake.pulls["8"].get("rebased"):
        problems.append("advance: it rebased a pull request nobody had asked to land")
    if said:
        problems.append(f"advance: a dispatch that took exited with {said!r}")
    return problems


def _unknown_is_waited_out(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING", "unknown": 2}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("7", "rebase")]:
        problems.append("advance: it took the first `UNKNOWN` for an answer and dispatched "
                        f"{fake.dispatched!r}")
    if said:
        problems.append(f"advance: waiting out an `UNKNOWN` exited with {said!r}")
    return problems


def _armed_conflicting_dispatched_not_rebased(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True, "mergeable": "CONFLICTING"},
                       8: {"behind": 1, "armed": True}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("7", "rebase")]:
        problems.append(f"advance: the armed conflicting one dispatched {fake.dispatched!r}")
    if fake.pulls["7"].get("rebased"):
        problems.append("advance: it asked GitHub to rebase a branch that conflicts")
    if not fake.pulls["8"].get("rebased"):
        problems.append("advance: the armed one that merely fell behind was left behind")
    if said:
        problems.append(f"advance: the armed conflicting one exited with {said!r}")
    return problems


def _approved_conflicting_dispatches_rebase(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": False, "mergeable": "CONFLICTING",
                           "verdicts": [("o-r-reviewer", "APPROVED")]}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("7", "rebase")]:
        problems.append(f"advance: the approved conflicting one dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"advance: the approved conflicting one exited with {said!r}")
    return problems


def _unanswered_changes_requested_dispatches_review(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                           "verdicts": [("o-r-reviewer", "CHANGES_REQUESTED")]}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("7", "review")]:
        problems.append(f"advance: unanswered changes requested one dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"advance: unanswered changes requested one exited with {said!r}")
    return problems


def _recent_changes_requested_left_to_the_run(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                           "updatedAt": datetime.datetime.now(datetime.UTC).isoformat(),
                           "verdicts": [("o-r-reviewer", "CHANGES_REQUESTED")]}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched:
        problems.append("advance: recent changes requested PR dispatched "
                        f"{fake.dispatched!r} during active run window")
    if said:
        problems.append(f"advance: recent changes requested PR exited with {said!r}")
    return problems


def _approved_with_failing_checks_dispatches_review(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                           "checks": [{"name": "gate", "conclusion": "FAILURE"}],
                           "verdicts": [("o-r-reviewer", "APPROVED")]}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("7", "review")]:
        problems.append(f"advance: approved PR with failing checks dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"advance: approved PR with failing checks exited with {said!r}")
    return problems


def _stranded_review_request_re_requested(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                           "requested": ["o-r-reviewer"],
                           "checks": [{"name": "reviewer", "conclusion": "FAILURE"}]}})
    said = run_verb(channel, fake, lambda: move.advance())
    if "o-r-reviewer" not in fake.pulls["7"]["requested"] or "7" not in fake.edited:
        problems.append(f"advance: stranded review request was not re-requested: {fake.pulls['7']!r}")
    if said:
        problems.append(f"advance: stranded review request exited with {said!r}")
    return problems


def _nothing_asked_dispatches_nothing(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "CONFLICTING"},
                       8: {"behind": 0, "armed": True,
                           "mergeable": "CONFLICTING", "branch": "solo/whatever"}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched:
        problems.append(f"advance: it dispatched {fake.dispatched!r}, which nobody had asked "
                        "to review or to land, or which was not a loop's branch")
    if said:
        problems.append(f"advance: the case that should dispatch nothing exited with {said!r}")
    return problems


def _lower_layer_of_a_stack_left_alone(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING"},
                       8: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "base": "claude/issue-7", "mergeable": "MERGEABLE"}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched:
        problems.append("advance: it dispatched the lower layer of a stack, "
                        f"{fake.dispatched!r}")
    if said:
        problems.append(f"advance: the stack it left alone exited with {said!r}")
    named_said = run_verb(channel, fake, lambda: move.advance("7"))
    if not named_said or "base of another open pull request" not in named_said:
        problems.append(f"advance: named stack base should be refused, got {named_said!r}")
    return problems


def _challenges_the_loop_does_not_hold(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING", "issue": {"level": "hard"}},
                       8: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING", "issue": {"state": "CLOSED"}},
                       9: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING", "issue": {"level": "human"}},
                       10: {"behind": 0, "armed": False, "requested": ["reviewer"],
                            "mergeable": "CONFLICTING", "issue": {"unreadable": True}}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched:
        problems.append("advance: it dispatched a Challenge the loop does not hold, "
                        f"{fake.dispatched!r}")
    if said:
        problems.append(f"advance: the Challenges it left alone exited with {said!r}")
    return problems


def _refused_dispatch_is_one_pull_requests_problem(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING"},
                       8: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING"}}, no_dispatch=[7])
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("8", "rebase")]:
        problems.append(f"advance: a refused dispatch left the rest at {fake.dispatched!r}")
    if not said or "#7" not in said:
        problems.append(f"advance: the refused dispatch was reported as {said!r}")
    return problems


def _named_and_merge_auto_dispatch_nothing(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": True, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING"}})
    named = run_verb(channel, fake, lambda: move.advance("7"))
    merging = run_verb(channel, fake, lambda: move.merge("7", auto=True))
    if fake.dispatched:
        problems.append(f"advance: a named pull request dispatched {fake.dispatched!r}")
    if named or merging:
        problems.append(f"advance: the two callers that dispatch nothing exited with "
                        f"{named!r} and {merging!r}")
    return problems


def _named_conflicting_pull_request_refused(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True, "mergeable": "CONFLICTING"}},
                      no_rebase=[7])
    said = run_verb(channel, fake, lambda: move.advance("7"))
    if not said or "conflicts" not in said:
        problems.append(f"advance: a named conflicting pull request exited with {said!r}")
    return problems


def _dispatch_review_on_a_standing_verdict(channel, move, reviewer) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False,
                           "verdicts": [(reviewer, "CHANGES_REQUESTED"),
                                        (reviewer, "COMMENTED")]}})
    said = run_verb(channel, fake, lambda: move.dispatch_pass("7", "review"))
    if fake.dispatched != [("7", "review")]:
        problems.append(f"dispatch: a verdict standing dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"dispatch: the pass it should have started exited with {said!r}")
    return problems


def _dispatch_review_on_approval_with_failing_checks(channel, move, reviewer) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False,
                           "checks": [{"name": "gate", "conclusion": "FAILURE"}],
                           "verdicts": [(reviewer, "APPROVED")]}})
    said = run_verb(channel, fake, lambda: move.dispatch_pass("7", "review"))
    if fake.dispatched != [("7", "review")]:
        problems.append(f"dispatch: approved PR with failing checks dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"dispatch: approved PR with failing checks exited with {said!r}")
    return problems


def _dispatch_review_refused_without_a_request_for_changes(channel, move, reviewer) -> list[str]:
    problems: list[str] = []
    for case, pull in (("an approval", {"verdicts": [(reviewer, "APPROVED")]}),
                       ("somebody else's", {"verdicts": [(reviewer, "APPROVED"),
                                                         ("passer-by", "CHANGES_REQUESTED")]}),
                       ("no verdict", {})):
        fake = FakeGitHub({7: {"behind": 0, "armed": False, **pull}})
        said = run_verb(channel, fake, lambda: move.dispatch_pass("7", "review"))
        if fake.dispatched:
            problems.append(f"dispatch: {case} dispatched {fake.dispatched!r}")
        if not said or "last verdict" not in said:
            problems.append(f"dispatch: {case} was refused with {said!r}")
    return problems


def _dispatch_review_refused_while_answered(channel, move, reviewer) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": [reviewer],
                           "verdicts": [(reviewer, "CHANGES_REQUESTED")]}})
    said = run_verb(channel, fake, lambda: move.dispatch_pass("7", "review"))
    if fake.dispatched:
        problems.append(f"dispatch: a verdict already answered dispatched {fake.dispatched!r}")
    if not said or "not yet given" not in said:
        problems.append(f"dispatch: the answered verdict was refused with {said!r}")
    return problems


def _dispatch_rebase_on_conflicting_not_on_behind(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "CONFLICTING"},
                       8: {"behind": 3, "armed": False}})
    said = run_verb(channel, fake, lambda: move.dispatch_pass("7", "rebase"))
    if fake.dispatched != [("7", "rebase")]:
        problems.append(f"dispatch: a conflicting branch dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"dispatch: the rebase it should have started exited with {said!r}")
    said = run_verb(channel, fake, lambda: move.dispatch_pass("8", "rebase"))
    if fake.dispatched != [("7", "rebase")]:
        problems.append(f"dispatch: a branch that merely fell behind dispatched {fake.dispatched!r}")
    if not said or "MERGEABLE" not in said:
        problems.append(f"dispatch: the branch that was not conflicting was refused with {said!r}")
    if said and "advance 8" in said:
        problems.append(f"dispatch: the branch that was not conflicting was sent to a verb "
                        f"that refuses an unarmed one — {said!r}")
    return problems


def _dispatch_rebase_refused_by_hand(channel, move) -> list[str]:
    problems: list[str] = []
    for case, pull in (("a branch that is not the loop's",
                        {"branch": "claude/issue-169-followup"}),
                       ("the solo's own branch", {"branch": "fix-the-thing"}),
                       ("a layer of a stack", {"layer": True})):
        fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "CONFLICTING", **pull}})
        said = run_verb(channel, fake, lambda: move.dispatch_pass("7", "rebase"))
        if fake.dispatched:
            problems.append(f"dispatch: {case} dispatched {fake.dispatched!r}")
        if not said or "by hand" not in said:
            problems.append(f"dispatch: {case} was refused with {said!r}")
    return problems


@check("dispatch probes", pre=True)
def dispatch_probes():
    """The dispatch reading of `advance` and the by-hand `dispatch` against a fake GitHub (solorepo's DR-133).

    Both waits are shortened to nothing before the first case, `SETTLES`
    (solorepo's DR-158) and `MERGEABILITY` (solorepo's DR-133), and for one
    reason: what the cases hold is that a wait happens and waits for an answer,
    and the seconds it lasts are GitHub's business rather than a gate's.

    The states, in the order they run:

    - The dispatch reading (solorepo's DR-133). A merge on trunk that leaves
      a review request unanswerable dispatches the coder's rebase pass, the
      task and not only the number, and does not touch the branch
      (solorepo's #159, solorepo's #161). `UNKNOWN` is waited out rather than
      taken for an answer. An armed conflicting one is dispatched and not
      rebased, and the sweep exits 0 having left it to the dispatch
      (solorepo's DR-149, solorepo's #201). An approved conflicting one is
      dispatched to rebase; an unanswered request for changes to review,
      unless it is recent enough that a run may still be standing on it; an
      approved one with failing checks to review; and a review request whose
      reviewer check failed without a verdict is re-requested
      (solorepo's DR-167, solorepo's DR-178, solorepo's #316). Nothing is
      dispatched for a branch nobody asked to review or to land, on which a
      Job may still be standing, for the solo's own branch, for the lower
      layer of a stack, whose rebase would rewrite the layer above with no
      event on it, or for a Challenge the loop does not hold — `hard`,
      closed, `human`, which is what `stop` leaves, or unreadable, which is
      an Issue deleted or transferred under its branch (solorepo's DR-142).
      One refused dispatch is one pull request's problem, and the refusal
      names the coder token without the Actions write. Neither `merge
      --auto`, which holds the branch it is arming, nor a typed `advance
      <n>`, which names one somebody is asking about, dispatches, since
      neither is the merge on `main` that stranded a request; and both keep
      GitHub's refusal over a branch that conflicts where the sweep skips it,
      because nobody stands behind a named pull request but whoever typed the
      verb.
    - The dispatch a person makes. It reads the pull request and nothing
      else, because the review dispatch is the delivery solorepo's DR-142
      exempts from `coder.yml`'s guard. The review pass starts on a request
      for changes with a `COMMENTED` review on top, which is what GitHub
      submits every reply on a thread as and which overturns nothing, and on
      an approval with failing checks (solorepo's DR-178); it is refused on an
      approval, which is not a request for changes; on somebody else's
      request for changes, which is not the verdict `coder.yml`'s own door
      reads; on no verdict, which is a pull request waiting on a review
      rather than on an answer; and while a review is outstanding of the
      reviewer, which is the coder having handed back. The rebase pass starts
      on a `CONFLICTING` branch and is refused on one that merely fell
      behind, by a sentence that does not send it to a verb refusing an
      unarmed one; and it is refused before `mergeable` is asked for on a
      branch that is not the loop's shape, on the solo's own, and on a layer
      of a stack. A branch that is not the loop's shape,
      `claude/issue-169-followup` here, names no Challenge for a pass that
      could not finish to hand back to; `coder.yml` holds that refusal only
      after the dispatch, and for the nearly-right name it holds none at all,
      so the verb refuses first. A layer of a stack is the solo's because
      rebasing one moves commits under the layer above with no event on it
      (solorepo's DR-133).

    `said` is read in every case whose whole assertion is an absence: a verb
    that died before dispatching leaves `dispatched` empty too, and without it
    a crash reads exactly like the filter doing its job. The fake's repository
    is `o/r`, so the reviewer's login is `o-r-reviewer`, as `channel.role_login`
    composes it (solorepo's DR-107).
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    move.SETTLES = (3, 0)
    move.MERGEABILITY = (3, 0)
    reviewer = "o-r-reviewer"
    return [problem for problems in (
        _conflicting_with_a_review_request_dispatches_rebase(channel, move),
        _unknown_is_waited_out(channel, move),
        _armed_conflicting_dispatched_not_rebased(channel, move),
        _approved_conflicting_dispatches_rebase(channel, move),
        _unanswered_changes_requested_dispatches_review(channel, move),
        _recent_changes_requested_left_to_the_run(channel, move),
        _approved_with_failing_checks_dispatches_review(channel, move),
        _stranded_review_request_re_requested(channel, move),
        _nothing_asked_dispatches_nothing(channel, move),
        _lower_layer_of_a_stack_left_alone(channel, move),
        _challenges_the_loop_does_not_hold(channel, move),
        _refused_dispatch_is_one_pull_requests_problem(channel, move),
        _named_and_merge_auto_dispatch_nothing(channel, move),
        _named_conflicting_pull_request_refused(channel, move),
        _dispatch_review_on_a_standing_verdict(channel, move, reviewer),
        _dispatch_review_on_approval_with_failing_checks(channel, move, reviewer),
        _dispatch_review_refused_without_a_request_for_changes(channel, move, reviewer),
        _dispatch_review_refused_while_answered(channel, move, reviewer),
        _dispatch_rebase_on_conflicting_not_on_behind(channel, move),
        _dispatch_rebase_refused_by_hand(channel, move)
    ) for problem in problems]

