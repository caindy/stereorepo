"""Tests for the pair loop: every turn and stopping rule, over a real git repository.

Run: uv run --with pyyaml python -m unittest discover -s pair -p 'test_*.py'
"""

from __future__ import annotations

import collections
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

import board
from loop import Loop, State, append_event, event_log, status, status_json, status_view
from seats import ALLOWED, TurnResult, command
from watch import watch

PROMPTS = Path(__file__).resolve().parent / "prompts"
Action = Callable[[Path], None]


def sh(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


def quiet(_cwd: Path) -> None:
    """A turn that changes nothing."""


CRASH = object()


def front(slug: str, **fields: str) -> Action:
    """Set front matter fields on the issue, wherever it sits."""

    def act(cwd: Path) -> None:
        issue = board.read(cwd, slug)
        assert issue is not None
        data = {**issue.front, **fields}
        lines = "\n".join(f"{k}: {v}" for k, v in data.items())
        (cwd / issue.path).write_text(f"---\n{lines}\n---\n{issue.body}")

    return act


def append(slug: str, text: str) -> Action:
    def act(cwd: Path) -> None:
        issue = board.read(cwd, slug)
        assert issue is not None
        path = cwd / issue.path
        path.write_text(path.read_text() + text)

    return act


def write(rel: str, text: str) -> Action:
    def act(cwd: Path) -> None:
        (cwd / rel).parent.mkdir(parents=True, exist_ok=True)
        (cwd / rel).write_text(text)

    return act


def both(*actions: Action) -> Action:
    def act(cwd: Path) -> None:
        for a in actions:
            a(cwd)

    return act


class FakeSeat:
    """A seat that plays scripted turns, and records its session as `ClaudeSeat` does."""

    def __init__(
        self, role: str, cwd: Path, resume: str | None, bench: Bench, loop: Loop
    ) -> None:
        self.role, self.cwd, self.bench, self.loop = role, cwd, bench, loop
        self.session_id = resume or f"{role}-session"
        loop.dir.mkdir(parents=True, exist_ok=True)
        (loop.dir / f"{role}.session").write_text(f"{self.session_id}\n")

    def send(self, text: str) -> TurnResult:
        self.bench.sent.append((self.role, text))
        if not self.bench.turns:
            raise AssertionError(f"unscripted turn for {self.role}:\n{text}")
        role, action = self.bench.turns.popleft()
        if role != self.role:
            raise AssertionError(f"expected a {role} turn, got {self.role}")
        if action is CRASH:
            return TurnResult(False, error="boom", session_id=self.session_id)
        action(self.cwd)
        if self.bench.stop_when_empty and not self.bench.turns:
            self.loop.stop_requested = True
        return TurnResult(
            True, session_id=self.session_id, usage={"cache_read_input_tokens": 1}
        )

    def stop(self) -> None:
        pass


class Bench:
    """The developer's checkout with a board, and a loop wired to fake seats and a fake gate."""

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "developer"
        self.repo.mkdir()
        sh(self.repo, "init", "-q", "-b", "main")
        for key, value in (
            ("user.name", "Test"),
            ("user.email", "t@example.com"),
            ("commit.gpgsign", "false"),
        ):
            sh(self.repo, "config", key, value)
        (self.repo / ".gitignore").write_text("worktrees/\n.pair/\n")
        for stage in board.STAGES:
            (self.repo / "issues" / stage).mkdir(parents=True)
            (self.repo / "issues" / stage / "README.md").write_text(f"{stage}\n")
        sh(self.repo, "add", "-A")
        sh(self.repo, "commit", "-q", "-m", "board")
        self.turns: collections.deque[tuple[str, object]] = collections.deque()
        self.sent: list[tuple[str, str]] = []
        self.opened: list[tuple[str, str | None]] = []
        self.gates: list[bool] = []
        self.gate_runs = 0
        self.delivers: list[tuple[bool, str]] = []
        self.deliver_runs = 0
        self.stop_when_empty = False
        self.developer_between: dict[int, Action] = {}
        self.notes: list[str] = []
        self.before_land: list[Action] = []
        self.lock_waits = 0
        bench = self

        class TestLoop(Loop):
            def absorb_developer(self, st):  # type: ignore[no-untyped-def]
                edit = bench.developer_between.pop(len(bench.sent), None)
                if edit:
                    edit(self.wt)
                return super().absorb_developer(st)

            def land(self, st, sha, retry="merge"):  # type: ignore[no-untyped-def]
                if bench.before_land:
                    bench.before_land.pop(0)(bench.repo)
                return super().land(st, sha, retry)

            def wait_for_lock(self) -> None:
                bench.lock_waits += 1
                (bench.repo / ".git" / "index.lock").unlink(missing_ok=True)

        def factory(kind: str) -> Callable[[str, Path, str | None], FakeSeat]:
            def make(role: str, cwd: Path, resume: str | None) -> FakeSeat:
                self.opened.append((role, resume))
                loop = self.groomer if kind == "groom" else self.loop
                return FakeSeat(role, cwd, resume, self, loop)

            return make

        def gate(_tree: Path) -> tuple[bool, str]:
            self.gate_runs += 1
            ok = self.gates.pop(0) if self.gates else True
            return ok, "" if ok else "FAILED: test_widget"

        def deliver(_tree: Path) -> tuple[bool, str] | None:
            """A repository with no `deliver` recipe, unless a test queues results."""
            self.deliver_runs += 1
            return self.delivers.pop(0) if self.delivers else None

        self.loop, self.groomer = (
            TestLoop(
                self.repo,
                factory(kind),
                gate,
                self.notes.append,
                prompts=PROMPTS,
                deliver=deliver,
                say=lambda _m: None,
                kind=kind,
            )
            for kind in ("pair", "groom")
        )

    def state(self, loop: Loop | None = None) -> State:
        """A loop's saved state, the Issue loop's by default, which a test expects to exist."""
        st = (loop or self.loop).load()
        assert st is not None
        return st

    def issue_in_worktree(self, slug: str) -> board.Issue:
        """The issue as it stands in the loop's worktree, which a test expects to exist."""
        issue = board.read(self.loop.wt, slug)
        assert issue is not None
        return issue

    def issue(self, stage: str, slug: str, title: str, **fields: str) -> None:
        head = "".join(f"{k}: {v}\n" for k, v in fields.items())
        text = (f"---\n{head}---\n" if head else "") + f"# {title}\n\nSome words.\n"
        (self.repo / "issues" / stage / f"{slug}.md").write_text(text)
        sh(self.repo, "add", "-A")
        sh(self.repo, "commit", "-q", "-m", f"add {slug}")

    def script(self, *turns: tuple[str, object]) -> None:
        self.turns.extend(turns)

    def on_main(self, rel: str) -> bool:
        return (
            subprocess.run(
                ["git", "cat-file", "-e", f"main:{rel}"],
                cwd=self.repo,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )

    def close(self) -> None:
        self.tmp.cleanup()


PLAN = "\n## The plan\n\nChange a.txt.\n"


class LoopTest(unittest.TestCase):
    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)

    def test_easy_issue_lands_as_one_squash_commit(self) -> None:
        b = self.b
        b.issue("backlog", "fix-typo", "Fix the typo")
        b.script(
            ("primary", front("fix-typo", difficulty="easy")),
            ("secondary", quiet),
            ("primary", append("fix-typo", PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "fixed\n")),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertTrue(b.on_main("issues/done/fix-typo.md"))
        self.assertFalse(b.on_main("issues/backlog/fix-typo.md"))
        self.assertFalse(b.on_main("issues/underway/fix-typo.md"))
        self.assertEqual((b.repo / "a.txt").read_text(), "fixed\n")
        log = sh(b.repo, "log", "--format=%s", "main")
        self.assertEqual(log.splitlines()[:2], ["Fix the typo", "Start fix-typo"])
        self.assertEqual(len(log.splitlines()), 4)
        self.assertIn("Seat: primary", sh(b.repo, "log", "-1", "--format=%B", "main"))
        self.assertEqual(b.opened, [("primary", None), ("secondary", None)])
        self.assertFalse((b.repo / ".pair" / "state.json").exists())
        self.assertEqual(b.gate_runs, 1)

    def test_two_quiet_turns_agree(self) -> None:
        b = self.b
        b.issue("backlog", "ready", "Ready already", difficulty="easy")
        b.stop_when_empty = True
        b.script(("primary", quiet), ("secondary", quiet))
        self.assertEqual(b.loop.run(), "stopped")
        self.assertEqual(b.state().stage, "todo")

    def test_the_secondary_can_change_and_the_primary_accept(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X")
        b.stop_when_empty = True
        b.script(
            ("primary", quiet),
            ("secondary", front("x", difficulty="medium")),
            ("primary", quiet),
        )
        b.loop.run()
        self.assertEqual(b.state().stage, "todo")

    def test_agreement_without_the_requirement_carries_on_and_says_what_is_missing(
        self,
    ) -> None:
        b = self.b
        b.issue("backlog", "x", "X")
        b.stop_when_empty = True
        b.script(("primary", quiet), ("secondary", quiet), ("primary", quiet))
        b.loop.run()
        st = b.state()
        self.assertEqual(st.stage, "backlog")
        self.assertIn("set `difficulty:`", b.sent[2][1])

    def test_gate_failure_goes_back_to_the_pair_with_its_output(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")
        b.gates = [False, True]
        b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("x", PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "1")),
            ("secondary", quiet),
            ("primary", write("a.txt", "2")),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertIn("FAILED: test_widget", b.sent[6][1])
        self.assertEqual(b.gate_runs, 2)

    def test_needs_elaboration_sends_the_issue_to_backlog_and_drops_the_code(
        self,
    ) -> None:
        b = self.b
        b.issue("backlog", "vague", "Vague")
        b.script(
            (
                "primary",
                both(
                    write("b.txt", "half"),
                    append("vague", "\n# Needs elaboration\n\nWhich widget?\n"),
                ),
            )
        )
        self.assertEqual(b.loop.run(once=True), "kicked")
        self.assertTrue(b.on_main("issues/backlog/vague.md"))
        self.assertFalse(b.on_main("issues/roadmap/vague.md"))
        self.assertFalse(b.on_main("b.txt"))
        self.assertIn(
            "Which widget?", sh(b.repo, "show", "main:issues/backlog/vague.md")
        )
        self.assertIsNone(board.next_ripe(b.repo, "main"))

    def test_a_vanished_issue_file_goes_back_to_backlog_and_sits_out(self) -> None:
        b = self.b
        b.issue("backlog", "gone", "Gone")

        def delete(cwd: Path) -> None:
            (cwd / "issues/underway/gone.md").unlink()

        b.script(("primary", delete))
        self.assertEqual(b.loop.run(once=True), "kicked")
        text = sh(b.repo, "show", "main:issues/backlog/gone.md")
        self.assertTrue(board.needs_elaboration(text))
        self.assertFalse(b.on_main("issues/underway/gone.md"))
        self.assertIsNone(board.next_ripe(b.repo, "main"))

    def test_round_cap_sends_the_issue_back_with_a_reason(self) -> None:
        b = self.b
        b.issue("backlog", "churn", "Churn")
        b.script(
            *[
                (role, write("c.txt", str(i)))
                for i in range(8)
                for role in [("primary", "secondary")[i % 2]]
            ]
        )
        self.assertEqual(b.loop.run(once=True), "kicked")
        self.assertIn(
            "did not settle the backlog stage",
            sh(b.repo, "show", "main:issues/backlog/churn.md"),
        )

    def test_a_round_cap_override_applies_to_every_difficulty(self) -> None:
        b = self.b
        b.issue("backlog", "short", "Short", difficulty="medium")
        b.loop.round_cap = 1
        b.script(("primary", write("c.txt", "1")), ("secondary", write("c.txt", "2")))
        self.assertEqual(b.loop.run(once=True), "kicked")
        self.assertIn(
            "within 2 turns", sh(b.repo, "show", "main:issues/backlog/short.md")
        )

    def test_a_seat_that_moves_the_issue_file_is_quietly_put_back(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X")

        def move(cwd: Path) -> None:
            front("x", difficulty="easy")(cwd)
            (cwd / "issues/underway/x.md").rename(cwd / "issues/todo/x.md")

        b.stop_when_empty = True
        b.script(("primary", move))
        b.loop.run()
        self.assertEqual(board.locations(b.loop.wt, "x"), ["underway"])
        self.assertEqual(b.issue_in_worktree("x").difficulty, "easy")

    def test_a_human_edit_between_turns_resets_agreement(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X")
        b.developer_between[1] = front("x", difficulty="easy")
        b.stop_when_empty = True
        b.script(("primary", quiet), ("secondary", quiet), ("primary", quiet))
        b.loop.run()
        self.assertEqual(b.state().stage, "todo")
        self.assertIn("developer: edits on x", sh(b.loop.wt, "log", "--format=%s"))
        self.assertIn("The developer changed things", b.sent[1][1])

    def test_a_crashed_seat_restarts_once_from_its_session(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")
        b.stop_when_empty = True
        b.script(("primary", CRASH), ("primary", quiet))
        b.loop.run()
        self.assertEqual(b.opened, [("primary", None), ("primary", "primary-session")])
        self.assertTrue(b.sent[1][1].startswith("(Your session was restarted"))

    def test_a_dead_supervisor_gives_the_interrupted_turn_back_to_its_seat(
        self,
    ) -> None:
        b = self.b
        b.issue("backlog", "x", "X")

        def supervisor_killed_mid_turn(cwd: Path) -> None:
            front("x", difficulty="easy")(cwd)
            raise KeyboardInterrupt

        b.script(("primary", supervisor_killed_mid_turn))
        with self.assertRaises(KeyboardInterrupt):
            b.loop.run()
        self.assertEqual(b.state().in_turn, "primary")
        b.stop_when_empty = True
        b.script(("primary", quiet))
        b.loop.run()
        self.assertEqual(b.opened[-1], ("primary", "primary-session"))
        self.assertTrue(b.sent[-1][1].startswith("(Your session was restarted"))
        log = sh(b.loop.wt, "log", "--format=%s", "main..HEAD")
        self.assertIn("primary: backlog turn on x", log)
        self.assertNotIn("developer:", log)

    def test_reap_stops_only_an_orphaned_seat_in_this_worktree(self) -> None:
        b = self.b
        b.loop.ensure_worktree()
        b.loop.dir.mkdir(exist_ok=True)
        b.loop.seat_command = "sleep"
        orphan = subprocess.Popen(["sleep", "60"], cwd=b.loop.wt)
        elsewhere = subprocess.Popen(["sleep", "60"], cwd=b.repo)
        self.addCleanup(elsewhere.wait)
        self.addCleanup(elsewhere.kill)
        self.addCleanup(orphan.kill)
        (b.loop.dir / "primary.pid").write_text(f"{orphan.pid}\n")
        (b.loop.dir / "secondary.pid").write_text(f"{elsewhere.pid}\n")
        b.loop.reap()
        self.assertIsNotNone(orphan.wait(timeout=10))
        self.assertIsNone(elsewhere.poll())

    def test_a_seat_that_crashes_twice_pauses_the_loop(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X")
        b.script(("primary", CRASH), ("primary", CRASH))
        self.assertEqual(b.loop.run(), "paused")
        self.assertIn("failed twice", b.state().paused or "")
        self.assertTrue(b.notes)

    def test_a_refused_fast_forward_pauses_until_the_human_clears_the_way(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")

        def developer_has_a_local_file(_cwd: Path) -> None:
            (b.repo / "a.txt").write_text("mine")

        b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("x", PLAN)),
            ("secondary", quiet),
            ("primary", both(write("a.txt", "branch"), developer_has_a_local_file)),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(), "paused")
        self.assertEqual(b.state().retry, "merge")
        (b.repo / "a.txt").unlink()
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual((b.repo / "a.txt").read_text(), "branch")

    def test_starting_an_issue_moves_it_to_underway_on_main_once(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")
        b.stop_when_empty = True
        b.script(("primary", quiet))
        self.assertEqual(b.loop.run(), "stopped")
        self.assertTrue(b.on_main("issues/underway/x.md"))
        self.assertFalse(b.on_main("issues/backlog/x.md"))
        self.assertEqual(sh(b.repo, "log", "-1", "--format=%s", "main"), "Start x")
        self.assertEqual(b.state().base, sh(b.repo, "rev-parse", "main"))
        self.assertIn("underway       1  x\n", status(b.repo))
        self.assertIn("underway: x in underway/, its backlog stage", status(b.repo))
        b.stop_when_empty = False
        b.loop.stop_requested = False
        b.script(*easy_turns("x")[1:])
        self.assertEqual(b.loop.run(once=True), "landed")
        log = sh(b.repo, "log", "--format=%s", "main").splitlines()
        self.assertEqual(log.count("Start x"), 1)
        self.assertTrue(b.on_main("issues/done/x.md"))
        self.assertFalse(b.on_main("issues/underway/x.md"))

    def test_a_refused_fast_forward_at_the_start_leaves_the_issue_in_backlog(
        self,
    ) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")
        in_the_way = b.repo / "issues/underway/x.md"
        in_the_way.write_text("mine\n")
        before = sh(b.repo, "rev-parse", "main")
        self.assertEqual(b.loop.run(), "paused")
        self.assertEqual(sh(b.repo, "rev-parse", "main"), before)
        self.assertTrue(b.on_main("issues/backlog/x.md"))
        self.assertIsNone(b.loop.load())
        self.assertEqual(b.sent, [])
        self.assertTrue(b.notes)
        in_the_way.unlink()
        b.script(*easy_turns("x"))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertTrue(b.on_main("issues/done/x.md"))

    def test_an_issue_left_underway_without_its_state_is_taken_up_again(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A", difficulty="easy")
        b.issue("backlog", "x", "X", difficulty="easy")
        b.loop.ensure_worktree()
        self.assertIsNotNone(b.loop.start(State(slug="x")))
        b.loop.clear()
        b.script(*easy_turns("x"))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertIn("Groom issues/underway/x.md", b.sent[0][1])
        log = sh(b.repo, "log", "--format=%s", "main").splitlines()
        self.assertEqual(log.count("Start x"), 1)
        self.assertTrue(b.on_main("issues/done/x.md"))
        self.assertTrue(b.on_main("issues/backlog/a.md"))

    def test_a_human_issue_waits_for_the_desk_check(self) -> None:
        b = self.b
        b.issue("backlog", "h", "Developer", difficulty="developer")
        b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("h", PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "x")),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(), "desk-check")
        self.assertEqual(b.loop.run(), "desk-check")
        self.assertFalse(b.on_main("a.txt"))
        self.assertEqual(b.groomer.groom(), "nothing")
        self.assertEqual(b.loop.accept(), "landed")
        self.assertTrue(b.on_main("issues/done/h.md"))

    def test_a_failed_desk_check_returns_to_the_pair(self) -> None:
        b = self.b
        b.issue("backlog", "h", "Developer", difficulty="developer")
        b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("h", PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "x")),
            ("secondary", quiet),
        )
        b.loop.run()
        append("h", "\nDesk check: the button is blue, make it red.\n")(b.loop.wt)
        b.stop_when_empty = True
        b.script(("primary", write("a.txt", "red")))
        b.loop.resume()
        st = b.state()
        self.assertEqual(st.stage, "in-progress")
        self.assertIn("desk check", b.sent[-1][1])
        self.assertIn("make it red", b.sent[-1][1])

    def test_an_accept_whose_gate_fails_goes_back_to_in_progress(self) -> None:
        b = self.b
        b.issue("backlog", "h", "Developer", difficulty="developer")
        b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("h", PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "x")),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(), "desk-check")
        (b.repo / "b.txt").write_text("elsewhere")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "main moves")
        b.gates = [False]
        b.stop_when_empty = True
        b.script(("primary", quiet))
        self.assertEqual(b.loop.accept(), "stopped")
        self.assertEqual(b.state().stage, "in-progress")
        self.assertEqual(board.locations(b.loop.wt, "h"), ["in-progress"])
        self.assertIn("Implement issues/in-progress/h.md", b.sent[-1][1])
        self.assertIn("without landing", b.sent[-1][1])
        self.assertIn("FAILED: test_widget", b.sent[-1][1])

    def accept_that_conflicts(self) -> None:
        """Bring a developer Issue to its desk check, then accept it into a conflict."""
        b = self.b
        b.issue("backlog", "h", "Developer", difficulty="developer")
        b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("h", PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "x")),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(), "desk-check")
        (b.repo / "a.txt").write_text("y")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "developer's a.txt")
        self.assertEqual(b.loop.accept(), "paused")
        st = b.state()
        self.assertEqual((st.stage, st.retry), ("desk-check", None))
        b.stop_when_empty = True
        b.script(("primary", quiet))

    def test_an_accept_that_conflicts_goes_back_to_in_progress(self) -> None:
        b = self.b
        self.accept_that_conflicts()
        self.assertEqual(b.loop.run(), "stopped")
        self.assertEqual(b.state().stage, "in-progress")
        self.assertEqual(board.locations(b.loop.wt, "h"), ["in-progress"])
        self.assertIn("Implement issues/in-progress/h.md", b.sent[-1][1])
        self.assertIn("conflicts with main", b.sent[-1][1])
        self.assertNotIn("The developer changed things", b.sent[-1][1])

    def test_a_resolved_conflict_reaches_the_pair_as_the_developers(self) -> None:
        b = self.b
        self.accept_that_conflicts()
        b.developer_between[len(b.sent)] = write("a.txt", "resolved")
        self.assertEqual(b.loop.run(), "stopped")
        self.assertEqual(b.state().stage, "in-progress")
        self.assertIn("conflicts with main", b.sent[-1][1])
        self.assertIn("The developer changed things", b.sent[-1][1])
        log = sh(b.loop.wt, "log", "--format=%s", "-3")
        self.assertIn("developer: edits on h", log)

    def test_a_hard_issue_is_split_into_backlog_children(self) -> None:
        b = self.b
        b.issue("backlog", "big", "Big")
        (b.repo / board.ORDER).write_text("big\n")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "order")
        b.script(
            (
                "primary",
                both(
                    front("big", difficulty="hard"),
                    write(
                        "issues/backlog/big-1-parse.md",
                        "---\ndifficulty: easy\nparent: big\n---\n# Parse\n",
                    ),
                    write(
                        "issues/backlog/big-2-render.md",
                        "---\ndifficulty: easy\nparent: big\n"
                        "waits_on: [big-1-parse]\n---\n# Render\n",
                    ),
                ),
            ),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertTrue(b.on_main("issues/backlog/big.md"))
        self.assertFalse(b.on_main("issues/underway/big.md"))
        self.assertFalse(b.on_main("issues/done/big.md"))
        self.assertEqual(sh(b.repo, "show", f"main:{board.ORDER}"), "big")
        self.assertEqual(board.next_ripe(b.repo, "main"), "big-1-parse")

    def test_a_failing_gate_after_a_split_goes_back_pauses_the_landing(self) -> None:
        b = self.b
        b.issue("backlog", "big", "Big")
        b.script(
            (
                "primary",
                both(
                    front("big", difficulty="hard"),
                    child("big-1"),
                    write("a.txt", "split\n"),
                ),
            ),
            ("secondary", quiet),
        )
        squash = b.loop.squash
        moved: list[bool] = []

        def main_moves_once(st: State) -> str:
            sha = squash(st)
            if not moved:
                moved.append(True)
                (b.repo / "elsewhere.txt").write_text("x\n")
                sh(b.repo, "add", "elsewhere.txt")
                sh(b.repo, "commit", "-q", "-m", "elsewhere")
            return sha

        b.loop.squash = main_moves_once  # type: ignore[method-assign]
        b.gates = [False]
        self.assertEqual(b.loop.run(once=True), "paused")
        self.assertEqual(b.state().retry, "merge")
        self.assertEqual(len(b.sent), 2)
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(len(b.sent), 2)
        self.assertTrue(b.on_main("issues/backlog/big.md"))
        self.assertFalse(b.on_main("issues/underway/big.md"))
        self.assertEqual((b.repo / "a.txt").read_text(), "split\n")

    def test_backlog_added_on_main_mid_issue_lands_alongside(self) -> None:
        b = self.b
        b.issue("backlog", "a-first", "First", difficulty="easy")

        def add_elsewhere(_cwd: Path) -> None:
            b.issue("backlog", "b-second", "Second")

        b.script(
            ("primary", append("a-first", PLAN)),
            ("secondary", quiet),
            ("primary", both(write("a.txt", "x"), add_elsewhere)),
            ("secondary", quiet),
        )
        b.turns.extendleft(reversed([("primary", quiet), ("secondary", quiet)]))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertTrue(b.on_main("issues/backlog/b-second.md"))
        self.assertTrue(b.on_main("issues/done/a-first.md"))
        self.assertEqual(board.next_ripe(b.repo, "main"), "b-second")

    def test_a_landed_issue_leaves_order_and_keeps_a_reordering_made_mid_issue(
        self,
    ) -> None:
        b = self.b
        b.issue("backlog", "b", "B")
        b.issue("backlog", "c", "C")
        b.issue("backlog", "a", "A", difficulty="easy")
        (b.repo / board.ORDER).write_text("a\n# groomed below\nb\nc\n")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "order")

        def reorder(_cwd: Path) -> None:
            (b.repo / board.ORDER).write_text("a\n# groomed below\nc\nb\n")
            sh(b.repo, "commit", "-q", "-am", "reorder")

        b.script(
            ("primary", append("a", PLAN)),
            ("secondary", quiet),
            ("primary", both(write("a.txt", "x"), reorder)),
            ("secondary", quiet),
            ("primary", quiet),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertTrue(b.on_main("issues/done/a.md"))
        self.assertEqual(
            sh(b.repo, "show", f"main:{board.ORDER}"), "# groomed below\nc\nb"
        )
        self.assertEqual(sh(b.repo, "log", "-1", "--format=%s", "main"), "A")
        self.assertEqual(board.next_ripe(b.repo, "main"), "c")


WAITING = {"difficulty": "easy", "waits_on": "[z]"}
"""Front matter for an issue that is groomed but never ripe, so a run ends at `empty`."""


def order(text: str) -> Action:
    return write(board.ORDER, text)


BRIEF = "\n## Desk-check brief\n\nDelivered; see it in a.txt.\n"
NOTES = "\n## Desk-check notes\n\n- make it red\n- make it loud\n"
CHILDREN = "\n## Desk-check children\n\n- big-red\n- `big-loud`\n"
FLIGHT = "issues/desk-check/big.md"
"""Where `FlightCheckTest`'s Flight lands once it passes its check."""


def child(slug: str) -> Action:
    return write(
        f"issues/backlog/{slug}.md",
        f"---\ndifficulty: easy\nparent: big\n---\n# {slug}\n",
    )


def unappend(slug: str, text: str) -> Action:
    """Take the last copy of `text` out of the issue, as `append` put it there."""

    def act(cwd: Path) -> None:
        issue = board.read(cwd, slug)
        assert issue is not None
        path = cwd / issue.path
        before, _, after = path.read_text().rpartition(text)
        path.write_text(before + after)

    return act


class FlightCheckTest(unittest.TestCase):
    """A Flight whose children have all landed, and the check the pair gives it."""

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)
        self.b.issue("backlog", "big", "Big", difficulty="hard")
        self.b.issue("done", "part", "Part", difficulty="easy", parent="big")
        (self.b.repo / board.ORDER).write_text("big\n# groomed below\n")
        sh(self.b.repo, "add", "-A")
        sh(self.b.repo, "commit", "-q", "-m", "order")

    def test_a_brief_lands_the_flight_at_its_desk_check_and_the_loop_goes_on(
        self,
    ) -> None:
        b = self.b
        b.issue("backlog", "next", "Next", difficulty="easy")
        b.script(
            ("primary", append("big", BRIEF)),
            ("secondary", quiet),
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("next", PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "x")),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(), "empty")
        first = b.sent[0][1]
        self.assertIn("Check the Flight issues/underway/big.md", first)
        self.assertTrue(b.on_main("issues/desk-check/big.md"))
        self.assertFalse(b.on_main("issues/backlog/big.md"))
        self.assertFalse(b.on_main("issues/underway/big.md"))
        self.assertTrue(b.on_main("issues/done/next.md"))
        self.assertEqual(sh(b.repo, "show", f"main:{board.ORDER}"), "# groomed below")
        self.assertIsNone(b.loop.load())
        self.assertEqual(b.deliver_runs, 1)
        self.assertNotIn("Delivered by", sh(b.repo, "show", f"main:{FLIGHT}"))

    def test_a_flight_paused_while_landing_still_lands_at_its_desk_check(
        self,
    ) -> None:
        b = self.b

        def developer_switches_branch(_cwd: Path) -> None:
            sh(b.repo, "checkout", "-q", "-b", "side")

        b.script(
            ("primary", both(append("big", BRIEF), developer_switches_branch)),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "paused")
        self.assertEqual((b.state().stage, b.state().retry), ("desk-check", "merge"))
        sh(b.repo, "checkout", "-q", "main")
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertTrue(b.on_main("issues/desk-check/big.md"))
        self.assertFalse(b.on_main("issues/done/big.md"))

    def test_a_flight_overtaken_and_conflicting_goes_back_to_its_check(
        self,
    ) -> None:
        """`main` moves while the Flight lands, and the rebase onto it conflicts.

        `start` lands too, so `before_land` holds a quiet action for it first.
        """
        b = self.b

        def main_edits_the_flight(repo: Path) -> None:
            append("big", "\n## Desk-check brief\n\nSomething else.\n")(repo)
            sh(repo, "commit", "-q", "-am", "edit big on main")

        b.before_land = [quiet, main_edits_the_flight]
        b.script(("primary", append("big", BRIEF)), ("secondary", quiet))
        self.assertEqual(b.loop.run(once=True), "paused")
        st = b.state()
        self.assertEqual((st.stage, st.retry), ("desk-check", None))
        b.stop_when_empty = True
        b.script(("primary", quiet))
        self.assertEqual(b.loop.run(once=True), "stopped")
        self.assertEqual(b.state().stage, "flight-check")
        self.assertEqual(board.locations(b.loop.wt, "big"), ["underway"])
        self.assertIn("Check the Flight issues/underway/big.md", b.sent[-1][1])
        self.assertIn("conflicts with main", b.sent[-1][1])

    def test_a_passing_delivery_is_recorded_in_the_brief(self) -> None:
        b = self.b
        b.delivers = [(True, "deployed")]
        b.script(("primary", append("big", BRIEF)), ("secondary", quiet))
        self.assertEqual(b.loop.run(once=True), "landed")
        text = sh(b.repo, "show", f"main:{FLIGHT}")
        sha = sh(b.repo, "rev-parse", "--short", "main~1")
        self.assertTrue(
            text.endswith(f"Delivered by `just deliver` from main at {sha}."), text
        )
        self.assertEqual(sh(b.repo, "status", "--porcelain"), "")

    def test_a_failing_delivery_pauses_before_the_desk_check(self) -> None:
        b = self.b
        b.delivers = [(False, "UAT refused the deploy")]
        b.script(("primary", append("big", BRIEF)), ("secondary", quiet))
        before = sh(b.repo, "rev-parse", "main")
        self.assertEqual(b.loop.run(once=True), "paused")
        st = b.state()
        self.assertEqual(st.retry, "merge")
        self.assertIn("UAT refused the deploy", st.paused or "")
        self.assertEqual(sh(b.repo, "rev-parse", "main~1"), before)
        self.assertEqual(sh(b.repo, "log", "-1", "--format=%s", "main"), "Start big")
        self.assertTrue(b.on_main("issues/underway/big.md"))
        self.assertIn("big", sh(b.repo, "show", f"main:{board.ORDER}"))
        b.delivers = [(True, "deployed")]
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertTrue(b.on_main(FLIGHT))
        self.assertEqual(b.deliver_runs, 2)

    def test_a_landing_retried_after_delivery_does_not_deliver_again(self) -> None:
        b = self.b
        b.delivers = [(True, "deployed"), (True, "deployed")]

        def developer_switches_branch(_cwd: Path) -> None:
            sh(b.repo, "checkout", "-q", "-b", "side")

        b.script(
            ("primary", both(append("big", BRIEF), developer_switches_branch)),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "paused")
        sh(b.repo, "checkout", "-q", "main")
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(b.deliver_runs, 1)
        self.assertEqual(sh(b.repo, "show", f"main:{FLIGHT}").count("Delivered by"), 1)

    def test_accept_with_a_slug_moves_the_flight_to_done(self) -> None:
        b = self.b
        b.script(("primary", append("big", BRIEF)), ("secondary", quiet))
        b.loop.run(once=True)
        self.assertEqual(b.loop.accept("big"), "accepted")
        self.assertTrue(b.on_main("issues/done/big.md"))
        self.assertFalse(b.on_main("issues/desk-check/big.md"))
        self.assertEqual(sh(b.repo, "status", "--porcelain"), "")

    def test_notes_come_back_as_children_and_the_flight_returns_to_its_desk_check(
        self,
    ) -> None:
        b = self.b
        b.script(("primary", append("big", BRIEF)), ("secondary", quiet))
        b.loop.run(once=True)
        flight = b.repo / "issues/desk-check/big.md"
        flight.write_text(flight.read_text() + NOTES)
        self.assertEqual(b.loop.resume("big"), "resumed")
        self.assertTrue(b.on_main("issues/backlog/big.md"))
        self.assertIn("make it loud", sh(b.repo, "show", "main:issues/backlog/big.md"))
        self.assertEqual(
            sh(b.repo, "show", f"main:{board.ORDER}"), "big\n# groomed below"
        )
        self.assertEqual(sh(b.repo, "status", "--porcelain"), "")
        b.script(
            ("primary", append("big", BRIEF)),
            ("secondary", quiet),
            ("primary", both(unappend("big", BRIEF), child("big-red"), child("big-loud"))),
            ("secondary", quiet),
            ("primary", append("big", CHILDREN)),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertIn("ends in a `## Desk-check notes` section", b.sent[-6][1])
        self.assertIn("This check wrote a brief", b.sent[-4][1])
        self.assertIn("## Desk-check children", b.sent[-2][1])
        self.assertTrue(b.on_main("issues/backlog/big.md"))
        self.assertTrue(b.on_main("issues/backlog/big-red.md"))
        for slug in ("big-red", "big-loud"):
            sh(b.repo, "mv", f"issues/backlog/{slug}.md", f"issues/done/{slug}.md")
        sh(b.repo, "commit", "-q", "-m", "children land")
        self.assertEqual(board.next_ripe(b.repo, "main"), "big")
        b.script(("primary", append("big", BRIEF)), ("secondary", quiet))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertNotIn("Desk-check notes` in", b.sent[-2][1])
        self.assertTrue(b.on_main("issues/desk-check/big.md"))
        body = sh(b.repo, "show", "main:issues/desk-check/big.md")
        self.assertEqual(
            [board.sections(body, name) for name in (
                "Desk-check brief", "Desk-check notes", "Desk-check children"
            )],
            [2, 1, 1],
        )

    def test_resume_drops_the_lines_of_the_flights_parts(self) -> None:
        b = self.b
        b.script(("primary", append("big", BRIEF)), ("secondary", quiet))
        b.loop.run(once=True)
        b.issue("backlog", "late", "Late", difficulty="easy", parent="big")
        (b.repo / board.ORDER).write_text("# groomed below\nlate\n")
        flight = b.repo / "issues/desk-check/big.md"
        flight.write_text(flight.read_text() + NOTES)
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "late placed, notes written")
        self.assertEqual(b.loop.resume("big"), "resumed")
        self.assertEqual(
            sh(b.repo, "show", f"main:{board.ORDER}"), "big\n# groomed below"
        )

    def test_resume_gives_a_nested_flight_no_line(self) -> None:
        b = self.b
        b.issue("backlog", "outer", "Outer")
        b.issue("backlog", "big", "Big", difficulty="hard", parent="outer")
        (b.repo / board.ORDER).write_text("outer\n# groomed below\n")
        sh(b.repo, "commit", "-q", "-am", "order")
        b.script(("primary", append("big", BRIEF)), ("secondary", quiet))
        self.assertEqual(b.loop.run(once=True), "landed")
        flight = b.repo / "issues/desk-check/big.md"
        flight.write_text(flight.read_text() + NOTES)
        self.assertEqual(b.loop.resume("big"), "resumed")
        self.assertEqual(
            sh(b.repo, "show", f"main:{board.ORDER}"), "outer\n# groomed below"
        )

    def test_a_children_section_must_list_the_new_children(self) -> None:
        b = self.b
        b.issue("backlog", "big", "Big" + BRIEF + NOTES, difficulty="hard")
        b.stop_when_empty = True
        b.script(
            ("primary", both(child("big-red"), append("big", CHILDREN))),
            ("secondary", quiet),
            ("primary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "stopped")
        self.assertIn("new children are big-red; make them match", b.sent[-1][1])

    def test_the_flight_desk_check_leaves_an_issue_underway_alone(self) -> None:
        b = self.b
        sh(b.repo, "mv", "issues/backlog/big.md", "issues/desk-check/big.md")
        sh(b.repo, "commit", "-q", "-m", "at the desk")
        b.loop.save(State(slug="other", stage="desk-check", retry="desk-check"))
        held = b.loop.state_file.read_text()
        flight = b.repo / "issues/desk-check/big.md"
        flight.write_text(flight.read_text() + NOTES)
        self.assertEqual(b.loop.resume("big"), "resumed")
        self.assertEqual(b.loop.state_file.read_text(), held)
        sh(b.repo, "mv", "issues/backlog/big.md", "issues/desk-check/big.md")
        sh(b.repo, "commit", "-q", "-m", "back at the desk")
        self.assertEqual(b.loop.accept("big"), "accepted")
        self.assertEqual(b.loop.state_file.read_text(), held)

    def test_the_flight_desk_check_refuses_what_it_cannot_answer(self) -> None:
        b = self.b
        self.assertEqual(b.loop.accept("big"), "none")
        self.assertEqual(b.loop.resume("nothing"), "none")
        sh(b.repo, "mv", "issues/backlog/big.md", "issues/desk-check/big.md")
        sh(b.repo, "commit", "-q", "-m", "at the desk")
        head = sh(b.repo, "rev-parse", "HEAD")
        self.assertEqual(b.loop.resume("big"), "none")
        flight = b.repo / "issues/desk-check/big.md"
        at_desk = flight.read_text()
        flight.write_text(at_desk + "\n## Desk-check notes\n\nno bullets here\n")
        self.assertEqual(b.loop.resume("big"), "none")
        flight.write_text(at_desk + NOTES + BRIEF)
        self.assertEqual(b.loop.resume("big"), "none")
        self.assertEqual(sh(b.repo, "rev-parse", "HEAD"), head)

    def test_a_gap_lands_as_a_child_and_the_flight_waits(self) -> None:
        b = self.b
        b.script(
            (
                "primary",
                write(
                    "issues/backlog/big-gap.md",
                    "---\ndifficulty: easy\nparent: big\n---\n# Gap\n",
                ),
            ),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertTrue(b.on_main("issues/backlog/big.md"))
        self.assertFalse(b.on_main("issues/underway/big.md"))
        self.assertTrue(b.on_main("issues/backlog/big-gap.md"))
        self.assertEqual(
            sh(b.repo, "show", f"main:{board.ORDER}"), "big\n# groomed below"
        )
        self.assertEqual(board.next_ripe(b.repo, "main"), "big-gap")
        self.assertEqual(b.deliver_runs, 0)

    def test_a_flight_check_left_underway_is_resumed_by_its_flight(self) -> None:
        b = self.b
        b.loop.ensure_worktree()
        self.assertIsNotNone(b.loop.start(State(slug="big", stage="flight-check")))
        b.loop.clear()
        self.assertTrue(b.on_main("issues/underway/big.md"))
        b.script(*flight_check_turns("big"))
        self.assertEqual(b.loop.run(flight="big"), "desk-check")
        self.assertTrue(b.on_main(FLIGHT))
        self.assertFalse(b.on_main("issues/underway/big.md"))

    def test_a_check_that_changes_nothing_is_not_accepted(self) -> None:
        b = self.b
        b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("big", BRIEF)),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertIn("Desk-check brief", b.sent[2][1])
        self.assertIn("not finished yet", b.sent[2][1])

    def test_a_check_that_changes_code_is_not_accepted(self) -> None:
        b = self.b
        b.stop_when_empty = True
        b.script(
            ("primary", both(append("big", BRIEF), write("a.txt", "x"))),
            ("secondary", quiet),
            ("primary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "stopped")
        self.assertIn("changes nothing outside issues/", b.sent[2][1])
        self.assertFalse(b.on_main("issues/done/big.md"))

    def test_an_earlier_rounds_brief_does_not_count(self) -> None:
        b = self.b
        b.issue("backlog", "big", "Big" + BRIEF, difficulty="hard")
        b.stop_when_empty = True
        b.script(("primary", quiet), ("secondary", quiet), ("primary", quiet))
        self.assertEqual(b.loop.run(once=True), "stopped")
        self.assertIn("not finished yet", b.sent[2][1])
        self.assertIn("underway: big in its Flight check", status(b.repo))

    def test_a_seat_that_moves_the_flight_file_is_put_back_in_underway(self) -> None:
        b = self.b

        def to_todo(cwd: Path) -> None:
            sh(cwd, "mv", "issues/underway/big.md", "issues/todo/big.md")

        b.script(
            ("primary", both(append("big", BRIEF), to_todo)),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertTrue(b.on_main("issues/desk-check/big.md"))
        self.assertFalse(b.on_main("issues/todo/big.md"))


def easy_turns(slug: str) -> tuple[tuple[str, object], ...]:
    """The six turns that take a groomed `easy` Issue from backlog to landing."""
    return (
        ("primary", quiet),
        ("secondary", quiet),
        ("primary", append(slug, PLAN)),
        ("secondary", quiet),
        ("primary", write(f"{slug}.txt", "x")),
        ("secondary", quiet),
    )


def flight_check_turns(slug: str) -> tuple[tuple[str, object], ...]:
    """The turns of a Flight check that writes a brief."""
    return (
        ("primary", append(slug, BRIEF)),
        ("secondary", quiet),
    )


class FlightRunTest(unittest.TestCase):
    """`run(flight=...)`: one Flight worked to its desk check, and nothing else."""

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)
        b = self.b
        b.issue("backlog", "big", "Big", difficulty="hard")
        b.issue("backlog", "big-a", "Big A", difficulty="easy", parent="big")
        b.issue(
            "backlog", "big-b", "Big B", difficulty="easy", parent="big",
            waits_on="[big-a]",
        )
        b.issue("backlog", "unflown", "Unflown", difficulty="easy")
        (b.repo / board.ORDER).write_text("unflown\nbig-b\nbig-a\nbig\n")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "order")

    def test_the_run_lands_the_flight_and_stops_at_its_desk_check(self) -> None:
        b = self.b
        b.script(*easy_turns("big-a"), *easy_turns("big-b"), *flight_check_turns("big"))
        self.assertEqual(b.loop.run(flight="big"), "desk-check")
        self.assertFalse(b.turns)
        self.assertTrue(b.on_main("issues/done/big-a.md"))
        self.assertTrue(b.on_main("issues/done/big-b.md"))
        self.assertTrue(b.on_main("issues/desk-check/big.md"))
        self.assertTrue(b.on_main("issues/backlog/unflown.md"))
        self.assertTrue(all("unflown" not in text for _, text in b.sent))

    def test_a_run_refuses_what_it_cannot_work(self) -> None:
        b = self.b
        head = sh(b.repo, "rev-parse", "HEAD")
        self.assertEqual(b.loop.run(flight="nothing"), "refused")
        self.assertEqual(b.loop.run(flight="unflown"), "refused")
        b.loop.save(State(slug="unflown", stage="todo"))
        self.assertEqual(b.loop.run(flight="big"), "refused")
        says: list[str] = []
        b.loop.say = says.append
        b.loop.save(State(slug="unflown", stage="desk-check", retry="desk-check"))
        self.assertEqual(b.loop.run(flight="big"), "refused")
        self.assertIn("`just pair-accept`", says[-1])
        b.loop.clear()
        sh(b.repo, "mv", "issues/backlog/big.md", "issues/desk-check/big.md")
        sh(b.repo, "commit", "-q", "-m", "at the desk")
        self.assertEqual(b.loop.run(flight="big"), "refused")
        self.assertEqual(b.sent, [])
        self.assertEqual(sh(b.repo, "rev-parse", "HEAD~1"), head)

    def test_an_issue_of_the_flight_underway_is_resumed(self) -> None:
        b = self.b
        b.loop.ensure_worktree()
        st = b.loop.start(State(slug="big-a", stage="backlog"))
        assert st is not None
        b.script(*easy_turns("big-a"), *easy_turns("big-b"), *flight_check_turns("big"))
        self.assertEqual(b.loop.run(flight="big"), "desk-check")
        self.assertTrue(b.on_main("issues/done/big-a.md"))
        self.assertTrue(b.on_main("issues/done/big-b.md"))

    def test_a_flight_below_is_worked_and_its_desk_check_stops_the_run(self) -> None:
        b = self.b
        sh(b.repo, "rm", "-q", "issues/backlog/big-b.md")
        b.issue("backlog", "big-a-1", "Big A 1", difficulty="easy", parent="big-a")
        says: list[str] = []
        b.loop.say = says.append
        b.script(*easy_turns("big-a-1"), *flight_check_turns("big-a"))
        self.assertEqual(b.loop.run(flight="big"), "empty")
        self.assertFalse(b.turns)
        self.assertTrue(b.on_main("issues/done/big-a-1.md"))
        self.assertTrue(b.on_main("issues/desk-check/big-a.md"))
        self.assertTrue(b.on_main("issues/backlog/big.md"))
        self.assertIn("waits on the desk check of big-a", says[-1])


class GroomingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)

    def main_order(self) -> str:
        return sh(self.b.repo, "show", f"main:{board.ORDER}")

    def commit_order(self, text: str) -> None:
        (self.b.repo / board.ORDER).write_text(text)
        sh(self.b.repo, "add", "-A")
        sh(self.b.repo, "commit", "-q", "-m", "order")

    def test_run_never_grooms(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A")
        b.stop_when_empty = True
        b.script(("primary", front("a", difficulty="easy")))
        self.assertEqual(b.loop.run(once=True), "stopped")
        self.assertTrue(b.sent[0][1].startswith("Groom issues/underway/a.md."))
        self.assertEqual(b.state().stage, "backlog")

    def test_a_pass_takes_up_only_the_issues_not_groomed(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A")
        b.issue("backlog", "b", "B", **WAITING)
        b.issue("backlog", "c", "C\n\n# Needs elaboration\n\nWhich C?")
        self.commit_order("# groomed below\nb\nc\n")
        self.assertEqual(board.to_groom(b.repo, "main"), ["a"])
        b.script(
            (
                "primary",
                both(front("a", difficulty="easy"), order("# groomed below\nb\nc\na\n")),
            ),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "groomed")
        prompt = b.sent[0][1]
        self.assertIn("- issues/backlog/a.md", prompt)
        self.assertNotIn("backlog/b.md", prompt)
        self.assertNotIn("backlog/c.md", prompt)
        self.assertIn("only insert", prompt)
        self.assertEqual(
            sh(b.repo, "log", "-1", "--format=%s", "main"), "Groom the backlog"
        )
        self.assertFalse((b.loop.dir / "groomed.json").exists())
        self.assertIsNone(b.groomer.load())
        self.assertEqual(b.groomer.groom(), "nothing")
        self.assertEqual(len(b.sent), 2)

    def test_nothing_to_groom_sends_no_turn(self) -> None:
        b = self.b
        self.assertEqual(b.groomer.groom(), "nothing")
        b.issue("backlog", "a", "A", **WAITING)
        self.commit_order("# groomed below\na\n")
        self.assertEqual(b.groomer.groom(), "nothing")
        self.assertEqual(b.sent, [])

    def test_a_pass_that_moves_a_ranked_issue_is_held_back(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A", **WAITING)
        b.issue("backlog", "b", "B", **WAITING)
        b.issue("backlog", "c", "C")
        self.commit_order("# groomed below\na\nb\n")
        b.stop_when_empty = True
        b.script(
            (
                "primary",
                both(front("c", difficulty="easy"), order("# groomed below\nb\nc\na\n")),
            ),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "stopped")
        self.assertIn("b, a moved", b.state(b.groomer).note)
        self.assertIn("ran in this order:\na\nb", b.state(b.groomer).note)
        b.stop_when_empty = False
        b.groomer.stop_requested = False
        b.script(("primary", order("# groomed below\na\nc\nb\n")), ("secondary", quiet))
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertEqual(self.main_order(), "# groomed below\na\nc\nb")

    def test_a_target_already_ranked_is_free_to_move(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A")
        b.issue("backlog", "b", "B", **WAITING)
        b.issue("backlog", "c", "C", **WAITING)
        self.commit_order("# groomed below\na\nb\nc\n")
        b.script(
            (
                "primary",
                both(front("a", difficulty="easy"), order("# groomed below\nb\nc\na\n")),
            ),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertEqual(self.main_order(), "# groomed below\nb\nc\na")

    def test_rerank_ranks_the_whole_order_with_nothing_to_groom(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A", **WAITING)
        b.issue("backlog", "b", "B", **WAITING)
        self.commit_order("# groomed below\na\nb\n")
        b.script(("primary", order("# groomed below\nb\na\n")), ("secondary", quiet))
        self.assertEqual(b.groomer.groom(rerank=True), "groomed")
        self.assertIn("(none: this pass only ranks)", b.sent[0][1])
        self.assertIn("judged across the whole backlog", b.sent[0][1])
        self.assertEqual(self.main_order(), "# groomed below\nb\na")

    def test_a_pass_that_changes_the_developers_lines_is_not_accepted(self) -> None:
        b = self.b
        for slug in ("a", "b", "c"):
            b.issue("backlog", slug, slug.upper())
        self.commit_order("a\n# groomed below\n")
        groomed = [front(s, difficulty="easy") for s in ("a", "b", "c")]
        b.stop_when_empty = True
        b.script(
            ("primary", both(*groomed, order("b\n# groomed below\na\nc\n"))),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "stopped")
        st = b.state(b.groomer)
        self.assertEqual(st.stage, "grooming")
        self.assertIn("are the developer's; put them back as they were:\na", st.note)
        b.stop_when_empty = False
        b.groomer.stop_requested = False
        b.script(
            ("primary", order("a\n# groomed below\nc\nb\n")),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertEqual(self.main_order(), "a\n# groomed below\nc\nb")

    def test_a_pass_that_deletes_a_backlog_issue_is_not_accepted(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A")
        b.issue("backlog", "b", "B", **WAITING)

        def delete(cwd: Path) -> None:
            (cwd / "issues/backlog/b.md").unlink()

        b.stop_when_empty = True
        b.script(
            (
                "primary",
                both(delete, front("a", difficulty="easy"), order("# groomed below\na\n")),
            ),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "stopped")
        self.assertIn("issues/backlog/b.md is gone", b.state(b.groomer).note)

    def test_a_pass_writes_order_and_its_marker_where_they_are_missing(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A", **WAITING)
        b.script(("primary", order("# groomed below\na\n")), ("secondary", quiet))
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertEqual(self.main_order(), "# groomed below\na")
        b.issue("backlog", "b", "B", **WAITING)
        self.commit_order("b\n")
        b.script(("primary", order("b\n# groomed below\na\n")), ("secondary", quiet))
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertEqual(self.main_order(), "b\n# groomed below\na")

    def test_a_hard_issue_split_in_a_pass_stays_in_backlog_and_order(
        self,
    ) -> None:
        b = self.b
        b.issue("backlog", "a", "A", **WAITING)
        b.issue("backlog", "big", "Big")
        self.commit_order("big\n# groomed below\n")
        b.script(
            (
                "primary",
                both(
                    front("big", difficulty="hard"),
                    write(
                        "issues/backlog/big-1.md",
                        "---\ndifficulty: easy\nparent: big\nwaits_on: [z]\n---\n"
                        "# One\n",
                    ),
                    order("big\n# groomed below\na\n"),
                ),
            ),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertTrue(b.on_main("issues/backlog/big.md"))
        self.assertFalse(b.on_main("issues/done/big.md"))
        self.assertEqual(self.main_order(), "big\n# groomed below\na")
        log = sh(b.repo, "log", "--format=%s", "main").splitlines()
        self.assertEqual(log[0], "Groom the backlog")

    def test_a_split_below_the_marker_keeps_its_line_and_writes_none_for_parts(
        self,
    ) -> None:
        b = self.b
        b.issue("backlog", "a", "A", **WAITING)
        b.issue("backlog", "big", "Big")
        self.commit_order("# groomed below\nbig\na\n")
        b.script(
            (
                "primary",
                both(
                    front("big", difficulty="hard"),
                    write(
                        "issues/backlog/big-1.md",
                        "---\ndifficulty: easy\nparent: big\n---\n# One\n",
                    ),
                ),
            ),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertEqual(self.main_order(), "# groomed below\nbig\na")
        self.assertEqual(board.running_order(b.repo, "main"), ["big-1", "big", "a"])

    def test_parts_left_out_of_order_leave_nothing_to_groom(self) -> None:
        b = self.b
        b.issue("backlog", "big", "Big", difficulty="hard")
        b.issue("backlog", "part", "Part", difficulty="easy", parent="big")
        self.commit_order("# groomed below\nbig\n")
        self.assertEqual(board.unnamed(b.repo, "main"), [])
        self.assertEqual(b.groomer.groom(), "nothing")
        self.assertEqual(b.sent, [])

    def test_a_hard_issue_the_pass_did_not_split_stays_in_backlog(self) -> None:
        b = self.b
        b.issue("backlog", "big", "Big", difficulty="hard")
        b.issue("backlog", "a", "A")
        self.commit_order("# groomed below\nbig\n")
        b.script(
            (
                "primary",
                both(front("a", difficulty="easy"), order("# groomed below\nbig\na\n")),
            ),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertTrue(b.on_main("issues/backlog/big.md"))

    def test_needs_elaboration_in_a_pass_parks_the_issue_and_lands(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A")
        b.script(
            (
                "primary",
                both(
                    append("a", "\n# Needs elaboration\n\nWhich A?\n"),
                    order("# groomed below\na\n"),
                ),
            ),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertTrue(b.on_main("issues/backlog/a.md"))
        self.assertIsNone(board.next_ripe(b.repo, "main"))
        self.assertEqual(b.groomer.groom(), "nothing")

    def test_a_send_back_writes_no_record(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A", difficulty="easy")
        b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("a", "\n# Needs elaboration\n\nWhich A?\n")),
        )
        self.assertEqual(b.loop.run(once=True), "kicked")
        self.assertTrue(b.on_main("issues/backlog/a.md"))
        self.assertFalse((b.loop.dir / "groomed.json").exists())

    def test_a_pass_past_its_cap_pauses_and_groom_gives_it_another(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A")
        b.groomer.round_cap = 1
        b.script(("primary", order("# groomed below\na\n")), ("secondary", quiet))
        self.assertEqual(b.groomer.groom(), "paused")
        st = b.state(b.groomer)
        self.assertEqual((st.stage, st.retry), ("grooming", "grooming"))
        b.script(("primary", front("a", difficulty="easy")), ("secondary", quiet))
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertEqual(self.main_order(), "# groomed below\na")

    def test_an_edit_on_main_mid_pass_lands_with_the_pass(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A")
        b.issue("backlog", "b", "B", **WAITING)
        self.commit_order("a\n# note\n# groomed below\n")

        def developer_edits_main(_cwd: Path) -> None:
            (b.repo / "issues/backlog/b.md").write_text(
                "---\ndifficulty: easy\nwaits_on: [z]\n---\n# B, sharper\n"
            )
            (b.repo / board.ORDER).write_text("# mine\na\n# note\n# groomed below\n")
            sh(b.repo, "commit", "-q", "-am", "the developer's edits")

        b.script(
            (
                "primary",
                both(
                    front("a", difficulty="easy"),
                    order("a\n# note\n# groomed below\nb\n"),
                    developer_edits_main,
                ),
            ),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertEqual(
            self.main_order(), "# mine\na\n# note\n# groomed below\nb"
        )
        self.assertIn("B, sharper", sh(b.repo, "show", "main:issues/backlog/b.md"))
        self.assertEqual(len(b.sent), 2)


def land_the_issue(slug: str) -> tuple[tuple[str, object], ...]:
    """The turns that take an easy Issue from its backlog stage's second turn to landing."""
    return (
        ("secondary", quiet),
        ("primary", append(slug, PLAN)),
        ("secondary", quiet),
        ("primary", write(f"{slug}.txt", "done\n")),
        ("secondary", quiet),
    )


class AlongsideTest(unittest.TestCase):
    """A grooming pass and an Issue at once, each in its own worktree."""

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")
        b.issue("backlog", "a", "A")
        (b.repo / board.ORDER).write_text("# groomed below\nx\n")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "order")

    def main_order(self) -> str:
        return sh(self.b.repo, "show", f"main:{board.ORDER}")

    def start_issue(self) -> None:
        """Take `x` through one turn of its backlog stage, and stop."""
        b = self.b
        b.stop_when_empty = True
        b.script(("primary", quiet))
        self.assertEqual(b.loop.run(), "stopped")
        b.loop.stop_requested = b.stop_when_empty = False

    def start_pass(self) -> None:
        """Groom `a` and place it after `x` in one turn of a pass, and stop."""
        b = self.b
        b.stop_when_empty = True
        b.script(
            ("primary", both(front("a", difficulty="easy"), order("# groomed below\nx\na\n")))
        )
        self.assertEqual(b.groomer.groom(), "stopped")
        b.groomer.stop_requested = b.stop_when_empty = False

    def test_a_pass_lands_while_an_issue_is_underway_and_the_issue_after_it(self) -> None:
        b = self.b
        self.start_issue()
        b.script(
            ("primary", both(front("a", difficulty="easy"), order("# groomed below\nx\na\n"))),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertIn("difficulty: easy", sh(b.repo, "show", "main:issues/backlog/a.md"))
        b.script(*land_the_issue("x"))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertTrue(b.on_main("issues/done/x.md"))
        self.assertEqual(self.main_order(), "# groomed below\na")
        log = sh(b.repo, "log", "--format=%s", "main").splitlines()
        self.assertEqual(log[:3], ["X", "Groom the backlog", "Start x"])
        self.assertEqual(b.notes[-1], "landed x")

    def test_an_issue_lands_while_a_pass_is_underway_and_the_pass_after_it(self) -> None:
        b = self.b
        self.start_pass()
        b.script(("primary", quiet), *land_the_issue("x"))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(self.main_order(), "# groomed below")
        b.script(("secondary", quiet))
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertEqual(self.main_order(), "# groomed below\na")
        self.assertTrue(b.on_main("issues/done/x.md"))
        self.assertIn("difficulty: easy", sh(b.repo, "show", "main:issues/backlog/a.md"))

    def test_status_shows_the_pass_and_the_issue(self) -> None:
        b = self.b
        self.start_issue()
        self.start_pass()
        shown = status(b.repo)
        self.assertIn("underway: x in underway/, its backlog stage", shown)
        self.assertIn("underway: grooming pass, turn 1", shown)
        self.assertIn("cd worktrees/pair && claude", shown)
        self.assertIn("cd worktrees/groom && claude", shown)

    def test_the_loop_leaves_alone_what_a_pass_targets(self) -> None:
        b = self.b
        sh(b.repo, "mv", "issues/backlog/x.md", "issues/done/x.md")
        sh(b.repo, "commit", "-q", "-m", "x is done")
        self.start_pass()
        self.assertEqual(b.loop.run(), "empty")
        b.issue("backlog", "y", "Y", difficulty="easy")
        b.stop_when_empty = True
        b.script(("primary", quiet))
        self.assertEqual(b.loop.run(), "stopped")
        self.assertEqual(b.state().slug, "y")

    def test_a_pass_that_loses_a_target_leaves_the_issue_underway_alone(self) -> None:
        b = self.b
        b.stop_when_empty = True
        b.script(
            ("primary", both(front("x", note="groomed"), order("# groomed below\nx\na\n")))
        )
        self.assertEqual(b.groomer.groom(), "stopped")
        b.groomer.stop_requested = b.stop_when_empty = False
        saved = b.groomer.state_file.read_text()
        b.groomer.clear()
        self.start_issue()
        b.groomer.state_file.write_text(saved)
        b.script(("secondary", both(front("a", difficulty="easy"))), ("primary", quiet))
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertNotIn("groomed", sh(b.repo, "show", "main:issues/underway/x.md"))
        self.assertEqual(self.main_order(), "# groomed below\nx\na")

    def test_a_rebuilt_order_that_undoes_the_commit_skips_it(self) -> None:
        b = self.b
        b.groomer.ensure_worktree()
        wt = b.groomer.wt
        sh(wt, "checkout", "-q", "-b", "pair/grooming")
        (wt / board.ORDER).write_text("# groomed below\nx\ngone\n")
        sh(wt, "commit", "-qam", "place a slug with no file")
        (b.repo / board.ORDER).write_text("# groomed below\nx\na\n")
        sh(b.repo, "commit", "-qam", "place a on main")
        st = State(slug="grooming", stage="grooming", base="x")
        self.assertIs(b.groomer.rebase(st), True)
        self.assertEqual(sh(wt, "rev-parse", "HEAD"), sh(b.repo, "rev-parse", "main"))

    def test_a_lock_that_stays_pauses_and_says_so(self) -> None:
        b = self.b

        def lock(repo: Path) -> None:
            (repo / ".git" / "index.lock").write_text("")

        b.loop.wait_for_lock = lambda: None  # type: ignore[method-assign]
        b.before_land = [lambda _repo: None, lock]
        b.script(("primary", quiet), *land_the_issue("x"))
        self.assertEqual(b.loop.run(once=True), "paused")
        self.assertIn(".git/index.lock stayed", b.state().paused or "")
        (b.repo / ".git" / "index.lock").unlink()

    def test_a_refused_fast_forward_is_tried_again(self) -> None:
        b = self.b

        def other_lands(repo: Path) -> None:
            z = repo / "z.txt"
            z.write_text((z.read_text() if z.exists() else "") + "z\n")
            sh(repo, "add", "z.txt")
            sh(repo, "commit", "-q", "-m", "the other process lands")

        def other_holds_the_index(repo: Path) -> None:
            (repo / ".git" / "index.lock").write_text("")

        b.before_land = [other_lands, other_holds_the_index, other_lands]
        b.script(("primary", quiet), *land_the_issue("x"))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual((b.before_land, b.lock_waits), ([], 1))
        self.assertEqual((b.repo / "z.txt").read_text(), "z\nz\n")
        self.assertTrue(b.on_main("issues/done/x.md"))
        self.assertTrue(b.on_main("z.txt"))
        b.before_land = [lambda _repo: None, other_lands]
        b.script(("primary", append("a", "\n# Needs elaboration\n\nWhich?\n")))
        self.assertEqual(b.loop.run(once=True), "kicked")
        self.assertIn("Which?", sh(b.repo, "show", "main:issues/backlog/a.md"))
        self.assertEqual(b.before_land, [])

    def test_local_edits_still_pause_a_landing(self) -> None:
        b = self.b

        def local_edits(repo: Path) -> None:
            (repo / "x.txt").write_text("mine\n")

        b.before_land = [lambda _repo: None, local_edits]
        b.script(("primary", quiet), *land_the_issue("x"))
        self.assertEqual(b.loop.run(once=True), "paused")
        self.assertIn("local edits in the way", b.state().paused or "")

    def test_a_pass_left_in_the_issue_worktree_is_dropped(self) -> None:
        b = self.b
        b.loop.ensure_worktree()
        sh(b.loop.wt, "checkout", "-q", "-b", "pair/grooming")
        b.loop.save(State(slug="grooming", stage="grooming", base="x", targets=["a"]))
        b.script(
            ("primary", both(front("a", difficulty="easy"), order("# groomed below\nx\na\n"))),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertIsNone(b.loop.load())
        b.loop.save(State(slug="grooming", stage="grooming", base="x", targets=["a"]))
        b.stop_when_empty = True
        b.script(("primary", quiet))
        self.assertEqual(b.loop.run(), "stopped")
        self.assertEqual(b.state().slug, "x")

    def test_the_two_locks_are_apart(self) -> None:
        from pair import hold_lock

        run = hold_lock(self.b.repo, "run.lock")
        self.assertIsNotNone(run)
        groom = hold_lock(self.b.repo, "groom.lock")
        self.assertIsNotNone(groom)
        self.assertIsNone(hold_lock(self.b.repo, "run.lock"))
        for lock in (run, groom):
            assert lock is not None
            lock.close()


class ExitCodeTest(unittest.TestCase):
    """`pair.py` exits with a code for each outcome, and 0 only when nothing more is needed."""

    def test_each_outcome_has_its_own_code(self) -> None:
        from pair import EXIT, LOCKED

        self.assertEqual(
            set(EXIT),
            {
                "landed", "groomed", "accepted", "resumed", "desk-check", "paused",
                "stopped", "kicked", "empty", "nothing", "refused", "none",
            },
        )
        done = {"landed", "groomed", "accepted", "resumed"}
        self.assertEqual({EXIT[o] for o in done}, {0})
        codes = [code for o, code in EXIT.items() if o not in done] + [LOCKED]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertTrue(set(codes).isdisjoint({0, 1, 2}))

    def test_the_script_exits_with_its_code(self) -> None:
        from pair import EXIT, LOCKED, hold_lock

        b = Bench()
        self.addCleanup(b.close)
        script = Path(__file__).resolve().parent / "pair.py"

        def exits(*args: str) -> int:
            return subprocess.run(
                [sys.executable, str(script), *args], cwd=b.repo, capture_output=True
            ).returncode

        self.assertEqual(exits("accept"), EXIT["none"])
        self.assertEqual(exits("resume"), EXIT["none"])
        self.assertEqual(exits("accept", "nosuch"), EXIT["none"])
        lock = hold_lock(b.repo, "run.lock")
        assert lock is not None
        self.addCleanup(lock.close)
        self.assertEqual(exits("accept"), LOCKED)


class EventLogTest(unittest.TestCase):
    """`.pair/events.jsonl`: one event for each transition, written once."""

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)

    def events(self, kind: str | None = None) -> list[dict[str, Any]]:
        path = event_log(self.b.repo)
        if not path.is_file():
            return []
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        return [row for row in rows if kind is None or row["kind"] == kind]

    def kinds(self) -> list[tuple[str, str, str | None]]:
        return [(e["loop"], e["kind"], e.get("slug")) for e in self.events()]

    def test_an_easy_issue_starts_moves_and_lands(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")
        b.script(*easy_turns("x"))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(
            self.kinds(),
            [("pair", "started", "x"), *[("pair", "moved", "x")] * 3, ("pair", "landed", "x")],
        )
        self.assertEqual(
            [(e["from"], e["to"]) for e in self.events("moved")],
            [("backlog", "todo"), ("todo", "in-progress"), ("in-progress", "done")],
        )
        landed = self.events("landed")[0]
        self.assertEqual(
            (landed["sha"], landed["stage"]), (sh(b.repo, "rev-parse", "main"), "done")
        )

    def test_a_developer_issue_logs_its_desk_check_and_not_a_pause(self) -> None:
        b = self.b
        b.issue("backlog", "h", "Developer", difficulty="developer")
        b.script(*easy_turns("h"))
        self.assertEqual(b.loop.run(), "desk-check")
        self.assertEqual(
            self.kinds()[-2:], [("pair", "moved", "h"), ("pair", "desk-check", "h")]
        )
        self.assertEqual(self.events("paused"), [])
        self.assertEqual(b.loop.run(), "desk-check")
        self.assertEqual(len(self.events("desk-check")), 1)
        self.assertEqual(b.loop.accept(), "landed")
        self.assertEqual(
            self.kinds()[-2:], [("pair", "moved", "h"), ("pair", "landed", "h")]
        )

    def test_a_send_back_is_logged(self) -> None:
        b = self.b
        b.issue("backlog", "vague", "Vague")
        b.script(("primary", append("vague", "\n# Needs elaboration\n\nWhich?\n")))
        self.assertEqual(b.loop.run(once=True), "kicked")
        self.assertEqual(
            self.kinds(), [("pair", "started", "vague"), ("pair", "sent-back", "vague")]
        )

    def test_a_flight_lands_then_reaches_its_desk_check(self) -> None:
        b = self.b
        b.issue("backlog", "big", "Big", difficulty="hard")
        b.issue("backlog", "big-a", "Big A", difficulty="easy", parent="big")
        b.script(*easy_turns("big-a"), *flight_check_turns("big"))
        self.assertEqual(b.loop.run(flight="big"), "desk-check")
        self.assertEqual(
            self.kinds()[-2:], [("pair", "landed", "big"), ("pair", "desk-check", "big")]
        )
        self.assertEqual(self.events("landed")[-1]["stage"], "desk-check")
        self.assertEqual(len(self.events("desk-check")), 1)

    def test_a_paused_landing_logs_the_pause_and_one_landing(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")

        def developer_has_a_local_file(_cwd: Path) -> None:
            (b.repo / "x.txt").write_text("mine")

        b.script(
            *easy_turns("x")[:4],
            ("primary", both(write("x.txt", "x"), developer_has_a_local_file)),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(), "paused")
        self.assertEqual([e["retry"] for e in self.events("paused")], ["merge"])
        (b.repo / "x.txt").unlink()
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual((len(self.events("moved")), len(self.events("landed"))), (3, 1))

    def test_a_landing_the_other_process_beats_is_logged_once(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")

        def other_lands(repo: Path) -> None:
            (repo / "z.txt").write_text("z\n")
            sh(repo, "add", "z.txt")
            sh(repo, "commit", "-q", "-m", "the other process lands")

        b.before_land = [lambda _repo: None, other_lands]
        b.script(*easy_turns("x"))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(b.before_land, [])
        self.assertEqual((len(self.events("moved")), len(self.events("landed"))), (3, 1))

    def test_a_stop_is_logged_as_stopped(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")
        b.stop_when_empty = True
        b.script(("primary", quiet))
        self.assertEqual(b.loop.run(), "stopped")
        self.assertEqual(
            self.kinds(), [("pair", "started", "x"), ("pair", "stopped", "x")]
        )

    def test_nothing_ripe_is_logged_without_a_slug(self) -> None:
        self.assertEqual(self.b.loop.run(), "empty")
        self.assertEqual(self.kinds(), [("pair", "empty", None)])

    def test_a_grooming_pass_logs_as_groom(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A")
        b.script(
            ("primary", both(front("a", difficulty="easy"), order("# groomed below\na\n"))),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertEqual(b.groomer.groom(), "nothing")
        self.assertEqual(
            self.kinds(),
            [
                ("groom", "started", "grooming"),
                ("groom", "groomed", "grooming"),
                ("groom", "empty", None),
            ],
        )

    def test_a_supervisor_logs_its_end_and_its_crash(self) -> None:
        from pair import supervise

        repo = self.b.repo
        self.assertEqual(supervise(repo, "pair", lambda: "landed"), "landed")

        def crash() -> str:
            raise RuntimeError("boom")

        def interrupted() -> str:
            raise KeyboardInterrupt

        with self.assertRaises(RuntimeError):
            supervise(repo, "groom", crash)
        with self.assertRaises(KeyboardInterrupt):
            supervise(repo, "pair", interrupted)
        self.assertEqual(
            [(e["loop"], e["outcome"]) for e in self.events("ended")],
            [("pair", "landed"), ("groom", "crashed"), ("pair", "abandoned")],
        )


class WatchTest(unittest.TestCase):
    """`just pair-watch`: it exits when its condition is met, and never outlives the loop."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        (self.repo / ".pair").mkdir()
        self.out: list[str] = []

    def supervisor(self, lock: str = "run.lock") -> subprocess.Popen[bytes]:
        """A process standing in for a supervisor, with `pair.py` in its command line."""
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)", "pair.py"]
        )
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)
        (self.repo / ".pair" / lock).write_text(f"{proc.pid}\n")
        return proc

    def later(self, *steps: Callable[[], object]) -> None:
        """Run each step a moment apart, after the watcher has started."""

        def go() -> None:
            for step in steps:
                time.sleep(0.2)
                step()

        thread = threading.Thread(target=go, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 10)

    def emit(self, kind: str, **fields: Any) -> Callable[[], None]:
        return lambda: append_event(self.repo, "pair", kind, **fields)

    def watch(self, *until: str) -> int:
        result: list[int] = []
        thread = threading.Thread(
            target=lambda: result.append(
                watch(self.repo, list(until), poll=0.02, out=self.out.append)
            ),
            daemon=True,
        )
        thread.start()
        thread.join(10)
        self.assertFalse(thread.is_alive(), "the watcher did not exit")
        return result[0]

    def test_each_condition_is_met(self) -> None:
        cases = [
            (("landed",), [self.emit("moved", slug="x"), self.emit("landed", slug="x")]),
            (("developer",), [self.emit("paused", slug="x", reason="r")]),
            (("developer",), [self.emit("sent-back", slug="x")]),
            (("developer",), [self.emit("ended", outcome="desk-check")]),
            (
                ("flight", "big"),
                [self.emit("desk-check", slug="other"), self.emit("desk-check", slug="big")],
            ),
        ]
        self.supervisor()
        for until, steps in cases:
            with self.subTest(until=until):
                self.later(*steps)
                self.assertEqual(self.watch(*until), 0)

    def test_a_supervisor_that_ends_first_fails_the_watch(self) -> None:
        self.supervisor()
        self.later(self.emit("landed", slug="x"), self.emit("ended", outcome="empty"))
        self.assertEqual(self.watch("flight", "big"), 1)
        self.assertEqual(len(self.out), 3)

    def test_a_killed_supervisor_fails_the_watch(self) -> None:
        proc = self.supervisor("groom.lock")
        self.later(proc.kill)
        self.assertEqual(self.watch("landed"), 1)

    def test_no_supervisor_fails_the_watch_at_once(self) -> None:
        self.assertEqual(self.watch("landed"), 2)
        gone = subprocess.Popen(["true"])
        gone.wait()
        other = subprocess.Popen(["sleep", "60"])
        self.addCleanup(other.wait)
        self.addCleanup(other.kill)
        for pid in (gone.pid, other.pid, os.getpid()):
            with self.subTest(pid=pid):
                (self.repo / ".pair" / "run.lock").write_text(f"{pid}\n")
                self.assertEqual(self.watch("landed"), 2)

    def test_events_from_before_the_watch_are_not_read(self) -> None:
        self.supervisor()
        append_event(self.repo, "pair", "landed", "x")
        self.later(self.emit("ended", outcome="empty"))
        self.assertEqual(self.watch("landed"), 1)

    def test_a_line_written_in_two_pieces_is_read_once_whole(self) -> None:
        self.supervisor()
        line = json.dumps({"at": "t", "kind": "landed", "loop": "pair", "slug": "x"})
        log = event_log(self.repo)

        def piece(text: str) -> Callable[[], None]:
            def write_it() -> None:
                with log.open("a") as f:
                    f.write(text)

            return write_it

        self.later(piece(line[:20]), piece(line[20:] + "\n"))
        self.assertEqual(self.watch("landed"), 0)
        self.assertEqual(self.out, ["t pair landed x"])


class StatusTest(unittest.TestCase):
    """`just pair-status`: what waits on the developer, what runs next, and the counts."""

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)

    def waiting(self) -> str:
        """The `waits on you` block of the screen, or "" when it is absent."""
        shown = status(self.b.repo)
        if not shown.startswith("waits on you:"):
            return ""
        return shown.split("\n\n", 1)[0]

    def test_nothing_waits_on_an_empty_board(self) -> None:
        shown = status(self.b.repo)
        self.assertNotIn("waits on you", shown)
        self.assertIn("nothing underway", shown)
        self.assertIn("next: nothing in backlog/", shown)
        self.assertIn("desk-check     0", shown)

    def test_a_send_back_waits_with_its_first_line(self) -> None:
        self.b.issue("backlog", "c", "C\n\n# Needs elaboration\n\nWhich C?\n\nMore.")
        self.assertIn("c", self.waiting())
        self.assertIn("needs elaboration: Which C?", self.waiting())
        self.assertNotIn("More.", self.waiting())
        self.assertRegex(status(self.b.repo), r"\n  c +waits on elaboration\n")

    def test_a_flight_at_its_desk_check_waits_with_its_latest_brief(self) -> None:
        b = self.b
        b.issue("done", "part", "Part", parent="big")
        b.issue("desk-check", "big", "Big\n\n## Desk-check brief\n\n**First round.** Done.")
        self.assertIn("desk check: First round. Done.", self.waiting())
        self.assertIn("just pair-accept big, or just pair-resume big", self.waiting())
        b.issue(
            "desk-check",
            "big",
            "Big\n\n## Desk-check brief\n\nFirst round.\n\n"
            "## Desk-check notes\n\n- fix\n\n## Desk-check brief\n\nSecond round.",
        )
        self.assertIn("desk check: Second round.", self.waiting())
        self.assertNotIn("First round.", self.waiting())

    def test_an_issue_at_its_desk_check_waits_once(self) -> None:
        b = self.b
        b.issue("underway", "x", "X", difficulty="developer")
        b.loop.save(
            State(
                slug="x",
                stage="desk-check",
                paused="ready for your desk check",
                retry="desk-check",
            )
        )
        waiting = self.waiting()
        self.assertIn("desk check in worktrees/pair", waiting)
        self.assertIn("just pair-accept, or just pair-resume", waiting)
        self.assertNotIn("paused", status(b.repo))

    def test_a_paused_loop_and_pass_wait_with_their_reasons(self) -> None:
        b = self.b
        b.loop.save(
            State(slug="x", stage="todo", paused="the primary seat failed twice", retry="merge")
        )
        b.groomer.save(
            State(slug="grooming", stage="grooming", paused="past its round cap", retry="merge")
        )
        shown = status(b.repo)
        waiting = self.waiting()
        self.assertIn("x", waiting)
        self.assertIn("paused: the primary seat failed twice", waiting)
        self.assertIn("grooming pass", waiting)
        self.assertIn("paused: past its round cap", waiting)
        self.assertEqual(shown.count("failed twice"), 1)
        self.assertEqual(shown.count("round cap"), 1)

    def test_take_over_lines_follow_the_counts(self) -> None:
        b = self.b
        b.issue("underway", "x", "X", difficulty="easy")
        b.loop.save(
            State(slug="x", stage="todo", turn=2, approvals=["primary"], sessions={"primary": "s1"})
        )
        shown = status(b.repo)
        self.assertIn("underway: x in todo/, turn 2, next primary, accepted by primary\n", shown)
        self.assertLess(shown.index("done           0"), shown.index("session s1"))
        self.assertIn("cd worktrees/pair && claude --resume s1", shown)

    def test_the_running_order_shows_ripeness_and_flights(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A", difficulty="easy", waits_on="[z]")
        b.issue("backlog", "b", "B", difficulty="easy")
        b.issue("backlog", "big", "Big", difficulty="hard")
        b.issue("done", "p1", "P1", parent="big")
        b.issue("backlog", "p3", "P3", difficulty="easy", parent="big", waits_on="[p2]")
        b.issue("backlog", "p2", "P2", difficulty="easy", parent="big")
        b.issue("backlog", "q", "Q")
        b.issue("backlog", "t", "T")
        (b.repo / board.ORDER).write_text("# groomed below\na\nb\nbig\n")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "order")
        b.groomer.save(State(slug="grooming", stage="grooming", targets=["t"]))
        shown = status(b.repo)
        self.assertRegex(shown, r"\n  a +waits on z\n")
        self.assertRegex(shown, r"\n  b +ripe\n")
        self.assertRegex(
            shown,
            r"\n  big \(Flight\)\n"
            r"    p1 +done\n"
            r"    p2 +ripe\n"
            r"    p3 +waits on p2\n"
            r"    big check +waits on part p2, part p3\n",
        )
        self.assertRegex(shown, r"\n  t +being groomed\n")
        self.assertIn("to groom: q, t  (just groom)", shown)
        self.assertNotIn("waits on you", shown)

    def test_json_holds_what_the_screen_shows(self) -> None:
        b = self.b
        b.issue("backlog", "c", "C\n\n# Needs elaboration\n\nWhich C?")
        b.issue("underway", "x", "X", difficulty="easy")
        b.issue("backlog", "big", "Big", difficulty="hard")
        b.issue("done", "p1", "P1", parent="big")
        b.issue("backlog", "p3", "P3", difficulty="easy", parent="big", waits_on="[p2]")
        b.issue("backlog", "p2", "P2", difficulty="easy", parent="big")
        (b.repo / board.ORDER).write_text("# groomed below\nbig\n")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "order")
        b.loop.save(State(slug="x", stage="todo", turn=2, sessions={"primary": "s1"}))
        shown = json.loads(status_json(b.repo))
        self.assertEqual(shown, status_view(b.repo))
        self.assertEqual(
            shown["waiting"],
            [{"slug": "c", "why": "needs elaboration: Which C?", "answer": []}],
        )
        self.assertEqual(
            [(st["slug"], st["stage"], st["turn"]) for st in shown["underway"]],
            [("x", "todo", 2)],
        )
        big = next(node for node in shown["order"] if node["slug"] == "big")
        self.assertTrue(big["flight"])
        self.assertEqual(big["out"], [{"slug": "p1", "stage": "done"}])
        self.assertEqual(
            [(part["slug"], part["mark"]) for part in big["parts"]],
            [("p2", "ripe"), ("p3", "waits on p2")],
        )
        self.assertEqual(shown["sessions"], [{"kind": "pair", "role": "primary", "id": "s1"}])
        script = Path(__file__).resolve().parent / "pair.py"
        printed = subprocess.run(
            [sys.executable, str(script), "status", "--json"],
            cwd=b.repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        self.assertEqual(json.loads(printed), shown)


class BoardTest(unittest.TestCase):
    def test_section_reads_headings_and_bold_leads(self) -> None:
        body = "# T\n\n**The plan.** \nDo it.\n\n**Other.**\nno\n"
        self.assertEqual(board.section(body, "The plan"), "Do it.")
        self.assertEqual(
            board.section("## The plan\n\nStep 1\n## Next\n", "the plan"), "Step 1"
        )
        self.assertIsNone(board.section("# T\n", "The plan"))
        nested = "## The plan\n\n### Steps\n\n1. Do it.\n\n## Risks\n\nnone\n"
        self.assertEqual(board.section(nested, "The plan"), "### Steps\n\n1. Do it.")
        self.assertTrue(board.needs_elaboration("x\n# Needs elaboration\n\nwhy\n"))

    def test_waits_on_holds_an_item_back(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A", waits_on="[z]")
        b.issue("backlog", "b", "B")
        self.assertEqual(board.next_ripe(b.repo, "main"), "b")
        b.issue("done", "z", "Z")
        self.assertEqual(board.next_ripe(b.repo, "main"), "a")

    def test_order_runs_the_backlog(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        for slug in ("a", "b", "c", "d"):
            b.issue("backlog", slug, slug.upper())

        def order(text: str) -> None:
            (b.repo / board.ORDER).write_text(text)
            sh(b.repo, "add", "-A")
            sh(b.repo, "commit", "-q", "-m", "order")

        self.assertEqual(board.next_ripe(b.repo, "main"), "a")
        order("# a comment\n\nmissing\nc\n# groomed below\nb\n")
        self.assertEqual(board.next_ripe(b.repo, "main"), "c")
        self.assertEqual(
            board.next_ripe(b.repo, "main", skip=frozenset({"c"})), "b"
        )
        self.assertEqual(
            board.next_ripe(b.repo, "main", skip=frozenset({"c", "b"})), "a"
        )
        order("# groomed below\nd\nc\n")
        self.assertEqual(board.next_ripe(b.repo, "main"), "d")
        b.issue("backlog", "d", "D", waits_on="[z]")
        self.assertEqual(board.next_ripe(b.repo, "main"), "c")
        b.issue("backlog", "c", "C\n\n# Needs elaboration\n\nWhich C?")
        self.assertEqual(board.next_ripe(b.repo, "main"), "a")

    def test_merge_order_inserts_placements_after_their_anchor(self) -> None:
        base = "# groomed below\nb\nc\n"
        theirs = "# groomed below\nb\nn\nc\nm\n"
        ours = "# groomed below\nc\nd\n"
        self.assertEqual(
            board.merge_order(ours, base, theirs, {"c", "d", "n", "m"}),
            "# groomed below\nn\nc\nm\nd\n",
        )

    def test_merge_order_keeps_mains_lines_above_the_marker(self) -> None:
        base = "# groomed below\nf\na\n"
        theirs = "# groomed below\nf\na\nn\n"
        ours = "f\n# mine\n# groomed below\na\n"
        self.assertEqual(
            board.merge_order(ours, base, theirs, {"f", "a", "n"}),
            "f\n# mine\n# groomed below\na\nn\n",
        )

    def test_merge_order_drops_what_may_not_have_a_line(self) -> None:
        base = "# groomed below\nbig\na\n"
        theirs = "# groomed below\nbig\na\npart\n"
        ours = "# groomed below\nbig\ngone\na\n"
        self.assertEqual(
            board.merge_order(ours, base, theirs, {"big", "a"}),
            "# groomed below\nbig\na\n",
        )

    def test_merge_order_with_rerank_takes_the_branchs_ranking(self) -> None:
        base = "# groomed below\na\nb\n"
        theirs = "# groomed below\nb\na\n"
        ours = "# groomed below\na\nb\nc\n"
        self.assertEqual(
            board.merge_order(ours, base, theirs, {"a", "b", "c"}, rerank=True),
            "# groomed below\nb\na\nc\n",
        )

    def test_order_keeps_names_top_level_backlog_and_underway(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "big", "Big", difficulty="hard")
        b.issue("backlog", "part", "Part", difficulty="easy", parent="big")
        b.issue("backlog", "solo", "Solo")
        b.issue("underway", "busy", "Busy")
        b.issue("done", "old", "Old")
        self.assertEqual(board.order_keeps(b.repo), {"big", "solo", "busy"})

    def test_grooming_faults_name_each_rule(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A", difficulty="easy")
        b.issue("backlog", "big", "Big", difficulty="hard")
        b.issue("backlog", "loose", "Loose")
        base = sh(b.repo, "rev-parse", "HEAD")
        targets = ("big", "loose")

        def faults() -> str:
            return "\n".join(
                board.grooming_faults(b.repo, b.repo, base, targets, False)
            )

        self.assertIn("needs the line `# groomed below`", faults())
        (b.repo / board.ORDER).write_text("# groomed below\na\na\nmissing\n")
        found = faults()
        self.assertIn("issues/backlog/loose.md needs `difficulty:`", found)
        self.assertIn("issues/backlog/big.md is hard, so split it", found)
        self.assertIn("rank big, loose below", found)
        self.assertIn("its Flight's line: a, missing.", found)
        (b.repo / "issues/backlog/loose.md").unlink()
        (b.repo / "issues/roadmap/r.md").write_text("# R\n")
        (b.repo / "x.txt").write_text("x\n")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "stray")
        found = faults()
        self.assertIn("issues/backlog/loose.md is gone", found)
        self.assertIn("issues/roadmap/r.md changed", found)
        self.assertIn("x.txt changed", found)
        sh(b.repo, "reset", "-q", "--hard", base)
        for slug in ("big", "loose"):
            (b.repo / f"issues/backlog/{slug}.md").write_text(
                "---\ndifficulty: easy\n---\n# X\n"
            )
        (b.repo / board.ORDER).write_text(
            "# groomed below\n# a note\nloose\nbig\n\na\n"
        )
        self.assertEqual(faults(), "")
        (b.repo / "issues/backlog/a.md").write_text("# A\n")
        self.assertEqual(faults(), "")

    def test_a_flight_waits_until_every_child_is_done(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "big", "Big", difficulty="hard")
        self.assertEqual(board.next_ripe(b.repo, "main"), "big")
        for stage in ("backlog", "underway", "todo", "desk-check"):
            b.issue(stage, "part", "Part", parent="big", waits_on="[z]")
            self.assertIsNone(board.next_ripe(b.repo, "main"), stage)
            sh(b.repo, "rm", "-q", f"issues/{stage}/part.md")
        b.issue("done", "part", "Part", parent="big")
        self.assertEqual(board.children(b.repo, "main", "big"), {"part": "done"})
        self.assertFalse(board.waiting(b.repo, "main", "big"))
        self.assertEqual(board.next_ripe(b.repo, "main"), "big")
        b.issue("roadmap", "someday", "Someday", parent="big")
        self.assertEqual(board.children(b.repo, "main", "big"), {"part": "done"})

    def test_a_ripe_flight_goes_first(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A")
        b.issue("backlog", "big", "Big")
        b.issue("done", "part", "Part", parent="big")
        (b.repo / board.ORDER).write_text("a\nbig\n")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "order")
        self.assertEqual(board.next_ripe(b.repo, "main"), "big")
        self.assertEqual(board.next_ripe(b.repo, "main", skip=frozenset({"big"})), "a")
        b.issue("backlog", "big", "Big\n\n# Needs elaboration\n\nWhich big?")
        self.assertEqual(board.next_ripe(b.repo, "main"), "a")
        b.issue("backlog", "big", "Big", waits_on="[z]")
        self.assertEqual(board.next_ripe(b.repo, "main"), "a")
        b.issue("backlog", "big", "Big")
        b.issue("backlog", "late", "Late", parent="big")
        self.assertEqual(board.next_ripe(b.repo, "main"), "a")
        sh(b.repo, "rm", "-q", "issues/backlog/late.md")
        sh(b.repo, "commit", "-q", "-m", "late gone")
        b.issue("backlog", "zed", "Zed")
        b.issue("done", "zed-part", "Zed part", parent="zed")
        self.assertEqual(board.next_ripe(b.repo, "main"), "big")
        (b.repo / board.ORDER).write_text("a\nzed\nbig\n")
        sh(b.repo, "commit", "-q", "-am", "reorder")
        self.assertEqual(board.next_ripe(b.repo, "main"), "zed")

    def test_descendants_and_within_keep_to_one_flight(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "loose", "Loose")
        b.issue("backlog", "big", "Big")
        b.issue("done", "mid", "Mid", parent="big")
        b.issue("backlog", "leaf", "Leaf", parent="mid")
        self.assertEqual(board.descendants(b.repo, "main", "big"), {"mid", "leaf"})
        self.assertEqual(board.descendants(b.repo, "main", "loose"), set())
        self.assertEqual(board.next_ripe(b.repo, "main"), "big")
        self.assertEqual(
            board.next_ripe(b.repo, "main", within=frozenset({"leaf", "loose"})),
            "leaf",
        )
        self.assertIsNone(board.next_ripe(b.repo, "main", within=frozenset({"mid"})))

    def order_is(self, b: Bench, text: str) -> None:
        (b.repo / board.ORDER).write_text(text)
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "order")

    def land(self, b: Bench, slug: str) -> None:
        sh(b.repo, "mv", f"issues/backlog/{slug}.md", f"issues/done/{slug}.md")
        sh(b.repo, "commit", "-q", "-m", f"land {slug}")

    def test_a_flight_runs_its_parts_at_its_line(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A")
        b.issue("backlog", "big", "Big")
        b.issue("backlog", "a-second", "Second", parent="big", waits_on="[b-first]")
        b.issue("backlog", "b-first", "First", parent="big")
        self.order_is(b, "big\na\n")
        self.assertEqual(
            board.running_order(b.repo, "main"), ["b-first", "a-second", "big", "a"]
        )
        self.assertEqual(board.next_ripe(b.repo, "main"), "b-first")
        self.land(b, "b-first")
        self.assertEqual(board.next_ripe(b.repo, "main"), "a-second")
        self.land(b, "a-second")
        self.assertEqual(board.next_ripe(b.repo, "main"), "big")
        self.land(b, "big")
        self.assertEqual(board.next_ripe(b.repo, "main"), "a")

    def test_a_waits_on_cycle_among_parts_falls_back_to_filename_order(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "big", "Big")
        b.issue("backlog", "p", "P", parent="big", waits_on="[q]")
        b.issue("backlog", "q", "Q", parent="big", waits_on="[p]")
        self.assertEqual(board.running_order(b.repo, "main"), ["p", "q", "big"])

    def test_a_flight_whose_parts_wait_outside_it_is_passed_over(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A")
        b.issue("backlog", "big", "Big")
        b.issue("backlog", "part", "Part", parent="big", waits_on="[z]")
        self.order_is(b, "big\na\n")
        self.assertEqual(board.next_ripe(b.repo, "main"), "a")

    def test_a_nested_flight_runs_at_the_outer_flights_line(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A")
        b.issue("backlog", "big", "Big")
        b.issue("backlog", "mid", "Mid", parent="big")
        b.issue("backlog", "leaf", "Leaf", parent="mid")
        b.issue("backlog", "side", "Side", parent="big")
        self.order_is(b, "big\na\n")
        self.assertEqual(
            board.running_order(b.repo, "main"), ["leaf", "mid", "side", "big", "a"]
        )
        self.assertEqual(board.next_ripe(b.repo, "main"), "leaf")

    def test_a_part_of_a_landed_flight_runs_from_its_own_line(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A")
        b.issue("done", "old", "Old")
        b.issue("backlog", "left", "Left", parent="old")
        self.order_is(b, "left\na\n")
        self.assertEqual(board.running_order(b.repo, "main"), ["left", "a"])
        self.assertEqual(board.next_ripe(b.repo, "main"), "left")
        self.assertEqual(board.unnamed(b.repo, "main"), [])

    def test_an_unlisted_flight_runs_at_its_filename(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        for slug in ("a", "b", "zed"):
            b.issue("backlog", slug, slug.upper())
        b.issue("backlog", "zed-part", "Zed part", parent="zed")
        self.order_is(b, "b\n")
        self.assertEqual(
            board.running_order(b.repo, "main"), ["b", "a", "zed-part", "zed"]
        )
        self.assertEqual(board.unnamed(b.repo, "main"), ["a", "zed"])

    def test_grooming_faults_refuse_a_line_for_a_part(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A", difficulty="easy")
        b.issue("backlog", "big", "Big", difficulty="hard")
        b.issue("backlog", "part", "Part", difficulty="easy", parent="big")
        self.order_is(b, "part\n# groomed below\nbig\na\n")
        base = sh(b.repo, "rev-parse", "HEAD")

        def faults() -> str:
            return "\n".join(board.grooming_faults(b.repo, b.repo, base, (), False))

        self.assertIn("delete the line for part", faults())
        (b.repo / board.ORDER).write_text("# groomed below\nbig\npart\na\n")
        self.assertIn("its Flight's line: part.", faults())
        (b.repo / board.ORDER).write_text("# groomed below\nbig\na\n")
        self.assertEqual(faults(), "")

    def test_grooming_faults_let_the_issue_underway_keep_its_line(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A", difficulty="easy")
        b.issue("backlog", "big", "Big", difficulty="hard")
        b.issue("underway", "u", "U", difficulty="easy")
        b.issue("underway", "part", "Part", difficulty="easy", parent="big")
        self.order_is(b, "u\n# groomed below\nbig\nu\na\n")
        base = sh(b.repo, "rev-parse", "HEAD")

        def faults() -> str:
            return "\n".join(board.grooming_faults(b.repo, b.repo, base, (), False))

        self.assertEqual(faults(), "")
        (b.repo / board.ORDER).write_text("u\n# groomed below\nbig\na\n")
        self.assertEqual(faults(), "")
        (b.repo / board.ORDER).write_text("u\n# groomed below\nbig\npart\na\n")
        self.assertIn("its Flight's line: part.", faults())

    def test_grooming_faults_read_the_parts_a_pass_just_wrote(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A", difficulty="easy")
        b.issue("backlog", "big", "Big")
        self.order_is(b, "# groomed below\na\n")
        base = sh(b.repo, "rev-parse", "HEAD")
        (b.repo / "issues/backlog/big.md").write_text("---\ndifficulty: hard\n---\n# Big\n")
        (b.repo / "issues/backlog/big-1.md").write_text(
            "---\ndifficulty: easy\nparent: big\n---\n# One\n"
        )
        (b.repo / board.ORDER).write_text("# groomed below\nbig\na\n")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "pass")
        self.assertEqual(board.grooming_faults(b.repo, b.repo, base, ("big",), False), [])

    def test_sections_counts_each_heading_of_a_name(self) -> None:
        body = "# F\n\n## Desk-check brief\n\none\n\n## Desk-check brief\n\ntwo\n"
        self.assertEqual(board.sections(body, "Desk-check brief"), 2)
        self.assertEqual(board.sections("# F\n", "Desk-check brief"), 0)

    def test_grooming_faults_count_children_in_any_stage(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "big", "Big", difficulty="hard")
        b.issue("done", "part", "Part", difficulty="easy", parent="big")
        (b.repo / board.ORDER).write_text("# groomed below\nbig\n")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "order")
        base = sh(b.repo, "rev-parse", "HEAD")
        self.assertEqual(board.grooming_faults(b.repo, b.repo, base, ("big",), False), [])

    def test_last_of_and_last_section_read_the_latest_round(self) -> None:
        body = "# F\n\n## Desk-check brief\n\none\n\n## Desk-check notes\n\n- a\n"
        names = ("Desk-check brief", "Desk-check notes")
        self.assertEqual(board.last_of(body, names), "Desk-check notes")
        self.assertIsNone(board.last_of("# F\n", names))
        later = body + "\n## Desk-check notes\n\n- `b`\n  more\n- c\n"
        self.assertEqual(
            board.bullets(board.last_section(later, "Desk-check notes")), ["b", "c"]
        )
        self.assertEqual(board.last_section(body, "Desk-check children"), "")

    def test_without_drops_only_the_slug(self) -> None:
        text = "a\n# a\n# groomed below\nab\na\n"
        self.assertEqual(board.without(text, "a"), "# a\n# groomed below\nab\n")
        self.assertEqual(board.without("b\n", "a"), "b\n")


class SeatCommandTest(unittest.TestCase):
    def test_a_seat_loads_the_project_settings_alone(self) -> None:
        argv = command("seat prompt", model="sonnet", resume="abc")
        at = argv.index("--setting-sources")
        self.assertEqual(argv[at + 1], "project")
        self.assertIn("--strict-mcp-config", argv)
        self.assertNotIn("--disable-slash-commands", argv)
        self.assertEqual(argv[argv.index("--append-system-prompt") + 1], "seat prompt")
        self.assertEqual(argv[-4:], ["--model", "sonnet", "--resume", "abc"])
        allowed = argv.index("--allowedTools") + 1
        self.assertEqual(argv[allowed : allowed + len(ALLOWED)], ALLOWED)


if __name__ == "__main__":
    unittest.main()
