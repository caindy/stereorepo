"""`advance`, `merge` and the by-hand `dispatch` against a GitHub stood in for, in the states solorepo's #98 found them in.

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""

from typing import Any

from checks.collect import check
from checks.probes.harness import (
    FakeGitHub,
    environment,
    load_channel,
    outcome,
    run_verb,
    stood_in,
)

REPORTED = "reported a problem of their own"
"""The header `advance` prints the failures it collected under, and so where a sweep's report starts in its output."""


def swept(channel: Any, move: Any, fake: FakeGitHub, problems: list[str]) -> str:
    """One `advance` sweep against `fake`: what it reported about the pull requests it read.

    The answer is the text after `REPORTED`, which is every failure the sweep
    collected and nothing it printed about the work it did. A sweep that read
    every open pull request is green whatever those pull requests reported
    (solorepo's DR-238), so the exit code is asserted here rather than in each
    case, and an exit is added to `problems` under the case that took it.

    Args:
        channel: The channel module whose `gh` is stood in by `fake`.
        move: The `move` program holding `advance`.
        fake: The `FakeGitHub` standing in for GitHub.
        problems: The case's findings, which an exit code is appended to.

    Returns:
        str: The sweep's report of the pull requests that failed, empty when none did.
    """
    with (stood_in(channel, gh=fake),
          environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe", AI_AGENT="probe")):
        ran = outcome(lambda: move.advance())
    if ran.code is not None:
        problems.append("advance: a sweep that read every open pull request exited with "
                        f"{ran.code!r}, so its colour answers for their weather rather than "
                        "for the sweep")
    return str(ran.out.partition(REPORTED)[2])


def _rebase_under_a_base_that_moved_again(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 2, "armed": True, "drops": True, "again": 1}})
    said = swept(channel, move, fake, problems)
    if not fake.pulls["7"]["armed"]:
        problems.append("advance: a rebase that dropped the arming left it dropped")
    if not said or "still behind" not in said:
        problems.append(f"advance: a base that moved again reported {said!r}")
    return problems


def _refusal_to_rebase_one_pull_request(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True}, 8: {"behind": 1, "armed": True}},
                      no_rebase=[7])
    said = swept(channel, move, fake, problems)
    if fake.pulls["8"]["behind"]:
        problems.append("advance: a refusal on one pull request ended the sweep for the rest")
    if not said or "#7" not in said:
        problems.append(f"advance: the refusal it swallowed was reported as {said!r}")
    return problems


def _refusal_to_arm_one_pull_request(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True, "drops": True},
                       8: {"behind": 1, "armed": True}}, no_arm=[7])
    said = swept(channel, move, fake, problems)
    if fake.pulls["8"]["behind"]:
        problems.append("advance: a refusal to arm one pull request ended the sweep")
    if not said or "clean status" not in said:
        problems.append(f"advance: the refusal to arm was reported as {said!r}")
    return problems


def _arming_github_did_not_hold(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True, "drops": True}}, no_stick=[7])
    said = swept(channel, move, fake, problems)
    if not said or "#7" not in said:
        problems.append(f"advance: an arming that did not take was reported as {said!r}")
    return problems


def _re_arming_that_merged_in_the_window(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True, "drops": True, "slow": 1}},
                      lands=[7])
    said = swept(channel, move, fake, problems)
    if said:
        problems.append(f"advance: a re-arming that merged reported {said!r}")
    if fake.pulls["7"]["state"] != "MERGED":
        problems.append("advance: the case that models a merge in the window did not merge")
    if fake.reads.get("7", 0) != 7:
        problems.append("advance: the wait for merge in the window did not stop early, "
                        f"costing {fake.reads.get('7', 0)} reads")
    return problems


def _rebase_github_had_not_shown_yet(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True, "drops": True, "slow": 2}})
    said = swept(channel, move, fake, problems)
    if said:
        problems.append(f"advance: a rebase GitHub had not shown yet reported {said!r}")
    if not fake.pulls["7"]["armed"]:
        problems.append("advance: it read the arming off the head GitHub had not moved, so "
                        "the arming the move dropped stayed dropped")
    return problems


def _push_landing_before_the_rebase(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True, "drops": True, "slow": 2, "pushed": 1}})
    said = swept(channel, move, fake, problems)
    if said:
        problems.append(f"advance: a push landing before the rebase reported {said!r}")
    if not fake.pulls["7"]["armed"]:
        problems.append("advance: it read the rebase off the commit the sweep listed rather "
                        "than the one it asked GitHub to rebase, so a push in between "
                        "answered for the rebase and the arming it dropped stayed dropped")
    return problems


def _push_that_brought_the_branch_current(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True, "pushed": 1, "leaves": 0}})
    said = swept(channel, move, fake, problems)
    if fake.pulls["7"].get("rebased"):
        problems.append("advance: a push brought the branch current inside the window and it "
                        "asked GitHub to rebase a branch with nothing to rebase, on a compare "
                        "of the commit that push orphaned")
    if said:
        problems.append(f"advance: a push that brought the branch current reported {said!r}")
    return problems


def _push_landing_inside_the_mergeability_poll(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True, "unknown": 1, "pushed": 2, "leaves": 0}})
    said = swept(channel, move, fake, problems)
    if fake.pulls["7"].get("rebased"):
        problems.append("advance: a push landed while it waited on `mergeability` and it "
                        "rebased the branch that push brought current, so the read the call "
                        "was made against was taken before the wait rather than after it")
    if said:
        problems.append(f"advance: a push landing inside the poll reported {said!r}")
    return problems


def _head_github_never_moved(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True, "slow": 9}})
    said = swept(channel, move, fake, problems)
    if not said or "has not moved it" not in said:
        problems.append(f"advance: a head GitHub never moved was reported as {said!r}")
    if said and "still behind" in said:
        problems.append("advance: a rebase GitHub had not shown was reported as a branch "
                        "that is still behind its base")
    return problems


def _two_pull_requests_failing_in_one_sweep(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True}, 8: {"behind": 1, "armed": True}},
                      no_rebase=[7, 8])
    said = swept(channel, move, fake, problems)
    for number in ("#7", "#8"):
        if number not in said:
            problems.append("advance: a sweep both pull requests failed in did not name "
                            f"{number} in its report, which said {said!r}")
    return problems


def _named_pull_request_not_armed(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
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
    return problems


def _stack_advances_as_one_transition(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({
        7: {"behind": 0, "armed": True, "layer": True, "requested": ["o-r-reviewer"]},
        8: {"behind": 1, "armed": False, "layer": True, "base": "claude/issue-7",
            "requested": ["o-r-reviewer"], "drops_review": True},
    })
    said = swept(channel, move, fake, problems)
    if (fake.checked_out != [("claude/issue-7",)] or fake.stack_rebases != ["7"]
            or fake.stack_rebase_args != [("--upstack",)]
            or fake.pushed_stacks != 1 or fake.pulls["7"].get("rebased")
            or not fake.pulls["8"].get("rebased")):
        problems.append("advance: a stack transition did not check out its root branch, rebase "
                        f"upstack, and push once, or misreported layer movements: {fake.checked_out!r}, {fake.stack_rebases!r}, "
                        f"{fake.stack_rebase_args!r}, {fake.pushed_stacks!r}, {fake.pulls!r}")
    if "7" in fake.edited or "8" not in fake.edited or "o-r-reviewer" not in fake.pulls["8"]["requested"]:
        problems.append(f"advance: review renewal touched unchanged layer or missed dropping layer: {fake.edited!r}")
    if said:
        problems.append(f"advance: a stack transition reported {said!r}")
    return problems


def _named_stack_base_advances_without_arming(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({
        7: {"behind": 1, "armed": False, "layer": True},
        8: {"behind": 1, "armed": False, "layer": True, "base": "claude/issue-7"},
    })
    said = run_verb(channel, fake, lambda: move.advance("7"))
    if (fake.checked_out != [("claude/issue-7",)] or fake.stack_rebases != ["7"]
            or not all(fake.pulls[n].get("rebased") for n in ("7", "8")) or said):
        problems.append(f"advance: named stack base was not advanced: {fake.checked_out!r}, {fake.stack_rebases!r}, {said!r}")
    return problems


def _named_unarmed_upper_layer_is_refused(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({
        7: {"behind": 1, "armed": False, "layer": True},
        8: {"behind": 1, "armed": False, "layer": True, "base": "claude/issue-7"},
    })
    said = run_verb(channel, fake, lambda: move.advance("8"))
    if not said or "not armed or approved" not in said or fake.stack_rebases:
        problems.append(f"advance: unarmed upper layer was not refused: {said!r}, {fake.stack_rebases!r}")
    return problems


def _named_unlinked_stack_base_is_refused(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({
        7: {"behind": 1, "armed": True, "layer": False},
        8: {"behind": 1, "armed": False, "layer": False, "base": "claude/issue-7"},
    })
    said = run_verb(channel, fake, lambda: move.advance("7"))
    if not said or "not linked as a GitHub stack" not in said or "solorepo's DR-243" not in said:
        problems.append(f"advance: unlinked stack base did not cite solorepo's DR-243: {said!r}")
    return problems


def _refused_stack_leaves_every_layer_unmoved(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({
        7: {"behind": 1, "armed": False, "layer": True},
        8: {"behind": 1, "armed": False, "layer": True, "base": "claude/issue-7"},
    }, no_stack=[7])
    said = run_verb(channel, fake, lambda: move.advance("7"))
    if not said or "#7" not in said or "#8" not in said or any(pull.get("rebased") for pull in fake.pulls.values()):
        problems.append(f"advance: a refused stack partially advanced or misreported: {said!r}, {fake.pulls!r}")
    return problems


def _stack_layer_still_behind_after_advance_is_reported(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    root, layer = 7, 8
    fake = FakeGitHub({
        root: {"behind": 1, "armed": True, "layer": True},
        layer: {"behind": 1, "armed": False, "layer": True, "base": f"claude/issue-{root}", "again": 1},
    })
    said = swept(channel, move, fake, problems)
    if not said or f"#{layer} is still behind claude/issue-{root} after #{root}'s stack advanced" not in said:
        problems.append(f"advance: a stack layer still behind was reported as {said!r}")
    return problems


def _stack_reaches_advance_via_approved_layer(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({
        7: {"behind": 1, "armed": False, "layer": True, "verdicts": [("o-r-reviewer", "APPROVED")]},
        8: {"behind": 1, "armed": False, "layer": True, "base": "claude/issue-7"},
    })
    said = swept(channel, move, fake, problems)
    if fake.checked_out != [("claude/issue-7",)] or fake.stack_rebases != ["7"] or said:
        problems.append(f"advance: approved stack base was not advanced: {fake.checked_out!r}, {fake.stack_rebases!r}, {said!r}")
    return problems


def _stack_reaches_advance_via_armed_upper_layer(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({
        7: {"behind": 1, "armed": False, "layer": True},
        8: {"behind": 1, "armed": True, "layer": True, "base": "claude/issue-7"},
    })
    said = swept(channel, move, fake, problems)
    if fake.checked_out != [("claude/issue-7",)] or fake.stack_rebases != ["7"] or said:
        problems.append(f"advance: armed upper layer did not advance stack from root: {fake.checked_out!r}, {fake.stack_rebases!r}, {said!r}")
    return problems


def _stack_with_multiple_armed_layers_rebases_once(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({
        7: {"behind": 1, "armed": True, "layer": True},
        8: {"behind": 1, "armed": True, "layer": True, "base": "claude/issue-7"},
    })
    said = swept(channel, move, fake, problems)
    if fake.stack_rebases != ["7"] or fake.pushed_stacks != 1 or said:
        problems.append(f"advance: stack with multiple armed layers rebased more than once: {fake.stack_rebases!r}, {fake.pushed_stacks!r}, {said!r}")
    return problems


def _three_layer_stack_advances_in_order(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({
        7: {"behind": 1, "armed": True, "layer": True},
        8: {"behind": 1, "armed": False, "layer": True, "base": "claude/issue-7"},
        9: {"behind": 1, "armed": False, "layer": True, "base": "claude/issue-8"},
    })
    said = swept(channel, move, fake, problems)
    if (fake.checked_out != [("claude/issue-7",)] or fake.stack_rebases != ["7"]
            or not all(fake.pulls[n].get("rebased") for n in ("7", "8", "9")) or said):
        problems.append(f"advance: three-layer stack did not advance in order: {fake.checked_out!r}, {fake.stack_rebases!r}, {fake.pulls!r}")
    return problems


def _branched_stack_is_refused(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({
        7: {"behind": 1, "armed": True, "layer": True},
        8: {"behind": 1, "armed": False, "layer": True, "base": "claude/issue-7"},
        9: {"behind": 1, "armed": False, "layer": True, "base": "claude/issue-7"},
    })
    said = swept(channel, move, fake, problems)
    if not said or "does not head a linear open stack" not in said or fake.stack_rebases:
        problems.append(f"advance: branched stack was not refused: {said!r}, {fake.stack_rebases!r}")
    return problems


def _stack_with_nothing_behind_is_skipped(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({
        7: {"behind": 0, "armed": True, "layer": True},
        8: {"behind": 0, "armed": False, "layer": True, "base": "claude/issue-7"},
    })
    with stood_in(channel, gh=fake):
        ran = outcome(lambda: move.advance())
    if ran.code is not None:
        problems.append(f"advance: stack with nothing behind exited with {ran.code!r}")
    if fake.checked_out or fake.stack_rebases or fake.pushed_stacks:
        problems.append("advance: stack with nothing behind called stack verbs: "
                        f"{fake.checked_out!r}, {fake.stack_rebases!r}, {fake.pushed_stacks!r}")
    if "1 pull request(s) current with their base" not in ran.out:
        problems.append(f"advance: stack with nothing behind did not report current: {ran.out!r}")
    return problems


def _stack_with_current_upper_layer_advances_both(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    root, upper = 7, 8
    fake = FakeGitHub({
        root: {"behind": 1, "armed": True, "layer": True},
        upper: {"behind": 0, "armed": False, "layer": True, "base": f"claude/issue-{root}", "slow": 1},
    })
    said = swept(channel, move, fake, problems)
    if (fake.checked_out != [(f"claude/issue-{root}",)] or fake.stack_rebases != [str(root)]
            or not fake.pulls[str(root)].get("rebased") or not fake.pulls[str(upper)].get("rebased")
            or said):
        problems.append("advance: stack with current upper layer did not advance both layers: "
                        f"{fake.checked_out!r}, {fake.stack_rebases!r}, {fake.pulls!r}, {said!r}")
    return problems


def _unlinked_chain_swept_rebases_top_layer_and_skips_base(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    base, top = 7, 8
    fake = FakeGitHub({
        base: {"behind": 1, "armed": True, "layer": False},
        top: {"behind": 1, "armed": True, "layer": False, "base": f"claude/issue-{base}"},
    })
    said = swept(channel, move, fake, problems)
    if fake.pulls[str(base)].get("rebased"):
        problems.append("advance: unlinked chain base was rebased")
    if not fake.pulls[str(top)].get("rebased"):
        problems.append("advance: unlinked chain top layer was not rebased")
    if fake.stack_rebases:
        problems.append(f"advance: unlinked chain called stack verbs: {fake.stack_rebases!r}")
    if said:
        problems.append(f"advance: unlinked chain sweep reported {said!r}")
    return problems


def _stack_review_renewal_failure_is_reported(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    root, layer = 7, 8
    fake = FakeGitHub({
        root: {"behind": 0, "armed": True, "layer": True},
        layer: {"behind": 1, "armed": False, "layer": True, "base": f"claude/issue-{root}",
                "requested": ["o-r-reviewer"], "drops_review": True},
    }, no_edit_sticks=[layer])
    said = swept(channel, move, fake, problems)
    if not said or f"#{layer} lost its review request during #{root}'s stack advance" not in said:
        problems.append(f"advance: review renewal failure was reported as {said!r}")
    return problems


def _refused_stack_review_renewal_is_the_sweeps_own_problem(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    root, layer = 7, 8
    fake = FakeGitHub({
        root: {"behind": 0, "armed": True, "layer": True},
        layer: {"behind": 1, "armed": False, "layer": True, "base": f"claude/issue-{root}",
                "requested": ["o-r-reviewer"], "drops_review": True},
    }, no_edit=[layer])
    said = run_verb(channel, fake, lambda: move.advance())
    if not said or f"#{layer}" not in said:
        problems.append(f"advance: a refused stack review renewal exited with {said!r}, "
                        "so a sweep that lost a review request during stack advance reports "
                        "the colour of one that re-requested it")
    return problems


def _conflicting_stack_advances_once_its_root_is_rebased(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    root = 7
    fake = FakeGitHub({
        root: {"behind": 1, "armed": True, "layer": True, "mergeable": "CONFLICTING"},
        8: {"behind": 0, "armed": False, "layer": True, "base": f"claude/issue-{root}"},
    })
    with stood_in(channel, gh=fake):
        ran = outcome(lambda: move.advance())
    if ran.code is not None:
        problems.append(f"advance: a conflicting stack exited with {ran.code!r}")
    if f"left #{root}'s stack alone" not in ran.out:
        problems.append(f"advance: a conflicting stack was skipped in silence rather than explained: {ran.out!r}")
    if fake.stack_rebases or any(pull.get("rebased") for pull in fake.pulls.values()):
        problems.append(f"advance: a conflicting stack was rebased: {fake.stack_rebases!r}, {fake.pulls!r}")
    if fake.dispatched != [(str(root), "rebase")]:
        problems.append(f"advance: a conflicting stack was dispatched to coders as "
                        f"{fake.dispatched!r}, where the root's rebase pass alone is dispatched "
                        "and the stack is left to be advanced once it is clean")
    said = str(ran.out.partition(REPORTED)[2])
    if said:
        problems.append(f"advance: a conflicting stack was reported as failed: {said!r}")
    return problems


def _merge_auto_after_a_failed_advance(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": False}}, no_rebase=[7])
    said = run_verb(channel, fake, lambda: move.merge("7", auto=True))
    if not fake.pulls["7"]["armed"]:
        problems.append("merge --auto: a failed advance left the pull request unarmed")
    if not said or "conflicts" not in said:
        problems.append(f"merge --auto: the failed advance was reported as {said!r}")
    return problems


def _merge_auto_over_a_merge_that_landed(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": False}}, no_rebase=[7], lands=[7])
    said = run_verb(channel, fake, lambda: move.merge("7", auto=True))
    if said:
        problems.append(f"merge --auto: a merge that landed exited with {said!r}")
    return problems


def _merge_auto_over_a_blip_on_the_read_back(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True}}, blip=[7])
    said = run_verb(channel, fake, lambda: move.merge("7", auto=True))
    if not fake.pulls["7"]["armed"] or fake.pulls["7"]["behind"]:
        problems.append("merge --auto: a blip on the read-back left the pull request "
                        f"{fake.pulls['7']!r}")
    if said:
        problems.append(f"merge --auto: a stall over a current branch exited with {said!r}")
    return problems


def _merge_github_had_not_shown_yet(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    landed = 7
    fake = FakeGitHub({landed: {"armed": False, "slow": 1}}, lands=[landed])
    with stood_in(channel, gh=fake):
        ran = outcome(lambda: move.merge(str(landed)))
    if ran.code is not None:
        problems.append(f"merge: a merge GitHub had not shown on the first read exited with {ran.code!r}, "
                        "so a squash GitHub accepted is reported as one that did not land")
    if f"merged #{landed} as merged{landed}" not in ran.out:
        problems.append("merge: a merge GitHub had not shown on the first read "
                        f"printed {ran.out!r}")
    return problems


def _merge_github_never_showed(channel: Any, move: Any) -> list[str]:
    problems: list[str] = []
    stuck = 7
    fake = FakeGitHub({stuck: {"armed": False, "slow": 9}}, lands=[stuck])
    said = run_verb(channel, fake, lambda: move.merge(str(stuck)))
    if not said or "is open after the merge call" not in said:
        problems.append(f"merge: a merge GitHub never showed exited with {said!r}, so the wait "
                        "swallowed the refusal it is wrapped around")
    return problems


def _notice_lifecycle_on_advance_failures(channel: Any, move: Any) -> list[str]:
    """Verification of in-place advance finding notice lifecycle (solorepo's DR-255).

    Verifies that:
    1. A failing PR during sweep receives a signed advance notice comment.
    2. An updated error message edits the existing notice comment in place without duplicates.
    3. When the PR advances cleanly on a subsequent run, the notice comment is deleted.
    """
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True, "drops": True}}, no_rebase=[7])
    with (stood_in(channel, gh=fake),
          environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe", AI_AGENT="probe")):
        swept(channel, move, fake, problems)
        if len(fake.posted_comments) != 1:
            problems.append(f"advance: expected 1 posted notice comment, got {len(fake.posted_comments)}")
        comments_7 = fake.comments.get("7", [])
        if not comments_7 or "advance-finding" not in comments_7[0].get("body", ""):
            problems.append(f"advance: notice comment was not recorded on PR 7: {comments_7}")
        elif "Actor: gha-1" not in comments_7[0].get("body", ""):
            problems.append(f"advance: notice comment missing signed Actor trailer: {comments_7[0].get('body')}")

        fake.no_rebase = set()
        fake.no_arm = {"7"}
        fake.pulls["7"]["behind"] = 1
        swept(channel, move, fake, problems)
        comments_after_update = fake.comments.get("7", [])
        if len(comments_after_update) != 1:
            problems.append(f"advance: expected exactly 1 notice comment on PR 7 after update, got {len(comments_after_update)}")
        elif "clean status" not in comments_after_update[0].get("body", ""):
            problems.append(f"advance: notice comment body did not update with new failure: {comments_after_update[0].get('body')}")

        fake.no_arm = set()
        fake.pulls["7"]["drops"] = False
        fake.pulls["7"]["armed"] = True
        fake.pulls["7"]["head"] = "head7"
        fake.pulls["7"]["behind"] = 1
        swept(channel, move, fake, problems)
        if fake.comments.get("7"):
            problems.append(f"advance: notice comment on PR 7 was not deleted after clean advance: {fake.comments.get('7')}")
        if not fake.cleared_comments:
            problems.append("advance: cleared_comments did not record deleted notice comment ID")

    return problems


def _advance_notice_local_operator_visibility(channel: Any, move: Any) -> list[str]:
    """Verification of advance notice visibility in Local Operator Plane (solorepo's DR-255)."""
    problems: list[str] = []
    fake = FakeGitHub({7: {"behind": 1, "armed": True}}, no_rebase=[7])
    with (stood_in(channel, gh=fake),
          environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe", AI_AGENT="probe")):
        swept(channel, move, fake, problems)
        from lib.check_pr import branch
        from lib.check_pr import github as check_pr_github
        with stood_in(check_pr_github, gh=fake):
            notice = branch.advance_notice(7)
            if not notice or "#7" not in notice:
                problems.append(f"advance: branch.advance_notice(7) did not find notice: {notice!r}")

    return problems


@check("advance probes", pre=True)
def advance_probes() -> list[str]:
    """`advance` and `merge` against a fake GitHub, in the states solorepo's #98 found them in.

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
    - Advance notice lifecycle and local operator visibility (solorepo's DR-255).
      A failing pull request receiving an in-place signed notice comment, updated
      in place on subsequent errors, deleted when the branch cleanly advances,
      and visible to local operators through branch.advance_notice.
    - Advance sweep failure cases and stack layer transitions.
    - The plain merge's read-back (solorepo's DR-158, solorepo's #773): a squash
      GitHub has accepted but not yet shown, which the read-back waits out, and
      one GitHub never shows, where the refusal the wait is wrapped around still
      stands.

    The dispatch reading and the dispatch a person makes are `dispatch_probes`
    in `probes/loops/dispatch.py`.

    `said` is read in every case whose whole assertion is an absence: a verb
    that died before dispatching leaves `dispatched` empty too, and without it
    a crash reads exactly like the filter doing its job. In a sweep it is what
    the verb printed rather than what it exited with, through `swept`, because
    a sweep that read every open pull request is green whatever they reported
    (solorepo's DR-238); `run_verb` still reads the exit in the cases that name
    one pull request, where the exit code is the answer. The fake's repository
    is `o/r`, so the reviewer's login is `o-r-reviewer`, as `channel.role_login`
    composes it (solorepo's DR-107).
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    channel.SETTLES = (3, 0)
    channel.MERGEABILITY = (3, 0)
    return [problem for problems in (
        _notice_lifecycle_on_advance_failures(channel, move),
        _advance_notice_local_operator_visibility(channel, move),
        _rebase_under_a_base_that_moved_again(channel, move),
        _refusal_to_rebase_one_pull_request(channel, move),
        _refusal_to_arm_one_pull_request(channel, move),
        _arming_github_did_not_hold(channel, move),
        _re_arming_that_merged_in_the_window(channel, move),
        _rebase_github_had_not_shown_yet(channel, move),
        _push_landing_before_the_rebase(channel, move),
        _push_that_brought_the_branch_current(channel, move),
        _push_landing_inside_the_mergeability_poll(channel, move),
        _head_github_never_moved(channel, move),
        _two_pull_requests_failing_in_one_sweep(channel, move),
        _named_pull_request_not_armed(channel, move),
        _stack_advances_as_one_transition(channel, move),
        _named_stack_base_advances_without_arming(channel, move),
        _named_unarmed_upper_layer_is_refused(channel, move),
        _named_unlinked_stack_base_is_refused(channel, move),
        _refused_stack_leaves_every_layer_unmoved(channel, move),
        _stack_layer_still_behind_after_advance_is_reported(channel, move),
        _stack_reaches_advance_via_approved_layer(channel, move),
        _stack_reaches_advance_via_armed_upper_layer(channel, move),
        _stack_with_multiple_armed_layers_rebases_once(channel, move),
        _three_layer_stack_advances_in_order(channel, move),
        _branched_stack_is_refused(channel, move),
        _stack_with_nothing_behind_is_skipped(channel, move),
        _stack_with_current_upper_layer_advances_both(channel, move),
        _unlinked_chain_swept_rebases_top_layer_and_skips_base(channel, move),
        _stack_review_renewal_failure_is_reported(channel, move),
        _refused_stack_review_renewal_is_the_sweeps_own_problem(channel, move),
        _conflicting_stack_advances_once_its_root_is_rebased(channel, move),
        _merge_auto_after_a_failed_advance(channel, move),
        _merge_auto_over_a_merge_that_landed(channel, move),
        _merge_auto_over_a_blip_on_the_read_back(channel, move),
        _merge_github_had_not_shown_yet(channel, move),
        _merge_github_never_showed(channel, move)
    ) for problem in problems]
