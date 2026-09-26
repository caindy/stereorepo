"""`--sweep`'s two degradation paths, each run against a GitHub that refuses (solorepo's DR-209).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import sys
import types
from collections.abc import Sequence
from typing import Any

from checks import citations
from checks.collect import check
from checks.probes.harness import answered, outcome, stood_in, unanswered

REFUSAL = "gh: HTTP 502: Server Error (https://api.github.com/graphql)"
"""What a `gh` that exits non-zero leaves behind, in the words `github.gh` exits with."""


@check("sweep probes", pre=True)
def sweep_probes() -> list[str]:
    """`--sweep` asks GitHub twice and reads the tree once, and neither question ending the command is what the cases hold (solorepo's #578, solorepo's #579).

    `github.gh` ends the process on a non-zero `gh`, so every caller that does
    not catch it hands the whole sweep to one refused node. The symptom
    recurred: `residue()` was protected on solorepo's #579 and `print_sweep()`'s
    own lookup, unprotected the same way, ended the sweep again from a branch
    GitHub would not answer for. Both handlers are a refusal and a sentence
    about it, so both are probed by standing `gh` in — the state costs a broken
    credential to reach for real and is gone by the time anyone could look.

    `print_sweep()`: a refused lookup prints a `?` line saying what this branch
    owns is unchecked and names the refusal under it, and the residue prints
    below that, because the branches an operator ran the command for are the
    half that never needed GitHub; a lookup GitHub answers prints the pull
    request and no `?` line at all, so the degrade is not the only path left.

    `residue()`: with one of two gone branches refused, the refused one is
    reported unreadable, carries what GitHub said in refusing on a continuation
    line, and keeps its removal command, and the branch after it is still
    listed — which is the listing solorepo's #578 lost entire.
    """
    check_pr = citations.load_check_pr()
    return _print_sweep_cases(check_pr) + _residue_cases(check_pr)


def _refuses(*_args: str) -> Any:
    """A `gh` that ends the process on every call, as `github.gh` does on a non-zero exit."""
    sys.exit(REFUSAL)


class _Tree:
    """The git reads `residue()` and `owned_and_open()` make, answered from a fixed tree.

    Stands in for `branch.subprocess`, whose `run` both reach for. Only
    `stdout` is answered, which is all either reads. `gone` names the branches
    whose upstream is reported gone, `worktrees` maps a branch to the worktree
    checked out on it, `here` is the top level of the current checkout, and
    `branch` is what `git branch --show-current` answers.
    """

    def __init__(self, gone: Sequence[str], worktrees: dict[str, str] | None = None,
                 here: str = "/repo", branch: str = "claude/issue-1") -> None:
        self.gone = gone
        self.worktrees = worktrees or {}
        self.here = here
        self.branch = branch

    def run(self, args: Sequence[str], **_: Any) -> types.SimpleNamespace:
        """What git answered for `args`, or an `AssertionError` naming a call this tree has no answer for."""
        verb = args[1]
        if verb == "for-each-ref":
            said = "".join(f"{name} gone\n" for name in self.gone) + "main \n"
        elif verb == "worktree":
            said = "".join(f"worktree {path}\nbranch refs/heads/{name}\n\n"
                           for name, path in self.worktrees.items())
        elif verb == "rev-parse":
            said = f"{self.here}\n"
        elif verb == "branch":
            said = f"{self.branch}\n"
        elif verb == "fetch":
            said = ""
        else:
            raise unanswered(list(args), "the git fake")
        return types.SimpleNamespace(stdout=said)


def _print_sweep_cases(check_pr: Any) -> list[str]:
    """`print_sweep()` over a refused lookup, open pull request, and both notice kinds."""
    problems = []
    left = ["  claude/issue-1 — no pull request", "    git branch -D claude/issue-1"]
    with stood_in(check_pr.github, gh=_refuses), stood_in(check_pr.branch, residue=lambda: left):
        shown = outcome(check_pr.cli.print_sweep)
    lines = shown.out.splitlines()
    if shown.code is not None:
        problems.append(f"print_sweep: a refused lookup exited with {shown.code!r}, and a sweep "
                        "that ends on it prints none of the branches it was run for")
    if not lines or not lines[0].startswith("?") or "unchecked" not in lines[0]:
        problems.append(f"print_sweep: a refused lookup headed itself {lines[:1]!r}, which does "
                        "not say that what this branch owns went unread")
    if REFUSAL not in shown.out:
        problems.append(f"print_sweep: the refusal {REFUSAL!r} is nowhere in {shown.out!r}, so "
                        "an expired credential reads the same as a server declining one node")
    if any(line not in lines for line in left):
        problems.append(f"print_sweep: the residue under a refused lookup was {lines[2:]!r}, "
                        "and the branches it names need no GitHub to be found")

    owned = [{"number": 42, "title": "A pull request this branch owns"}]
    with stood_in(check_pr.branch, subprocess=_Tree([])), \
         stood_in(check_pr.github, gh=lambda *a: owned, threads=lambda ref: []):
        shown = outcome(check_pr.cli.print_sweep)
    if "#42 A pull request this branch owns" not in shown.out or "?" in shown.out:
        problems.append(f"print_sweep: a lookup GitHub answered printed {shown.out!r}, and the "
                        "degrade is for a refusal rather than for every run")

    comments = {
        "comments": [
            {"body": "<!-- solorepo:merge-refusal -->\n> Merge refused"},
            {"body": "<!-- solorepo:advance-finding -->\n> Rebase failed"},
        ],
    }
    with stood_in(check_pr.branch,
                  owned_and_open=lambda: ("claude/issue-1", [(42, "A pull request", [])]),
                  residue=lambda: []), \
            stood_in(check_pr.github, gh=lambda *_args: comments):
        shown = outcome(check_pr.cli.print_sweep)
    if "refusal: Merge refused" not in shown.out or "advance: Rebase failed" not in shown.out:
        problems.append(
            f"print_sweep: both active notice kinds were not reported: {shown.out!r}")
    return problems


def _residue_cases(check_pr: Any) -> list[str]:
    """`residue()` with one of two gone branches refused: the refusal named and the listing whole."""
    closed = {"number": 2, "state": "CLOSED"}

    def lookup(*args: str) -> Any:
        """`pr list --head <branch>`: a closed pull request for each gone branch, and a refusal for the first."""
        head = args[args.index("--head") + 1]
        if head == "claude/issue-1":
            sys.exit(REFUSAL)
        return [closed]

    problems = []
    tree = _Tree(["claude/issue-1", "claude/issue-2"])
    with stood_in(check_pr.branch, subprocess=tree), stood_in(check_pr.github, gh=lookup):
        value, code, _ = answered(check_pr.branch.residue)
    if code is not None:
        problems.append(f"residue: one refused node ended the listing with {code!r}")
    left: list[str] = value or []
    unreadable = "  claude/issue-1 — pull request unreadable"
    under = left[left.index(unreadable) + 1:] if unreadable in left else []
    if unreadable not in left:
        problems.append(f"residue: a branch GitHub would not answer for was listed as {left!r}")
    elif not under or under[0].strip() != REFUSAL:
        problems.append(f"residue: what GitHub said in refusing is not under the branch it "
                        f"refused, which reads as {left!r}")
    if "    git branch -D claude/issue-1" not in left:
        problems.append(f"residue: the refused branch lost the removal command an operator ran "
                        f"the sweep for, leaving {left!r}")
    listed = f"  claude/issue-2 — #{closed['number']} {str(closed['state']).lower()}"
    if listed not in left:
        problems.append(f"residue: the branch after a refused one is missing from {left!r}, "
                        "which is the whole listing solorepo's #578 lost")
    return problems
