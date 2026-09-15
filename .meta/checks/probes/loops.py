"""The PR First loops, run against a GitHub stood in for (solorepo's DR-209).

Not invariants over the record: these load `.meta/say/move` and
`.meta/check_pr.py` and run the verbs the loops turn on — `advance`, `merge
--auto`, the by-hand `dispatch`, `request-review`, `stop` and the merge
manager — and the readers beside them: `--watch`, the `unheld` sweep, and
`--handoff`'s reading of an enacted decision. Every one reaches GitHub in every
branch, and the states reviewers found them wrong in (solorepo's #98,
solorepo's #195, solorepo's #316) cost a merge on trunk to reach for real and
are gone by the time anyone could look; so GitHub is answered from a dict or
from a list of polls, and each state is a case rather than an argument about a
code path nothing ran.

One module for one subject, so that a history log's receipt names the file
holding the probe it cites (solorepo's DR-209). The fakes and the loaders are
the harness's, and the gate over assertions takes no import from a test suite
(solorepo's DR-150).
"""
import datetime
import sys
from typing import Any

import citations
from collect import META, CouldNotRun, check
from probes.harness import (
    FakeGitHub,
    FakeIssue,
    WatchGitHub,
    load_channel,
    load_module,
    outcome,
    run_verb,
    stood_in,
)


@check("advance probes", pre=True)
def advance_probes():
    """`advance`, `merge --auto` and the by-hand `dispatch` against a fake GitHub, in the states solorepo's #98 found them in.

    Each case is one of the reviewer's reproductions on solorepo's #94, read
    off the code because `advance` reaches GitHub in every branch and, until
    `channel.gh` could be stood in for, what it did when a call failed was an
    argument. Both waits are shortened to nothing before the first case,
    `SETTLES` (solorepo's DR-158) and `MERGEABILITY` (solorepo's DR-133), and
    for one reason: what the cases hold is that a wait happens and waits for
    an answer, and the seconds it lasts are GitHub's business rather than a
    gate's. Every case that rebases reads the head back, and one puts a push
    inside the poll, so trunk's timings would be paid on each. Nothing
    restores them, because the process ends with the gate.

    The states, in the order they run:

    - The rebase and the re-arming. A rebase that drops the arming under a
      base that moved again, where the two read-backs are two questions
      (solorepo's #98). A refusal to rebase, a refusal to arm, and an arming
      `gh` reported that GitHub does not hold (solorepo's #93): each is one
      pull request's problem and not the sweep's, and the third is the one an
      exit code cannot see, and it leaves the pull request rebased and
      unarmed. A re-arming GitHub acts on inside the read-back window, because
      the last check went green and the merge cleared the `autoMergeRequest`
      that made it: the first read after it shows the pull request unarmed
      and open, neither of the two states that end the wait, and the
      read-back tolerates that read and ends on `MERGED` rather than spending
      its bound and reporting a lost arming over a branch that is on trunk
      (solorepo's #253). A rebase GitHub has taken and not yet shown, which
      read once is a failure that did not happen (solorepo's #245). A push
      landing between the opening `pr list` and the rebase, and one landing
      inside the `mergeability` poll — the window that is actually open,
      since an `UNKNOWN` sleeps and re-reads — which the compare and the wait
      must be anchored past (solorepo's #252); and the push that is itself a
      rebase, `leaves: 0`, where what is asserted is that `update-branch` is
      not called on a branch with nothing to rebase, and not what GitHub
      would answer to that, which is GitHub's fact and a fake modelling it
      either way would be asserting it. A head GitHub never moves, reported
      as itself and not as a branch still behind, because the rebase may yet
      land and drop the arming, and a pull request rebased and unarmed is out
      of reach of every later sweep, which reads only the armed ones
      (solorepo's DR-133). Then a named pull request that is not armed,
      refused in the exit code so that `advance <n> && <next step>` does not
      carry on, and taken with `held=True` by the caller that holds the
      branch, which is `merge --auto`'s path.
    - `merge --auto`. The arming happens though advancing did not, since
      armed and behind is what the next push to trunk sweeps up and rebased
      and unarmed is solorepo's #93. A stall is not reported over a merge that
      landed, which would be `merged` followed by an exit claiming the pull
      request armed and behind (solorepo's #46); nor over a branch a blip on
      the read-back left armed and current, since the exit code is the last
      thing the Job says.
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
    problems = []
    move.SETTLES = (3, 0)
    move.MERGEABILITY = (3, 0)

    fake = FakeGitHub({7: {"behind": 2, "armed": True, "drops": True, "again": 1}})
    said = run_verb(channel, fake, lambda: move.advance())
    if not fake.pulls["7"]["armed"]:
        problems.append("advance: a rebase that dropped the arming left it dropped")
    if not said or "still behind" not in said:
        problems.append(f"advance: a base that moved again reported {said!r}")

    fake = FakeGitHub({7: {"behind": 1, "armed": True}, 8: {"behind": 1, "armed": True}},
                      no_rebase=[7])
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.pulls["8"]["behind"]:
        problems.append("advance: a refusal on one pull request ended the sweep for the rest")
    if not said or "#7" not in said:
        problems.append(f"advance: the refusal it swallowed was reported as {said!r}")

    fake = FakeGitHub({7: {"behind": 1, "armed": True, "drops": True},
                       8: {"behind": 1, "armed": True}}, no_arm=[7])
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.pulls["8"]["behind"]:
        problems.append("advance: a refusal to arm one pull request ended the sweep")
    if not said or "clean status" not in said:
        problems.append(f"advance: the refusal to arm was reported as {said!r}")

    fake = FakeGitHub({7: {"behind": 1, "armed": True, "drops": True}}, no_stick=[7])
    said = run_verb(channel, fake, lambda: move.advance())
    if not said or "#7" not in said:
        problems.append(f"advance: an arming that did not take was reported as {said!r}")

    fake = FakeGitHub({7: {"behind": 1, "armed": True, "drops": True, "slow": 1}},
                      lands=[7])
    said = run_verb(channel, fake, lambda: move.advance())
    if said:
        problems.append(f"advance: a re-arming that merged reported {said!r}")
    if fake.pulls["7"]["state"] != "MERGED":
        problems.append("advance: the case that models a merge in the window did not merge")
    if fake.reads.get("7", 0) != 7:
        problems.append("advance: the wait for merge in the window did not stop early, "
                        f"costing {fake.reads.get('7', 0)} reads")

    fake = FakeGitHub({7: {"behind": 1, "armed": True, "drops": True, "slow": 2}})
    said = run_verb(channel, fake, lambda: move.advance())
    if said:
        problems.append(f"advance: a rebase GitHub had not shown yet reported {said!r}")
    if not fake.pulls["7"]["armed"]:
        problems.append("advance: it read the arming off the head GitHub had not moved, so "
                        "the arming the move dropped stayed dropped")

    fake = FakeGitHub({7: {"behind": 1, "armed": True, "drops": True, "slow": 2, "pushed": 1}})
    said = run_verb(channel, fake, lambda: move.advance())
    if said:
        problems.append(f"advance: a push landing before the rebase reported {said!r}")
    if not fake.pulls["7"]["armed"]:
        problems.append("advance: it read the rebase off the commit the sweep listed rather "
                        "than the one it asked GitHub to rebase, so a push in between "
                        "answered for the rebase and the arming it dropped stayed dropped")

    fake = FakeGitHub({7: {"behind": 1, "armed": True, "pushed": 1, "leaves": 0}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.pulls["7"].get("rebased"):
        problems.append("advance: a push brought the branch current inside the window and it "
                        "asked GitHub to rebase a branch with nothing to rebase, on a compare "
                        "of the commit that push orphaned")
    if said:
        problems.append(f"advance: a push that brought the branch current reported {said!r}")

    fake = FakeGitHub({7: {"behind": 1, "armed": True, "unknown": 1, "pushed": 2, "leaves": 0}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.pulls["7"].get("rebased"):
        problems.append("advance: a push landed while it waited on `mergeability` and it "
                        "rebased the branch that push brought current, so the read the call "
                        "was made against was taken before the wait rather than after it")
    if said:
        problems.append(f"advance: a push landing inside the poll reported {said!r}")

    fake = FakeGitHub({7: {"behind": 1, "armed": True, "slow": 9}})
    said = run_verb(channel, fake, lambda: move.advance())
    if not said or "has not moved it" not in said:
        problems.append(f"advance: a head GitHub never moved was reported as {said!r}")
    if said and "still behind" in said:
        problems.append("advance: a rebase GitHub had not shown was reported as a branch "
                        "that is still behind its base")

    fake = FakeGitHub({7: {"behind": 1, "armed": False}})
    said = run_verb(channel, fake, lambda: move.advance("7"))
    if not fake.pulls["7"]["behind"]:
        problems.append("advance: it rebased a pull request nobody had asked to land")
    if not said or "not armed" not in said:
        problems.append(f"advance: it declined a named pull request and said {said!r}")
    if run_verb(channel, fake, lambda: move.advance("7", held=True)):
        problems.append("advance: the caller that holds the branch was refused too")
    if fake.pulls["7"]["behind"]:
        problems.append("advance: it refused the caller that holds the branch")

    fake = FakeGitHub({7: {"behind": 1, "armed": False}}, no_rebase=[7])
    said = run_verb(channel, fake, lambda: move.merge("7", auto=True))
    if not fake.pulls["7"]["armed"]:
        problems.append("merge --auto: a failed advance left the pull request unarmed")
    if not said or "conflicts" not in said:
        problems.append(f"merge --auto: the failed advance was reported as {said!r}")

    fake = FakeGitHub({7: {"behind": 1, "armed": False}}, no_rebase=[7], lands=[7])
    said = run_verb(channel, fake, lambda: move.merge("7", auto=True))
    if said:
        problems.append(f"merge --auto: a merge that landed exited with {said!r}")

    fake = FakeGitHub({7: {"behind": 1, "armed": True}}, blip=[7])
    said = run_verb(channel, fake, lambda: move.merge("7", auto=True))
    if not fake.pulls["7"]["armed"] or fake.pulls["7"]["behind"]:
        problems.append("merge --auto: a blip on the read-back left the pull request "
                        f"{fake.pulls['7']!r}")
    if said:
        problems.append(f"merge --auto: a stall over a current branch exited with {said!r}")

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

    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING", "unknown": 2}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("7", "rebase")]:
        problems.append("advance: it took the first `UNKNOWN` for an answer and dispatched "
                        f"{fake.dispatched!r}")
    if said:
        problems.append(f"advance: waiting out an `UNKNOWN` exited with {said!r}")

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

    fake = FakeGitHub({7: {"behind": 1, "armed": False, "mergeable": "CONFLICTING",
                           "verdicts": [("o-r-reviewer", "APPROVED")]}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("7", "rebase")]:
        problems.append(f"advance: the approved conflicting one dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"advance: the approved conflicting one exited with {said!r}")

    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                           "verdicts": [("o-r-reviewer", "CHANGES_REQUESTED")]}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("7", "review")]:
        problems.append(f"advance: unanswered changes requested one dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"advance: unanswered changes requested one exited with {said!r}")

    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                           "updatedAt": datetime.datetime.now(datetime.UTC).isoformat(),
                           "verdicts": [("o-r-reviewer", "CHANGES_REQUESTED")]}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched:
        problems.append("advance: recent changes requested PR dispatched "
                        f"{fake.dispatched!r} during active run window")
    if said:
        problems.append(f"advance: recent changes requested PR exited with {said!r}")

    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                           "checks": [{"name": "gate", "conclusion": "FAILURE"}],
                           "verdicts": [("o-r-reviewer", "APPROVED")]}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("7", "review")]:
        problems.append(f"advance: approved PR with failing checks dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"advance: approved PR with failing checks exited with {said!r}")

    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "MERGEABLE",
                           "requested": ["o-r-reviewer"],
                           "checks": [{"name": "reviewer", "conclusion": "FAILURE"}]}})
    said = run_verb(channel, fake, lambda: move.advance())
    if "o-r-reviewer" not in fake.pulls["7"]["requested"] or "7" not in fake.edited:
        problems.append(f"advance: stranded review request was not re-requested: {fake.pulls['7']!r}")
    if said:
        problems.append(f"advance: stranded review request exited with {said!r}")

    fake = FakeGitHub({7: {"behind": 0, "armed": False, "mergeable": "CONFLICTING"},
                       8: {"behind": 0, "armed": True,
                           "mergeable": "CONFLICTING", "branch": "solo/whatever"}})
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched:
        problems.append(f"advance: it dispatched {fake.dispatched!r}, which nobody had asked "
                        "to review or to land, or which was not a loop's branch")
    if said:
        problems.append(f"advance: the case that should dispatch nothing exited with {said!r}")

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

    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING"},
                       8: {"behind": 0, "armed": False, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING"}}, no_dispatch=[7])
    said = run_verb(channel, fake, lambda: move.advance())
    if fake.dispatched != [("8", "rebase")]:
        problems.append(f"advance: a refused dispatch left the rest at {fake.dispatched!r}")
    if not said or "#7" not in said:
        problems.append(f"advance: the refused dispatch was reported as {said!r}")

    fake = FakeGitHub({7: {"behind": 0, "armed": True, "requested": ["reviewer"],
                           "mergeable": "CONFLICTING"}})
    named = run_verb(channel, fake, lambda: move.advance("7"))
    merging = run_verb(channel, fake, lambda: move.merge("7", auto=True))
    if fake.dispatched:
        problems.append(f"advance: a named pull request dispatched {fake.dispatched!r}")
    if named or merging:
        problems.append(f"advance: the two callers that dispatch nothing exited with "
                        f"{named!r} and {merging!r}")

    fake = FakeGitHub({7: {"behind": 1, "armed": True, "mergeable": "CONFLICTING"}},
                      no_rebase=[7])
    said = run_verb(channel, fake, lambda: move.advance("7"))
    if not said or "conflicts" not in said:
        problems.append(f"advance: a named conflicting pull request exited with {said!r}")

    reviewer = "o-r-reviewer"

    fake = FakeGitHub({7: {"behind": 0, "armed": False,
                           "verdicts": [(reviewer, "CHANGES_REQUESTED"),
                                        (reviewer, "COMMENTED")]}})
    said = run_verb(channel, fake, lambda: move.dispatch_pass("7", "review"))
    if fake.dispatched != [("7", "review")]:
        problems.append(f"dispatch: a verdict standing dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"dispatch: the pass it should have started exited with {said!r}")

    fake = FakeGitHub({7: {"behind": 0, "armed": False,
                           "checks": [{"name": "gate", "conclusion": "FAILURE"}],
                           "verdicts": [(reviewer, "APPROVED")]}})
    said = run_verb(channel, fake, lambda: move.dispatch_pass("7", "review"))
    if fake.dispatched != [("7", "review")]:
        problems.append(f"dispatch: approved PR with failing checks dispatched {fake.dispatched!r}")
    if said:
        problems.append(f"dispatch: approved PR with failing checks exited with {said!r}")

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

    fake = FakeGitHub({7: {"behind": 0, "armed": False, "requested": [reviewer],
                           "verdicts": [(reviewer, "CHANGES_REQUESTED")]}})
    said = run_verb(channel, fake, lambda: move.dispatch_pass("7", "review"))
    if fake.dispatched:
        problems.append(f"dispatch: a verdict already answered dispatched {fake.dispatched!r}")
    if not said or "not yet given" not in said:
        problems.append(f"dispatch: the answered verdict was refused with {said!r}")

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


@check("handoff probes", pre=True)
def handoff_probes():
    """`request-review` on a branch GitHub reports as `CONFLICTING`, `--watch` on one that becomes it, and the `unheld` sweep over the shapes a webhook should have carried.

    The two readings of solorepo's #195: a request made on a conflicting
    branch is held by GitHub and answered by nobody, since there is no merge
    ref and so `review.yml`'s `pull_request` trigger creates no run, and
    neither the verb nor the watch said so, which is why solorepo's #192 stood
    unreviewed. Both halves are a state GitHub reports and a sentence about
    it, so both are probed by standing GitHub in, as `advance probes` does:
    the state costs a merge on trunk to reach for real and is gone by the time
    anyone could look. `MERGEABILITY` is shortened to nothing first, for the
    reason `advance probes` gives: that the verb waits out an `UNKNOWN` is the
    claim, and the seconds it waits are GitHub's business.

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
    problems = []
    move.MERGEABILITY = (3, 0)

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

    check_pr = citations.load_check_pr()

    def watched(polls):
        """What `--watch` printed on pull request 7, GitHub answering one poll at a time from `polls`."""
        with stood_in(check_pr, gh=WatchGitHub(polls)):
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

    def pull_of(number, title, **fields):
        """A pull request on the loop's branch for `number`, based on trunk, not a draft, with no review requested, and `fields` over that."""
        return {"number": number, "title": title, "headRefName": f"claude/issue-{number}",
                "baseRefName": "main", "isDraft": False, "reviewRequests": [], **fields}

    armed = pull_of(10, "Stuck armed PR", autoMergeRequest={"enabledAt": "2026-09-11"},
                    mergeable="MERGEABLE")
    with stood_in(check_pr, threads=lambda n: [{"id": "t1", "isResolved": False}]):
        owed = check_pr.unheld([armed], minutes=30, clean={10})
    if len(owed) != 1 or "unresolved conversation" not in owed[0]:
        problems.append(f"unheld: an armed PR with unresolved threads reported {owed!r}")

    with stood_in(check_pr, threads=lambda n: [{"id": "t1", "isResolved": True}]):
        clean_owed = check_pr.unheld([armed], minutes=30, clean={10})
        if clean_owed:
            problems.append(f"unheld: an armed PR with no unresolved threads reported {clean_owed!r}")

        recent = {**armed, "updatedAt": datetime.datetime.now(datetime.UTC).isoformat()}
        recent_owed = check_pr.unheld([recent], minutes=30, clean={10},
                                      unresolved={10: [{"id": "t1", "isResolved": False}]})
        if recent_owed:
            problems.append(f"unheld: recent armed PR reported {recent_owed!r} instead of passing in silence")

        reviewer_name = check_pr.role_login("reviewer")
        approved = [{"author": {"login": reviewer_name}, "state": "APPROVED"}]
        changes_requested = [{"author": {"login": reviewer_name}, "state": "CHANGES_REQUESTED"}]
        approved_conflicting = check_pr.unheld(
            [pull_of(11, "Approved conflicting PR", mergeable="CONFLICTING", latestReviews=approved)],
            minutes=30, clean={11})
        if len(approved_conflicting) != 1 or "approved, on a branch that conflicts" not in approved_conflicting[0]:
            problems.append(f"unheld: approved conflicting PR reported {approved_conflicting!r}")

        old_time = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=60)).isoformat()
        gate_failed = [{"name": "gate", "conclusion": "FAILURE", "startedAt": "2026-09-11T12:00:00Z"}]
        gate_passed = [{"name": "gate", "conclusion": "SUCCESS", "startedAt": "2026-09-11T12:00:00Z"}]
        idle = (
            ("changes requested PR", "medium", set(),
             ("changes requested by reviewer, and unanswered",),
             pull_of(12, "Changes requested PR", mergeable="MERGEABLE", statusCheckRollup=gate_failed,
                     latestReviews=changes_requested, updatedAt=old_time)),
            ("green PR with human challenge", "human", {13},
             (f"while #{'13'} is at human",),
             pull_of(13, "Human challenge PR", mergeable="MERGEABLE", statusCheckRollup=gate_passed,
                     updatedAt=old_time)),
            ("green conflicting PR with human challenge", "human", {14},
             ("rebase claude/issue-14 onto main",),
             pull_of(14, "Human conflicting PR", mergeable="CONFLICTING", statusCheckRollup=gate_passed,
                     updatedAt=old_time)),
            ("green PR with hard challenge", "hard", {15},
             (f"while #{'15'} is at hard",),
             pull_of(15, "Hard challenge PR", mergeable="MERGEABLE", statusCheckRollup=gate_passed,
                     updatedAt=old_time)),
            ("approved failing loop PR", "medium", set(),
             ("approved, with failing checks", ".meta/say/move dispatch 16"),
             pull_of(16, "Approved failing loop PR", mergeable="MERGEABLE", statusCheckRollup=gate_failed,
                     latestReviews=approved, updatedAt=old_time)),
            ("approved failing human PR", "hard", set(),
             ("approved, with failing checks", "fix the failing checks"),
             pull_of(17, "Approved failing human PR", mergeable="MERGEABLE", statusCheckRollup=gate_failed,
                     latestReviews=approved, updatedAt=old_time)),
            ("stranded reviewer PR", "medium", set(),
             ("reviewer check failed without a verdict", ".meta/say/move request-review 18"),
             pull_of(18, "Stranded reviewer PR", mergeable="MERGEABLE",
                     reviewRequests=[{"login": reviewer_name}],
                     statusCheckRollup=[{"name": "reviewer", "conclusion": "FAILURE",
                                         "startedAt": "2026-09-11T12:00:00Z"}],
                     updatedAt=old_time)),
            ("approved conflicting hard PR", "hard", set(),
             (f"Challenge #{'19'} is hard so the loop stands down",),
             pull_of(19, "Approved conflicting hard PR", mergeable="CONFLICTING",
                     latestReviews=approved, updatedAt=old_time)),
        )
        for case, level, clean, phrases, pull in idle:
            with stood_in(check_pr, gh=lambda *a, level=level: {"state": "OPEN", "labels": [{"name": level}]}):
                owed = check_pr.unheld([pull], minutes=30, clean=clean)
            if len(owed) != 1 or any(phrase not in owed[0] for phrase in phrases):
                problems.append(f"unheld: {case} reported {owed!r}")
    return problems


@check("enacted probes", pre=True)
def enacted_probes():
    """`--handoff`'s reading of a decision against the artifacts the branch edits.

    Three parts, and they fail differently. The judgement, which edited
    artifacts a settled decision leaves unnamed, is run against a branch stood
    in for, because the real one is whatever this session happens to be doing
    and a check cannot be written against that: a branch settling no decision,
    one settling the first decision on disk beside a declared non-record
    Artifact, and that decision read as adopted and naming nothing. Then the
    ordering the step depends on: it reads the record's rendered index, so it
    is skipped, and says so rather than answering, wherever that page's
    freshness is not established — a render that could not run leaves it
    unknown, and `ok` over an unknown is the reading the ordering exists to
    refuse. The render answers under two prefixes, `stale` and `unrendered`,
    and a page nothing renders is as unestablished as a stale one, since
    `just render` writes nothing for it; so the index arriving under either
    word skips the step, a page that is not the index under either word does
    not, and each finding names its page, which is the repair the coder
    needs. The step's own unknown is a base git cannot resolve: `git diff`
    against it exits non-zero, and read as an empty diff that would be a
    branch reported to settle no decision, `ok` over a diff nobody read.
    Last, the readers under all of it are run against the tree itself,
    because their failure is silence: both are regexes over text
    `check_pr.py` has no YAML reader for, and a reformat of either file would
    leave them matching nothing and every question answered green. What is
    held is that they still find something and still agree, every file the
    record's rendered table names being a declared Artifact, which is the
    claim a drift in either shape breaks first.
    """
    check_pr = citations.load_check_pr()
    problems = []

    def read(changed):
        """`unenacted("origin/main")` with the branch's diff stood in for by `changed`."""
        with stood_in(check_pr, touched=lambda base: changed):
            return check_pr.unenacted("origin/main")

    found, note = read([".meta/arc/deploy", ".meta/say/move"])
    if found or "settles no decision" not in note:
        problems.append(f"unenacted: a branch settling no decision reported {found!r}, {note!r}")

    decisions = sorted((META / "assertions" / "decisions").glob("DR-*.yaml"))
    if not decisions:
        return CouldNotRun("no decision files found in assertions/decisions/")
    sample = decisions[0]
    number = int(sample.stem.removeprefix("DR-"))
    entry = f".meta/assertions/decisions/{sample.name}"
    artifact = next((p for p in check_pr.artifact_map().values()
                     if not any(p.startswith(r) for r in check_pr.RECORD)), "AGENTS.md")
    found, note = read([entry, artifact])
    if found:
        problems.append(f"unenacted: DR-{number:03d} (valid) reported problems {found!r}")

    with stood_in(check_pr, parse_decision_yaml=lambda path: ("ADOPTED", [])):
        found, note = read([entry])
    if not found or f"DR-{number:03d}" not in found[0]:
        problems.append(f"unenacted: DR-{number:03d} with no artifacts did not report expected problem, got {found!r}")

    def handed_off(render):
        """What `handoff("origin/main")` printed with `RENDER` stood in for by the command `render`, and the bases the enacted step was asked about, the step itself answering nothing."""
        asked = []
        with stood_in(check_pr, RENDER=render,
                      unenacted=lambda base: (asked.append(base), ([], ""))[1]):
            said = outcome(lambda: check_pr.handoff("origin/main")).out
        return asked, said.splitlines()

    asked, lines = handed_off(["no-such-program-here"])
    enacted = [line for line in lines if "enacted" in line]
    if asked or not enacted or not all(line.startswith("?") for line in enacted):
        problems.append(f"handoff: with the render unrunnable it said {enacted!r} and asked "
                        f"{len(asked)} question(s) of an index whose freshness is unknown")

    index = check_pr.INDEX.split("/")[-1]
    for answer, run in ((f"unrendered: {index}", False),
                        (f"stale: {index}", False),
                        ("unrendered: justfile", True),
                        ("stale: justfile", True)):
        asked, lines = handed_off([sys.executable, "-c",
                                   f"import sys; print({answer!r}); sys.exit(1)"])
        enacted = [line for line in lines if " enacted" in line]
        if bool(asked) is not run or not enacted or any(
                line.startswith("?") is run for line in enacted):
            problems.append(f"handoff: the render answering {answer!r} left the enacted step "
                            f"saying {enacted!r}, which is not the "
                            + ("reading" if run else "skip") + " that page calls for")
        page = answer.split(": ", 1)[1]
        if not any(line.startswith("x ") and page in line for line in lines):
            problems.append(f"handoff: the render answering {answer!r} produced no finding "
                            "naming the page, so the repair the coder needs is unsaid")

    found, note = check_pr.unenacted("no-such-ref-on-any-checkout")
    if found is not None:
        problems.append(f"unenacted: an unresolvable base answered {found!r}, {note!r}, "
                        "rather than saying the diff went unread")

    declared, named = check_pr.artifacts(), check_pr.accounted()
    if not declared or not named:
        problems.append(f"the handoff's readers found {len(declared)} declared artifact(s) and "
                        f"{len(named)} accounted for; a regex over a file that has been "
                        "reformatted matches nothing and answers every question green")
    stray = sorted(set(named) - declared)
    if stray:
        problems.append(f"the record's table names {stray}, which no `artifacts:` list "
                        "declares; the two readers disagree about what a path is")
    return problems


@check("stop probes", pre=True)
def stop_probes():
    """`stop` against one Issue's labels and assignees: the hand-back, the refusal, and a GitHub that fails every call.

    A stop on a Challenge labels it `human`, removes the level it was at, and
    releases the assignee (solorepo's DR-112); a stop on an Issue that is not
    a Challenge is refused, naming the label it lacks; and a GitHub that fails
    every call, which is what a deleted Issue or a token without the scope
    looks like to the channel, is tolerated without an exit, each step warning
    on stderr rather than ending the hand-back.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    problems = []

    def stopped(fake, issue, body):
        """`stop(issue, body)` against `fake`: what it exited with, and what it printed on both streams."""
        with stood_in(channel, gh=fake):
            return outcome(lambda: move.stop(issue, body))

    fake = FakeIssue(["challenge", "medium"], assignees=["o-r-coder"])
    ended = stopped(fake, "7", "stopped working")
    if ended.code is not None:
        problems.append(f"stop: normal stop failed with error: {ended.code}")
    if "human" not in fake.labels:
        problems.append("stop: normal stop did not label issue as `human`")
    if "medium" in fake.labels:
        problems.append("stop: normal stop did not remove the stale level label")
    if "o-r-coder" in fake.assignees:
        problems.append("stop: normal stop did not release the assignee")

    fake = FakeIssue(["medium"], assignees=["o-r-coder"])
    ended = stopped(fake, "7", "stopped working")
    if ended.code is None or "not a Challenge" not in ended.code:
        problems.append("stop: stopping on a non-Challenge should refuse with label error, "
                        f"got: {ended.code}")

    fake = FakeIssue(["challenge", "medium"], fail=True)
    ended = stopped(fake, "7", "stopped working")
    if ended.code is not None:
        problems.append("stop: persistent API failure should be tolerated without crashing, "
                        f"but got: {ended.code}")
    if "warning" not in ended.err:
        problems.append("stop: persistent API failure should print warnings to stderr")
    return problems


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
    problems = []
    reviewer = "owner-repo-reviewer"

    def evaluated(pull):
        """`evaluate_pr` of `pull` as the reviewer's account over `owner/repo`."""
        return move.evaluate_pr(pull, reviewer, "owner", "repo")

    ok, reasons = evaluated({"number": 1, "isDraft": True})
    if ok or "draft" not in reasons:
        problems.append("merge manager: draft PR was reported as eligible")

    green = [{"conclusion": "SUCCESS"}]
    approved = [{"author": {"login": reviewer}, "state": "APPROVED"}]
    refused = (
        ("PR with empty checks rollup", "checks pending",
         {"mergeable": "MERGEABLE", "statusCheckRollup": []}),
        ("PR with failing check", "checks failing",
         {"mergeable": "MERGEABLE", "statusCheckRollup": [{"name": "gate", "conclusion": "FAILURE"}]}),
        ("conflicting PR", "conflicts",
         {"mergeable": "CONFLICTING", "statusCheckRollup": green}),
        ("behind PR", "behind",
         {"mergeable": "MERGEABLE", "mergeStateStatus": "BEHIND", "statusCheckRollup": green}),
        ("PR with changes requested", "changes requested",
         {"mergeable": "MERGEABLE", "statusCheckRollup": green,
          "latestReviews": [{"author": {"login": reviewer}, "state": "CHANGES_REQUESTED"}]}),
        ("unreviewed PR", "no review",
         {"mergeable": "MERGEABLE", "statusCheckRollup": green, "latestReviews": []}),
        ("PR with unresolved threads", "unresolved",
         {"mergeable": "MERGEABLE", "statusCheckRollup": green, "latestReviews": approved,
          "reviewThreads": [{"isResolved": False}]}),
        ("PR targeting non-main branch", "base is feature-branch, not main",
         {"mergeable": "MERGEABLE", "baseRefName": "feature-branch", "statusCheckRollup": green,
          "latestReviews": approved, "reviewThreads": [{"isResolved": True}]}),
    )
    for case, phrase, pull in refused:
        ok, reasons = evaluated({"number": 1, "isDraft": False, **pull})
        if ok or not any(phrase in r for r in reasons):
            problems.append(f"merge manager: {case} was reported as eligible")

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

    def broken_graphql(*args, **kwargs):
        """A GraphQL that raises, whatever it is asked."""
        raise RuntimeError("GraphQL outage")

    with stood_in(channel, graphql=broken_graphql):
        ok_th, msg_th = move.check_threads({"number": 99}, "owner", "repo")
    if ok_th or "could not read conversations" not in msg_th:
        problems.append(f"merge manager: check_threads did not fail closed on exception: {msg_th}")

    ok, reasons = evaluated({"number": 1, "isDraft": False, "mergeable": "MERGEABLE",
                             "baseRefName": "main", "statusCheckRollup": green,
                             "latestReviews": approved, "reviewThreads": [{"isResolved": True}]})
    if not ok or reasons != ["eligible"]:
        problems.append(f"merge manager: eligible PR failed evaluation: {reasons}")

    pulls = [
        {"number": 10, "title": "stack base PR", "headRefName": "branch-a", "baseRefName": "main",
         "isDraft": False, "mergeable": "MERGEABLE", "statusCheckRollup": green,
         "latestReviews": approved, "reviewThreads": [{"isResolved": True}],
         "body": "implements base", "additions": 100, "deletions": 20},
        {"number": 11, "title": "dependent PR", "headRefName": "branch-b", "baseRefName": "main",
         "isDraft": False, "mergeable": "MERGEABLE", "statusCheckRollup": green,
         "latestReviews": approved, "reviewThreads": [{"isResolved": True}],
         "body": f"**Waits on.** #{'10'}", "additions": 500, "deletions": 100},
        {"number": 12, "title": "unreviewed PR", "headRefName": "branch-c", "baseRefName": "main",
         "isDraft": False, "mergeable": "MERGEABLE", "statusCheckRollup": green,
         "latestReviews": [], "body": ""},
        {"number": 13, "title": "layered PR with non-main base", "headRefName": "branch-d",
         "baseRefName": "branch-a", "isDraft": False, "mergeable": "MERGEABLE",
         "statusCheckRollup": green, "latestReviews": approved,
         "reviewThreads": [{"isResolved": True}], "body": ""},
    ]
    issues = [
        {"number": 50, "body": f"**Waits on.** #{'10'}", "title": "blocked issue"},
        {"number": 51, "body": "**Waits on.** Nothing", "title": "natively blocked issue",
         "blockedBy": {"nodes": [{"number": 10}]}},
    ]

    class ManagerFake:
        """As much of GitHub as `merge_manager` asks about, over `owner/repo`: the four pull requests, the two Issues, every review thread resolved, and the merges asked for, recorded in `merged`.

        `pr view` answers `MERGED` once anything has been merged, `api
        .../pulls/10` answers a `stack` object so the winner is merged as a
        stack, and any other call answers an empty dict.
        """

        def __init__(self):
            self.merged = []

        def gh(self, *args, parse=True):
            """One `gh` call, answered as the class docstring says."""
            head = args[:2]
            if head == ("repo", "view") or args[0] == "repo":
                return {"nameWithOwner": "owner/repo", "deleteBranchOnMerge": True}
            if head == ("pr", "list"):
                return list(pulls)
            if head == ("issue", "list"):
                return list(issues)
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

    fake = ManagerFake()
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


@check("merge manager advance probes", pre=True)
def merge_manager_advance_probes():
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
    outdate the anchored comment PR First's seventh step parks work on. A
    refusal is printed and the verb still exits 0, since `merge.yml` runs on a
    fifteen-minute schedule and a stack base that stays behind would otherwise
    paint it red on the clock. Under `--dry-run` the same GitHub is named and
    not touched, and with `stranded=False` — what `merge.yml` passes on the push
    to `main` that `advance.yml` answers itself — nothing is named or touched.

    The conversations are read where production reads them, over GraphQL:
    `MERGE_MANAGER_FIELDS` does not ask `pr list` for `reviewThreads` and `gh`
    answers only the fields it is asked for, so a fixture injecting the field
    into the listing would take a branch no run of `merge.yml` takes.

    Both waits are shortened to nothing, as in `advance_probes` above and for
    the same reason: what the cases hold is that the rebase is read back, and
    the seconds it waits are GitHub's business.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    problems: list[str] = []
    move.SETTLES = (3, 0)
    move.MERGEABILITY = (3, 0)
    reviewer = "o-r-reviewer"
    green = [{"name": "gate", "conclusion": "SUCCESS"}]
    red = [{"name": "gate", "conclusion": "FAILURE"}]
    approved = [{"author": {"login": reviewer}, "state": "APPROVED"}]
    talking = {24}

    def stranded(checks: Any = green, reviews: Any = approved, **fields: Any) -> dict[str, Any]:
        """The fields `merge_manager` reads of a pull request that is behind its base."""
        return {"isDraft": False, "mergeStateStatus": "BEHIND", "statusCheckRollup": checks,
                "latestReviews": reviews, **fields}

    def conversations(query: Any, number: int = 0, **_: Any) -> Any:
        """The review threads GitHub answers for `number`: resolved, unless the case is talking."""
        return {"data": {"repository": {"pullRequest": {
            "reviewThreads": {"nodes": [{"isResolved": number not in talking}]}}}}}

    def github() -> Any:
        """The five pull requests, fresh, so a dry run and a real run do not share a state."""
        return FakeGitHub({
            20: {"behind": 2, "armed": False, "verdicts": [(reviewer, "APPROVED")],
                 "manager": stranded()},
            21: {"behind": 2, "armed": False, "verdicts": [(reviewer, "APPROVED")],
                 "manager": stranded()},
            22: {"behind": 0, "armed": False, "base": "claude/issue-21",
                 "manager": stranded(checks=[], reviews=[], mergeStateStatus=None)},
            23: {"behind": 2, "armed": False, "verdicts": [(reviewer, "APPROVED")],
                 "manager": stranded(checks=red)},
            24: {"behind": 2, "armed": False, "verdicts": [(reviewer, "APPROVED")],
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

    fake = github()
    with stood_in(channel, gh=manager_github(fake), graphql=conversations):
        dry = outcome(lambda: move.merge_manager(dry_run=True))
    if f"dry run — not advancing #{'20'}" not in dry.out:
        problems.append(f"merge manager: a dry run did not name the stranded pull request:\n{dry.out}")
    if any(pull.get("rebased") for pull in fake.pulls.values()):
        problems.append("merge manager: a dry run rebased a branch")

    fake = github()
    with stood_in(channel, gh=manager_github(fake), graphql=conversations):
        held = outcome(lambda: move.merge_manager(dry_run=False, stranded=False))
    if any(pull.get("rebased") for pull in fake.pulls.values()):
        problems.append("merge manager: it rebased a branch on the event advance.yml answers")
    if "advancing" in held.out:
        problems.append(f"merge manager: it named a stranded pull request it had left alone:\n{held.out}")

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
    return problems
