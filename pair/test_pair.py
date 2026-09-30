"""Tests for the pair loop: every turn and stopping rule, over a real git repository.

Run: uv run --with pyyaml python -m unittest discover -s tools/pair -p 'test_*.py'
"""

from __future__ import annotations

import collections
import subprocess
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

import board
from loop import Loop, State, status
from seats import ALLOWED, TurnResult, command

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

    def __init__(self, role: str, cwd: Path, resume: str | None, bench: Bench) -> None:
        self.role, self.cwd, self.bench = role, cwd, bench
        self.session_id = resume or f"{role}-session"
        bench.loop.dir.mkdir(exist_ok=True)
        (bench.loop.dir / f"{role}.session").write_text(f"{self.session_id}\n")

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
            self.bench.loop.stop_requested = True
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
        bench = self

        class TestLoop(Loop):
            def absorb_developer(self, st):  # type: ignore[no-untyped-def]
                edit = bench.developer_between.pop(len(bench.sent), None)
                if edit:
                    edit(self.wt)
                return super().absorb_developer(st)

        def factory(role: str, cwd: Path, resume: str | None) -> FakeSeat:
            self.opened.append((role, resume))
            return FakeSeat(role, cwd, resume, self)

        def gate(_tree: Path) -> tuple[bool, str]:
            self.gate_runs += 1
            ok = self.gates.pop(0) if self.gates else True
            return ok, "" if ok else "FAILED: test_widget"

        def deliver(_tree: Path) -> tuple[bool, str] | None:
            """A repository with no `deliver` recipe, unless a test queues results."""
            self.deliver_runs += 1
            return self.delivers.pop(0) if self.delivers else None

        self.loop = TestLoop(
            self.repo,
            factory,
            gate,
            self.notes.append,
            prompts=PROMPTS,
            deliver=deliver,
            say=lambda _m: None,
        )

    def state(self) -> State:
        """The loop's saved state, which a test expects to exist."""
        st = self.loop.load()
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
        self.assertEqual((b.repo / "a.txt").read_text(), "fixed\n")
        log = sh(b.repo, "log", "--format=%s", "main")
        self.assertEqual(log.splitlines()[0], "Fix the typo")
        self.assertEqual(len(log.splitlines()), 3)
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
            (cwd / "issues/backlog/gone.md").unlink()

        b.script(("primary", delete))
        self.assertEqual(b.loop.run(once=True), "kicked")
        text = sh(b.repo, "show", "main:issues/backlog/gone.md")
        self.assertTrue(board.needs_elaboration(text))
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
            (cwd / "issues/backlog/x.md").rename(cwd / "issues/todo/x.md")

        b.stop_when_empty = True
        b.script(("primary", move))
        b.loop.run()
        self.assertEqual(board.locations(b.loop.wt, "x"), ["backlog"])
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
        self.assertEqual(b.loop.run(), "paused")
        self.assertEqual(b.loop.run(), "desk-check")
        self.assertFalse(b.on_main("a.txt"))
        said: list[str] = []
        b.loop.say = said.append
        self.assertEqual(b.loop.groom(), "busy")
        self.assertIn("`just pair-accept` or `just pair-resume`", said[-1])
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
        self.assertFalse(b.on_main("issues/done/big.md"))
        self.assertEqual(sh(b.repo, "show", f"main:{board.ORDER}"), "big")
        self.assertEqual(board.next_ripe(b.repo, "main"), "big-1-parse")

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
        self.assertIn("Check the Flight issues/backlog/big.md", first)
        self.assertTrue(b.on_main("issues/desk-check/big.md"))
        self.assertFalse(b.on_main("issues/backlog/big.md"))
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
        self.assertEqual(sh(b.repo, "rev-parse", "main"), before)
        self.assertTrue(b.on_main("issues/backlog/big.md"))
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
        self.assertTrue(b.on_main("issues/backlog/big-gap.md"))
        self.assertEqual(
            sh(b.repo, "show", f"main:{board.ORDER}"), "big\n# groomed below"
        )
        self.assertEqual(board.next_ripe(b.repo, "main"), "big-gap")
        self.assertEqual(b.deliver_runs, 0)

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

    def test_a_seat_that_moves_the_flight_file_is_put_back_in_backlog(self) -> None:
        b = self.b

        def to_todo(cwd: Path) -> None:
            sh(cwd, "mv", "issues/backlog/big.md", "issues/todo/big.md")

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
        b.issue("backlog", "other", "Other", difficulty="easy")
        (b.repo / board.ORDER).write_text("other\nbig-b\nbig-a\nbig\n")
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
        self.assertTrue(b.on_main("issues/backlog/other.md"))
        self.assertTrue(all("other" not in text for _, text in b.sent))

    def test_a_run_refuses_what_it_cannot_work(self) -> None:
        b = self.b
        head = sh(b.repo, "rev-parse", "HEAD")
        self.assertEqual(b.loop.run(flight="nothing"), "refused")
        self.assertEqual(b.loop.run(flight="other"), "refused")
        b.loop.save(State(slug="other", stage="todo"))
        self.assertEqual(b.loop.run(flight="big"), "refused")
        says: list[str] = []
        b.loop.say = says.append
        b.loop.save(State(slug="other", stage="desk-check", retry="desk-check"))
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
        self.assertTrue(b.sent[0][1].startswith("Groom issues/backlog/a.md."))
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
        self.assertEqual(b.loop.groom(), "groomed")
        prompt = b.sent[0][1]
        self.assertIn("- issues/backlog/a.md", prompt)
        self.assertNotIn("backlog/b.md", prompt)
        self.assertNotIn("backlog/c.md", prompt)
        self.assertIn("only insert", prompt)
        self.assertEqual(
            sh(b.repo, "log", "-1", "--format=%s", "main"), "Groom the backlog"
        )
        self.assertFalse((b.loop.dir / "groomed.json").exists())
        self.assertIsNone(b.loop.load())
        self.assertEqual(b.loop.groom(), "nothing")
        self.assertEqual(len(b.sent), 2)

    def test_nothing_to_groom_sends_no_turn(self) -> None:
        b = self.b
        self.assertEqual(b.loop.groom(), "nothing")
        b.issue("backlog", "a", "A", **WAITING)
        self.commit_order("# groomed below\na\n")
        self.assertEqual(b.loop.groom(), "nothing")
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
        self.assertEqual(b.loop.groom(), "stopped")
        self.assertIn("b, a moved", b.state().note)
        self.assertIn("ran in this order:\na\nb", b.state().note)
        b.stop_when_empty = False
        b.loop.stop_requested = False
        b.script(("primary", order("# groomed below\na\nc\nb\n")), ("secondary", quiet))
        self.assertEqual(b.loop.groom(), "groomed")
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
        self.assertEqual(b.loop.groom(), "groomed")
        self.assertEqual(self.main_order(), "# groomed below\nb\nc\na")

    def test_rerank_ranks_the_whole_order_with_nothing_to_groom(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A", **WAITING)
        b.issue("backlog", "b", "B", **WAITING)
        self.commit_order("# groomed below\na\nb\n")
        b.script(("primary", order("# groomed below\nb\na\n")), ("secondary", quiet))
        self.assertEqual(b.loop.groom(rerank=True), "groomed")
        self.assertIn("(none: this pass only ranks)", b.sent[0][1])
        self.assertIn("judged across the whole backlog", b.sent[0][1])
        self.assertEqual(self.main_order(), "# groomed below\nb\na")

    def test_a_pass_and_an_issue_never_share_the_worktree(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A", **WAITING)
        b.issue("backlog", "x", "X")
        b.stop_when_empty = True
        b.script(("primary", order("# groomed below\na\n")))
        self.assertEqual(b.loop.groom(), "stopped")
        self.assertIn("underway: grooming pass, turn 1", status(b.repo))
        self.assertEqual(b.loop.run(), "grooming")
        b.stop_when_empty = False
        b.loop.stop_requested = False
        b.script(
            (
                "secondary",
                both(front("x", difficulty="easy"), order("# groomed below\na\nx\n")),
            ),
            ("primary", quiet),
        )
        self.assertEqual(b.loop.groom(rerank=True), "groomed")
        self.assertIn("nothing underway", status(b.repo))
        self.assertEqual(self.main_order(), "# groomed below\na\nx")
        b.stop_when_empty = True
        b.script(("primary", quiet))
        self.assertEqual(b.loop.run(), "stopped")
        self.assertEqual(b.state().slug, "x")
        self.assertEqual(b.loop.groom(), "busy")

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
        self.assertEqual(b.loop.groom(), "stopped")
        st = b.state()
        self.assertEqual(st.stage, "grooming")
        self.assertIn("are the developer's; put them back as they were:\na", st.note)
        b.stop_when_empty = False
        b.loop.stop_requested = False
        b.script(
            ("primary", order("a\n# groomed below\nc\nb\n")),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.groom(), "groomed")
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
        self.assertEqual(b.loop.groom(), "stopped")
        self.assertIn("issues/backlog/b.md is gone", b.state().note)

    def test_a_pass_writes_order_and_its_marker_where_they_are_missing(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A", **WAITING)
        b.script(("primary", order("# groomed below\na\n")), ("secondary", quiet))
        self.assertEqual(b.loop.groom(), "groomed")
        self.assertEqual(self.main_order(), "# groomed below\na")
        b.issue("backlog", "b", "B", **WAITING)
        self.commit_order("b\n")
        b.script(("primary", order("b\n# groomed below\na\n")), ("secondary", quiet))
        self.assertEqual(b.loop.groom(), "groomed")
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
                    order("big\n# groomed below\nbig-1\na\n"),
                ),
            ),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.groom(), "groomed")
        self.assertTrue(b.on_main("issues/backlog/big.md"))
        self.assertFalse(b.on_main("issues/done/big.md"))
        self.assertEqual(self.main_order(), "big\n# groomed below\nbig-1\na")
        log = sh(b.repo, "log", "--format=%s", "main").splitlines()
        self.assertEqual(log[0], "Groom the backlog")

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
        self.assertEqual(b.loop.groom(), "groomed")
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
        self.assertEqual(b.loop.groom(), "groomed")
        self.assertTrue(b.on_main("issues/backlog/a.md"))
        self.assertIsNone(board.next_ripe(b.repo, "main"))
        self.assertEqual(b.loop.groom(), "nothing")

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
        b.loop.round_cap = 1
        b.script(("primary", order("# groomed below\na\n")), ("secondary", quiet))
        self.assertEqual(b.loop.groom(), "paused")
        st = b.state()
        self.assertEqual((st.stage, st.retry), ("grooming", "grooming"))
        b.script(("primary", front("a", difficulty="easy")), ("secondary", quiet))
        self.assertEqual(b.loop.groom(), "groomed")
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
        self.assertEqual(b.loop.groom(), "groomed")
        self.assertEqual(
            self.main_order(), "# mine\na\n# note\n# groomed below\nb"
        )
        self.assertIn("B, sharper", sh(b.repo, "show", "main:issues/backlog/b.md"))
        self.assertEqual(len(b.sent), 2)


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
        self.assertIn("nothing else: a, missing.", found)
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
        for stage in ("backlog", "todo", "desk-check"):
            b.issue(stage, "part", "Part", parent="big", waits_on="[z]")
            self.assertIsNone(board.next_ripe(b.repo, "main"), stage)
            sh(b.repo, "rm", "-q", f"issues/{stage}/part.md")
        b.issue("done", "part", "Part", parent="big")
        self.assertEqual(board.children(b.repo, "main", "big"), {"part": "done"})
        self.assertFalse(board.waiting(b.repo, "main", "big"))
        self.assertEqual(board.next_ripe(b.repo, "main"), "big")
        b.issue("roadmap", "someday", "Someday", parent="big")
        self.assertEqual(board.children(b.repo, "main", "big"), {"part": "done"})

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
