"""The dispatch reading of `advance` and the by-hand `dispatch` against a GitHub stood in for (solorepo's DR-133).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import datetime
from typing import Any

from checks.collect import check
from checks.probes.harness import (
    FakeGitHub,
    load_channel,
    run_verb,
)
from checks.probes.loops.advance import swept


def _conflicting_with_a_review_request_dispatches_rebase(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING"},
                       8: {"behind": 1, "armed": False, "requested": ["reviewer"]}})
    said = swept(channel, move, fake, problems)
    if fake.dispatched != [("7", "rebase")]:
        problems.append(f"advance: the conflicting one dispatched {fake.dispatched!r}")
    if fake.pulls["7"].get("rebased") or fake.pulls["8"].get("rebased"):
        problems.append("advance: it rebased a pull request nobody had asked to land")
    if said:
        problems.append(f"advance: a dispatch that took exited with {said!r}")
    return problems


def _unknown_is_waited_out(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING", "unknown": 2}})
    said = swept(channel, move, fake, problems)
    if fake.dispatched != [("7", "rebase")]:
        problems.append("advance: it took the first `UNKNOWN` for an answer and dispatched "
                        f"{fake.dispatched!r}")
    if said:
        problems.append(f"advance: waiting out an `UNKNOWN` exited with {said!r}")
    return problems


def _armed_conflicting_dispatched_not_rebased(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True, "mergeable": "CONFLICTING"},
                       8: {"behind": 1, "armed": True}})
    said = swept(channel, move, fake, problems)
    if fake.dispatched != [("7", "rebase")]:
        problems.append(f"advance: the armed conflicting one dispatched {fake.dispatched!r}")
    if fake.pulls["7"].get("rebased"):
        problems.append("advance: it asked GitHub to rebase a branch that conflicts")
    if not fake.pulls["8"].get("rebased"):
        problems.append("advance: the armed one that merely fell behind was left behind")
    if said:
        problems.append(f"advance: the armed conflicting one exited with {said!r}")
    return problems


def _approved_conflicting_dispatches_rebase(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": False, "mergeable": "CONFLICTING",
                           "verdicts": [("o-r-reviewer", "APPROVED")]}})
    said = swept(channel, move, fake, problems)
    if fake.dispatched != [("7", "rebase")]:
        problems.append(f"advance: the approved conflicting one dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"advance: the approved conflicting one exited with {said!r}")
    return problems


def _conflicting_changes_requested_dispatches_rebase(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "CONFLICTING",
                           "verdicts": [("o-r-reviewer", "CHANGES_REQUESTED")]}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("7", "rebase")]:
        problems.append("advance: a conflicting one with a verdict standing dispatched "
                        f"{fake.dispatched!r}")
    if said:
        problems.append(f"advance: the conflicting one with a verdict standing exited with {said!r}")
    return problems


def _recent_conflicting_changes_requested_left_to_the_run(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "CONFLICTING",
                           "updatedAt": datetime.datetime.now(datetime.UTC).isoformat(),
                           "verdicts": [("o-r-reviewer", "CHANGES_REQUESTED")]}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched:
        problems.append("advance: a conflicting one whose verdict is recent enough for a run to "
                        f"be standing on it dispatched {fake.dispatched!r}")
    if said:
        problems.append("advance: the conflicting one left to the run it may already have "
                        f"exited with {said!r}")
    return problems


def _unanswered_changes_requested_dispatches_review(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                           "verdicts": [("o-r-reviewer", "CHANGES_REQUESTED")]}})
    said = swept(channel, move, fake, problems)
    if fake.dispatched != [("7", "review")]:
        problems.append(f"advance: unanswered changes requested one dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"advance: unanswered changes requested one exited with {said!r}")
    return problems


def _recent_changes_requested_left_to_the_run(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                           "updatedAt": datetime.datetime.now(datetime.UTC).isoformat(),
                           "verdicts": [("o-r-reviewer", "CHANGES_REQUESTED")]}})
    said = swept(channel, move, fake, problems)
    if fake.dispatched:
        problems.append("advance: recent changes requested PR dispatched "
                        f"{fake.dispatched!r} during active run window")
    if said:
        problems.append(f"advance: recent changes requested PR exited with {said!r}")
    return problems


def _approved_with_failing_checks_dispatches_review(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                           "checks": [{"name": "gate", "conclusion": "FAILURE"}],
                           "verdicts": [("o-r-reviewer", "APPROVED")]}})
    said = swept(channel, move, fake, problems)
    if fake.dispatched != [("7", "review")]:
        problems.append(f"advance: approved PR with failing checks dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"advance: approved PR with failing checks exited with {said!r}")
    return problems


def _stranded_review_request_re_requested(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                           "requested": ["o-r-reviewer"],
                           "checks": [{"name": "reviewer", "conclusion": "FAILURE"}]}})
    said = swept(channel, move, fake, problems)
    if "o-r-reviewer" not in fake.pulls["7"]["requested"] or "7" not in fake.edited:
        problems.append(f"advance: stranded review request was not re-requested: {fake.pulls['7']!r}")
    if said:
        problems.append(f"advance: stranded review request exited with {said!r}")
    return problems


def _nothing_asked_dispatches_nothing(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "CONFLICTING"},
                       8: {"behind": 0, "armed": True,
                           "mergeable": "CONFLICTING", "branch": "solo/whatever"}})
    said = swept(channel, move, fake, problems)
    if fake.dispatched:
        problems.append(f"advance: it dispatched {fake.dispatched!r}, which nobody had asked "
                        "to review or to land, or which was not a loop's branch")
    if said:
        problems.append(f"advance: the case that should dispatch nothing exited with {said!r}")
    return problems


def _stack_root_rebased_by_sweep_refused_by_name(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING"},
                       8: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "base": "claude/issue-7", "mergeable": "CONFLICTING"}})
    said = swept(channel, move, fake, problems)
    if fake.dispatched != [("7", "rebase")]:
        problems.append("advance: a conflicting stack should have its root rebased and the "
                        f"layer above it left alone, and it dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"advance: the stack it resolved from the bottom exited with {said!r}")
    named_said = run_verb(channel, fake, lambda: move.advance("7"))
    if not named_said or "base of another open pull request" not in named_said:
        problems.append(f"advance: named stack base should be refused, got {named_said!r}")
    return problems


def _challenges_the_loop_does_not_hold(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING", "issue": {"level": "hard"}},
                       8: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING", "issue": {"state": "CLOSED"}},
                       9: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING", "issue": {"level": "human"}},
                       10: {"behind": 0, "armed": False, "requested": ["reviewer"],
                            "mergeable": "CONFLICTING", "issue": {"unreadable": True}}})
    said = swept(channel, move, fake, problems)
    if fake.dispatched:
        problems.append("advance: it dispatched a Challenge the loop does not hold, "
                        f"{fake.dispatched!r}")
    if said:
        problems.append(f"advance: the Challenges it left alone exited with {said!r}")
    return problems


def _refused_dispatch_is_the_sweeps_own_problem(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING"},
                       8: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING"}}, no_dispatch=[7])
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("8", "rebase")]:
        problems.append(f"advance: a refused dispatch left the rest at {fake.dispatched!r}")
    if not said or "#7" not in said:
        problems.append(f"advance: a refused dispatch exited with {said!r}, so a sweep that "
                        "dispatched no coder pass reports the colour of one that did")
    return problems


def _refused_re_request_is_the_sweeps_own_problem(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    stranded = {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                "requested": ["o-r-reviewer"],
                "checks": [{"name": "reviewer", "conclusion": "FAILURE"}]}
    fake = FakeGitHub({7: dict(stranded), 8: dict(stranded)}, no_edit=[7])
    said = run_verb(channel, fake, lambda: move.advance())
    if "8" not in fake.edited or "o-r-reviewer" not in (fake.pulls["8"].get("requested") or []):
        problems.append(f"advance: a refused re-request left the rest at {fake.edited!r}")
    if not said or "#7" not in said:
        problems.append(f"advance: a refused re-request exited with {said!r}, so a sweep that "
                        "left a review request stranded reports the colour of one that "
                        "re-requested it")
    return problems


def _re_request_not_sticking_is_one_pull_requests_line(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    stranded = {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                "requested": ["o-r-reviewer"],
                "checks": [{"name": "reviewer", "conclusion": "FAILURE"}]}
    fake = FakeGitHub({7: dict(stranded), 8: dict(stranded)}, no_edit_sticks=[7])
    said = swept(channel, move, fake, problems)
    if "8" not in fake.edited or "o-r-reviewer" not in (fake.pulls["8"].get("requested") or []):
        problems.append(f"advance: a non-sticking re-request left the rest at {fake.edited!r}")
    if "#7" not in said:
        problems.append(f"advance: a non-sticking re-request reported {said!r}, so the pull "
                        "request left with a stranded review is named nowhere")
    return problems


def _merged_pull_request_stranded_review_is_one_pull_requests_line(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({
        7: {
            "behind": 0, "armed": False, "mergeable": "MERGEABLE",
            "state": "MERGED",
            "requested": ["o-r-reviewer"],
            "checks": [{"name": "reviewer", "conclusion": "FAILURE"}],
        },
        8: {
            "behind": 0, "armed": False, "mergeable": "MERGEABLE",
            "requested": ["o-r-reviewer"],
            "checks": [{"name": "reviewer", "conclusion": "FAILURE"}],
        },
    })
    said = swept(channel, move, fake, problems)
    if "8" not in fake.edited or "o-r-reviewer" not in (fake.pulls["8"].get("requested") or []):
        problems.append(f"advance: a merged pull request left the rest at {fake.edited!r}")
    if not said or "#7" not in said or "merged, not open" not in said:
        problems.append(f"advance: a merged pull request reported {said!r}, so the line "
                        "preventing a false red write is named nowhere")
    return problems


def _refused_mergeability_read_is_one_pull_requests_line(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING", "unknown": 1},
                       8: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING"}}, no_view=[7])
    said = swept(channel, move, fake, problems)
    if fake.dispatched != [("8", "rebase")]:
        problems.append(f"advance: a refused mergeability read left the rest at "
                        f"{fake.dispatched!r}, so the sweep ended at the pull request whose "
                        "read was refused rather than going on to the ones behind it")
    if "#7" not in said:
        problems.append(f"advance: a refused mergeability read reported {said!r}, so the pull "
                        "request it was left where it stands is named nowhere")
    return problems


def _named_and_merge_auto_dispatch_nothing(channel: Any, move: Any) -> list[str]:
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


def _named_conflicting_pull_request_refused(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True, "mergeable": "CONFLICTING"}},
                      no_rebase=[7])
    said = run_verb(channel, fake, lambda: move.advance("7"))
    if not said or "conflicts" not in said:
        problems.append(f"advance: a named conflicting pull request exited with {said!r}")
    return problems


def _dispatch_review_on_a_standing_verdict(channel: Any, move: Any, reviewer: str) -> list[str]:
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


def _dispatch_review_on_approval_with_failing_checks(channel: Any, move: Any, reviewer: str) -> list[str]:
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


def _dispatch_review_refused_without_a_request_for_changes(channel: Any, move: Any, reviewer: str) -> list[str]:
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


def _dispatch_review_refused_while_answered(channel: Any, move: Any, reviewer: str) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": [reviewer],
                           "verdicts": [(reviewer, "CHANGES_REQUESTED")]}})
    said = run_verb(channel, fake, lambda: move.dispatch_pass("7", "review"))
    if fake.dispatched:
        problems.append(f"dispatch: a verdict already answered dispatched {fake.dispatched!r}")
    if not said or "not yet given" not in said:
        problems.append(f"dispatch: the answered verdict was refused with {said!r}")
    return problems


def _dispatch_rebase_on_conflicting_not_on_behind(channel: Any, move: Any) -> list[str]:
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


def _dispatch_rebase_refused_by_hand(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    for case, pull in (("a branch that is not the loop's",
                        {"branch": "claude/issue-169-followup"}),
                       ("the solo's own branch", {"branch": "fix-the-thing"})):
        fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "CONFLICTING", **pull}})
        said = run_verb(channel, fake, lambda: move.dispatch_pass("7", "rebase"))
        if fake.dispatched:
            problems.append(f"dispatch: {case} dispatched {fake.dispatched!r}")
        if not said or "by hand" not in said:
            problems.append(f"dispatch: {case} was refused with {said!r}")
    stack = {6: {"behind": 0, "armed": False, "mergeable": "CONFLICTING", "layer": True},
             7: {"behind": 0, "armed": False, "mergeable": "CONFLICTING", "layer": True,
                 "base": "claude/issue-6"}}
    fake = FakeGitHub(stack)
    said = run_verb(channel, fake, lambda: move.dispatch_pass("7", "rebase"))
    if fake.dispatched or not said or "resolved from the bottom" not in said:
        problems.append(f"dispatch: a layer above a conflicting root dispatched "
                        f"{fake.dispatched!r} and was refused with {said!r}, where the root "
                        "is rebased first")
    fake = FakeGitHub(stack)
    said = run_verb(channel, fake, lambda: move.dispatch_pass("6", "rebase"))
    if fake.dispatched != [("6", "rebase")] or said:
        problems.append(f"dispatch: the root of a conflicting stack dispatched "
                        f"{fake.dispatched!r} and said {said!r}, where the root is any loop "
                        "branch's rebase")
    return problems


@check("dispatch probes", pre=True)
def dispatch_probes() -> list[str]:
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
      dispatched to rebase, and so is one carrying a request for changes the
      coder has not answered, which asks nobody for anything and so stands in
      no request GitHub reports — unless GitHub has shown it moving more
      recently than a run may last, where the verdict's own pass may be
      standing on the branch and a rebase dispatched beside it would
      force-push under it (solorepo's DR-237); an unanswered request for
      changes on a branch that still merges goes to review,
      unless it is recent enough that a run may still be standing on it; an
      approved one with failing checks to review; and a review request whose
      reviewer check failed without a verdict is re-requested
      (solorepo's DR-167, solorepo's DR-178, solorepo's #316). Nothing is
      dispatched for a branch nobody asked to review or to land, on which a
      Job may still be standing, for the solo's own branch, for a layer above
      a conflicting one, since a stack is resolved from the bottom and the
      root is rebased first, or for a Challenge the loop does not hold — `hard`,
      closed, `human`, which is what `stop` leaves, or unreadable, which is
      an Issue deleted or transferred under its branch (solorepo's DR-142).
      A refused write is the sweep's own problem rather than one pull
      request's, the refusal here being the token without the write it
      needs, which no pull request's state can cause and which stops the
      write taking for any of them: the sweep goes on to the rest and then
      exits naming the one it could not write for (solorepo's DR-238). Both
      writes it makes are held that way — the `coder.yml` dispatch, whose
      pass never starts, and the `pr edit` that re-requests a stranded
      review, which leaves the request stranded (solorepo's #656).
      A refused read of whether a branch still merges is the other way round,
      and one pull request's line: `mergeability` re-reads GitHub for an
      `UNKNOWN` answer, which is what GitHub says while it computes a merge
      ref and so is routine on the push this runs on, and that re-read fails
      the ordinary way — so the pull request it was refused for is named in
      the report and the one behind it in the list is still dispatched for
      (solorepo's #655). A re-request that does not stick is one pull request's
      line too: `request_review` reads back the requested reviewers after
      writing them, and if GitHub does not show the assignment the write was
      refused for that pull request alone — so it is named in the printed report
      and leaves the sweep green (solorepo's #656).
      Neither `merge --auto`, which holds the branch it is arming, nor a
      typed `advance <n>`, which names one somebody is asking about,
      dispatches, since neither is the merge on `main` that stranded a
      request; and both keep GitHub's refusal over a branch that conflicts
      where the sweep skips it, because nobody stands behind a named pull
      request but whoever typed the verb.
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
      unarmed one; it is refused before `mergeable` is asked for on a branch
      that is not the loop's shape and on the solo's own; and it is refused
      on a layer above a conflicting lower layer, which is the one refusal
      that asks GitHub first, since the lower layers' mergeability is what
      it turns on. A branch that is not the loop's shape,
      `claude/issue-169-followup` here, names no Challenge for a pass that
      could not finish to hand back to; `coder.yml` holds that refusal only
      after the dispatch, and for the nearly-right name it holds none at all,
      so the verb refuses first. A layer above a conflicting root is refused
      because rebasing it first would carry the root's unresolved commits as
      its own; the root is dispatched on the same terms as an unstacked loop
      branch, the stack being no condition on it, and so a stack is resolved
      from the bottom (solorepo's DR-133).

    `said` is read in every case whose whole assertion is an absence: a verb
    that died before dispatching leaves `dispatched` empty too, and without it
    a crash reads exactly like the filter doing its job. In a sweep it is what
    the verb printed rather than what it exited with, through `swept` from
    `probes/loops/advance.py`, which also holds the sweep's exit code green
    (solorepo's DR-238); `run_verb` reads the exit in the cases that name one
    pull request, where the exit code is the answer, and in the two refused
    writes, where the failure is the sweep's own and the exit code is the
    assertion. The fake's repository is `o/r`, so the reviewer's login is
    `o-r-reviewer`, as `channel.role_login` composes it (solorepo's DR-107).
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    channel.SETTLES = (3, 0)
    channel.MERGEABILITY = (3, 0)
    reviewer = "o-r-reviewer"
    return [problem for problems in (
        _conflicting_with_a_review_request_dispatches_rebase(channel, move),
        _unknown_is_waited_out(channel, move),
        _armed_conflicting_dispatched_not_rebased(channel, move),
        _approved_conflicting_dispatches_rebase(channel, move),
        _conflicting_changes_requested_dispatches_rebase(channel, move),
        _recent_conflicting_changes_requested_left_to_the_run(channel, move),
        _unanswered_changes_requested_dispatches_review(channel, move),
        _recent_changes_requested_left_to_the_run(channel, move),
        _approved_with_failing_checks_dispatches_review(channel, move),
        _stranded_review_request_re_requested(channel, move),
        _nothing_asked_dispatches_nothing(channel, move),
        _stack_root_rebased_by_sweep_refused_by_name(channel, move),
        _challenges_the_loop_does_not_hold(channel, move),
        _refused_dispatch_is_the_sweeps_own_problem(channel, move),
        _refused_re_request_is_the_sweeps_own_problem(channel, move),
        _refused_mergeability_read_is_one_pull_requests_line(channel, move),
        _re_request_not_sticking_is_one_pull_requests_line(channel, move),
        _merged_pull_request_stranded_review_is_one_pull_requests_line(channel, move),
        _named_and_merge_auto_dispatch_nothing(channel, move),
        _named_conflicting_pull_request_refused(channel, move),
        _dispatch_review_on_a_standing_verdict(channel, move, reviewer),
        _dispatch_review_on_approval_with_failing_checks(channel, move, reviewer),
        _dispatch_review_refused_without_a_request_for_changes(channel, move, reviewer),
        _dispatch_review_refused_while_answered(channel, move, reviewer),
        _dispatch_rebase_on_conflicting_not_on_behind(channel, move),
        _dispatch_rebase_refused_by_hand(channel, move)
    ) for problem in problems]

