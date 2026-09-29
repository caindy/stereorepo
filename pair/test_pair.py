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
from loop import Loop, State
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

        self.loop = TestLoop(
            self.repo,
            factory,
            gate,
            self.notes.append,
            prompts=PROMPTS,
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

    def test_needs_elaboration_sends_the_issue_to_roadmap_and_drops_the_code(
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
        self.assertTrue(b.on_main("issues/roadmap/vague.md"))
        self.assertFalse(b.on_main("issues/backlog/vague.md"))
        self.assertFalse(b.on_main("b.txt"))
        self.assertIn(
            "Which widget?", sh(b.repo, "show", "main:issues/roadmap/vague.md")
        )

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
            sh(b.repo, "show", "main:issues/roadmap/churn.md"),
        )

    def test_a_round_cap_override_applies_to_every_difficulty(self) -> None:
        b = self.b
        b.issue("backlog", "short", "Short", difficulty="medium")
        b.loop.round_cap = 1
        b.script(("primary", write("c.txt", "1")), ("secondary", write("c.txt", "2")))
        self.assertEqual(b.loop.run(once=True), "kicked")
        self.assertIn(
            "within 2 turns", sh(b.repo, "show", "main:issues/roadmap/short.md")
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
        self.assertTrue(b.on_main("issues/done/big.md"))
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
