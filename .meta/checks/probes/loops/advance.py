"""`advance`, `merge --auto` and the by-hand `dispatch` against a GitHub stood in for, in the states solorepo's #98 found them in.

One module for one probe, so a history log's receipt names the file holding it (solorepo's DR-209).
"""
import datetime

from collect import check
from probes.harness import (
    FakeGitHub,
    load_channel,
    run_verb,
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
