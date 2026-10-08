"""Tests for the pair loop: every turn and stopping rule, over a real git repository.

Run: uv run --with pyyaml --with ruff==0.14.0 python -m unittest discover -s pair -p 'test_*.py'
Run across worker processes: uv run --script pair/gate.py
"""

from __future__ import annotations

import ast
import collections
import contextlib
import dataclasses
import functools
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any
from unittest import mock

import board
import gate
import touched
from loop import (
    NOTE_STOPS,
    GateFailure,
    GateUnrunnable,
    Loop,
    State,
    append_event,
    event_log,
    gate_line,
    gate_record,
    gate_unrunnable,
    redact,
    status,
    status_json,
    status_view,
    unwritable_pages,
)
from seats import (
    ALLOWED,
    DISALLOWED,
    SEAT_GPG,
    ClaudeSeat,
    Confinement,
    TurnResult,
    command,
    confinement,
    env_names,
    env_values,
    is_refusal,
    unwritable,
    versioned_gpg_conf,
)
from watch import ENDED_FIRST, NOT_RUNNING, watch

PROMPTS = Path(__file__).resolve().parent / "prompts"
Action = Callable[[Path], None]


def sh(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


RENAMED = "".join(f"line {n}\n" for n in range(20))
"""Content enough for `git diff` to see a file the landing moves as renamed."""


def commit_on(repo: Path, parent: str, files: dict[str, str | None]) -> str:
    """A commit on `parent` with `files` written, built without touching `repo`'s index or tree.

    A path whose content is `None` is removed.
    """
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}

        def run(*args: str, stdin: str | None = None) -> str:
            return subprocess.run(
                ["git", *args], cwd=repo, env=env, input=stdin,
                capture_output=True, text=True, check=True,
            ).stdout.strip()

        run("read-tree", parent)
        for path, content in files.items():
            if content is None:
                run("update-index", "--force-remove", path)
                continue
            blob = run("hash-object", "-w", "--stdin", stdin=content)
            run("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}")
        return run("commit-tree", "-p", parent, "-m", "commit_on", run("write-tree"))


def inspects_processes() -> bool:
    """Whether `ps` runs here. A seat's sandbox refuses it (DR-302)."""
    try:
        subprocess.run(["ps", "-p", str(os.getpid())], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def skip_git_trampoline() -> None:
    """Put the git that macOS's `/usr/bin/git` resolves to first on `PATH`.

    `/usr/bin/git` hands every call to `xcrun`, which costs about 7 ms a
    process, and these tests and the loop under test start thousands of git
    processes. Child processes inherit `os.environ`, so the loop's own calls
    skip the trampoline too. A `PATH` whose git is not `/usr/bin/git`, such as
    Homebrew's or Linux's, is left as it is.
    """
    if shutil.which("git") != "/usr/bin/git" or not shutil.which("xcrun"):
        return
    found = subprocess.run(
        ["xcrun", "-f", "git"], capture_output=True, text=True, check=False
    )
    real = Path(found.stdout.strip())
    if found.returncode == 0 and real.is_file() and os.access(real, os.X_OK):
        os.environ["PATH"] = f"{real.parent}{os.pathsep}{os.environ.get('PATH', '')}"


skip_git_trampoline()

NO_PS = "`ps` cannot run in a seat's sandbox; the loop's own gate runs this test"
INSPECTS = inspects_processes()


def quiet(_cwd: Path) -> None:
    """A turn that changes nothing."""


CRASH = object()
REFUSED = object()
REFUSAL = (
    "API Error: Opus 5.5's safeguards flagged this message "
    "(https://www.anthropic.com/legal/aup). This sometimes happens with safe, "
    "normal conversations. Claude Code can't respond to this message with Opus 5.5.\n"
    "Details: `[reasoning_extraction]`"
)
"""The error text of a turn the model refused, as Claude Code reported it on 2026-10-01."""


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


@dataclasses.dataclass(frozen=True)
class Says:
    """A scripted turn that runs `action` and ends with the closing message `text`."""

    text: str
    action: Action = quiet


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
            raise AssertionError(f"unscripted turn for {self.role}:\n{text}")  # noqa: TRY003  # reason: a test failure carrying the prompt the script ran out on, which a class of its own would only rename
        role, action = self.bench.turns.popleft()
        if role != self.role:
            raise AssertionError(f"expected a {role} turn, got {self.role}")  # noqa: TRY003  # reason: a test failure naming the seat the script expected, read where the turns are scripted
        if action is CRASH:
            return TurnResult(False, error="boom", session_id=self.session_id)
        if action is REFUSED:
            return TurnResult(
                False,
                error=REFUSAL,
                session_id=self.session_id,
                refused=is_refusal(REFUSAL),
            )
        text = ""
        if isinstance(action, Says):
            text, action = action.text, action.action
        action(self.cwd)
        if self.bench.stop_when_empty and not self.bench.turns:
            self.loop.stop_requested = True
        return TurnResult(
            True,
            text=text,
            session_id=self.session_id,
            usage={"cache_read_input_tokens": 1},
        )

    def stop(self) -> None:
        pass


def project(name: str, path: str) -> str:
    return f"  - id: work:project/{name}\n    name: {path}\n"


def product(name: str, *projects: str) -> str:
    built = "".join(f"      - work:project/{p}\n" for p in projects)
    return f"  - id: work:product/{name}\n    built_from:\n{built}"


STRUCTURE = (
    "projects:\n"
    + project("meta", ".meta")
    + project("rust-seed", "bootstraps/rust/seed")
    + project("python-seed", "bootstraps/python/seed")
    + project("pair", "pair")
    + project("widgets", "widgets")
    + "products:\n"
    + product("scaffold", "meta", "pair")
    + product("rust-standard", "rust-seed")
    + product("python-standard", "python-seed")
    + product("widget-kit", "widgets")
)
"""A `structure.yaml` shaped like stereorepo's, with a fifth Project, `widgets`,
that stereorepo does not have: a Project asserted here is selected with no
change to the loop's code."""


TEMPLATES = tempfile.TemporaryDirectory()
"""Where `board_repository` builds its repository, once per process."""

os.environ["PAIRS_DIR"] = str(Path(TEMPLATES.name) / "pairs")
"""Where a loop under test publishes its status (`loop.publish`) until a `Bench`
points it at its own: never the developer's `~/.pairs`, from any test or any
`pair.py` a test runs, which inherits it."""


@functools.cache
def board_repository() -> Path:
    """A committed, empty board on `main`, which each `Bench` copies.

    Building it once and copying it saves every test the git processes that
    building it takes. It has no worktrees, so its `.git` names no absolute
    path and a copy of it is a whole repository.
    """
    repo = Path(TEMPLATES.name) / "board"
    repo.mkdir()
    sh(repo, "init", "-q", "-b", "main")
    for key, value in (
        ("user.name", "Test"),
        ("user.email", "t@example.com"),
        ("commit.gpgsign", "false"),
    ):
        sh(repo, "config", key, value)
    (repo / ".gitignore").write_text("worktrees/\n.pair/\n")
    for stage in board.STAGES:
        (repo / "issues" / stage).mkdir(parents=True)
        (repo / "issues" / stage / "README.md").write_text(f"{stage}\n")
    sh(repo, "add", "-A")
    sh(repo, "commit", "-q", "-m", "board")
    return repo


class Bench:
    """The developer's checkout with a board, and a loop wired to fake seats and a fake gate."""

    def __init__(self) -> None:  # noqa: C901  # reason: the fakes are closures over the bench, so the branches of each one count toward the method that builds them
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "developer"
        shutil.copytree(board_repository(), self.repo, symlinks=True)
        self.pairs = Path(self.tmp.name) / "pairs"
        """Where this `Bench`'s loop publishes.

        A worker process runs one test at a time, so it is the one in force
        until `close`.
        """
        self.pairs_before = os.environ["PAIRS_DIR"]
        os.environ["PAIRS_DIR"] = str(self.pairs)
        self.turns: collections.deque[tuple[str, object]] = collections.deque()
        self.sent: list[tuple[str, str]] = []
        self.opened: list[tuple[str, str | None]] = []
        self.models: list[tuple[str, str | None]] = []
        self.gates: list[bool | tuple[bool, str]] = []
        """Each gate's verdict in turn, alone or with its output; a gate past the end passes."""
        self.gate_runs = 0
        self.gate_targets: list[list[str] | None] = []
        self.gate_envs: list[dict[str, str]] = []
        """The declared keys each gate was started with."""
        self.delivers: list[tuple[bool, str]] = []
        self.deliver_runs = 0
        self.stop_when_empty = False
        self.developer_between: dict[int, Action] = {}
        self.notes: list[str] = []
        self.before_land: list[Action] = []
        self.during_gate: list[Action] = []
        self.lock_waits = 0
        self.while_waiting: Callable[[], None] | None = None
        bench = self

        class TestLoop(Loop):
            def absorb_developer(self, st, keep_approvals=False):  # type: ignore[no-untyped-def]
                edit = bench.developer_between.pop(len(bench.sent), None)
                if edit:
                    edit(self.wt)
                return super().absorb_developer(st, keep_approvals)

            def land(self, st, sha, retry="merge"):  # type: ignore[no-untyped-def]
                if bench.before_land:
                    bench.before_land.pop(0)(bench.repo)
                return super().land(st, sha, retry)

            def wait_for_lock(self) -> None:
                """The other process frees its locks, or does what `while_waiting` says instead."""
                bench.lock_waits += 1
                if bench.while_waiting is not None:
                    bench.while_waiting()
                    return
                (bench.repo / ".git" / "index.lock").unlink(missing_ok=True)
                (bench.repo / ".git" / "refs" / "heads" / "main.lock").unlink(
                    missing_ok=True
                )

        def factory(
            kind: str,
        ) -> Callable[[str, Path, str | None, str | None], FakeSeat]:
            def make(
                role: str, cwd: Path, resume: str | None, model: str | None
            ) -> FakeSeat:
                self.opened.append((role, resume))
                self.models.append((role, model))
                loop = self.groomer if kind == "groom" else self.loop
                return FakeSeat(role, cwd, resume, self, loop)

            return make

        def gate(
            _tree: Path, targets: Sequence[str] | None, env: Mapping[str, str]
        ) -> tuple[bool, str]:
            self.gate_runs += 1
            self.gate_targets.append(None if targets is None else list(targets))
            self.gate_envs.append(dict(env))
            if self.during_gate:
                self.during_gate.pop(0)(self.repo)
            ok = self.gates.pop(0) if self.gates else True
            if isinstance(ok, tuple):
                return ok
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

    def structure(self, text: str = STRUCTURE) -> None:
        """Commit `text` to `main` as the repository's `structure.yaml`."""
        path = self.repo / touched.STRUCTURE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        sh(self.repo, "add", "-A")
        sh(self.repo, "commit", "-q", "-m", "structure")

    def script(self, *turns: tuple[str, object]) -> None:
        self.turns.extend(turns)

    def on_main(self, rel: str) -> bool:
        return (
            subprocess.run(
                ["git", "cat-file", "-e", f"main:{rel}"],
                check=False,
                cwd=self.repo,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )

    def close(self) -> None:
        os.environ["PAIRS_DIR"] = self.pairs_before
        self.tmp.cleanup()

    def events(self, kind: str | None = None) -> list[dict[str, Any]]:
        """The loop's logged events, or only those of `kind`."""
        path = event_log(self.repo)
        if not path.is_file():
            return []
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        return [row for row in rows if kind is None or row["kind"] == kind]


PLAN = "\n## The plan\n\nChange a.txt.\n"
UNRUNNABLE = (True, "ok a — 1 test\n?  proj/neo4j tests: no Docker daemon\n")
"""A gate that passes with a step that could not run."""
SKILL_PAGE = ".claude/skills/s/SKILL.md"
STALE_SKILL = (
    False,
    "ok meta/schemas — 3\n"
    "x  meta/rendered prose (1)\n"
    "     ../.claude/skills/s/SKILL.md\n"
    "x  meta (1)\n"
    "     meta: rendered prose\n",
)
"""A gate that fails only on a page under `.claude/skills/`, which the seats cannot write."""


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

    def test_a_commit_on_main_while_merge_gates_is_not_reverted(self) -> None:
        """`main` moves during `merge`'s own gate, between its rebase and the squash.

        The first gate is the `in-progress` check; its commit makes `merge`'s
        rebase move, so `merge` gates, and that gate's commit falls in the window.
        """
        b = self.b

        def commits(rel: str) -> Action:
            def act(repo: Path) -> None:
                write(rel, "main\n")(repo)
                sh(repo, "add", rel)
                sh(repo, "commit", "-q", "-m", f"add {rel}")

            return act

        b.issue("backlog", "fix-typo", "Fix the typo", difficulty="easy")
        b.during_gate = [commits("b.txt"), commits("c.txt"), quiet]
        b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("fix-typo", PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "fixed\n")),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertTrue(b.on_main("b.txt"))
        self.assertTrue(b.on_main("c.txt"))
        self.assertEqual(sh(b.repo, "log", "-1", "--format=%s", "main~1"), "add c.txt")
        changed = sh(
            b.repo, "diff", "--name-only", "--no-renames", "main~1", "main"
        ).splitlines()
        self.assertEqual(
            sorted(changed),
            ["a.txt", "issues/done/fix-typo.md", "issues/underway/fix-typo.md"],
        )
        self.assertEqual(b.gate_runs, 3)

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

    def test_a_failed_gate_goes_to_the_primary_even_when_it_went_quiet_last(
        self,
    ) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")
        b.gates = [False, True]
        b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("x", PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "1")),
            ("secondary", write("a.txt", "2")),
            ("primary", quiet),
            ("primary", write("a.txt", "3")),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(b.sent[7][0], "primary")
        self.assertIn("FAILED: test_widget", b.sent[7][1])
        self.assertEqual(b.gate_runs, 2)

    def test_a_gate_that_fails_while_landing_goes_to_the_primary(self) -> None:
        b = self.b

        def commits(repo: Path) -> None:
            write("b.txt", "main\n")(repo)
            sh(repo, "add", "b.txt")
            sh(repo, "commit", "-q", "-m", "add b.txt")

        b.issue("backlog", "x", "X", difficulty="easy")
        b.gates = [True, False]
        b.during_gate = [commits]
        b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("x", PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "1")),
            ("secondary", write("a.txt", "2")),
            ("primary", quiet),
            ("primary", write("a.txt", "3")),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(b.sent[7][0], "primary")
        self.assertIn("FAILED: test_widget", b.sent[7][1])
        self.assertEqual(b.gate_runs, 3)

    def implemented(self, slug: str) -> None:
        """Script an easy Issue through to both seats leaving `in-progress` as it stands."""
        self.b.issue("backlog", slug, "X", difficulty="easy")
        self.b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append(slug, PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "1")),
            ("secondary", quiet),
        )

    def test_a_gate_step_that_could_not_run_pauses_until_the_developer_supplies_it(
        self,
    ) -> None:
        b = self.b
        self.implemented("x")
        b.gates = [UNRUNNABLE]
        self.assertEqual(b.loop.run(once=True), "paused")
        st = b.state()
        self.assertEqual(st.retry, "gate")
        assert st.paused is not None
        self.assertIn("proj/neo4j tests: no Docker daemon", st.paused)
        self.assertEqual(st.approvals, ["primary", "secondary"])
        self.assertEqual(board.locations(b.loop.wt, "x"), ["in-progress"])
        self.assertFalse(b.on_main("a.txt"))
        sent = len(b.sent)
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(len(b.sent), sent)
        self.assertEqual(b.gate_runs, 2)
        self.assertTrue(b.on_main("a.txt"))

    def test_a_resumed_gate_that_still_could_not_run_pauses_again(self) -> None:
        b = self.b
        self.implemented("x")
        b.gates = [UNRUNNABLE, UNRUNNABLE]
        self.assertEqual(b.loop.run(once=True), "paused")
        sent = len(b.sent)
        self.assertEqual(b.loop.run(once=True), "paused")
        self.assertEqual(len(b.sent), sent)
        self.assertEqual(b.state().retry, "gate")
        self.assertFalse(b.on_main("a.txt"))

    def test_a_failed_gate_with_a_step_that_could_not_run_goes_to_the_primary(
        self,
    ) -> None:
        b = self.b
        self.implemented("x")
        b.gates = [(False, "x  a (1)\n     boom\n?  b: no tool\n"), True]
        b.script(("primary", write("a.txt", "2")), ("secondary", quiet))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(b.sent[6][0], "primary")
        self.assertIn("x  a (1)", b.sent[6][1])

    def test_a_gate_step_that_could_not_run_while_landing_pauses_the_landing(
        self,
    ) -> None:
        b = self.b

        def commits(repo: Path) -> None:
            write("b.txt", "main\n")(repo)
            sh(repo, "add", "b.txt")
            sh(repo, "commit", "-q", "-m", "add b.txt")

        self.implemented("x")
        b.gates = [True, UNRUNNABLE]
        b.during_gate = [commits]
        self.assertEqual(b.loop.run(once=True), "paused")
        self.assertEqual(b.state().retry, "merge")
        self.assertFalse(b.on_main("a.txt"))
        sent = len(b.sent)
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(len(b.sent), sent)
        self.assertEqual(b.gate_runs, 3)

    def gated_lines(self, body: str) -> list[str]:
        return [line for line in body.splitlines() if line.startswith("Gated by the supervisor")]

    def test_a_passing_gate_that_closes_in_progress_is_logged_and_kept_in_the_issue(
        self,
    ) -> None:
        b = self.b
        self.implemented("x")
        b.gates = [(True, "ok proj/tests — 3\nok proj — 1 steps across 1 project\n")]
        self.assertEqual(b.loop.run(once=True), "landed")
        [event] = b.events("gated")
        self.assertEqual((event["slug"], event["stage"]), ("x", "in-progress"))
        self.assertEqual((event["outcome"], event["steps"]), ("passed", 1))
        body = sh(b.repo, "show", "main:issues/done/x.md")
        self.assertEqual(self.gated_lines(body), [gate_line(event)])
        self.assertTrue(gate_line(event).endswith("; 1 step passed."))

    def test_a_failing_gate_that_closes_in_progress_is_logged_and_kept_in_the_issue(
        self,
    ) -> None:
        b = self.b
        self.implemented("x")
        b.gates = [(False, "x  proj/tests (1)\n     boom\nx  proj (1)\n"), True]
        b.script(("primary", write("a.txt", "2")), ("secondary", quiet))
        self.assertEqual(b.loop.run(once=True), "landed")
        failed, passed = b.events("gated")
        self.assertEqual(
            (failed["outcome"], failed["failed"], passed["outcome"]),
            ("failed", ["proj/tests"], "passed"),
        )
        body = sh(b.repo, "show", "main:issues/done/x.md")
        self.assertEqual(self.gated_lines(body), [gate_line(failed), gate_line(passed)])
        self.assertIn(gate_line(failed), b.sent[6][1])

    def test_a_gate_step_that_could_not_run_is_logged_kept_and_shown_in_the_status(
        self,
    ) -> None:
        b = self.b
        self.implemented("x")
        b.gates = [UNRUNNABLE]
        self.assertEqual(b.loop.run(once=True), "paused")
        [event] = b.events("gated")
        self.assertEqual(event["outcome"], "could-not-run")
        self.assertEqual(event["could_not_run"], {"proj/neo4j tests": "no Docker daemon"})
        body = b.issue_in_worktree("x").body
        self.assertEqual(self.gated_lines(body), [gate_line(event)])
        self.assertEqual(sh(b.loop.wt, "status", "--porcelain"), "")
        [underway] = status_view(b.repo)["underway"]
        self.assertEqual(
            underway["gate"],
            {"stage": "in-progress", "outcome": "could-not-run", "at": event["at"]},
        )
        self.assertIn("last gate: in-progress, could-not-run at", status(b.repo))

    def test_a_landing_gate_is_logged_as_landing_and_adds_no_line(self) -> None:
        b = self.b

        def commits(repo: Path) -> None:
            write("b.txt", "main\n")(repo)
            sh(repo, "add", "b.txt")
            sh(repo, "commit", "-q", "-m", "add b.txt")

        self.implemented("x")
        b.during_gate = [commits]
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual([e["stage"] for e in b.events("gated")], ["in-progress", "landing"])
        body = sh(b.repo, "show", "main:issues/done/x.md")
        self.assertEqual(len(self.gated_lines(body)), 1)

    def test_a_branch_that_changes_nothing_logs_no_gate(self) -> None:
        b = self.b
        sh(b.repo, "worktree", "add", "-q", "--detach", str(b.loop.wt), "main")
        self.assertIsNone(b.loop.run_gate("x", "in-progress"))
        self.assertEqual((b.gate_runs, b.events("gated")), (0, []))

    def test_an_issue_underway_with_no_gate_yet_shows_none(self) -> None:
        b = self.b
        b.loop.save(State(slug="x", stage="todo"))
        self.assertIsNone(status_view(b.repo)["underway"][0]["gate"])

    def test_a_gate_failing_only_on_a_page_the_seats_cannot_write_pauses(
        self,
    ) -> None:
        b = self.b
        self.implemented("x")
        b.gates = [STALE_SKILL]
        self.assertEqual(b.loop.run(once=True), "paused")
        st = b.state()
        self.assertEqual(st.retry, "gate")
        assert st.paused is not None
        self.assertIn(f"- {SKILL_PAGE}", st.paused)
        self.assertIn("run `just render`", st.paused)
        self.assertIn("outside the sandbox", st.paused)
        self.assertEqual(st.approvals, ["primary", "secondary"])
        self.assertFalse(b.on_main("a.txt"))
        sent = len(b.sent)
        write(SKILL_PAGE, "rendered\n")(b.loop.wt)
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(len(b.sent), sent)
        self.assertTrue(b.on_main("a.txt"))
        self.assertTrue(b.on_main(SKILL_PAGE))

    def test_a_page_the_seats_cannot_write_while_landing_pauses_the_landing(
        self,
    ) -> None:
        b = self.b

        def commits(repo: Path) -> None:
            write("b.txt", "main\n")(repo)
            sh(repo, "add", "b.txt")
            sh(repo, "commit", "-q", "-m", "add b.txt")

        self.implemented("x")
        b.gates = [True, STALE_SKILL]
        b.during_gate = [commits]
        self.assertEqual(b.loop.run(once=True), "paused")
        self.assertEqual(b.state().retry, "merge")
        write(SKILL_PAGE, "rendered\n")(b.loop.wt)
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertTrue(b.on_main(SKILL_PAGE))
        self.assertTrue(b.on_main("b.txt"))

    def test_a_page_the_seats_cannot_write_and_a_step_that_could_not_run_name_both(
        self,
    ) -> None:
        b = self.b
        self.implemented("x")
        b.gates = [(False, STALE_SKILL[1] + "?  b: no tool\n")]
        self.assertEqual(b.loop.run(once=True), "paused")
        paused = b.state().paused
        assert paused is not None
        self.assertIn(f"- {SKILL_PAGE}", paused)
        self.assertIn("- b: no tool", paused)

    def test_a_stale_page_beside_another_failure_goes_to_the_primary(self) -> None:
        b = self.b
        self.implemented("x")
        out = (
            "x  meta/rendered prose (1)\n     ../.claude/skills/s/SKILL.md\n"
            "x  meta/a (1)\n     boom\n"
            "x  meta (1)\n     meta: rendered prose, a\n"
        )
        b.gates = [(False, out), True]
        b.script(("primary", write("a.txt", "2")), ("secondary", quiet))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(b.sent[6][0], "primary")
        self.assertIn("x  meta/a (1)", b.sent[6][1])

    def test_a_stale_page_the_seats_can_write_goes_to_the_primary(self) -> None:
        b = self.b
        self.implemented("x")
        out = (
            "x  meta/rendered prose (1)\n     ../README.md\n"
            "x  meta (1)\n     meta: rendered prose\n"
        )
        b.gates = [(False, out), True]
        b.script(("primary", write("README.md", "2")), ("secondary", quiet))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(b.sent[6][0], "primary")
        self.assertIn("../README.md", b.sent[6][1])

    def test_an_unmet_requirement_other_than_the_gate_goes_to_the_other_seat(
        self,
    ) -> None:
        b = self.b
        b.issue("backlog", "x", "X")
        b.stop_when_empty = True
        b.script(
            ("primary", append("x", "\nOne.\n")),
            ("secondary", append("x", "\nTwo.\n")),
            ("primary", quiet),
        )
        b.loop.run()
        st = b.state()
        self.assertEqual(st.stage, "backlog")
        self.assertEqual(st.next_role, "secondary")
        self.assertIn("set `difficulty:`", st.note)

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

    def test_a_seat_interrupted_before_a_model_change_starts_fresh_unrestarted(
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
        b.loop.stage_models = {"backlog": "B"}
        b.stop_when_empty = True
        b.script(("primary", quiet))
        b.loop.run()
        self.assertEqual(b.opened[-1], ("primary", None))
        self.assertEqual(b.models[-1], ("primary", "B"))
        self.assertFalse(b.sent[-1][1].startswith("(Your session was restarted"))

    def test_a_state_file_without_models_resumes_on_the_same_model(self) -> None:
        b = self.b
        b.loop.model = "A"
        b.issue("backlog", "x", "X")
        b.stop_when_empty = True
        b.script(("primary", front("x", difficulty="easy")))
        b.loop.run()
        saved = json.loads(b.loop.state_file.read_text())
        del saved["models"]
        b.loop.state_file.write_text(json.dumps(saved))
        b.loop.stop_requested = False
        b.script(("secondary", quiet), ("primary", quiet))
        b.loop.run()
        self.assertEqual(b.opened[-1], ("primary", "primary-session"))
        self.assertEqual(b.models[-1], ("primary", "A"))

    @unittest.skipUnless(INSPECTS, NO_PS)
    def test_reap_stops_only_an_orphaned_seat_in_this_worktree(self) -> None:
        """The orphan is started through `sh`, so that it is not this process's child.

        A child that `reap` stops stays a zombie, which `Loop.alive` counts as
        alive until this process waits on it, so `reap` would poll for its full
        ten seconds. The orphan's output goes to /dev/null, or `run` would wait
        for the `sleep` to close the captured stdout.
        """
        b = self.b
        b.loop.ensure_worktree()
        b.loop.dir.mkdir(exist_ok=True)
        b.loop.seat_command = "sleep"
        orphan = int(
            subprocess.run(
                ["sh", "-c", "sleep 60 >/dev/null 2>&1 & echo $!"],
                cwd=b.loop.wt,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        )

        def kill_orphan() -> None:
            with contextlib.suppress(ProcessLookupError):
                os.kill(orphan, signal.SIGKILL)

        self.addCleanup(kill_orphan)
        elsewhere = subprocess.Popen(["sleep", "60"], cwd=b.repo)
        self.addCleanup(elsewhere.wait)
        self.addCleanup(elsewhere.kill)
        (b.loop.dir / "primary.pid").write_text(f"{orphan}\n")
        (b.loop.dir / "secondary.pid").write_text(f"{elsewhere.pid}\n")
        b.loop.reap()
        deadline = time.monotonic() + 10
        while Loop.alive(orphan) and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertFalse(Loop.alive(orphan))
        self.assertIsNone(elsewhere.poll())

    def test_a_seat_that_crashes_twice_pauses_the_loop(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X")
        b.script(("primary", CRASH), ("primary", CRASH))
        self.assertEqual(b.loop.run(), "paused")
        self.assertIn("failed twice", b.state().paused or "")
        self.assertTrue(b.notes)

    def test_a_refusal_is_told_apart_from_a_failure(self) -> None:
        self.assertTrue(is_refusal(REFUSAL))
        for error in ("boom", "turn timed out after 2700s", "seat exited mid-turn: ", None):
            self.assertFalse(is_refusal(error))

    def test_a_refused_seat_restarts_once_with_a_fresh_session(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")
        b.stop_when_empty = True
        b.script(("primary", REFUSED), ("primary", quiet))
        b.loop.run()
        self.assertEqual(b.opened, [("primary", None), ("primary", None)])
        self.assertEqual(b.sent[0][1], b.sent[1][1])
        self.assertFalse(b.sent[1][1].startswith("(Your session was restarted"))
        refused = b.events("seat-refused")
        self.assertEqual([(e["role"], e["error"]) for e in refused], [("primary", REFUSAL)])

    def test_a_crashed_seat_refused_on_its_restart_pauses_with_no_session_kept(
        self,
    ) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")
        b.script(("primary", CRASH), ("primary", REFUSED))
        self.assertEqual(b.loop.run(), "paused")
        st = b.state()
        self.assertIn("the primary seat was refused on its restart", st.paused or "")
        self.assertNotIn("primary", st.sessions)
        self.assertFalse((b.loop.dir / "primary.session").exists())
        b.stop_when_empty = True
        b.script(("primary", quiet))
        b.loop.run()
        self.assertEqual(b.opened[-1], ("primary", None))
        self.assertFalse(b.sent[-1][1].startswith("(Your session was restarted"))

    def test_a_seat_refused_twice_pauses_with_no_session_kept(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")
        b.script(("primary", REFUSED), ("primary", REFUSED))
        self.assertEqual(b.loop.run(), "paused")
        st = b.state()
        self.assertIn("the primary seat was refused twice", st.paused or "")
        self.assertNotIn("primary", st.sessions)
        self.assertFalse((b.loop.dir / "primary.session").exists())
        paused = b.events("paused")
        self.assertIn("refused twice", paused[-1]["reason"])
        b.stop_when_empty = True
        b.script(("primary", quiet))
        b.loop.run()
        self.assertEqual(b.opened[-1], ("primary", None))
        self.assertFalse(b.sent[-1][1].startswith("(Your session was restarted"))

    def test_a_refused_resumed_turn_restarts_fresh_without_claiming_a_session(
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
        b.stop_when_empty = True
        b.script(("primary", REFUSED), ("primary", quiet))
        b.loop.run()
        self.assertEqual(b.opened[-2:], [("primary", "primary-session"), ("primary", None)])
        self.assertTrue(b.sent[-2][1].startswith("(Your session was restarted"))
        self.assertFalse(b.sent[-1][1].startswith("(Your session was restarted"))
        self.assertTrue(b.sent[-2][1].endswith(b.sent[-1][1]))

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

    def test_an_accept_whose_gate_could_not_run_pauses_then_goes_back_on_failure(
        self,
    ) -> None:
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
        b.gates = [UNRUNNABLE]
        self.assertEqual(b.loop.accept(), "paused")
        self.assertEqual(b.state().retry, "merge")
        self.assertFalse(b.on_main("a.txt"))
        b.gates = [False]
        b.stop_when_empty = True
        b.script(("primary", quiet))
        self.assertEqual(b.loop.run(), "stopped")
        self.assertEqual(board.locations(b.loop.wt, "h"), ["in-progress"])
        self.assertIn("FAILED: test_widget", b.sent[-1][1])
        self.assertNotIn("no Docker daemon", b.sent[-1][1])

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

    def main_edits_a(self, repo: Path) -> None:
        """Another process lands a change to `a.txt` on `main`."""
        write("a.txt", "main's")(repo)
        sh(repo, "add", "-A")
        sh(repo, "commit", "-q", "-m", "main's a.txt")

    def test_a_landing_overtaken_and_conflicting_goes_back_to_in_progress(
        self,
    ) -> None:
        """`main` moves while the Issue lands from `done/`, and the rebase conflicts.

        `start` lands too, so `before_land` holds a quiet action for it first.
        """
        b = self.b
        b.issue("backlog", "h", "Ordinary")
        b.before_land = [quiet, self.main_edits_a]
        b.script(
            ("primary", front("h", difficulty="easy")),
            ("secondary", quiet),
            ("primary", append("h", PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "x")),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "paused")
        st = b.state()
        self.assertEqual((st.stage, st.retry), ("done", None))
        b.stop_when_empty = True
        b.script(("primary", quiet))
        self.assertEqual(b.loop.run(once=True), "stopped")
        self.assertEqual(b.state().stage, "in-progress")
        self.assertEqual(board.locations(b.loop.wt, "h"), ["in-progress"])
        self.assertIn("Implement issues/in-progress/h.md", b.sent[-1][1])
        self.assertIn("This came back from done/", b.sent[-1][1])
        self.assertIn("conflicts with main", b.sent[-1][1])
        self.assertNotIn("The developer changed things", b.sent[-1][1])

    def test_an_accept_overtaken_and_conflicting_goes_back_to_its_desk_check(
        self,
    ) -> None:
        """`main` moves while an accepted Issue lands, and the rebase conflicts.

        The developer resolves the conflict in the worktree, as the pause asks,
        and the changed code goes back under their check.
        """
        b = self.b
        b.issue("backlog", "h", "Developer", difficulty="developer")
        b.before_land = [quiet, self.main_edits_a]
        b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("h", PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "x")),
            ("secondary", quiet),
        )
        self.assertEqual(b.loop.run(), "desk-check")
        self.assertEqual(b.loop.accept(), "paused")
        st = b.state()
        self.assertEqual((st.stage, st.retry), ("done", None))
        sh(b.loop.wt, "rebase", "-q", "-X", "theirs", "main")
        b.script(("primary", quiet), ("secondary", quiet))
        self.assertEqual(b.loop.run(), "desk-check")
        st = b.state()
        self.assertEqual((st.stage, st.retry), ("desk-check", "desk-check"))
        self.assertEqual(board.locations(b.loop.wt, "h"), ["desk-check"])
        self.assertIn("This came back from done/", b.sent[-2][1])
        self.assertIn("The developer changed things", b.sent[-2][1])

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


def turn_rows(loop: Loop) -> list[dict[str, Any]]:
    """The rows of `loop`'s `turns.jsonl`."""
    return [json.loads(row) for row in (loop.dir / "turns.jsonl").read_text().splitlines()]


class PairNotesTest(unittest.TestCase):
    """Each turn's closing message, quoted under `## Pair notes` in its Issue file."""

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)
        self.b.issue("backlog", "x", "X", difficulty="easy")
        self.b.stop_when_empty = True

    def test_each_closing_message_is_kept_once_and_the_turns_stay_quiet(
        self,
    ) -> None:
        b = self.b
        b.script(
            ("primary", Says("Looks groomed.\n\nNothing to add.")),
            ("secondary", Says("Agreed.")),
        )
        said: list[str] = []
        b.loop.say = said.append
        self.assertEqual(b.loop.run(), "stopped")
        st = b.state()
        self.assertEqual(st.stage, "todo")
        body = b.issue_in_worktree("x").body
        self.assertEqual(board.sections(body, "Pair notes"), 1)
        self.assertEqual(body.count("Looks groomed."), 1)
        self.assertIn(
            "## Pair notes\n\n> **primary, backlog turn 1**\n>\n> Looks groomed.\n>\n"
            "> Nothing to add.\n\n> **secondary, backlog turn 2**\n>\n> Agreed.\n",
            body,
        )
        rows = turn_rows(b.loop)
        self.assertEqual([row["quiet"] for row in rows], [True, True])
        self.assertEqual([row["notes_restored"] for row in rows], [False, False])
        self.assertEqual([row["note_from"] for row in rows], ["message", "message"])
        self.assertFalse([line for line in said if "Pair notes" in line])
        self.assertEqual(st.seats_used, [])

    def test_the_other_seat_sees_a_note_in_its_diff_and_its_author_does_not(
        self,
    ) -> None:
        b = self.b
        b.script(
            ("primary", Says("Mine.")),
            ("secondary", Says("Theirs.", write("a.txt", "more\n"))),
            ("primary", quiet),
        )
        b.loop.run()
        self.assertNotIn("+> Mine.", b.sent[2][1])
        self.assertIn("+> Theirs.", b.sent[2][1])
        self.assertNotIn("The developer changed things", b.sent[2][1])

    def test_a_note_naming_the_headings_the_loop_reads_steers_nothing(self) -> None:
        b = self.b
        steer = Says(
            "# Needs elaboration\n\nwhy\n\n## The plan\n\n**The plan.**\nDo it."
        )
        b.script(*[(role, steer) for role in ("primary", "secondary") * 2])
        self.assertEqual(b.loop.run(), "stopped")
        st = b.state()
        self.assertEqual(st.stage, "todo")
        self.assertIn("write the plan", st.note)
        self.assertFalse(b.on_main("issues/backlog/x.md"))

    def test_an_empty_closing_message_leaves_no_note(self) -> None:
        b = self.b
        b.script(("primary", Says("  \n")), ("secondary", quiet))
        b.loop.run()
        self.assertNotIn("Pair notes", b.issue_in_worktree("x").body)
        log = sh(b.loop.wt, "log", "--format=%s")
        self.assertNotIn("note on", log)

    def test_a_turn_that_lost_its_issue_file_keeps_no_note(self) -> None:
        b = self.b
        gone = Says(
            "Removed it.",
            lambda wt: (wt / board.ISSUES / "underway" / "x.md").unlink(),
        )
        b.script(("primary", gone))
        b.loop.run()
        self.assertTrue(b.on_main("issues/backlog/x.md"))
        self.assertNotIn("note on", sh(b.loop.wt, "log", "--format=%s"))
        self.assertEqual([row["notes_restored"] for row in turn_rows(b.loop)], [False])

    def test_a_grooming_pass_keeps_no_note(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A")
        b.script(
            (
                "primary",
                Says(
                    "Groomed a.",
                    both(front("a", difficulty="easy"), order("# groomed below\na\n")),
                ),
            ),
            ("secondary", Says("Agreed.")),
        )
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertNotIn("Pair notes", sh(b.repo, "show", "main:issues/backlog/a.md"))
        self.assertNotIn("note on", sh(b.repo, "log", "--format=%s", "main"))
        self.assertFalse(any(row["notes_restored"] for row in turn_rows(b.groomer)))

    # The Pair notes are the loop's: `settle` puts back whatever a seat
    # changed in them before it judges the turn (`Loop.restore_notes`), and
    # `keep_note` writes back what the seat added as the turn's note.

    def notes_after(self, *turns: tuple[str, object]) -> tuple[str, list[dict[str, Any]]]:
        """Run the primary's note "A." and then `turns`; the body and the turn rows."""
        b = self.b
        b.script(("primary", Says("A.")), *turns)
        self.said: list[str] = []
        b.loop.say = self.said.append
        b.loop.run()
        return b.issue_in_worktree("x").body, turn_rows(b.loop)

    def test_a_seats_own_note_is_its_turns_note_and_its_turn_stays_quiet(self) -> None:
        body, rows = self.notes_after(
            ("secondary", Says("B.", append("x", "\nMy own note.\n")))
        )
        self.assertEqual(self.b.state().stage, "todo")
        self.assertNotIn("> B.", body)
        self.assertEqual(body.count("My own note."), 1)
        self.assertTrue(
            body.endswith("> A.\n\n> **secondary, backlog turn 2**\n>\n> My own note.\n")
        )
        self.assertEqual([row["quiet"] for row in rows], [True, True])
        self.assertEqual([row["notes_restored"] for row in rows], [False, True])
        self.assertEqual([row["note_from"] for row in rows], ["message", "seat"])
        self.assertIn("put back the secondary seat's edits to the Pair notes", self.said)

    def test_an_earlier_note_a_seat_deleted_comes_back(self) -> None:
        body, rows = self.notes_after(("secondary", Says("B.", unappend("x", "> A.\n"))))
        self.assertEqual(self.b.state().stage, "todo")
        self.assertIn("> **primary, backlog turn 1**\n>\n> A.\n", body)
        self.assertEqual([row["quiet"] for row in rows], [True, True])

    def test_a_turn_that_changed_code_keeps_it_and_its_own_note(self) -> None:
        body, rows = self.notes_after(
            ("secondary", Says("B.", both(write("a.txt", "x\n"), append("x", "\nMine.\n")))),
            ("primary", quiet),
        )
        self.assertEqual((self.b.loop.wt / "a.txt").read_text(), "x\n")
        self.assertIn("> **secondary, backlog turn 2**\n>\n> Mine.\n", body)
        self.assertNotIn("> B.", body)
        self.assertEqual([row["quiet"] for row in rows], [True, False, True])
        self.assertEqual([row["notes_restored"] for row in rows], [False, True, False])

    def test_a_seats_needs_elaboration_after_the_notes_stays_and_sends_it_back(
        self,
    ) -> None:
        _, rows = self.notes_after(
            ("secondary", Says("B.", append("x", "\n# Needs elaboration\n\nWhat for?\n")))
        )
        self.assertIn("What for?", sh(self.b.repo, "show", "main:issues/backlog/x.md"))
        self.assertEqual([row["notes_restored"] for row in rows], [False, False])

    def test_a_label_a_seat_copied_into_its_note_is_not_kept_twice(self) -> None:
        seat = "\nA paragraph.\n\n**secondary, backlog turn 2**\n\nCopied.\n"
        body, rows = self.notes_after(("secondary", Says("B.", append("x", seat))))
        self.assertTrue(
            body.endswith(
                "> **secondary, backlog turn 2**\n>\n> A paragraph.\n>\n> Copied.\n"
            )
        )
        self.assertEqual(body.count("**secondary, backlog turn 2**"), 1)
        self.assertEqual([row["quiet"] for row in rows], [True, True])

    def test_a_note_a_seat_quoted_like_the_loops_is_not_quoted_twice(self) -> None:
        seat = "\n> **secondary, backlog turn 2**\n>\n> Quoted.\n"
        body, _ = self.notes_after(("secondary", Says("B.", append("x", seat))))
        self.assertTrue(body.endswith("> A.\n\n> **secondary, backlog turn 2**\n>\n> Quoted.\n"))
        self.assertNotIn("> >", body)

    def test_a_seats_edit_to_an_earlier_note_is_put_back_and_its_own_note_kept(
        self,
    ) -> None:
        def edit(cwd: Path) -> None:
            issue = cwd / board.ISSUES / "underway" / "x.md"
            issue.write_text(issue.read_text().replace("turn 1**", "turn 1, edited**") + "\nNew.\n")

        body, rows = self.notes_after(("secondary", Says("B.", edit)))
        self.assertNotIn("edited", body)
        self.assertTrue(body.endswith("> A.\n\n> **secondary, backlog turn 2**\n>\n> New.\n"))
        self.assertEqual([row["note_from"] for row in rows], ["message", "seat"])

    def test_a_pair_notes_section_a_seat_added_leaves_only_the_loops(self) -> None:
        b = self.b
        b.script(
            ("primary", Says("A.", append("x", "\n## Pair notes\n\nMine.\n"))),
            ("secondary", Says("B.")),
        )
        b.loop.run()
        body = b.issue_in_worktree("x").body
        self.assertEqual(board.sections(body, "Pair notes"), 1)
        self.assertNotIn("> A.", body)
        self.assertIn(
            "Some words.\n\n## Pair notes\n\n> **primary, backlog turn 1**\n>\n> Mine.\n", body
        )
        self.assertEqual([row["quiet"] for row in turn_rows(b.loop)], [True, True])

    def test_two_notes_sections_restore_by_order_and_keep_the_plan_between(
        self,
    ) -> None:
        b = self.b
        notes = "\n## Pair notes\n\n> **primary, backlog turn 1**\n>\n> One.\n"
        later = "\n## Pair notes\n\n> **secondary, backlog turn 2**\n>\n> Two.\n"
        path = b.repo / "issues" / "backlog" / "x.md"
        path.write_text(path.read_text() + notes + "\n## The plan\n\nDo it.\n" + later)
        sh(b.repo, "commit", "-qam", "notes")

        def edit(cwd: Path) -> None:
            issue = cwd / "issues" / "underway" / "x.md"
            text = issue.read_text().replace("> One.\n", "> One, edited.\n")
            issue.write_text(text.replace("Do it.", "Do it well."))

        b.script(("primary", edit))
        b.loop.run()
        body = b.issue_in_worktree("x").body
        self.assertIn("> One.\n\n## The plan\n\nDo it well.\n" + later, body)
        self.assertNotIn("One, edited.", body)
        rows = turn_rows(b.loop)
        self.assertEqual([(row["quiet"], row["notes_restored"]) for row in rows], [(False, True)])


class GateUnrunnableTest(unittest.TestCase):
    def test_each_step_that_could_not_run_is_named_with_why(self) -> None:
        out = (
            "ok meta/schemas — 3\n"
            "?  meta: no gate asserted\n"
            "?  python-seed/mutation: mutmut is not installed\n"
            "?  steps that could not run (1) — zero where a person runs the gate, "
            "non-zero under CI\n"
            "  mutation: mutmut is not installed\n"
        )
        reason = gate_unrunnable(out)
        assert reason is not None
        self.assertIn("could not run 2 step(s)", reason)
        self.assertIn("- meta: no gate asserted", reason)
        self.assertIn("- python-seed/mutation: mutmut is not installed", reason)
        self.assertNotIn("steps that could not run (1)", reason)

    def test_a_gate_where_every_step_ran_is_none(self) -> None:
        self.assertIsNone(gate_unrunnable("ok a — 1\nok b — 2\nok portfolio — 3 steps\n"))


class GateRecordTest(unittest.TestCase):
    """`gate_record` counts and names only the steps `.meta/gate` forwarded."""

    def test_a_pass_counts_each_project_step_and_not_the_closing_line(self) -> None:
        out = "ok a/x — 3\nok a/y\nok portfolio — 2 steps across 1 project\n"
        record = gate_record(out, "passed", None)
        self.assertEqual(record["steps"], 2)
        self.assertEqual(record["failed"], [])
        self.assertEqual(record["could_not_run"], {})

    def test_a_failure_names_the_step_and_not_the_closing_block(self) -> None:
        out = "ok a/x\nx  a/y (2)\n     one\n     two\nx  portfolio (1)\n     a: y\n"
        record = gate_record(out, "failed", ["a"])
        self.assertEqual(record["steps"], 2)
        self.assertEqual(record["failed"], ["a/y"])
        self.assertEqual(record["targets"], ["a"])

    def test_a_step_that_could_not_run_is_named_with_why_and_the_summary_is_not(
        self,
    ) -> None:
        out = (
            "ok a/x\n"
            "?  a/neo4j: no Docker daemon\n"
            "?  b: no gate asserted\n"
            "?  steps that could not run (1) — zero where a person runs the gate\n"
            "  neo4j: no Docker daemon\n"
        )
        record = gate_record(out, "could-not-run", None)
        self.assertEqual(record["steps"], 3)
        self.assertEqual(
            record["could_not_run"], {"a/neo4j": "no Docker daemon", "b": "no gate asserted"}
        )

    def test_a_line_a_project_wrote_to_stderr_is_not_a_step(self) -> None:
        out = "ok something\nx  noise (1)\n?  note: just a remark\nok a/x\n"
        record = gate_record(out, "passed", None)
        self.assertEqual(record["steps"], 1)
        self.assertEqual(record["failed"], [])
        self.assertEqual(record["could_not_run"], {})

    def test_the_line_names_the_time_the_targets_and_what_was_found(self) -> None:
        row = {
            "at": "2026-10-03T11:58:07",
            **gate_record("x  a/y (1)\n?  b/z: no `docker`\n", "failed", ["a", "b"]),
        }
        self.assertEqual(
            gate_line(row),
            "Gated by the supervisor at 11:58: `a`, `b`; 2 steps; "
            "failed: `a/y`; could not run: `b/z` (no docker).",
        )
        row = {"at": "2026-10-03T09:01:00", **gate_record("ok a/x\n", "passed", None)}
        self.assertEqual(
            gate_line(row), "Gated by the supervisor at 09:01: the whole gate; 1 step passed."
        )

    def test_a_note_after_the_line_stays_under_the_same_pair_notes(self) -> None:
        line = "Gated by the supervisor at 09:01: the whole gate; 1 step passed."
        text = board.with_note("# X\n", "primary, in-progress turn 1", "Done.")
        text = board.with_note(f"{text}\n{line}\n", "secondary, in-progress turn 2", "Ok.")
        self.assertEqual(board.sections(text, "Pair notes"), 1)
        self.assertIn(f">\n> Done.\n\n{line}\n\n> **secondary", text)


class UnwritablePagesTest(unittest.TestCase):
    """`unwritable_pages` answers only when every failure is a page the seats cannot write."""

    wt = Path("/w")
    denied = (Path("/w/.claude/skills"), Path("/elsewhere"))

    def pages(self, out: str) -> list[str] | None:
        return unwritable_pages(out, self.wt, self.denied)

    def test_a_stale_skill_page_alone_is_named_from_the_worktree(self) -> None:
        self.assertEqual(self.pages(STALE_SKILL[1]), [SKILL_PAGE])

    def test_another_failing_step_is_none(self) -> None:
        out = (
            "x  meta/rendered prose (1)\n     ../.claude/skills/s/SKILL.md\n"
            "x  meta/a (1)\n     boom\n"
            "x  meta (1)\n     meta: rendered prose, a\n"
        )
        self.assertIsNone(self.pages(out))

    def test_a_stale_page_the_seats_can_write_is_none(self) -> None:
        out = (
            "x  meta/rendered prose (1)\n     ../README.md\n"
            "x  meta (1)\n     meta: rendered prose\n"
        )
        self.assertIsNone(self.pages(out))

    def test_a_finding_that_is_not_a_page_is_none(self) -> None:
        out = (
            "x  meta/rendered prose (1)\n     x.md exists but nothing renders it\n"
            "x  meta (1)\n     meta: rendered prose\n"
        )
        self.assertIsNone(self.pages(out))

    def test_a_project_that_failed_with_no_step_is_none(self) -> None:
        out = STALE_SKILL[1] + (
            "     rust-seed: every step reported ok or ? and the gate exited 1\n"
        )
        self.assertIsNone(self.pages(out))

    def test_output_without_the_closing_block_is_none(self) -> None:
        self.assertIsNone(self.pages("FAILED: test_widget"))
        self.assertIsNone(
            self.pages("x  meta/rendered prose (1)\n     ../.claude/skills/s/SKILL.md\n")
        )


class SeatModelTest(unittest.TestCase):
    """Each stage runs the model it names, and a seat changes session only to change model."""

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)
        self.b.loop.model = "A"
        self.b.issue("backlog", "x", "X")

    def easy_issue(self) -> None:
        self.b.script(
            ("primary", front("x", difficulty="easy")),
            ("secondary", quiet),
            ("primary", append("x", PLAN)),
            ("secondary", quiet),
            ("primary", write("a.txt", "x\n")),
            ("secondary", quiet),
        )

    def test_with_no_stage_model_both_seats_run_model_for_the_whole_issue(
        self,
    ) -> None:
        b = self.b
        self.easy_issue()
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(b.models, [("primary", "A"), ("secondary", "A")])
        self.assertEqual(b.events("seat-model"), [])

    def test_a_stage_with_another_model_starts_both_seats_fresh_on_it(self) -> None:
        b = self.b
        b.loop.stage_models = {"in-progress": "B"}
        self.easy_issue()
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(
            b.models,
            [("primary", "A"), ("secondary", "A"), ("primary", "B"), ("secondary", "B")],
        )
        self.assertEqual(b.opened[2:], [("primary", None), ("secondary", None)])
        self.assertEqual(
            [(e["role"], e["from"], e["to"]) for e in b.events("seat-model")],
            [("primary", "A", "B"), ("secondary", "A", "B")],
        )

    def test_a_stage_that_keeps_the_model_resumes_the_sessions(self) -> None:
        b = self.b
        b.loop.stage_models = {"todo": "B", "in-progress": "B"}
        self.easy_issue()
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(
            b.models,
            [("primary", "A"), ("secondary", "A"), ("primary", "B"), ("secondary", "B")],
        )

    def test_a_restarted_loop_switches_a_seat_only_for_a_changed_model(self) -> None:
        b = self.b
        b.stop_when_empty = True

        def again(*turns: tuple[str, object]) -> None:
            b.loop.stop_requested = False
            b.script(*turns)
            b.loop.run()

        again(
            ("primary", front("x", difficulty="easy")),
            ("secondary", quiet),
            ("primary", append("x", PLAN)),
        )
        again(("secondary", append("x", "\nAgreed.\n")))
        self.assertEqual(b.opened[-1], ("secondary", "secondary-session"))
        self.assertEqual(b.models[-1], ("secondary", "A"))
        b.loop.stage_models = {"todo": "B"}
        again(("primary", quiet))
        self.assertEqual(b.opened[-1], ("primary", None))
        self.assertEqual(b.models[-1], ("primary", "B"))
        self.assertEqual(b.state().models["primary"], "B")
        self.assertEqual(b.state().stage, "in-progress")
        b.loop.stage_models = {"in-progress": "B"}
        again(("primary", write("a.txt", "x\n")), ("secondary", append("x", "\n")))
        self.assertEqual(
            b.opened[-2:], [("primary", "primary-session"), ("secondary", None)]
        )
        self.assertEqual(b.models[-2:], [("primary", "B"), ("secondary", "B")])

    def test_a_loop_restarted_with_another_model_starts_fresh_on_it(self) -> None:
        b = self.b
        b.stop_when_empty = True
        b.script(("primary", front("x", difficulty="easy")))
        b.loop.run()
        self.assertEqual(b.state().models["primary"], "A")
        b.loop.stop_requested = False
        b.loop.model = "C"
        b.script(("secondary", quiet), ("primary", quiet))
        b.loop.run()
        self.assertEqual(b.opened[-1], ("primary", None))
        self.assertEqual(b.models[-1], ("primary", "C"))

    def test_only_the_commands_that_work_an_issue_take_stage_models(self) -> None:
        from pair import STAGE_MODELS, arguments

        for name in ("run", "accept", "resume"):
            for stage in STAGE_MODELS:
                args = arguments().parse_args([name, f"--{stage}-model", "B"])
                self.assertEqual(getattr(args, f"{stage.replace('-', '_')}_model"), "B")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            arguments().parse_args(["groom", "--todo-model", "B"])


class SingleSeatTest(unittest.TestCase):
    """`run --single-seat`: the primary seat alone takes every turn of an Issue."""

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)
        self.b.loop.mode = "single"
        self.b.issue("backlog", "x", "X", difficulty="easy")

    def again(self, *turns: tuple[str, object]) -> str:
        """Run the loop until `turns` are spent, as a developer stopping it would."""
        self.b.stop_when_empty = True
        self.b.loop.stop_requested = False
        self.b.script(*turns)
        return self.b.loop.run()

    def test_single_seat_runs_an_issue_to_main_with_the_primary_alone(self) -> None:
        """The primary seat alone lands an Issue, and is never shown its own change.

        The turn after a changing one is told that nothing has changed, a risk
        the Issue's plan records.
        """
        b = self.b
        b.script(
            ("primary", quiet),
            ("primary", append("x", PLAN)),
            ("primary", quiet),
            ("primary", write("x.txt", "x")),
            ("primary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertTrue(b.on_main("x.txt"))
        self.assertEqual(
            [(row["role"], row["mode"]) for row in turn_rows(b.loop)],
            [("primary", "single")] * 5,
        )
        self.assertEqual([e["mode"] for e in b.events("started")], ["single"])
        self.assertEqual({role for role, _ in b.opened}, {"primary"})
        self.assertIn("Nothing has changed since your last turn.", b.sent[-1][1])

    def test_a_changing_turn_does_not_close_the_stage(self) -> None:
        self.assertEqual(self.again(("primary", write("a.txt", "x"))), "stopped")
        st = self.b.state()
        self.assertEqual(
            (st.stage, st.next_role, st.approvals), ("backlog", "primary", ["primary"])
        )

    def test_a_quiet_turn_closes_a_stage_whose_requirement_is_met(self) -> None:
        self.assertEqual(self.again(("primary", quiet)), "stopped")
        st = self.b.state()
        self.assertEqual((st.stage, st.next_role), ("todo", "primary"))

    def test_a_failed_gate_keeps_the_stage_and_reaches_the_primary_seat(self) -> None:
        b = self.b
        b.gates = [False]
        b.script(
            ("primary", quiet),
            ("primary", append("x", PLAN)),
            ("primary", quiet),
            ("primary", write("x.txt", "x")),
            ("primary", quiet),
            ("primary", quiet),
        )
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(b.gate_runs, 2)
        self.assertIn("FAILED: test_widget", b.sent[-1][1])

    def test_a_seat_that_never_goes_quiet_is_kicked_back_at_twice_the_cap(
        self,
    ) -> None:
        b = self.b
        b.loop.round_cap = 1
        b.script(("primary", write("c.txt", "1")), ("primary", write("c.txt", "2")))
        self.assertEqual(b.loop.run(once=True), "kicked")
        self.assertIn("within 2 turns", sh(b.repo, "show", "main:issues/backlog/x.md"))

    def test_without_the_flag_rows_and_the_started_event_say_pair(self) -> None:
        self.b.loop.mode = "pair"
        self.again(("primary", quiet), ("secondary", quiet))
        self.assertEqual({row["mode"] for row in turn_rows(self.b.loop)}, {"pair"})
        self.assertEqual([e["mode"] for e in self.b.events("started")], ["pair"])

    def test_an_issue_started_alone_stays_alone_when_run_as_a_pair(self) -> None:
        self.again(("primary", write("a.txt", "x")))
        self.b.loop.mode = "pair"
        self.again(("primary", quiet))
        self.assertEqual([row["mode"] for row in turn_rows(self.b.loop)], ["single"] * 2)
        self.assertEqual(self.b.state().stage, "todo")

    def test_an_issue_started_as_a_pair_stays_a_pair_when_run_alone(self) -> None:
        self.b.loop.mode = "pair"
        self.again(("primary", quiet))
        self.b.loop.mode = "single"
        self.again(("secondary", quiet))
        self.assertEqual([row["mode"] for row in turn_rows(self.b.loop)], ["pair"] * 2)
        self.assertEqual(self.b.state().stage, "todo")

    def test_a_state_file_without_a_mode_loads_as_a_pair(self) -> None:
        self.again(("primary", write("a.txt", "x")))
        saved = json.loads(self.b.loop.state_file.read_text())
        del saved["mode"]
        self.b.loop.state_file.write_text(json.dumps(saved))
        self.assertEqual(self.b.state().mode, "pair")

    def test_only_run_takes_the_flag(self) -> None:
        from pair import arguments

        self.assertTrue(arguments().parse_args(["run", "--single-seat"]).single_seat)
        self.assertFalse(arguments().parse_args(["run"]).single_seat)
        for name in ("groom", "accept", "resume"):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                arguments().parse_args([name, "--single-seat"])


class GateSelectionTest(unittest.TestCase):
    """The loop gates the Projects a change touches and the Products built from them (DR-303)."""

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)

    def select(self, *paths: str) -> list[str] | None:
        if not (self.b.repo / touched.STRUCTURE).is_file():
            self.b.structure()
        return touched.select(self.b.repo, paths)

    def test_a_change_selects_its_projects_and_the_products_built_from_them(
        self,
    ) -> None:
        cases = {
            ("pair/loop.py",): ["meta", "pair"],
            ("bootstraps/rust/seed/src/lib.rs",): ["rust-seed"],
            ("wiki/pair/loop.md",): ["meta", "pair"],
            ("issues/backlog/x.md",): ["meta", "pair"],
            (".meta/gate", "justfile"): ["meta", "pair"],
            (
                "bootstraps/rust/seed/Cargo.toml",
                "bootstraps/python/seed/pyproject.toml",
            ): ["rust-seed", "python-seed"],
            ("bootstraps/rust/render/x.md",): ["meta", "pair"],
            ("widgets/x.py",): ["widgets"],
            (): [],
        }
        for paths, expected in cases.items():
            with self.subTest(paths=paths):
                self.assertEqual(self.select(*paths), expected)

    def test_every_project_selected_is_the_whole_gate(self) -> None:
        paths = ("pair/x", "widgets/x", "bootstraps/rust/seed/x", "bootstraps/python/seed/x")
        self.assertIsNone(self.select(*paths))

    def test_no_structure_is_the_whole_gate(self) -> None:
        self.assertIsNone(touched.select(self.b.repo, ["pair/loop.py"]))

    def test_a_path_under_no_project_with_no_meta_project_is_the_whole_gate(
        self,
    ) -> None:
        self.b.structure("projects:\n" + project("widgets", "widgets"))
        self.assertIsNone(touched.select(self.b.repo, ["wiki/x.md"]))
        self.assertIsNone(touched.select(self.b.repo, ["widgets/x.py"]))

    def root_structure(self, root: str, *more: str) -> None:
        """Commit Projects `meta` and `app` at `root`, plus `more`, beside a three-item bundle."""
        bundle = self.b.repo / touched.BUNDLE
        bundle.parent.mkdir(parents=True, exist_ok=True)
        bundle.write_text(
            "items:\n"
            "  - path: README.md\n    kind: file\n"
            "  - path: wiki/stereorepo/\n    kind: dir\n"
            "  - path: stakeholders\n    kind: dir\n"
        )
        extra = "".join(project(name, name) for name in more)
        self.b.structure("projects:\n" + project("meta", ".meta") + project("app", root) + extra)

    def test_a_project_at_the_root_holds_what_no_deeper_project_or_the_bundle_holds(
        self,
    ) -> None:
        cases = {
            ("tests/test_x.py",): ["app"],
            ("build.py",): ["app"],
            ("lib/x.py",): ["lib"],
            ("issues/backlog/a.md",): ["meta"],
            (".meta/assertions/structure.yaml",): ["meta"],
            ("README.md",): ["meta"],
            ("wiki/stereorepo/x.md",): ["meta"],
            ("wiki/app/x.md",): ["app"],
            ("stakeholders/p.md",): ["meta"],
            ("stakeholders.md",): ["app"],
            ("tests/test_x.py", "issues/backlog/a.md"): ["meta", "app"],
        }
        for root in (".", "./"):
            self.root_structure(root, "lib")
            for paths, expected in cases.items():
                with self.subTest(root=root, paths=paths):
                    self.assertEqual(touched.select(self.b.repo, paths), expected)

    def test_the_root_project_and_meta_together_are_the_whole_gate(self) -> None:
        self.root_structure(".")
        self.assertIsNone(touched.select(self.b.repo, ["tests/test_x.py", "issues/backlog/a.md"]))

    def test_with_no_bundle_the_board_and_meta_still_stay_with_meta(self) -> None:
        self.b.structure("projects:\n" + project("meta", ".meta") + project("app", "."))
        for path in ("issues/backlog/a.md", ".meta/x.py"):
            with self.subTest(path=path):
                self.assertEqual(touched.select(self.b.repo, [path]), ["meta"])
        self.assertEqual(touched.select(self.b.repo, ["README.md"]), ["app"])

    def specialization_structure(self, *, declared: bool = True) -> None:
        """Commit `meta` and `pair` in one Product, `seed` in none, and `specialization` if
        `declared`, beside a bundle of every ownership.

        `seed` keeps the selection short of every Project, which would be the whole gate.
        """
        bundle = self.b.repo / touched.BUNDLE
        bundle.parent.mkdir(parents=True, exist_ok=True)
        bundle.write_text(
            "items:\n"
            "  - path: .meta/checks/\n    kind: dir\n    ownership: managed\n"
            "  - path: .meta/bundle.yaml\n    kind: file\n    ownership: managed\n"
            "  - path: stakeholders/README.md\n    kind: file\n    ownership: managed\n"
            "  - path: stakeholders/\n    kind: dir\n    ownership: portfolio\n"
            "  - path: AGENTS.md\n    source: template/AGENTS.md\n    target: AGENTS.md\n"
            "    kind: file\n    ownership: template\n"
            "  - path: CLAUDE.md\n    target: AGENTS.md\n"
            "    kind: symlink\n    ownership: symlink\n"
        )
        projects = project("meta", ".meta") + project("pair", "pair") + project("seed", "seed")
        if declared:
            projects += project("specialization", "specialization")
        self.b.structure(
            "projects:\n" + projects + "products:\n" + product("scaffold", "meta", "pair")
        )

    def test_a_change_to_what_a_portfolio_receives_selects_the_specialization(
        self,
    ) -> None:
        self.specialization_structure()
        cases = {
            ".meta/checks/x.py": ["meta", "pair", "specialization"],
            ".meta/bundle.yaml": ["meta", "pair", "specialization"],
            "template/AGENTS.md": ["meta", "pair", "specialization"],
            "stakeholders/README.md": ["meta", "pair", "specialization"],
            "issues/backlog/a.md": ["meta", "pair"],
            "pair/loop.py": ["meta", "pair"],
            ".meta/test_specialization.py": ["meta", "pair"],
            "stakeholders/p.md": ["meta", "pair"],
            "AGENTS.md": ["meta", "pair"],
            "CLAUDE.md": ["meta", "pair"],
            "seed/x.py": ["seed"],
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(touched.select(self.b.repo, [path]), expected)

    def test_where_no_specialization_is_declared_the_bundle_selects_nothing_more(
        self,
    ) -> None:
        self.specialization_structure(declared=False)
        self.assertEqual(touched.select(self.b.repo, [".meta/checks/x.py"]), ["meta", "pair"])

    def run_widget_issue(self, *, gates: list[bool]) -> None:
        """Carry an Issue that changes `widgets/x.py` to landing, under `STRUCTURE`."""
        b = self.b
        b.structure()
        b.issue("backlog", "w", "W", difficulty="easy")
        b.gates = list(gates)
        b.script(
            ("primary", quiet),
            ("secondary", quiet),
            ("primary", append("w", PLAN)),
            ("secondary", quiet),
            *(
                turn
                for n in range(len(gates) or 1)
                for turn in (("primary", write("widgets/x.py", f"{n}\n")), ("secondary", quiet))
            ),
        )
        self.assertEqual(b.loop.run(once=True), "landed")

    def test_the_loop_gates_the_projects_its_branch_touches(self) -> None:
        self.run_widget_issue(gates=[])
        self.assertEqual(self.b.gate_targets, [["meta", "pair", "widgets"]])

    def test_the_gate_at_landing_after_main_moves_selects_the_same_projects(
        self,
    ) -> None:
        def commits(repo: Path) -> None:
            write("b.txt", "main\n")(repo)
            sh(repo, "add", "b.txt")
            sh(repo, "commit", "-q", "-m", "add b.txt")

        self.b.during_gate = [commits]
        self.run_widget_issue(gates=[])
        self.assertEqual(self.b.gate_runs, 2)
        self.assertEqual(self.b.gate_targets, [["meta", "pair", "widgets"]] * 2)

    def test_a_gate_failure_names_what_was_gated(self) -> None:
        self.run_widget_issue(gates=[False, True])
        self.assertIn("`just gate meta pair widgets` fails", self.b.sent[6][1])

    def test_a_file_moved_out_of_a_project_gates_the_project_it_left(self) -> None:
        b = self.b
        b.structure()
        write("bootstraps/rust/seed/notes.md", "notes\n" * 20)(b.repo)
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "notes")
        wt = b.loop.wt
        sh(b.repo, "worktree", "add", "-q", "--detach", str(wt), "main")
        (wt / "wiki").mkdir(exist_ok=True)
        sh(wt, "mv", "bootstraps/rust/seed/notes.md", "wiki/notes.md")
        sh(wt, "commit", "-q", "-m", "move notes")
        self.assertIsNone(b.loop.run_gate("x", "in-progress"))
        self.assertEqual(b.gate_targets, [["meta", "rust-seed", "pair"]])

    def test_a_branch_that_changes_nothing_passes_without_a_gate(self) -> None:
        b = self.b
        b.structure()
        sh(b.repo, "worktree", "add", "-q", "--detach", str(b.loop.wt), "main")
        self.assertIsNone(b.loop.run_gate("x", "in-progress"))
        self.assertEqual(b.gate_runs, 0)


class GateKeysTest(unittest.TestCase):
    """The landing gate is given the keys `main` declares, and its output hides them (DR-357)."""

    SECRET = "s3cret-value-of-declared"

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)

    def gate_on_branch(
        self, *, declared: Sequence[str], branch_declares: Sequence[str] = ()
    ) -> GateFailure | GateUnrunnable | None:
        """Gate a branch under a `.env` holding `DECLARED` and `OTHER`, `declared` on `main`."""
        b = self.b
        keys = "".join(f"    - {name}\n" for name in declared)
        b.structure(STRUCTURE + ("portfolio:\n  gate_keys:\n" + keys if keys else ""))
        (b.repo / ".env").write_text(
            f'# keys\nexport DECLARED="{self.SECRET}"\nOTHER=b\nEMPTY=\n'
        )
        wt = b.loop.wt
        sh(b.repo, "worktree", "add", "-q", "--detach", str(wt), "main")
        write("widgets/x.py", "1\n")(wt)
        if branch_declares:
            more = "".join(f"    - {name}\n" for name in branch_declares)
            (wt / touched.STRUCTURE).write_text(STRUCTURE + "portfolio:\n  gate_keys:\n" + more)
        sh(wt, "add", "widgets", str(touched.STRUCTURE))
        sh(wt, "commit", "-q", "-m", "change")
        return b.loop.run_gate("x", "in-progress")

    def test_the_gate_is_given_the_declared_key_and_not_an_undeclared_one(self) -> None:
        self.assertIsNone(self.gate_on_branch(declared=["DECLARED", "MISSING", "EMPTY"]))
        self.assertEqual(self.b.gate_envs, [{"DECLARED": self.SECRET}])

    def test_a_portfolio_that_declares_nothing_gives_the_gate_nothing(self) -> None:
        self.gate_on_branch(declared=[])
        self.assertEqual(self.b.gate_envs, [{}])

    def test_a_key_declared_only_on_the_branch_is_not_given(self) -> None:
        self.gate_on_branch(declared=["DECLARED"], branch_declares=["DECLARED", "OTHER"])
        self.assertEqual(self.b.gate_envs, [{"DECLARED": self.SECRET}])

    def test_a_declared_value_the_gate_prints_is_redacted(self) -> None:
        self.b.gates = [(False, f"FAILED: key was {self.SECRET}\n")]
        failure = self.gate_on_branch(declared=["DECLARED"])
        assert failure is not None
        self.assertNotIn(self.SECRET, failure)
        self.assertIn("key was <DECLARED>", failure)

    def test_a_declared_value_in_a_step_that_could_not_run_is_redacted(self) -> None:
        self.b.gates = [(True, f"?  live: rejected key {self.SECRET}\n")]
        reason = self.gate_on_branch(declared=["DECLARED"])
        self.assertIsInstance(reason, GateUnrunnable)
        assert reason is not None
        self.assertNotIn(self.SECRET, reason)
        self.assertIn("- live: rejected key <DECLARED>", reason)

    def test_redact_replaces_a_longer_value_before_one_it_holds(self) -> None:
        self.assertEqual(redact("abcd ab", {"A": "ab", "B": "abcd"}), "<B> <A>")

    def test_the_real_gate_lays_the_keys_over_the_loops_environment(self) -> None:
        from pair import gate as real_gate

        done = subprocess.CompletedProcess([], 0, "", "")
        with mock.patch("subprocess.run", return_value=done) as run:
            real_gate(Path(), None, {})
            real_gate(Path(), ["pair"], {"DECLARED": "x"})
        self.assertEqual(run.call_args_list[0].kwargs["env"], dict(os.environ))
        self.assertEqual(
            run.call_args_list[1].kwargs["env"], {**os.environ, "DECLARED": "x"}
        )


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

    def test_notes_from_a_flight_check_leave_its_brief_intact(self) -> None:
        b = self.b
        b.stop_when_empty = True
        b.script(
            (
                "primary",
                Says("Wrote it.\n\n## Desk-check brief\n\nfake", append("big", BRIEF)),
            ),
            ("secondary", Says("**Desk-check notes.**\nChecked it.")),
        )
        b.loop.run(once=True)
        self.assertTrue(b.on_main(FLIGHT))
        landed = sh(b.repo, "show", f"main:{FLIGHT}")
        self.assertEqual(
            board.last_section(landed, "Desk-check brief"),
            "Delivered; see it in a.txt.",
        )
        self.assertEqual(board.sections(landed, "Desk-check notes"), 0)
        self.assertIn("> **secondary, flight-check turn 2**", landed)

    def test_a_flight_check_with_its_own_model_runs_its_seats_on_it(self) -> None:
        b = self.b
        b.loop.stage_models = {"flight-check": "B"}
        b.stop_when_empty = True
        b.script(("primary", append("big", BRIEF)), ("secondary", quiet))
        b.loop.run(once=True)
        self.assertEqual(b.models, [("primary", "B"), ("secondary", "B")])

    def test_a_failed_gate_in_a_flight_check_goes_to_the_primary(self) -> None:
        b = self.b
        b.gates = [False]
        b.stop_when_empty = True
        b.script(
            ("primary", append("big", BRIEF)),
            ("secondary", append("big", "\nMore.\n")),
            ("primary", quiet),
            ("primary", quiet),
            ("secondary", quiet),
        )
        b.loop.run(once=True)
        self.assertEqual(b.sent[3][0], "primary")
        self.assertIn("FAILED: test_widget", b.sent[3][1])
        self.assertTrue(b.on_main("issues/desk-check/big.md"))

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


class RestartTest(unittest.TestCase):
    """`run` re-executes itself between Issues once its own code has changed on disk."""

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)
        b = self.b
        b.issue("backlog", "first", "First", difficulty="easy")
        b.issue("backlog", "second", "Second", difficulty="easy")
        (b.repo / board.ORDER).write_text("first\nsecond\n")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "order")
        self.changes: list[bool] = []
        """Each answer of `code_changed` in turn; past the end the code is unchanged."""
        self.restarts = 0

        def changed() -> bool:
            return self.changes.pop(0) if self.changes else False

        def restart() -> None:
            self.restarts += 1

        b.loop.code_changed, b.loop.restart = changed, restart

    def test_a_changed_loop_restarts_before_the_next_issue(self) -> None:
        b = self.b
        self.changes = [True]
        b.script(*easy_turns("first"))
        self.assertEqual(b.loop.run(), "landed")
        self.assertEqual(self.restarts, 1)
        self.assertTrue(b.on_main("issues/done/first.md"))
        self.assertTrue(b.on_main("issues/backlog/second.md"))
        self.assertTrue(all("second" not in text for _, text in b.sent))
        self.assertEqual(
            [e["kind"] for e in b.events()][-2:], ["landed", "restarted"]
        )
        self.assertEqual(b.events("ended"), [])

    def test_an_unchanged_loop_works_on_in_the_same_process(self) -> None:
        b = self.b
        b.script(*easy_turns("first"), *easy_turns("second"))
        self.assertEqual(b.loop.run(), "empty")
        self.assertEqual(self.restarts, 0)
        self.assertTrue(b.on_main("issues/done/second.md"))
        self.assertEqual(b.events("restarted"), [])

    def test_a_run_that_ends_anyway_does_not_restart(self) -> None:
        b = self.b
        self.changes = [True, True]
        b.script(*easy_turns("first"))
        self.assertEqual(b.loop.run(once=True), "landed")
        b.stop_when_empty = True
        b.script(*easy_turns("second"))
        self.assertEqual(b.loop.run(), "empty")
        self.assertEqual(self.restarts, 0)
        self.assertTrue(b.on_main("issues/done/second.md"))
        self.assertEqual(b.events("restarted"), [])

    def test_the_fingerprint_follows_the_code_and_the_prompts(self) -> None:
        from pair import code_fingerprint

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        here = Path(tmp.name)
        (here / "prompts").mkdir()
        (here / "loop.py").write_text("a")
        (here / "prompts" / "primary.md").write_text("a")
        (here / "README.md").write_text("a")
        start = code_fingerprint(here)
        (here / "README.md").write_text("b")
        self.assertEqual(code_fingerprint(here), start)
        for path in (here / "loop.py", here / "prompts" / "primary.md"):
            with self.subTest(path=path.name):
                path.write_text("b")
                self.assertNotEqual(code_fingerprint(here), start)
                path.write_text("a")
                self.assertEqual(code_fingerprint(here), start)

    def test_one_ctrl_c_passed_on_by_uv_stops_and_does_not_abandon(self) -> None:
        from pair import CTRL_C_ECHO, stopper

        now = [100.0]
        stop = stopper(self.b.loop, clock=lambda: now[0])
        with contextlib.redirect_stdout(io.StringIO()):
            stop(signal.SIGINT, None)
            self.assertTrue(self.b.loop.stop_requested)
            now[0] += CTRL_C_ECHO / 2
            stop(signal.SIGINT, None)
            now[0] += CTRL_C_ECHO
            with self.assertRaises(KeyboardInterrupt):
                stop(signal.SIGINT, None)
            now[0] += CTRL_C_ECHO / 2
            stop(signal.SIGINT, None)


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

    def test_a_failed_gate_in_a_pass_goes_to_the_primary(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A")
        b.gates = [False]
        b.script(
            (
                "primary",
                both(front("a", difficulty="easy"), order("# groomed below\na\n")),
            ),
            ("secondary", append("a", "\nMore.\n")),
            ("primary", quiet),
            ("primary", quiet),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertEqual(b.sent[3][0], "primary")
        self.assertIn("FAILED: test_widget", b.sent[3][1])
        self.assertEqual(b.gate_runs, 2)

    def test_a_pass_whose_gate_could_not_run_pauses_then_lands(self) -> None:
        b = self.b
        b.issue("backlog", "a", "A")
        b.gates = [UNRUNNABLE]
        b.script(
            (
                "primary",
                both(front("a", difficulty="easy"), order("# groomed below\na\n")),
            ),
            ("secondary", quiet),
        )
        self.assertEqual(b.groomer.groom(), "paused")
        self.assertEqual(b.state(b.groomer).retry, "gate")
        sent = len(b.sent)
        self.assertEqual(b.groomer.groom(), "groomed")
        self.assertEqual(len(b.sent), sent)

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

        b.while_waiting = lambda: None
        b.before_land = [lambda _repo: None, lock]
        b.script(("primary", quiet), *land_the_issue("x"))
        self.assertEqual(b.loop.run(once=True), "paused")
        reason = b.state().paused or ""
        self.assertIn(".git/index.lock stayed", reason)
        self.assertIn("(git: ", reason)
        self.assertIn("index.lock': File exists", reason)
        (b.repo / ".git" / "index.lock").unlink()

    def test_a_lock_on_mains_ref_is_waited_out(self) -> None:
        b = self.b

        def other_holds_main(repo: Path) -> None:
            (repo / ".git" / "refs" / "heads" / "main.lock").write_text("")

        b.before_land = [lambda _repo: None, other_holds_main]
        b.script(("primary", quiet), *land_the_issue("x"))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(b.lock_waits, 1)
        self.assertTrue(b.on_main("issues/done/x.md"))

    def race_main(self) -> tuple[str, str]:
        """Play the other process's half of a landing race in the developer's checkout.

        Commits `a.txt`, `b.txt` and `r.txt` on `main`, then builds the landing
        `sha` (changes `b.txt`, adds `c.txt`, renames `r.txt` to `moved.txt`,
        which `git diff` reports under the new name alone unless told
        `--no-renames`) and the other process's commit A
        (changes `a.txt`) on it. A's merge has written A's tree and holds the
        lock on `main`'s ref; waiting for the lock finishes it by moving `main` to
        A. Answers `(sha, A)`.
        """
        b = self.b
        (b.repo / "a.txt").write_text("a\n")
        (b.repo / "b.txt").write_text("b\n")
        (b.repo / "r.txt").write_text(RENAMED)
        sh(b.repo, "add", "a.txt", "b.txt", "r.txt")
        sh(b.repo, "commit", "-q", "-m", "a, b and r")
        base = sh(b.repo, "rev-parse", "main")
        sha = commit_on(
            b.repo,
            base,
            {"b.txt": "landing\n", "c.txt": "new\n", "r.txt": None, "moved.txt": RENAMED},
        )
        other = commit_on(b.repo, base, {"a.txt": "other\n"})
        sh(b.repo, "read-tree", "-m", "-u", "HEAD", other)
        lock = b.repo / ".git" / "refs" / "heads" / "main.lock"
        lock.write_text("")

        def other_moves_main() -> None:
            lock.unlink()
            sh(b.repo, "update-ref", "refs/heads/main", other)

        b.while_waiting = other_moves_main
        return sha, other

    def test_a_ref_refusal_overtaken_by_main_is_put_back(self) -> None:
        b = self.b
        sha, _other = self.race_main()
        self.assertEqual(b.loop.land(State(slug="x", stage="todo"), sha), "moved")
        self.assertEqual(sh(b.repo, "status", "--porcelain"), "")
        self.assertEqual((b.repo / "a.txt").read_text(), "other\n")
        self.assertEqual((b.repo / "b.txt").read_text(), "b\n")
        self.assertFalse((b.repo / "c.txt").exists())
        self.assertEqual((b.repo / "r.txt").read_text(), RENAMED)
        self.assertFalse((b.repo / "moved.txt").exists())

    def test_a_put_back_keeps_unrelated_local_edits(self) -> None:
        b = self.b
        sha, _other = self.race_main()
        with (b.repo / ".gitignore").open("a") as ignore:
            ignore.write("scratch/\n")
        self.assertEqual(b.loop.land(State(slug="x", stage="todo"), sha), "moved")
        self.assertIn("scratch/", (b.repo / ".gitignore").read_text())
        self.assertEqual(sh(b.repo, "status", "--porcelain"), "M .gitignore")

    def test_a_lock_on_mains_ref_that_stays_pauses_and_says_so(self) -> None:
        b = self.b
        lock = b.repo / ".git" / "refs" / "heads" / "main.lock"

        def other_holds_main(_repo: Path) -> None:
            lock.write_text("")

        b.while_waiting = lambda: None
        b.before_land = [lambda _repo: None, other_holds_main]
        b.script(("primary", quiet), *land_the_issue("x"))
        self.assertEqual(b.loop.run(once=True), "paused")
        reason = b.state().paused or ""
        self.assertIn("refs/heads/main.lock stayed", reason)
        self.assertIn("holds the half-done landing as staged changes to ", reason)
        self.assertIn("issues/done/x.md", reason)
        self.assertIn("(git: ", reason)
        lock.unlink()

    def test_a_refusal_with_nothing_in_the_way_is_tried_again(self) -> None:
        b = self.b
        refusals = [subprocess.CompletedProcess([], 1, "", "fatal: a passing race\n")]

        def refuse_once(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
            if args[:2] == ("merge", "--ff-only") and refusals:
                return refusals.pop()
            return board.git_run(cwd, *args)

        b.script(("primary", quiet), *land_the_issue("x"))
        with mock.patch("loop.git_run", refuse_once):
            self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual((refusals, b.lock_waits), ([], 1))
        self.assertTrue(b.on_main("issues/done/x.md"))

    def test_edits_the_landing_does_not_touch_do_not_stop_it(self) -> None:
        b = self.b

        def unrelated_edits(repo: Path) -> None:
            (repo / "notes.txt").write_text("mine\n")
            with (repo / ".gitignore").open("a") as ignore:
                ignore.write("scratch/\n")

        b.before_land = [lambda _repo: None, unrelated_edits]
        b.script(("primary", quiet), *land_the_issue("x"))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(b.lock_waits, 0)
        self.assertTrue(b.on_main("issues/done/x.md"))
        self.assertEqual((b.repo / "notes.txt").read_text(), "mine\n")
        self.assertIn("scratch/", (b.repo / ".gitignore").read_text())

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
        reason = b.state().paused or ""
        self.assertIn("local edits in the way: x.txt", reason)
        self.assertIn("(git: ", reason)
        self.assertEqual(b.lock_waits, 0)

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
        codes = [code for o, code in EXIT.items() if o not in done]
        codes += [LOCKED, ENDED_FIRST, NOT_RUNNING]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertTrue(set(codes).isdisjoint({0, 1, 2}))

    def test_the_script_exits_with_its_code(self) -> None:
        from pair import EXIT, LOCKED, hold_lock

        b = Bench()
        self.addCleanup(b.close)
        script = Path(__file__).resolve().parent / "pair.py"

        def exits(*args: str) -> int:
            return subprocess.run(
                [sys.executable, str(script), *args], check=False, cwd=b.repo, capture_output=True
            ).returncode

        self.assertEqual(exits("accept"), EXIT["none"])
        self.assertEqual(exits("resume"), EXIT["none"])
        self.assertEqual(exits("accept", "nosuch"), EXIT["none"])
        lock = hold_lock(b.repo, "run.lock")
        assert lock is not None
        self.addCleanup(lock.close)
        self.assertEqual(exits("accept"), LOCKED)


class TurnLogTest(unittest.TestCase):
    """`.pair/turns.jsonl`: one row per turn, with the tool calls the harness refused."""

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)

    def rows(self) -> list[dict[str, Any]]:
        lines = (self.b.loop.dir / "turns.jsonl").read_text().splitlines()
        return [json.loads(line) for line in lines]

    def test_a_row_records_the_turns_denials(self) -> None:
        st = State(slug="x")
        self.b.loop.record(st, "primary", TurnResult(True, denied=["x=$(pwd)", "Write"]), False)
        self.b.loop.record(st, "secondary", TurnResult(True), True)
        self.assertEqual(
            [(row["denials"], row["denied"]) for row in self.rows()],
            [(2, ["x=$(pwd)", "Write"]), (0, [])],
        )

    def test_status_shows_the_denials_and_a_row_older_than_them(self) -> None:
        row = {"at": "2026-10-02T10:00:00", "slug": "x", "stage": "todo", "turn": 1,
               "role": "primary", "quiet": False, "seconds": 3.0,
               "cache_read": 1, "cache_write": 2}
        self.b.loop.dir.mkdir(parents=True, exist_ok=True)
        (self.b.loop.dir / "turns.jsonl").write_text(
            json.dumps(row) + "\n"
            + json.dumps({**row, "at": "2026-10-02T10:01:00", "turn": 2, "denials": 2}) + "\n"
        )
        lines = [line for line in status(self.b.repo).splitlines() if " x todo #" in line]
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].endswith("write 2"), lines[0])
        self.assertTrue(lines[1].endswith("write 2  denied 2"), lines[1])


class EventLogTest(unittest.TestCase):
    """`.pair/events.jsonl`: one event for each transition, written once."""

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)

    def events(self, kind: str | None = None) -> list[dict[str, Any]]:
        return self.b.events(kind)

    def kinds(self) -> list[tuple[str, str, str | None]]:
        return [(e["loop"], e["kind"], e.get("slug")) for e in self.events()]

    def test_an_easy_issue_starts_moves_and_lands(self) -> None:
        b = self.b
        b.issue("backlog", "x", "X", difficulty="easy")
        b.script(*easy_turns("x"))
        self.assertEqual(b.loop.run(once=True), "landed")
        self.assertEqual(
            self.kinds(),
            [
                ("pair", "started", "x"),
                *[("pair", "moved", "x")] * 2,
                ("pair", "gated", "x"),
                ("pair", "moved", "x"),
                ("pair", "landed", "x"),
            ],
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
                ("groom", "gated", "grooming"),
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


@unittest.skipUnless(INSPECTS, NO_PS)
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
        """An event to log later, whose publish, outside any git repository, fails unheard."""
        return lambda: append_event(
            self.repo, "pair", kind, report=lambda _: None, **fields
        )

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
        self.assertEqual(self.watch("flight", "big"), ENDED_FIRST)
        self.assertEqual(len(self.out), 3)

    def test_a_restarted_supervisor_is_still_watched(self) -> None:
        self.supervisor()
        self.later(self.emit("restarted"), self.emit("landed", slug="y"))
        self.assertEqual(self.watch("landed"), 0)
        self.assertEqual([line.split()[2] for line in self.out], ["restarted", "landed"])

    def test_a_killed_supervisor_fails_the_watch(self) -> None:
        proc = self.supervisor("groom.lock")
        self.later(proc.kill)
        self.assertEqual(self.watch("landed"), ENDED_FIRST)

    def test_no_supervisor_fails_the_watch_at_once(self) -> None:
        self.assertEqual(self.watch("landed"), NOT_RUNNING)
        gone = subprocess.Popen(["true"])
        gone.wait()
        other = subprocess.Popen(["sleep", "60"])
        self.addCleanup(other.wait)
        self.addCleanup(other.kill)
        for pid in (gone.pid, other.pid, os.getpid()):
            with self.subTest(pid=pid):
                (self.repo / ".pair" / "run.lock").write_text(f"{pid}\n")
                self.assertEqual(self.watch("landed"), NOT_RUNNING)

    def test_events_from_before_the_watch_are_not_read(self) -> None:
        self.supervisor()
        append_event(self.repo, "pair", "landed", "x")
        self.later(self.emit("ended", outcome="empty"))
        self.assertEqual(self.watch("landed"), ENDED_FIRST)

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

    def test_a_refused_seat_waits_as_refused(self) -> None:
        self.b.loop.save(
            State(slug="x", stage="todo", paused="the primary seat was refused twice: …")
        )
        self.assertIn("paused: the primary seat was refused twice", self.waiting())

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

    def test_a_wait_on_another_repository_shows_whole(self) -> None:
        self.b.issue("backlog", "a", "A", difficulty="easy", waits_on="[elsewhere:b]")
        self.b.issue("done", "b", "B")
        self.assertRegex(status(self.b.repo), r"\n  a +waits on elsewhere:b\n")

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


class PublishTest(unittest.TestCase):
    """`~/.pairs/<repo>.json`: the loop's status, published for a cockpit to read."""

    def setUp(self) -> None:
        self.b = Bench()
        self.addCleanup(self.b.close)
        self.said: list[str] = []
        self.b.loop.say = self.said.append

    def to_desk_check(self) -> str:
        """Run a `developer` Issue, `h`, to its desk check, and return the loop's outcome."""
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
        return b.loop.run()

    def published(self) -> dict[str, Any]:
        return json.loads((self.b.pairs / "developer.json").read_text())

    def test_the_file_is_the_status_view(self) -> None:
        b = self.b
        self.assertEqual(self.to_desk_check(), "desk-check")
        shown = self.published()
        self.assertEqual(shown, {"repo": str(b.repo.resolve()), **status_view(b.repo)})
        self.assertEqual([st["slug"] for st in shown["underway"]], ["h"])
        self.assertEqual([item["slug"] for item in shown["waiting"]], ["h"])
        self.assertEqual([p.name for p in b.pairs.iterdir()], ["developer.json"])
        self.assertFalse([line for line in self.said if "could not publish" in line])

    def test_an_event_alone_republishes(self) -> None:
        b = self.b
        append_event(b.repo, "pair", "x")
        (b.pairs / "developer.json").unlink()
        append_event(b.repo, "pair", "x")
        self.assertEqual(self.published()["underway"], [])

    def test_accepting_a_flight_republishes(self) -> None:
        b = self.b
        b.issue("backlog", "big", "Big", difficulty="hard")
        b.issue("done", "part", "Part", difficulty="easy", parent="big")
        b.script(("primary", append("big", BRIEF)), ("secondary", quiet))
        b.loop.run(once=True)
        self.assertEqual([item["slug"] for item in self.published()["waiting"]], ["big"])
        self.assertEqual(b.loop.accept("big"), "accepted")
        self.assertEqual(self.published()["waiting"], [])

    def test_resuming_a_flight_republishes(self) -> None:
        b = self.b
        b.issue("backlog", "big", "Big", difficulty="hard")
        b.issue("done", "part", "Part", difficulty="easy", parent="big")
        b.script(("primary", append("big", BRIEF)), ("secondary", quiet))
        b.loop.run(once=True)
        flight = b.repo / "issues/desk-check/big.md"
        flight.write_text(flight.read_text() + NOTES)
        self.assertEqual(b.loop.resume("big"), "resumed")
        self.assertEqual(self.published()["waiting"], [])
        self.assertIn("big", self.published()["counts"]["backlog"])

    def test_a_publish_failure_does_not_stop_the_loop(self) -> None:
        blocked = self.b.pairs.with_name("blocked")
        blocked.write_text("a file where the directory would be\n")
        with mock.patch.dict(os.environ, {"PAIRS_DIR": str(blocked)}):
            self.assertEqual(self.to_desk_check(), "desk-check")
        self.assertIn(f"could not publish {blocked / 'developer.json'}", "\n".join(self.said))
        self.assertEqual(self.b.state().retry, "desk-check")


class BoardTest(unittest.TestCase):
    def test_a_note_opens_its_own_section_after_any_other(self) -> None:
        text = "# Big\n" + BRIEF + NOTES
        note = "Done.\n\n## Desk-check notes\n- no"
        out = board.with_note(text, "primary, x turn 1", note)
        self.assertEqual(
            board.last_section(out, "Desk-check notes"),
            board.last_section(text, "Desk-check notes"),
        )
        self.assertEqual(board.sections(out, "Desk-check notes"), 1)
        self.assertTrue(
            out.endswith(
                "## Pair notes\n\n> **primary, x turn 1**\n>\n> Done.\n>\n"
                "> ## Desk-check notes\n> - no\n"
            )
        )

    def test_a_note_keeps_a_line_citation_as_written(self) -> None:
        # Built by concatenation so this file holds no citation of its own.
        cite = "`pair/loop.py" + ":99999`"
        text = "# T\n\nThe brief names `keep_note`.\n"
        out = board.with_note(text, "primary, x turn 1", f"See {cite} in `keep_note`.")
        self.assertTrue(out.startswith(text))
        self.assertIn(f"> See {cite} in `keep_note`.\n", out)

    def test_the_citation_steps_copy_where_a_note_section_ends(self) -> None:
        # The steps skip quoted notes, and `.meta/` cannot import `pair/`.
        # Parsed, not imported: `loaders` needs `linkml_runtime`, which these
        # tests do not carry.
        source = Path(__file__).parent.parent / ".meta/checks/citations/loaders.py"
        found = {
            node.targets[0].id: node.value
            for node in ast.parse(source.read_text()).body
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        }
        self.assertEqual(ast.literal_eval(found["NOTES"]), board.PAIR_NOTES)
        self.assertEqual(ast.literal_eval(found["NOTE_STOPS"]), NOTE_STOPS)
        heading = found["HEADING"]
        assert isinstance(heading, ast.Call)
        self.assertEqual(ast.literal_eval(heading.args[0]), board._HEADING.pattern)

    def test_notes_share_a_trailing_section_and_never_join_a_later_one(self) -> None:
        once = board.with_note("# T\n", "primary, x turn 1", "One.")
        twice = board.with_note(once, "secondary, x turn 2", "Two.")
        self.assertEqual(board.sections(twice, "Pair notes"), 1)
        self.assertIn("> One.\n\n> **secondary, x turn 2**", twice)
        for later, name in (
            ("\n## The plan\n\nDo it.\n", "The plan"),
            ("\n### Needs elaboration\n\nDo it.\n", "Needs elaboration"),
            ("\n**Needs elaboration.**\nDo it.\n", "Needs elaboration"),
        ):
            out = board.with_note(twice + later, "primary, x turn 3", "Three.")
            self.assertEqual(board.section(out, name), "Do it.")
            self.assertEqual(board.sections(out, "Pair notes"), 2)

    def test_restore_notes_puts_each_notes_section_back_and_keeps_the_rest(self) -> None:
        stops = ("Needs elaboration", "The plan")
        before = board.with_note("# T\n\nBody.\n", "primary, x turn 1", "One.")
        self.assertIs(board.restore_notes(before, before, stops), before)
        for seat in (
            "\nMine.\n",
            "\n**primary, x turn 2**\n\nCopied.\n",
            "\n## Pair notes\n\nAnother.\n",
            "\n\n",
        ):
            self.assertEqual(board.restore_notes(before, before + seat, stops), before)
        for kept in ("\n# Needs elaboration\n\nWhy?\n", "\n**The plan.**\nDo it.\n"):
            self.assertEqual(board.restore_notes(before, before + kept, stops), before + kept)
        edited = before.replace("Body.", "New body.").replace("> One.", "> Uno.")
        self.assertEqual(
            board.restore_notes(before, edited, stops), before.replace("Body.", "New body.")
        )

    def test_restore_notes_drops_a_new_section_and_returns_a_deleted_one(self) -> None:
        stops = ("The plan",)
        bare = "# T\n\nBody.\n"
        added = bare + "\n## Pair notes\n\nMine.\n\n## The plan\n\nDo it.\n"
        self.assertEqual(
            board.restore_notes(bare, added, stops), bare + "\n## The plan\n\nDo it.\n"
        )
        noted = board.with_note(bare, "primary, x turn 1", "One.")
        planned = noted + "\n## The plan\n\nDo it.\n"
        spaced = planned.replace("\n## The plan", "\n\n\n## The plan")
        self.assertEqual(board.restore_notes(planned, spaced, stops), planned)
        self.assertEqual(
            board.restore_notes(noted, bare + "\nMore body.\n", stops),
            bare + "\nMore body.\n" + noted.removeprefix(bare),
        )

    def test_added_note_is_what_a_seat_wrote_after_the_notes_and_no_edit(self) -> None:
        stops = ("Needs elaboration", "The plan")
        before = board.with_note("# T\n\nBody.\n", "primary, x turn 1", "One.")
        self.assertEqual(board.added_note(before, before, stops), "")
        for seat, note in (
            ("\nMine.\n", "Mine."),
            ("\n**primary, x turn 2**\n\nCopied.\n", "Copied."),
            ("\n> **primary, x turn 2**\n>\n> Quoted.\n>\n> Twice.\n", "Quoted.\n\nTwice."),
            ("\n## Pair notes\n\nAnother.\n", "Another."),
            ("\nMine.\n\n### Details\n\nMore.\n", "Mine.\n\n### Details\n\nMore."),
            ("\nMine.\n\n## Next\n\nMore.\n", "Mine."),
            ("\n\n", ""),
            ("\n# Needs elaboration\n\nWhy?\n", ""),
        ):
            self.assertEqual(board.added_note(before, before + seat, stops), note)
        edited = before.replace("> **primary", "> Above.\n> **primary")
        self.assertEqual(board.added_note(before, edited + "\nNew.\n", stops), "New.")
        self.assertEqual(board.added_note(before, before.replace("> One.", "> Uno."), stops), "")
        self.assertEqual(
            board.added_note("# T\n", "# T\n\n## Pair notes\n\nFirst.\n", stops), "First."
        )

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

    def test_listing_every_stage_at_once_matches_listing_each(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "b", "B")
        b.issue("backlog", "a", "A")
        b.issue("done", "z", "Z")
        (b.repo / "issues" / "done" / "old").mkdir()
        (b.repo / "issues" / "done" / "old" / "y.md").write_text("# Y\n")
        (b.repo / "issues" / "todo" / "notes.txt").write_text("not an issue\n")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "clutter")
        each = {stage: board.listed(b.repo, "main", stage) for stage in board.STAGES}
        self.assertEqual(board.listed_by_stage(b.repo, "main"), each)
        self.assertEqual(each["backlog"], ["a", "b"])

    def test_a_commit_is_read_once_and_a_moved_ref_reads_its_new_commit(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "big", "Big")
        b.issue("backlog", "a", "A", parent="big")
        b.issue("done", "b", "B", parent="big")
        b.issue("roadmap", "r", "R", parent="big")
        b.issue("todo", "t", "T")
        (b.repo / board.ORDER).write_text("big\r\n# groomed below\r\nt\r\n")
        sh(b.repo, "add", "-A")
        sh(b.repo, "commit", "-q", "-m", "order")

        def round_(ref: str) -> tuple[Any, ...]:
            return (
                board.listed_by_stage(b.repo, ref),
                board.at_ref(b.repo, ref, "backlog", "a"),
                board.order(b.repo, ref),
                board.families(b.repo, ref),
                board.show(b.repo, ref, board.ORDER),
            )

        sha = sh(b.repo, "rev-parse", "main")
        first = round_(sha)
        with mock.patch("board.subprocess.run", wraps=subprocess.run) as run:
            again = round_(sha)
        self.assertEqual(run.call_count, 0)
        self.assertEqual(again, first)
        self.assertEqual(first[3], {"big": {"a": "backlog", "b": "done"}})
        self.assertEqual(first[2], ["big", "t"])
        self.assertEqual(first[4], "big\n# groomed below\nt")
        sh(b.repo, "mv", "issues/todo/t.md", "issues/done/t.md")
        (b.repo / board.ORDER).write_text("t\n")
        sh(b.repo, "commit", "-q", "-am", "move t")
        listed, _, order, _, _ = round_("main")
        self.assertEqual((listed["todo"], listed["done"], order), ([], ["b", "t"], ["t"]))

    def test_a_ref_not_yet_made_reads_as_an_empty_board_until_it_is(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A", parent="big")
        later = "pair/later"
        self.assertEqual(
            board.listed_by_stage(b.repo, later), {stage: [] for stage in board.STAGES}
        )
        self.assertEqual(board.order(b.repo, later), [])
        self.assertIsNone(board.at_ref(b.repo, later, "backlog", "a"))
        self.assertEqual(board.families(b.repo, later), {})
        self.assertEqual(board.show(b.repo, later, board.ORDER), "")
        sh(b.repo, "branch", later, "main")
        self.assertEqual(board.listed(b.repo, later, "backlog"), ["a"])
        self.assertEqual(board.families(b.repo, later), {"big": {"a": "backlog"}})

    def test_a_blob_git_cannot_give_raises_rather_than_reading_short(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        with self.assertRaisesRegex(board.GitError, "missing"):
            board._blobs(b.repo, ["0" * 40])

    def test_head_and_dirty_reads_a_worktree_in_one_status(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        head = sh(b.repo, "rev-parse", "HEAD")
        self.assertEqual(board.head_and_dirty(b.repo), (head, False))
        (b.repo / "untracked.md").write_text("new\n")
        self.assertEqual(board.head_and_dirty(b.repo), (head, True))

    def test_waits_on_holds_an_item_back(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A", waits_on="[z]")
        b.issue("backlog", "b", "B")
        self.assertEqual(board.next_ripe(b.repo, "main"), "b")
        b.issue("done", "z", "Z")
        self.assertEqual(board.next_ripe(b.repo, "main"), "a")

    def test_a_waits_on_elsewhere_is_not_met_by_a_local_slug(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A", waits_on="[elsewhere:b]")
        b.issue("done", "b", "B")
        self.assertIsNone(board.next_ripe(b.repo, "main"))
        self.assertEqual(board.holds(b.repo, "main", "a", {"b"}, {}), ["elsewhere:b"])

    def test_a_waits_on_elsewhere_holds_with_no_local_slug(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "a", "A", waits_on="[elsewhere:b]")
        self.assertIsNone(board.next_ripe(b.repo, "main"))
        self.assertEqual(board.holds(b.repo, "main", "a", set(), {}), ["elsewhere:b"])

    def test_a_waits_on_elsewhere_does_not_order_parts(self) -> None:
        b = Bench()
        self.addCleanup(b.close)
        b.issue("backlog", "big", "Big")
        b.issue("backlog", "a", "A", parent="big", waits_on="[elsewhere:b]")
        b.issue("backlog", "b", "B", parent="big")
        self.assertEqual(board.running_order(b.repo, "main"), ["a", "b", "big"])

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
    CONFINED = Confinement(
        [Path("/r/.git/objects"), Path("/c/uv")],
        [Path("/r/.git/hooks")],
        {},
        [Path("/g/S.gpg-agent")],
    )

    def test_a_seat_loads_the_project_settings_alone(self) -> None:
        argv = command("seat prompt", self.CONFINED, model="sonnet", resume="abc")
        at = argv.index("--setting-sources")
        self.assertEqual(argv[at + 1], "project")
        self.assertIn("--strict-mcp-config", argv)
        self.assertNotIn("--disable-slash-commands", argv)
        self.assertEqual(argv[argv.index("--append-system-prompt") + 1], "seat prompt")
        self.assertEqual(argv[-4:], ["--model", "sonnet", "--resume", "abc"])

    def test_a_seat_runs_claude_unless_given_a_program(self) -> None:
        self.assertEqual(command("p", self.CONFINED)[:2], ["claude", "-p"])
        self.assertEqual(
            command("p", self.CONFINED, program=["py", "s"])[:3], ["py", "s", "-p"]
        )

    def test_bash_runs_in_a_sandbox_and_the_loops_git_commands_are_refused(self) -> None:
        argv = command("p", self.CONFINED)
        sandbox = json.loads(argv[argv.index("--settings") + 1])["sandbox"]
        self.assertIs(sandbox["enabled"], True)
        self.assertIs(sandbox["autoAllowBashIfSandboxed"], True)
        self.assertIs(sandbox["failIfUnavailable"], True)
        self.assertIs(sandbox["allowUnsandboxedCommands"], False)
        self.assertEqual(sandbox["filesystem"]["allowWrite"], ["/r/.git/objects", "/c/uv"])
        self.assertEqual(sandbox["filesystem"]["denyWrite"], ["/r/.git/hooks"])
        self.assertEqual(sandbox["network"]["allowedDomains"], ["*"])
        self.assertEqual(sandbox["network"]["allowUnixSockets"], ["/g/S.gpg-agent"])
        allowed = argv.index("--allowedTools") + 1
        self.assertEqual(argv[allowed : allowed + len(ALLOWED)], ALLOWED)
        for tool in ("Bash", "Edit", "Write", "NotebookEdit"):
            self.assertFalse([t for t in ALLOWED if t.split("(")[0] == tool], tool)
        denied = argv.index("--disallowedTools") + 1
        self.assertEqual(argv[denied : denied + len(DISALLOWED)], DISALLOWED)
        self.assertIn("Bash(git push*)", DISALLOWED)
        for rule in ("Bash(kill *)", "Bash(pkill*)", "Bash(killall*)"):
            self.assertIn(rule, DISALLOWED)

    def test_with_no_key_files_nothing_is_denied_reading(self) -> None:
        argv = command("p", self.CONFINED)
        settings = json.loads(argv[argv.index("--settings") + 1])
        self.assertEqual(list(settings), ["sandbox"])
        self.assertNotIn("denyRead", settings["sandbox"]["filesystem"])

    def test_env_names_takes_the_names_and_never_the_values(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(subprocess.run, ["rm", "-rf", str(tmp)], check=True)
        text = tmp / ".env"
        text.write_text("# c\n\nexport SOME_KEY=x\nB = y=z\nnoeq\n")
        self.assertEqual(env_names(text), {"SOME_KEY", "B"})
        binary = tmp / ".env.gpg"
        binary.write_bytes(b"\xff\xfe\x00=\x80\n")
        env_names(binary)
        locked = tmp / ".env.locked"
        locked.write_text("LOCKED=x\n")
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o600)
        if not os.access(locked, os.R_OK):
            self.assertEqual(env_names(locked), set())

    def test_env_values_reads_only_the_named_values_and_unquotes_them(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(subprocess.run, ["rm", "-rf", str(tmp)], check=True)
        text = tmp / ".env"
        text.write_text(
            "# A=no\nexport A = \"x y\"\nB='q'\nC=a=b\nD=\"\nE=unasked\nC=later\n"
        )
        self.assertEqual(
            env_values(text, ["A", "B", "C", "D", "Z"]),
            {"A": "x y", "B": "q", "C": "later", "D": '"'},
        )
        self.assertEqual(env_values(tmp / "absent", ["A"]), {})


def snapshot(root: Path) -> dict[Path, tuple[int, int, int]]:
    """Every path under `root`, with what a write to it changes."""
    return {
        p: (s.st_mtime_ns, s.st_size, s.st_ino)
        for p in [root, *root.rglob("*")]
        for s in [p.lstat()]
    }


class ConfinementTest(unittest.TestCase):
    """`confinement` lets a commit through and keeps the rest of the git common directory."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        sh(self.repo, "init", "-q", "-b", "main")
        sh(self.repo, "config", "user.email", "t@example.com")
        sh(self.repo, "config", "user.name", "t")
        sh(self.repo, "config", "commit.gpgsign", "false")
        (self.repo / "a").write_text("a\n")
        sh(self.repo, "add", "a")
        sh(self.repo, "commit", "-qm", "a")
        sh(self.repo, "branch", "dev")
        sh(self.repo, "branch", "claude/side")
        sh(self.repo, "pack-refs", "--all")
        self.wt = self.tmp / "wt"
        sh(self.repo, "worktree", "add", "-q", "-b", "pair/x", str(self.wt))
        sh(self.repo, "worktree", "add", "-q", "--detach", str(self.tmp / "other"))
        self.common = self.repo / ".git"

    def tearDown(self) -> None:
        subprocess.run(["rm", "-rf", str(self.tmp)], check=True)

    def denied(self, path: Path, deny: list[Path]) -> bool:
        return any(path.is_relative_to(d) for d in deny)

    def test_a_commit_writes_only_allowed_paths_and_none_denied(self) -> None:
        """The root itself is left out: a commit creates and removes a lock file there.

        The sandbox grants the root, and the commit leaves no entry behind.
        """
        confined = confinement(self.wt)
        before = snapshot(self.common)
        (self.wt / "b").write_text("b\n")
        sh(self.wt, "add", "b")
        sh(self.wt, "commit", "-qm", "b")
        after = snapshot(self.common)
        written = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
        self.assertEqual(
            {p for p in before if p.parent == self.common},
            {p for p in after if p.parent == self.common},
        )
        written.discard(self.common)
        self.assertTrue(written)
        for path in written:
            self.assertFalse(self.denied(path, confined.deny), path)
            self.assertTrue(any(path.is_relative_to(a) for a in confined.allow), path)

    def test_what_moves_code_or_other_branches_is_denied(self) -> None:
        confined = confinement(self.wt)
        heads = self.common / "refs" / "heads"
        for path in [
            self.common / "hooks",
            self.common / "config",
            self.common / "HEAD",
            self.common / "packed-refs",
            self.common / "index",
            heads / "main",
            heads / "dev",
            heads / "claude" / "side",
            self.common / "refs" / "tags",
            self.common / "worktrees" / "other",
        ]:
            self.assertTrue(self.denied(path, confined.deny), path)
        self.assertFalse((heads / "dev").exists(), "dev should be held only in packed-refs")
        for path in confined.allow:
            self.assertFalse(self.denied(path, confined.deny), path)
        self.assertNotIn(self.common, confined.allow)

    def test_unwritable_holds_the_confinement_and_what_the_sandbox_denies_itself(
        self,
    ) -> None:
        held = unwritable(self.wt)
        for path in confinement(self.wt).deny:
            self.assertIn(path, held)
        self.assertTrue(self.denied(self.wt / ".claude" / "skills" / "s" / "SKILL.md", held))
        self.assertFalse(self.denied(self.wt / "README.md", held))

    def test_key_files_in_every_checkout_are_denied_reading(self) -> None:
        other = self.tmp / "other"
        keys = [self.repo / ".env", self.repo / ".env.local", self.wt / ".env", other / ".env"]
        for key in keys:
            key.write_text("export SOME_KEY=x\n")
        target = self.tmp / "secrets"
        target.write_text("LINKED=y\n")
        (other / ".env.link").symlink_to(target)
        (self.wt / ".env.d").mkdir()
        (self.repo / "env").write_text("NOT_A_KEY=z\n")
        confined = confinement(self.wt)
        self.assertEqual(
            confined.unreadable, sorted([*keys, other / ".env.link", target])
        )
        self.assertEqual(confined.withheld, {"SOME_KEY", "LINKED"})
        argv = command("p", confined)
        settings = json.loads(argv[argv.index("--settings") + 1])
        self.assertEqual(
            settings["sandbox"]["filesystem"]["denyRead"],
            [str(p) for p in confined.unreadable],
        )
        self.assertEqual(
            settings["permissions"]["deny"],
            [f"Read(/{p})" for p in confined.unreadable],
        )
        self.assertTrue(all(r.startswith("Read(//") for r in settings["permissions"]["deny"]))

    def track_env_example(self) -> None:
        """Commit a `.env.example` in the checkout and the worktree; leave a `.env` untracked."""
        (self.repo / ".env.example").write_text("export TEMPLATE_ONLY=\n")
        sh(self.repo, "add", ".env.example")
        sh(self.repo, "commit", "-qm", "template")
        sh(self.wt, "checkout", "main", "--", ".env.example")
        sh(self.wt, "commit", "-qm", "template")
        for root in [self.repo, self.wt]:
            (root / ".env").write_text("export SOME_KEY=x\n")

    def test_a_tracked_env_file_that_matches_its_commit_is_readable(self) -> None:
        self.track_env_example()
        confined = confinement(self.wt)
        self.assertEqual(confined.unreadable, sorted([self.repo / ".env", self.wt / ".env"]))
        self.assertEqual(confined.withheld, {"SOME_KEY"})
        argv = command("p", confined)
        settings = json.loads(argv[argv.index("--settings") + 1])
        denied = [
            *settings["sandbox"]["filesystem"]["denyRead"],
            *settings["permissions"]["deny"],
        ]
        self.assertFalse([d for d in denied if ".env.example" in d], denied)

    def test_a_tracked_env_file_changed_on_disk_is_denied(self) -> None:
        """`EDITED_KEY` is not `SOME_KEY`, which the untracked `.env` files withhold anyway."""
        self.track_env_example()
        example = self.wt / ".env.example"
        example.write_text("EDITED_KEY=x\n")
        confined = confinement(self.wt)
        self.assertIn(example, confined.unreadable)
        self.assertIn("EDITED_KEY", confined.withheld)
        sh(self.wt, "add", ".env.example")
        self.assertIn(example, confinement(self.wt).unreadable)
        sh(self.wt, "checkout", "HEAD", "--", ".env.example")
        self.assertNotIn(example, confinement(self.wt).unreadable)
        example.write_text("EDITED_KEY=x\n")
        sh(self.wt, "update-index", "--skip-worktree", ".env.example")
        confined = confinement(self.wt)
        self.assertIn(example, confined.unreadable)
        self.assertIn("EDITED_KEY", confined.withheld)

    def test_a_tracked_env_file_a_clean_filter_rewrites_is_denied(self) -> None:
        """The history holds what the filter wrote, as git-crypt's ciphertext, not the disk's bytes.

        `git diff` reports such a file unchanged, so only hashing it with
        `--no-filters` tells the two apart.
        """
        sh(self.repo, "config", "filter.rot.clean", "tr a-z n-za-m")
        sh(self.repo, "config", "filter.rot.smudge", "cat")
        (self.wt / ".gitattributes").write_text(".env.production filter=rot\n")
        secret = self.wt / ".env.production"
        secret.write_text("SEALED_KEY=plain\n")
        sh(self.wt, "add", ".gitattributes", ".env.production")
        sh(self.wt, "commit", "-qm", "sealed")
        self.assertEqual(sh(self.wt, "status", "--porcelain").strip(), "")
        confined = confinement(self.wt)
        self.assertIn(secret, confined.unreadable)
        self.assertEqual(confined.withheld, {"SEALED_KEY"})

    def test_a_tracked_env_symlink_is_denied_with_its_target(self) -> None:
        target = self.tmp / "secrets"
        target.write_text("LINKED=y\n")
        (self.wt / ".env.link").symlink_to(target)
        sh(self.wt, "add", ".env.link")
        sh(self.wt, "commit", "-qm", "link")
        confined = confinement(self.wt)
        self.assertIn(self.wt / ".env.link", confined.unreadable)
        self.assertIn(target, confined.unreadable)
        self.assertEqual(confined.withheld, {"LINKED"})

    def test_with_no_key_files_nothing_is_withheld(self) -> None:
        confined = confinement(self.wt)
        self.assertEqual(confined.unreadable, [])
        self.assertEqual(confined.withheld, set())

    def test_uv_tools_and_cargo_binaries_stay_out_of_reach(self) -> None:
        confined = confinement(self.wt)
        cargo = Path(os.environ.get("CARGO_HOME", Path.home() / ".cargo"))
        self.assertNotIn(cargo, confined.allow)
        self.assertFalse(any((cargo / "bin").is_relative_to(a) for a in confined.allow))
        if "UV_TOOL_DIR" in confined.env:
            tools = Path(confined.env["UV_TOOL_DIR"])
            self.assertTrue(any(tools.is_relative_to(a) for a in confined.allow))

    def seat_git(self, confined: Confinement, *args: str) -> str:
        """What `git config args` reads in the worktree under the seat's environment."""
        gitconfig = self.tmp / "seat.gitconfig"
        gitconfig.write_text(confined.gitconfig)
        return subprocess.run(
            ["git", "config", *args],
            cwd=self.wt,
            env={**os.environ, **confined.env, "GIT_CONFIG_GLOBAL": str(gitconfig)},
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def developer(self, text: str) -> None:
        """Make `text` the developer's global git config, with no system config."""
        path = self.tmp / "developer.gitconfig"
        path.write_text(text)
        patched = mock.patch.dict(
            os.environ, {"GIT_CONFIG_GLOBAL": str(path), "GIT_CONFIG_NOSYSTEM": "1"}
        )
        patched.start()
        self.addCleanup(patched.stop)

    def test_signature_display_is_off_and_the_developers_settings_are_kept(self) -> None:
        self.developer("[log]\n\tshowSignature = true\n[core]\n\tabbrev = 12\n")
        confined = confinement(self.wt)
        self.assertEqual(self.seat_git(confined, "--bool", "log.showSignature"), "false")
        self.assertEqual(self.seat_git(confined, "core.abbrev"), "12")

    def test_a_relative_global_config_is_still_included(self) -> None:
        self.developer("[core]\n\tabbrev = 12\n")
        below = self.tmp / "below"
        below.mkdir()
        self.addCleanup(os.chdir, Path.cwd())
        os.chdir(below)
        with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": "../developer.gitconfig"}):
            confined = confinement(self.wt)
        self.assertEqual(self.seat_git(confined, "core.abbrev"), "12")

    def test_the_seats_git_runs_seat_gpg_in_front_of_the_gpg_git_would_run(self) -> None:
        both = "[gpg]\n\tprogram = /a/gpg\n[gpg \"openpgp\"]\n\tprogram = /b/gpg\n"
        self.developer(both)
        confined = confinement(self.wt)
        self.assertEqual(confined.env["PAIR_SEAT_GPG"], "/b/gpg")
        for key in ("gpg.program", "gpg.openpgp.program"):
            self.assertEqual(self.seat_git(confined, key), str(SEAT_GPG), key)
        self.developer("[gpg \"openpgp\"]\n\tprogram = /b/gpg\n[gpg]\n\tprogram = /a/gpg\n")
        self.assertEqual(confinement(self.wt).env["PAIR_SEAT_GPG"], "/a/gpg")

    def test_a_seat_started_by_a_seat_keeps_the_real_gpg(self) -> None:
        self.developer(f"[gpg]\n\tprogram = {SEAT_GPG}\n")
        with mock.patch.dict(os.environ, {"PAIR_SEAT_GPG": "/real/gpg"}):
            self.assertEqual(confinement(self.wt).env["PAIR_SEAT_GPG"], "/real/gpg")

    def test_without_a_gpg_the_seat_gets_no_gpg_program(self) -> None:
        self.developer("")
        with mock.patch("seats.shutil.which", return_value=None):
            confined = confinement(self.wt)
        self.assertNotIn("PAIR_SEAT_GPG", confined.env)
        self.assertNotIn("gpg", confined.gitconfig)

    def test_seat_gpg_runs_the_real_gpg_with_the_always_trust_model(self) -> None:
        stand_in = self.tmp / "gpg"
        stand_in.write_text('#!/bin/sh\necho "$@"\n')
        stand_in.chmod(0o755)
        ran = subprocess.run(
            [str(SEAT_GPG), "a", "b c"],
            check=False,
            env={**os.environ, "PAIR_SEAT_GPG": str(stand_in)},
            capture_output=True,
            text=True,
        )
        self.assertEqual(ran.stdout, "--trust-model always a b c\n")
        env = {k: v for k, v in os.environ.items() if k != "PAIR_SEAT_GPG"}
        unset = subprocess.run(
            [str(SEAT_GPG)], check=False, env=env, capture_output=True, text=True
        )
        self.assertNotEqual(unset.returncode, 0)

    def test_the_main_checkout_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            confinement(self.repo)

    def test_gnupg_is_reachable_only_for_signing_and_never_its_configuration(self) -> None:
        self.assertEqual(confinement(self.wt).sockets, [])
        gnupg = self.tmp / "gnupg"
        gnupg.mkdir()
        for name in ("gpg-agent.conf", "trustdb.gpg", "S.gpg-agent", "trustdb.gpg.lock"):
            (gnupg / name).write_text("")
        sh(self.repo, "config", "commit.gpgsign", "true")
        with mock.patch.dict(os.environ, {"GNUPGHOME": str(gnupg)}):
            confined = confinement(self.wt)
        self.assertIn(gnupg, confined.allow)
        self.assertIn(gnupg / "S.gpg-agent", confined.sockets)
        for name in ("gpg-agent.conf", "gpg.conf", "trustdb.gpg", "private-keys-v1.d"):
            self.assertTrue(self.denied(gnupg / name, confined.deny), name)
        for name in versioned_gpg_conf():
            self.assertTrue(self.denied(gnupg / name, confined.deny), name)
        for name in ("S.gpg-agent", "trustdb.gpg.lock", ".#lk0x1.host.1"):
            self.assertFalse(self.denied(gnupg / name, confined.deny), name)


STAND_IN = """\
import json, os, sys, time
from pathlib import Path

script = json.loads(Path(os.environ["STAND_IN_SCRIPT"]).read_text())


def play(steps):
    for step in steps:
        if "sleep" in step:
            time.sleep(step["sleep"])
        elif "write" in step:
            Path(step["write"]).write_text("late\\n")
        elif "env" in step:
            Path(step["to"]).write_text(os.environ.get(step["env"], ""))
        else:
            print(json.dumps(step["emit"]), flush=True)


play(script["start"])
turns = iter(script["turns"])
for _line in sys.stdin:
    play(next(turns, []))
"""
"""A `claude` that plays scripted stream-json: `start` at once, then a list of steps per message."""


def task(subtype: str, task_id: str, description: str = "") -> dict[str, object]:
    return {"emit": {"type": "system", "subtype": subtype, "task_id": task_id,
                     "description": description, "session_id": "s1"}}


def result(
    text: str, output: int = 1, denials: Sequence[object] = ()
) -> dict[str, object]:
    event: dict[str, object] = {
        "type": "result", "subtype": "success", "is_error": False, "result": text,
        "session_id": "s1", "total_cost_usd": 0.5,
        "usage": {"input_tokens": 1, "output_tokens": output},
    }
    if denials:
        event["permission_denials"] = list(denials)
    return {"emit": event}


def denial(tool: str, **tool_input: object) -> dict[str, object]:
    """One entry of `permission_denials`, as Claude Code lists a refused tool call."""
    return {"tool_name": tool, "tool_use_id": "toolu_1", "tool_input": tool_input}


class ClaudeSeatTest(unittest.TestCase):
    """`ClaudeSeat.send` returns only when the session is idle, against a stand-in `claude`.

    The stand-in is a script run by this interpreter, not a `#!` file on
    `PATH`. On macOS under load, exec'ing a newly written executable took
    several times as long, enough to stall a 1 s turn.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(subprocess.run, ["rm", "-rf", str(self.tmp)], check=True)
        repo = self.tmp / "repo"
        repo.mkdir()
        sh(repo, "init", "-q", "-b", "main")
        sh(repo, "config", "user.email", "t@example.com")
        sh(repo, "config", "user.name", "t")
        sh(repo, "config", "commit.gpgsign", "false")
        sh(repo, "commit", "-q", "--allow-empty", "-m", "a")
        self.wt = self.tmp / "wt"
        sh(repo, "worktree", "add", "-q", "-b", "pair/x", str(self.wt))
        self.stand_in = self.tmp / "stand_in.py"
        self.stand_in.write_text(STAND_IN)
        self.script = self.tmp / "script.json"
        self.log = self.tmp / "log"
        patched = mock.patch.dict(os.environ, {"STAND_IN_SCRIPT": str(self.script)})
        patched.start()
        self.addCleanup(patched.stop)

    def seat(self, start: list[object], *turns: list[object], timeout: float = 30) -> ClaudeSeat:
        self.script.write_text(json.dumps({"start": start, "turns": list(turns)}))
        seat = ClaudeSeat(
            "primary", self.wt, "p", self.log, timeout=timeout,
            program=[sys.executable, str(self.stand_in)],
        )
        self.addCleanup(seat.stop)
        return seat

    def started(self, seat: ClaudeSeat, lines: int = 1) -> None:
        """Wait until the stand-in has written `lines` lines, so its start-up is not timed."""
        deadline = time.monotonic() + 10
        while seat.lines.qsize() < lines and time.monotonic() < deadline:
            time.sleep(0.01)
        if seat.lines.qsize() < lines:
            self.fail(f"the stand-in wrote {seat.lines.qsize()} of {lines} lines in 10 s")

    def logged(self) -> list[dict[str, Any]]:
        lines = (self.log / "primary.jsonl").read_text().splitlines()
        return [json.loads(line) for line in lines]

    def test_a_seat_given_no_program_starts_claude(self) -> None:
        """The seat's own command is caught; the `git` that `confinement` runs is not."""

        class StartedError(Exception):
            pass

        real = subprocess.Popen
        argvs: list[list[str]] = []

        def popen(argv: list[str], **kwargs: Any) -> subprocess.Popen[Any]:
            if "stream-json" not in argv:
                return real(argv, **kwargs)
            argvs.append(argv)
            raise StartedError

        with mock.patch.object(subprocess, "Popen", popen), self.assertRaises(StartedError):
            ClaudeSeat("primary", self.wt, "p", self.log)
        self.assertEqual(argvs[0][:2], ["claude", "-p"])

    def test_a_seat_starts_without_the_variables_its_key_files_name(self) -> None:
        (self.wt / ".env").write_text("# c\nexport SOME_KEY=x\n")
        real = subprocess.Popen
        envs: list[dict[str, str]] = []

        class StartedError(Exception):
            pass

        def popen(argv: list[str], **kwargs: Any) -> subprocess.Popen[Any]:
            if "stream-json" not in argv:
                return real(argv, **kwargs)
            envs.append(kwargs["env"])
            raise StartedError

        keys = {"SOME_KEY": "x", "OTHER": "y", "ANTHROPIC_API_KEY": "k"}
        with (
            mock.patch.dict(os.environ, keys),
            mock.patch.object(subprocess, "Popen", popen),
            self.assertRaises(StartedError),
        ):
            ClaudeSeat("primary", self.wt, "p", self.log)
        self.assertNotIn("SOME_KEY", envs[0])
        self.assertNotIn("ANTHROPIC_API_KEY", envs[0])
        self.assertEqual(envs[0]["OTHER"], "y")

    def test_a_seat_starts_without_the_rustc_wrapper_its_sandbox_refuses(self) -> None:
        seen = self.tmp / "seen"
        with mock.patch.dict(os.environ, {"RUSTC_WRAPPER": "sccache"}):
            seat = self.seat([], [{"env": "RUSTC_WRAPPER", "to": str(seen)}, result("ok")])
        turn = seat.send("go")
        self.assertTrue(turn.ok, turn.error)
        self.assertEqual(seen.read_text(), "")

    def test_the_seat_reads_its_git_config_from_a_file_outside_the_worktree(self) -> None:
        seen = self.tmp / "seen"
        seat = self.seat([], [{"env": "GIT_CONFIG_GLOBAL", "to": str(seen)}, result("ok")])
        turn = seat.send("go")
        self.assertTrue(turn.ok, turn.error)
        gitconfig = Path(seen.read_text())
        self.assertEqual(gitconfig, self.log / "primary.gitconfig")
        self.assertIn("showSignature = false", gitconfig.read_text())

    def test_a_background_task_holds_the_turn_until_the_session_is_idle(self) -> None:
        seat = self.seat(
            [],
            [
                task("task_started", "t1", "Run the pair gate"),
                result("first", output=2, denials=[denial("Bash", command="a=$(pwd)")]),
                {"sleep": 0.3},
                task("task_notification", "t1"),
                {"write": "late.txt"},
                result("second", output=3, denials=[denial("Write", file_path="/f")]),
            ],
        )
        turn = seat.send("go")
        self.assertTrue(turn.ok, turn.error)
        self.assertEqual(turn.text, "second")
        self.assertTrue((self.wt / "late.txt").exists())
        self.assertEqual(turn.usage, {"input_tokens": 2, "output_tokens": 5})
        self.assertEqual(turn.denied, ["a=$(pwd)", "Write"])
        self.assertEqual(seat.tasks, {})
        kinds = [(e["type"], e.get("result") or e.get("text", "")) for e in self.logged()]
        sent = [text for kind, text in kinds if kind == "pair/sent"]
        self.assertEqual(len(sent), 2)
        self.assertIn("`t1`: Run the pair gate", sent[1])
        self.assertLess(kinds.index(("result", "first")), kinds.index(("pair/sent", sent[1])))
        readable = (self.log / "primary.log").read_text()
        self.assertIn("[task t1 started] Run the pair gate", readable)
        self.assertIn("[task t1 ended]", readable)

    def test_a_turn_reports_the_tool_calls_the_harness_refused(self) -> None:
        refused = [
            denial("Bash", command="x=$(git rev-parse HEAD) && echo $x"),
            denial("Write", file_path="/elsewhere"),
            denial("Bash", description="no command"),
            {"tool_name": "Bash", "tool_input": "x=$(pwd)"},
            "not an entry",
        ]
        seat = self.seat([], [result("one", denials=refused)], [result("two")])
        self.assertEqual(
            seat.send("go").denied,
            ["x=$(git rev-parse HEAD) && echo $x", "Write", "Bash", "Bash", "?"],
        )
        self.assertEqual(seat.send("again").denied, [])

    def test_a_result_waiting_before_the_message_is_not_the_turns(self) -> None:
        seat = self.seat([result("stale")], [result("answer")])
        self.started(seat)
        turn = seat.send("go")
        self.assertTrue(turn.ok, turn.error)
        self.assertEqual(turn.text, "answer")
        kinds = [e["type"] for e in self.logged()]
        self.assertEqual(kinds, ["result", "pair/sent", "result"])

    def test_a_task_started_in_waiting_output_still_holds_the_turn(self) -> None:
        seat = self.seat(
            [task("task_started", "t2"), result("stale")],
            [result("early"), task("task_notification", "t2"), result("answer")],
        )
        self.started(seat, lines=2)
        turn = seat.send("go")
        self.assertEqual(turn.text, "answer")

    def test_a_task_that_never_finishes_times_the_turn_out(self) -> None:
        init = {"emit": {"type": "system", "subtype": "init", "session_id": "s1"}}
        seat = self.seat([init, task("task_started", "t9", "Serve")], [], timeout=1)
        self.started(seat, lines=2)
        turn = seat.send("go")
        self.assertFalse(turn.ok)
        self.assertIn("t9", turn.error or "")
        self.assertIsNotNone(seat.proc.poll())


class GateLintTest(unittest.TestCase):
    """The gate's ruff step, over a directory of its own rather than `pair/`."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_a_finding_fails_the_step_with_one_line_for_it(self) -> None:
        (self.tmp / "unused.py").write_text("import os\n")
        passed, lines = gate.lint(self.tmp)
        self.assertFalse(passed)
        self.assertEqual(lines[0], "x  ruff (1)")
        self.assertEqual(len(lines), 2)
        self.assertIn("F401", lines[1])

    def test_a_clean_directory_passes_with_one_line(self) -> None:
        (self.tmp / "clean.py").write_text('"""Nothing to find."""\n')
        self.assertEqual(gate.lint(self.tmp), (True, [f"ok ruff — {self.tmp.name}/"]))

    def test_the_gate_exits_non_zero_when_only_the_ruff_step_fails(self) -> None:
        """With no test modules to run, the ruff step's verdict alone sets the exit code."""
        for passed, code in ((False, 1), (True, 0)):
            with (
                mock.patch.object(gate, "HERE", self.tmp),
                mock.patch.object(gate, "lint", return_value=(passed, ["ruff said"])),
                mock.patch.object(sys, "argv", ["gate.py"]),
                mock.patch.object(sys, "path", list(sys.path)),
                contextlib.redirect_stdout(io.StringIO()) as out,
            ):
                self.assertEqual(gate.main(), code)
            self.assertEqual(out.getvalue(), "ruff said\n")


if __name__ == "__main__":
    unittest.main()
