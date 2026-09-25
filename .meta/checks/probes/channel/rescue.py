"""Probes for coder rescue phase (solorepo's DR-264, solorepo's #946).

Defect history in .meta/coder_door.history.md (solorepo's DR-171).
"""
import contextlib
import pathlib
from collections.abc import Iterator, Sequence
from typing import Any

from checks.collect import check
from checks.probes.harness import (
    load_channel,
    load_module,
    outcome,
    stood_in,
)

ISSUE = "7"
"""The Challenge the loop's branch names."""


class _RescueCommands:
    """A stand-in for command recording calls and answering mapped outputs."""

    def __init__(self, answers: dict[tuple[str, ...], bytes] | None = None) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.answers = answers or {}

    def __call__(self, argv: Sequence[str], stdin: bytes | None = None) -> bytes:
        self.calls.append(tuple(argv))
        for key, ans in self.answers.items():
            if tuple(argv[:len(key)]) == key:
                return ans
        return b""


@contextlib.contextmanager
def _workspace() -> Iterator[pathlib.Path]:
    """A run's workspace context without an agent."""
    yield pathlib.Path()


def _rescue(on: Any, delivery: tuple[str, str, str], number: str,
            branch_prefix: str, commands: _RescueCommands) -> tuple[Any, _RescueCommands]:
    """Runs `coder rescue` within a mocked workspace and answers outcome and command recorder."""
    from lib.coder_door import handoff
    common = on.common
    with _workspace(), stood_in(common, command=commands), \
            stood_in(handoff.common, command=commands):
        ended = outcome(lambda: on.coder("rescue", number, on.Delivery(*delivery),
                                         on.Ended(None, branch_prefix)))
    return ended, commands


def _feature_branch_cases(on: Any) -> list[str]:
    """Verify rescue behavior when active checkout is already on a loop branch."""
    problems: list[str] = []
    take = ("take", "issues", "")

    clean_cmds = _RescueCommands(
        answers={("git", "branch", "--show-current"): b"claude/issue-7\n"}
    )
    ended, cmds = _rescue(on, take, ISSUE, "claude", clean_cmds)
    if ended.code is not None:
        problems.append(f"rescue: clean tree ended {ended.code!r}")
    if ("git", "push", "-u", "origin", "claude/issue-7") not in cmds.calls:
        problems.append(f"rescue: clean tree did not push claude/issue-7, calls: {cmds.calls!r}")
    if any("commit" in call for call in cmds.calls):
        problems.append(f"rescue: clean tree authored an unexpected commit, calls: {cmds.calls!r}")

    dirty_cmds = _RescueCommands(answers={
        ("git", "branch", "--show-current"): b"claude/issue-7\n",
        ("git", "status", "--porcelain"): b" M file.py\n",
    })
    ended, cmds = _rescue(on, take, ISSUE, "claude", dirty_cmds)
    if ended.code is not None:
        problems.append(f"rescue: dirty tree ended {ended.code!r}")
    if ("git", "add", "-A") not in cmds.calls:
        problems.append(f"rescue: dirty tree did not stage changes, calls: {cmds.calls!r}")
    expected_msg = f"[rescue] Uncommitted session work on Challenge #{ISSUE}"
    if not any(expected_msg in arg for call in cmds.calls for arg in call):
        problems.append(f"rescue: dirty tree did not commit rescue message, calls: {cmds.calls!r}")
    if ("git", "push", "-u", "origin", "claude/issue-7") not in cmds.calls:
        problems.append(f"rescue: dirty tree did not push, calls: {cmds.calls!r}")

    return problems


def _main_branch_cases(on: Any) -> list[str]:
    """Verify rescue behavior when active checkout is on main or detached HEAD."""
    problems: list[str] = []
    take = ("take", "issues", "")
    expected_msg = f"[rescue] Uncommitted session work on Challenge #{ISSUE}"

    main_clean = _RescueCommands(answers={("git", "branch", "--show-current"): b"main\n"})
    ended, cmds = _rescue(on, take, ISSUE, "claude", main_clean)
    if ended.code is not None:
        problems.append(f"rescue: clean tree on main ended {ended.code!r}")
    if any(call[:2] == ("git", "checkout") for call in cmds.calls):
        problems.append(f"rescue: clean tree on main checked out branch, calls: {cmds.calls!r}")
    if any(call[:3] == ("git", "push", "-u") for call in cmds.calls):
        problems.append(f"rescue: clean tree on main pushed, calls: {cmds.calls!r}")

    main_dirty = _RescueCommands(answers={
        ("git", "branch", "--show-current"): b"main\n",
        ("git", "status", "--porcelain"): b" M file.py\n",
    })
    ended, cmds = _rescue(on, take, ISSUE, "claude", main_dirty)
    if ended.code is not None:
        problems.append(f"rescue: dirty tree on main ended {ended.code!r}")
    if ("git", "checkout", "-B", "claude/issue-7") not in cmds.calls:
        problems.append(f"rescue: did not create rescue branch with -B, calls: {cmds.calls!r}")
    if ("git", "add", "-A") not in cmds.calls:
        problems.append(f"rescue: dirty tree on main did not stage changes, calls: {cmds.calls!r}")
    if not any(expected_msg in arg for call in cmds.calls for arg in call):
        problems.append(f"rescue: dirty tree on main did not commit message: {cmds.calls!r}")
    if ("git", "push", "-u", "origin", "claude/issue-7") not in cmds.calls:
        problems.append(f"rescue: dirty tree on main did not push, calls: {cmds.calls!r}")

    main_guard = _RescueCommands(answers={("git", "branch", "--show-current"): b"main\n"})
    ended, cmds = _rescue(on, ("answer", "pull_request_review", ""), "12", "", main_guard)
    if any(call[:3] == ("git", "push", "-u") and "main" in call for call in cmds.calls):
        problems.append(f"rescue: pushed directly to main branch, calls: {cmds.calls!r}")

    return problems


@check("coder rescue probes", pre=True)
def coder_rescue_probes() -> list[str]:
    """Verify coder rescue phase commits uncommitted modifications and pushes to loop branch."""
    load_channel()
    on = load_module(".meta/coder_door.py")
    return _feature_branch_cases(on) + _main_branch_cases(on)
