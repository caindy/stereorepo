"""The supervisor: a deterministic state machine over one issue at a time.

The seats never learn this machine exists. After each turn the loop observes
the working tree (where the issue file sits, whether anything changed, and
whether the gate passes) and decides what happens next:

- A turn that changes nothing is *quiet*: that seat accepts the stage as it
  stands. A turn that changes something makes its author the only seat that
  has accepted the new state. When both seats have accepted the same state
  and the stage's requirement holds, the stage advances.
- An issue whose file gains a `Needs elaboration` section, or whose stage runs
  past its round cap, goes back to `issues/backlog/` on `main` with that
  section, and sits out until the developer answers it.
- Otherwise the other seat takes the next turn.

The loop takes the next issue in running order as it stands, a ripe Flight
first, and starts it by moving its file from `issues/backlog/` to
`issues/underway/` in a commit of its own on `main`, so the board there shows
what is being worked. Landing moves it on out of `underway/`. Grooming is a separate command: a pass takes up the backlog issues that
are not groomed (no valid difficulty, and no `Needs elaboration` section) and
runs the same turns on its own branch, `pair/grooming`, with no issue file, in
its own worktree, `worktrees/groom`, so it runs alongside an Issue. It
ends when both seats accept a backlog where each of those issues has a
difficulty and `issues/backlog/ORDER` places it without moving the rest, and
lands as one commit. An issue no pass has groomed is groomed by its own backlog
stage. Whichever of the two lands second rebases onto the other, and
`ORDER` never stops it (`Loop.rebase`).

An issue with children, which name it in `parent:`, is a Flight. Splitting a
`hard` issue makes one, and the Flight lands back in `issues/backlog/`, not
ripe while any child is outside `issues/done/`. Once the last child lands, the
loop takes the Flight through a Flight check, a stage of its own whose file
sits in `underway/`: the seats check its "Done when" on `main`, and either write each gap
as a new child, which lands and leaves the Flight waiting in `backlog/`, or write a
`## Desk-check brief` into the Flight file, which lands it in `desk-check/`.

A Flight's desk check does not hold the loop, since its parts are already on
`main`. The developer answers it in their own checkout while the loop works on:
`accept <slug>` moves it to `done/`, and `resume <slug>` takes the
`## Desk-check notes` they wrote after its latest brief back to `backlog/`.
There the Flight is ripe again, and its next check owes children: one per note,
listed in a `## Desk-check children` section, which marks the notes answered.
"""

from __future__ import annotations

import dataclasses
import json
import os
import signal
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import board
from board import git, git_ok, git_run
from seats import Seat, TurnResult

ROLES = ("primary", "secondary")
ROUND_CAP = {"easy": 4, "medium": 8, "developer": 8, "hard": 4, None: 4}
GROOMING = "grooming"
"""The slug and the stage of a grooming pass, which has no issue file."""
FLIGHT_CHECK = "flight-check"
"""The stage of a Flight whose children have all landed. Its file sits in `underway/`."""
BRIEF = "Desk-check brief"
NOTES = "Desk-check notes"
CHILDREN = "Desk-check children"
DIFF_LIMIT = 40_000
GATE_TAIL = 6_000
DELIVER_TAIL = 2_000
"""Less than `GATE_TAIL`: a failed delivery's tail goes into a pause reason, which is also notified."""
LAND_TRIES = 5
"""How many times a landing goes round when the other process lands first."""
LOCK_WAIT = 0.5
"""Seconds to wait for the other process to let go of the checkout's index lock."""
RESTARTED = (
    "(Your session was restarted after an interruption. The working tree is as you "
    "left it; check `git status` and carry on.)\n\n"
)

SeatFactory = Callable[[str, Path, "str | None"], Seat]
Gate = Callable[[Path], "tuple[bool, str]"]
Deliver = Callable[[Path], "tuple[bool, str] | None"]


@dataclass
class State:
    """Everything the loop carries across restarts. Lives in `.pair/state.json`."""

    slug: str
    stage: str = "backlog"
    turn: int = 0
    next_role: str = "primary"
    approvals: list[str] = field(default_factory=list)
    head: str = ""
    seen: dict[str, str] = field(default_factory=dict)
    sessions: dict[str, str] = field(default_factory=dict)
    seats_used: list[str] = field(default_factory=list)
    note: str = ""
    paused: str | None = None
    retry: str | None = None
    kick_text: str | None = None
    in_turn: str | None = None
    base: str = ""
    targets: list[str] = field(default_factory=list)
    rerank: bool = False


def runtime_dir(repo: Path, kind: str) -> Path:
    """Where a loop of `kind` keeps its state, seat sessions, pids and logs.

    The loop that works Issues keeps them in `.pair/`, and a grooming pass in
    `.pair/groom/`, so the two run at once without reading each other's.
    """
    return repo / ".pair" if kind == "pair" else repo / ".pair" / kind


def groom_targets(repo: Path) -> frozenset[str]:
    """The Issues a grooming pass underway took up, which the loop leaves alone.

    A paused pass is still underway, so its targets count until it lands.
    """
    path = runtime_dir(repo, "groom") / "state.json"
    if not path.is_file():
        return frozenset()
    return frozenset(json.loads(path.read_text()).get("targets", []))


def other(role: str) -> str:
    return ROLES[1 - ROLES.index(role)]


def home(stage: str) -> str:
    """The directory under `issues/` that holds an issue in `stage`.

    An issue in its backlog stage or its Flight check sits in `underway/`, on
    `main` as on its branch, so the board shows what is being worked and
    nothing that edits the backlog can edit it.
    """
    return "underway" if stage in ("backlog", FLIGHT_CHECK) else stage


class Loop:
    """Runs issues from `issues/backlog/` on `main` through a pair of seats.

    A loop of kind `pair` works Issues in `worktrees/pair`, and one of kind
    `groom` runs grooming passes in `worktrees/groom`. Each holds its own
    state (`runtime_dir`), so one of each can run at once.
    """

    def __init__(
        self,
        repo: Path,
        seat_factory: SeatFactory,
        gate: Gate,
        notify: Callable[[str], None],
        *,
        prompts: Path,
        main: str = "main",
        push: bool = False,
        provision: Callable[[Path], None] | None = None,
        deliver: Deliver | None = None,
        say: Callable[[str], None] = print,
        round_cap: int | None = None,
        kind: str = "pair",
    ) -> None:
        self.repo = repo
        self.kind = kind
        self.wt = repo / "worktrees" / kind
        self.tree = f"worktrees/{kind}"
        self.dir = runtime_dir(repo, kind)
        self.seat_factory = seat_factory
        self.gate = gate
        self.notify = notify
        self.prompts = prompts
        self.main = main
        self.push = push
        self.provision = provision
        self.deliver = deliver
        self.say = say
        self.round_cap = round_cap
        self.seat_command = "claude"
        self.stop_requested = False
        self.seats: dict[str, Seat] = {}

    # --- state ---------------------------------------------------------------

    @property
    def state_file(self) -> Path:
        return self.dir / "state.json"

    def load(self) -> State | None:
        if not self.state_file.is_file():
            return None
        return State(**json.loads(self.state_file.read_text()))

    def save(self, st: State) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(dataclasses.asdict(st), indent=1))

    def clear(self) -> None:
        self.state_file.unlink(missing_ok=True)

    def pause(self, st: State, reason: str, retry: str | None) -> str:
        st.paused, st.retry = reason, retry
        self.save(st)
        self.notify(f"{st.slug}: {reason}")
        self.say(f"paused: {reason}")
        return "paused"

    # --- entry points ----------------------------------------------------------

    def run(self, once: bool = False, flight: str | None = None) -> str:
        """Work issues until the backlog empties or the developer is needed.

        It never grooms. A grooming pass may run alongside it in its own
        worktree, and the loop does not take up an Issue the pass targets.

        A turn cut short by the supervisor dying belongs to its seat: a restart
        gives it back to that seat, and does not mistake its leftovers for the
        developer's edits.

        With `flight`, only that Flight and the Issues below it are worked,
        read again from `main` before each pick so that children written during
        the run join it. The run ends when the Flight lands in `desk-check/`.
        """
        self.ensure_worktree()
        self.reap()
        self.discard_old_pass()
        st = self.load() or self.adopt()
        if flight is not None:
            refusal = self.flight_refusal(flight, st)
            if refusal:
                self.say(refusal)
                return "refused"
        while True:
            if st is None:
                within = None
                if flight is not None:
                    below = board.descendants(self.repo, self.main, flight)
                    within = frozenset(below | {flight})
                slug = board.next_ripe(
                    self.repo, self.main, skip=groom_targets(self.repo), within=within
                )
                if slug is None:
                    self.say(self.nothing_ripe(flight))
                    return "empty"
                kids = board.children(self.repo, self.main, slug)
                st = self.start(
                    State(slug=slug, stage=FLIGHT_CHECK if kids else "backlog")
                )
                if st is None:
                    return "paused"
            elif not st.base:
                st = self.start(st)
                if st is None:
                    return "paused"
            elif st.retry == "desk-check":
                self.say(
                    f"{st.slug} is waiting for your desk check: "
                    "`just pair-accept` or `just pair-resume`"
                )
                return "desk-check"
            outcome = self.work(st)
            if outcome in ("paused", "stopped") or once:
                return outcome
            if flight in board.listed(self.repo, self.main, "desk-check"):
                self.say(
                    f"{flight} is waiting for your desk check: "
                    f"`just pair-accept {flight}` or `just pair-resume {flight}`"
                )
                return "desk-check"
            st = None

    def adopt(self) -> State | None:
        """An unstarted state for the issue in `underway/` on `main`, if there is one.

        A supervisor that died after landing an issue's move to `underway/`, but
        before saving its state, leaves the file there and no state. The issue
        can only be in its backlog stage or its Flight check then, since the
        later stages live on its branch alone.
        """
        underway = board.listed(self.repo, self.main, "underway")
        if not underway:
            return None
        slug = underway[0]
        kids = board.children(self.repo, self.main, slug)
        return State(slug=slug, stage=FLIGHT_CHECK if kids else "backlog")

    def flight_refusal(self, flight: str, st: State | None) -> str | None:
        """Why `run` cannot work `flight` from here, or None when it can."""
        if flight in board.listed(self.repo, self.main, "desk-check"):
            return (
                f"{flight} is waiting for your desk check: "
                f"`just pair-accept {flight}` or `just pair-resume {flight}`"
            )
        queued = board.listed(self.repo, self.main, "backlog") + board.listed(
            self.repo, self.main, "underway"
        )
        if flight not in queued or not board.children(self.repo, self.main, flight):
            return f"{flight} is not a Flight in issues/backlog/ or issues/underway/"
        below = board.descendants(self.repo, self.main, flight)
        if st is not None and st.slug != flight and st.slug not in below:
            finish = (
                "`just pair-accept` or `just pair-resume`"
                if st.retry == "desk-check"
                else "`just pair`"
            )
            return (
                f"{st.slug} is underway and is not part of {flight}; "
                f"finish it with {finish} first"
            )
        return None

    def nothing_ripe(self, flight: str | None) -> str:
        """What `run` says when no issue it may work is ripe."""
        if flight is None:
            return "backlog is empty (or nothing in it is ripe)"
        desk = set(board.listed(self.repo, self.main, "desk-check"))
        kin = board.families(self.repo, self.main)
        below = board.descendants(self.repo, self.main, flight)
        held = sorted(slug for slug in below & desk if kin.get(slug))
        if held:
            return f"nothing in {flight} is ripe; it waits on the desk check of " + (
                ", ".join(held)
            )
        return f"nothing in {flight} is ripe"

    def groom(self, rerank: bool = False) -> str:
        """Groom the backlog issues that are not groomed, and place them in `ORDER`.

        With `rerank`, the pass ranks the whole order below the marker again.
        A pass underway resumes with the targets and mode it started with. A
        pass does not start when there is nothing to groom, place or rerank.
        It runs in its own worktree, so an Issue may be underway meanwhile;
        that Issue is in `underway/`, where no pass takes it up.
        """
        self.ensure_worktree()
        self.reap()
        self.discard_old_pass()
        st = self.load()
        if st is not None:
            if rerank != st.rerank:
                self.say(
                    "resuming the grooming pass already underway, "
                    f"{'with' if st.rerank else 'without'} --rerank as it started"
                )
            return self.work(st)
        targets = board.to_groom(self.repo, self.main)
        if not (targets or board.unnamed(self.repo, self.main) or rerank):
            self.say("nothing to groom")
            return "nothing"
        st = self.start(
            State(slug=GROOMING, stage=GROOMING, targets=targets, rerank=rerank)
        )
        return "paused" if st is None else self.work(st)

    def discard_old_pass(self) -> None:
        """Drop a grooming pass left paused in `worktrees/pair` by an older loop.

        Before passes had their own worktree, a pass kept its state in
        `.pair/state.json` and its branch, `pair/grooming`, in `worktrees/pair`.
        Nothing it did had landed, and a pass is cheap to run again, so it is
        dropped: the branch is freed for `worktrees/groom` to check out, and
        `.pair/state.json` for an Issue.
        """
        old = runtime_dir(self.repo, "pair") / "state.json"
        if not old.is_file() or json.loads(old.read_text()).get("stage") != GROOMING:
            return
        tree = self.repo / "worktrees" / "pair"
        if (tree / ".git").exists():
            git(tree, "checkout", "-q", "--detach", "--force", self.main)
        git(self.repo, "branch", "-q", "-D", f"pair/{GROOMING}", check=False)
        old.unlink()
        self.say(
            "dropped a grooming pass left paused in worktrees/pair; "
            "`just groom` runs it again in worktrees/groom"
        )

    def accept(self, slug: str | None = None) -> str:
        """The developer passes the desk check: merge what is in the worktree.

        With `slug`, the desk check of that Flight instead, on `main`.
        """
        if slug is not None:
            return self.accept_flight(slug)
        self.reap()
        st = self.load()
        if st is None or st.retry != "desk-check":
            self.say("nothing is waiting for a desk check")
            return "none"
        st.paused = st.retry = None
        changed = self.absorb_developer(st)
        outcome = self.merge(st, force_gate=changed)
        if outcome:
            return outcome
        failure = st.note
        self.move(st, "in-progress")
        st.note = failure
        return self.work(st)

    def resume(self, slug: str | None = None) -> str:
        """The developer fails the desk check: their notes go back to the pair.

        With `slug`, the desk check of that Flight instead, on `main`.
        """
        if slug is not None:
            return self.resume_flight(slug)
        self.reap()
        st = self.load()
        if st is None or st.retry != "desk-check":
            self.say("nothing is waiting for a desk check")
            return "none"
        st.paused = st.retry = None
        self.absorb_developer(st)
        self.move(st, "in-progress")
        st.note = (
            "The developer sent this back from the desk check. "
            "Their notes are in the issue file."
        )
        return self.work(st)

    # --- the desk check of a Flight --------------------------------------------

    def flight_at_desk(self, slug: str) -> Path | None:
        """The Flight's file in the developer's checkout, if it waits for its desk check.

        The file must sit in `desk-check/` on `main`, with the checkout on `main`,
        since the answer is committed there. Otherwise say why and return None.
        """
        branch = git(self.repo, "symbolic-ref", "--short", "-q", "HEAD", check=False)
        if branch != self.main:
            self.say(
                f"your checkout is on {branch or 'a detached HEAD'}, not {self.main}; "
                "switch back, then run again"
            )
            return None
        if board.at_ref(self.repo, self.main, "desk-check", slug) is None or not (
            board.children(self.repo, self.main, slug)
        ):
            self.say(f"no Flight named {slug} is waiting for a desk check")
            return None
        return self.repo / board.ISSUES / "desk-check" / f"{slug}.md"

    def accept_flight(self, slug: str) -> str:
        """Call the Flight delivered: move it to `done/` in one commit on `main`."""
        if self.flight_at_desk(slug) is None:
            return "none"
        paths = self.commit_move(slug, "done", f"Accept {slug} at its desk check")
        self.say(f"accepted {slug} ({paths})")
        return "accepted"

    def resume_flight(self, slug: str) -> str:
        """Send the Flight back with the developer's notes, to be checked again.

        The notes, uncommitted or not, go in the same commit that moves the file
        to `backlog/` and puts its slug first in `ORDER`, so the loop takes it up
        next. A Flight that is a part of another in the backlog gets no line, as
        no part does, and the same commit drops any line naming one of the
        Flight's own parts, which a pass may have placed while the Flight sat at
        its desk check.
        """
        path = self.flight_at_desk(slug)
        if path is None:
            return "none"
        issue = board.parse(path.read_text())[1]
        if board.last_of(issue, (BRIEF, NOTES, CHILDREN)) != NOTES or not (
            board.bullets(board.last_section(issue, NOTES))
        ):
            self.say(
                f"write your notes in {path.relative_to(self.repo)} under a "
                f"`## {NOTES}` heading after its latest brief, one bullet per note"
            )
            return "none"
        if git(self.repo, "status", "--porcelain", "--", board.ORDER):
            self.say(f"{board.ORDER} has uncommitted edits; commit or discard them first")
            return "none"
        order = self.repo / board.ORDER
        text = order.read_text() if order.is_file() else f"{board.MARKER}\n"
        for part in board.descendants(self.repo, self.main, slug):
            text = board.without(text, part)
        text = board.without(text, slug)
        flight = board.at_ref(self.repo, self.main, "desk-check", slug)
        parent = flight and flight.front.get("parent")
        if not (parent and str(parent) in board.listed(self.repo, self.main, "backlog")):
            text = f"{slug}\n" + text
        order.write_text(text)
        paths = self.commit_move(
            slug, "backlog", f"Send {slug} back from its desk check", board.ORDER
        )
        self.say(f"sent {slug} back to backlog/ with your notes ({paths})")
        return "resumed"

    def commit_move(self, slug: str, to: str, subject: str, *also: str) -> str:
        """Move a Flight out of `desk-check/` on `main` and commit only that.

        The developer's other work in their checkout, staged or not, stays out.
        """
        old = f"{board.ISSUES}/desk-check/{slug}.md"
        new = f"{board.ISSUES}/{to}/{slug}.md"
        git(self.repo, "mv", old, new)
        git(self.repo, "add", new, *also)
        git(self.repo, "commit", "-q", "-m", subject, "-m", "Seat: developer",
            "--", old, new, *also)
        return git(self.repo, "rev-parse", "--short", "HEAD")

    # --- the worktree ----------------------------------------------------------

    def ensure_worktree(self) -> None:
        if not (self.wt / ".git").exists():
            self.wt.parent.mkdir(exist_ok=True)
            git(self.repo, "worktree", "add", "-q", "--detach", str(self.wt), self.main)
            if self.provision:
                self.provision(self.wt)

    def start(self, st: State) -> State | None:
        """Branch `pair/<slug>` from `main` for an issue or a grooming pass.

        An issue's file first moves from `backlog/` to `underway/` in a commit
        of its own on `main`, landed in the developer's checkout before the
        branch starts from it. If that landing is refused, the issue stays in
        `backlog/` and nothing is started. A file already in `underway/` is
        not moved again.
        """
        if git(self.wt, "status", "--porcelain"):
            self.pause(
                st,
                f"{self.tree} has uncommitted changes from before this issue; "
                "commit or discard them, then run again",
                retry=None,
            )
            self.clear()
            return None
        if st.stage != GROOMING and not self.move_underway(st):
            git(self.wt, "checkout", "-q", "--detach", "--force", self.main)
            self.clear()
            return None
        git(self.wt, "checkout", "-q", "-B", f"pair/{st.slug}", self.main)
        for role in ROLES:
            (self.dir / f"{role}.session").unlink(missing_ok=True)
        st.head = st.base = git(self.wt, "rev-parse", "HEAD")
        self.save(st)
        self.say(f"started {st.slug}")
        return st

    def move_underway(self, st: State) -> bool:
        """Land the move of the issue's file from `backlog/` to `underway/` on `main`.

        When a grooming pass lands first, the move is made again on the new
        `main`. False when the developer's checkout refuses the fast-forward
        otherwise; the loop is then paused.
        """
        for _ in range(LAND_TRIES):
            if board.at_ref(self.repo, self.main, "underway", st.slug):
                return True
            git(self.wt, "checkout", "-q", "--detach", "--force", self.main)
            (self.wt / board.ISSUES / "underway").mkdir(parents=True, exist_ok=True)
            git(
                self.wt,
                "mv",
                f"{board.ISSUES}/backlog/{st.slug}.md",
                f"{board.ISSUES}/underway/{st.slug}.md",
            )
            git(self.wt, "commit", "-q", "-m", f"Start {st.slug}", "-m", "Seat: loop")
            landed = self.land(st, git(self.wt, "rev-parse", "HEAD"), retry=None)
            if landed != "moved":
                return landed == "landed"
        self.pause(st, "main kept moving while starting; run again", retry=None)
        return False

    # --- the turn loop ---------------------------------------------------------

    def work(self, st: State) -> str:
        try:
            if st.retry == "merge":
                st.retry = None
                outcome = self.merge(st)
                if outcome:
                    return outcome
            elif st.retry == "kickback":
                return self.kick_back(st, None)
            elif st.retry == GROOMING:
                st.turn = 0
            st.retry = st.paused = None
            while True:
                if self.stop_requested:
                    self.pause(st, "stopped by the developer", retry=None)
                    return "stopped"
                role = st.next_role
                restarted = st.in_turn == role
                if not restarted:
                    self.absorb_developer(st)
                st.in_turn = role
                self.save(st)
                message = self.message(st, role)
                result = self.turn(
                    st, role, RESTARTED + message if restarted else message
                )
                if result is None:
                    return "paused"
                quiet = self.settle(st, role)
                st.in_turn = None
                self.record(st, role, result, quiet)
                outcome = self.decide(st, role, quiet)
                if outcome:
                    return outcome
        finally:
            for seat in self.seats.values():
                seat.stop()
            self.seats.clear()

    def seat(self, st: State, role: str) -> Seat:
        if role not in self.seats:
            resume = st.sessions.get(role) or self.saved_session(role)
            self.seats[role] = self.seat_factory(role, self.wt, resume)
        return self.seats[role]

    def saved_session(self, role: str) -> str | None:
        """The session a seat recorded for this issue, if it recorded one."""
        path = self.dir / f"{role}.session"
        return (path.read_text().strip() or None) if path.is_file() else None

    def reap(self) -> None:
        """Stop seats a dead supervisor left running in the worktree.

        A seat runs in its own session, so killing the supervisor does not kill
        it; it goes on editing the worktree unsupervised. Only a process whose
        command names the harness and whose working directory is this worktree
        is stopped, because a stale pid file may name a reused pid.
        """
        for role in ROLES:
            pid_file = self.dir / f"{role}.pid"
            try:
                pid = int(pid_file.read_text().strip())
            except (OSError, ValueError):
                continue
            if not self.owns(pid):
                continue
            os.kill(pid, signal.SIGTERM)
            for _ in range(50):
                if not self.alive(pid):
                    break
                time.sleep(0.2)
            else:
                os.kill(pid, signal.SIGKILL)
            self.say(f"stopped an orphaned {role} seat (pid {pid})")

    def owns(self, pid: int) -> bool:
        command = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True
        ).stdout
        if self.seat_command not in command:
            return False
        cwd = subprocess.run(
            ["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
            capture_output=True,
            text=True,
        ).stdout
        paths = [line[1:] for line in cwd.splitlines() if line.startswith("n")]
        return any(Path(p).resolve() == self.wt.resolve() for p in paths)

    @staticmethod
    def alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True

    def turn(self, st: State, role: str, message: str) -> TurnResult | None:
        """Send one turn; restart the seat once from its session if it fails."""
        result = self.seat(st, role).send(message)
        if not result.ok:
            self.say(f"{role} failed ({result.error}); restarting it once")
            if result.session_id:
                st.sessions[role] = result.session_id
            self.seats.pop(role).stop()
            result = self.seat(st, role).send(RESTARTED + message)
            if not result.ok:
                self.pause(
                    st, f"the {role} seat failed twice: {result.error}", retry=None
                )
                return None
        if result.session_id:
            st.sessions[role] = result.session_id
        return result

    def absorb_developer(self, st: State) -> bool:
        """Commit edits the developer made in the worktree between turns, as a turn of their own."""
        dirty = bool(git(self.wt, "status", "--porcelain"))
        moved = git(self.wt, "rev-parse", "HEAD") != st.head
        if not (dirty or moved):
            return False
        if dirty:
            git(self.wt, "add", "-A")
            git(
                self.wt,
                "commit",
                "-q",
                "-m",
                f"developer: edits on {st.slug}",
                "-m",
                "Seat: developer",
            )
        st.head = git(self.wt, "rev-parse", "HEAD")
        st.approvals = []
        st.note = (
            st.note
            + "\n\nThe developer changed things since the last turn; see the changes below."
        ).strip()
        self.say("absorbed the developer's edits")
        self.save(st)
        return True

    def settle(self, st: State, role: str) -> bool:
        """Put the issue file back, commit leftovers, and say if the turn was quiet."""
        where = board.locations(self.wt, st.slug)
        at = home(st.stage)
        if st.stage != GROOMING and where != [at]:
            keep = self.wt / board.ISSUES / at / f"{st.slug}.md"
            for stage in where:
                if stage == at:
                    continue
                stray = self.wt / board.ISSUES / stage / f"{st.slug}.md"
                if keep.exists():
                    stray.unlink()
                else:
                    keep.parent.mkdir(parents=True, exist_ok=True)
                    stray.rename(keep)
            self.say(
                f"moved {st.slug}.md back to {at}/ after the {role} seat moved it"
            )
        if git(self.wt, "status", "--porcelain"):
            git(self.wt, "add", "-A")
            if git(self.wt, "diff", "--cached", "--name-only"):
                git(
                    self.wt,
                    "commit",
                    "-q",
                    "-m",
                    f"{role}: {st.stage} turn on {st.slug}",
                    "-m",
                    f"Seat: {role}",
                )
        head = git(self.wt, "rev-parse", "HEAD")
        quiet = head == st.head or not git(
            self.wt, "diff", "--name-only", st.head, head
        )
        if not quiet and role not in st.seats_used:
            st.seats_used.append(role)
        st.head = st.seen[role] = head
        return quiet

    def record(self, st: State, role: str, result: TurnResult, quiet: bool) -> None:
        usage = result.usage
        row = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "slug": st.slug,
            "stage": st.stage,
            "turn": st.turn + 1,
            "role": role,
            "quiet": quiet,
            "session": result.session_id,
            "seconds": round(result.seconds, 1),
            "input": usage.get("input_tokens"),
            "cache_read": usage.get("cache_read_input_tokens"),
            "cache_write": usage.get("cache_creation_input_tokens"),
            "output": usage.get("output_tokens"),
            "cost_usd": result.cost_usd,
        }
        self.dir.mkdir(parents=True, exist_ok=True)
        with (self.dir / "turns.jsonl").open("a") as f:
            f.write(json.dumps(row) + "\n")
        self.say(
            f"{st.slug} {st.stage} turn {st.turn + 1}: {role} "
            f"{'quiet' if quiet else 'changed things'}"
        )

    # --- the rules -------------------------------------------------------------

    def decide(self, st: State, role: str, quiet: bool) -> str | None:
        grooming = st.stage == GROOMING
        issue = None if grooming else board.read(self.wt, st.slug)
        if not grooming and (issue is None or board.needs_elaboration(issue.body)):
            return self.kick_back(st, None)
        st.turn += 1
        st.note = ""
        st.next_role = other(role)
        st.approvals = sorted(set(st.approvals) | {role}) if quiet else [role]
        if set(st.approvals) >= set(ROLES):
            missing = self.requirement(st, issue)
            if missing is None:
                return self.advance(st, issue)
            if missing == "paused":
                return "paused"
            st.approvals = []
            st.note = (
                "Both of you left this stage as it stands, "
                f"but it is not finished yet: {missing}"
            )
        difficulty = "medium" if issue is None else issue.difficulty
        cap = self.round_cap or ROUND_CAP.get(difficulty, ROUND_CAP[None])
        if st.turn >= 2 * cap and grooming:
            return self.pause(
                st,
                f"the grooming pass did not settle within {st.turn} turns; "
                f"steer it in {self.tree} if you like, then run again",
                retry=GROOMING,
            )
        if st.turn >= 2 * cap:
            return self.kick_back(
                st,
                f"The pair did not settle the {st.stage} stage within {st.turn} turns.",
            )
        self.save(st)
        return None

    def requirement(self, st: State, issue: board.Issue | None) -> str | None:
        """What the current stage still lacks, or None when it is finished."""
        if issue is None:
            faults = board.grooming_faults(
                self.wt, self.wt, st.base, st.targets, st.rerank
            )
            if faults:
                return "the backlog is not groomed yet:\n" + "\n".join(
                    f"- {fault}" for fault in faults
                )
            ok, out = self.gate(self.wt)
            return None if ok else f"`just gate` fails:\n```\n{out[-GATE_TAIL:]}\n```"
        if st.stage == "backlog":
            if issue.difficulty is None:
                return (
                    "set `difficulty:` in the front matter "
                    "to easy, medium, hard or developer."
                )
            if issue.difficulty == "hard" and not board.children(
                self.wt, "HEAD", st.slug
            ):
                return (
                    "it is hard, so split it: write each part as a new file "
                    "in issues/backlog/ "
                    f"with `parent: {st.slug}` in its front matter."
                )
            return None
        if st.stage == FLIGHT_CHECK:
            return self.flight_checked(st, issue)
        if st.stage == "todo":
            return (
                None
                if board.section(issue.body, "The plan")
                else "write the plan under a `## The plan` heading."
            )
        if st.stage == "in-progress":
            if not self.touches_code():
                return "nothing outside issues/ has changed on this branch yet."
            if self.rebase(st) is None:
                return "paused"
            ok, out = self.gate(self.wt)
            return (
                None
                if ok
                else f"`just gate` fails:\n```\n{out[-GATE_TAIL:]}\n```"
            )
        return None

    def flight_checked(self, st: State, issue: board.Issue) -> str | None:
        """What a Flight check still lacks: a new child for a gap, or a new brief.

        A child counts only if the check wrote it, not if it moved one back to
        `backlog/`; a brief counts only if the Flight file holds one more than
        it did when the check began, since each round's brief stays in it. A
        Flight whose file ended in desk-check notes when the check began owes
        children and no brief (`owed_children`).
        """
        if self.touches_code():
            return "the Flight check changes nothing outside issues/; undo those changes."
        before: set[str] = set()
        for stage in board.STAGES:
            before.update(board.listed(self.wt, st.base, stage))
        gaps = [
            slug
            for slug, stage in board.children(self.wt, "HEAD", st.slug).items()
            if stage == "backlog" and slug not in before
        ]
        was = board.at_ref(self.wt, st.base, home(st.stage), st.slug)
        if was and board.last_of(was.body, (BRIEF, NOTES, CHILDREN)) == NOTES:
            missing = self.owed_children(st, issue, was, gaps)
            if missing:
                return missing
            ok, out = self.gate(self.wt)
            return None if ok else f"`just gate` fails:\n```\n{out[-GATE_TAIL:]}\n```"
        briefs = board.sections(issue.body, BRIEF)
        if not gaps and briefs <= (board.sections(was.body, BRIEF) if was else 0):
            return (
                "check the Flight's \"Done when\" on main, then either write each gap "
                "as a new file in issues/backlog/ with "
                f"`parent: {st.slug}` in its front matter, or add a "
                f"`## {BRIEF}` section to {issue.path}."
            )
        ok, out = self.gate(self.wt)
        return None if ok else f"`just gate` fails:\n```\n{out[-GATE_TAIL:]}\n```"

    def owed_children(
        self, st: State, issue: board.Issue, was: board.Issue, gaps: list[str]
    ) -> str | None:
        """What a Flight check answering desk-check notes still lacks.

        It writes a child for each note, lists them in one new children
        section at the end of the Flight file, and writes no brief. The
        children section marks the notes answered, so the check after those
        children land owes nothing.
        """
        ask = (
            f"the developer's `## {NOTES}` in {issue.path} are unanswered: write "
            "each note as a new file in issues/backlog/ with "
            f"`parent: {st.slug}` in its front matter, then add a `## {CHILDREN}` "
            "section at the end of the Flight file listing each new slug as a "
            "bullet, and write no brief."
        )
        if board.sections(issue.body, BRIEF) > board.sections(was.body, BRIEF):
            return f"{ask} This check wrote a brief; take it out."
        if (
            not gaps
            or board.sections(issue.body, CHILDREN)
            != board.sections(was.body, CHILDREN) + 1
            or board.last_of(issue.body, (BRIEF, NOTES, CHILDREN)) != CHILDREN
        ):
            return ask
        listed = board.bullets(board.last_section(issue.body, CHILDREN))
        if sorted(listed) != sorted(gaps):
            return (
                f"the `## {CHILDREN}` section lists {', '.join(listed) or 'nothing'}, "
                f"but the new children are {', '.join(sorted(gaps))}; make them match."
            )
        return None

    def advance(self, st: State, issue: board.Issue | None) -> str | None:
        if (
            issue is None
            or st.stage == FLIGHT_CHECK
            or (st.stage == "backlog" and issue.difficulty == "hard")
        ):
            return self.merge(st)
        if st.stage == "backlog":
            self.move(st, "todo")
            return None
        if st.stage == "todo":
            self.move(st, "in-progress")
            return None
        if st.stage == "in-progress" and issue.difficulty == "developer":
            self.move(st, "desk-check")
            return self.pause(
                st,
                f"ready for your desk check in {self.tree} "
                "(`just pair-accept`, or leave notes and `just pair-resume`)",
                retry="desk-check",
            )
        return self.merge(st)

    def move(self, st: State, to: str) -> None:
        (self.wt / board.ISSUES / to).mkdir(parents=True, exist_ok=True)
        git(
            self.wt,
            "mv",
            f"{board.ISSUES}/{home(st.stage)}/{st.slug}.md",
            f"{board.ISSUES}/{to}/{st.slug}.md",
        )
        git(
            self.wt,
            "commit",
            "-q",
            "-m",
            f"{st.slug}: {st.stage} -> {to}",
            "-m",
            "Seat: loop",
        )
        self.say(f"{st.slug}: {st.stage} -> {to}")
        st.stage, st.turn, st.approvals, st.next_role = to, 0, [], "primary"
        st.head = git(self.wt, "rev-parse", "HEAD")
        st.note = f"The pair agreed the previous stage; the issue is now in {to}/."
        self.save(st)

    # --- landing ---------------------------------------------------------------

    def touches_code(self) -> bool:
        changed = git(
            self.wt, "diff", "--name-only", f"{self.main}...HEAD"
        ).splitlines()
        return any(not p.startswith(f"{board.ISSUES}/") for p in changed)

    def rebase(self, st: State) -> bool | None:
        """Rebase the branch onto `main`.

        True if it moved, False if it was already there, None if it conflicted
        (the loop is then paused). A conflict in `ORDER` alone is no conflict:
        the file is rebuilt from `main`'s (`board.merge_order`), since a
        landing on `main` drops a line and a pass inserts them.

        A grooming pass is squashed before it is rebased, so one commit is
        replayed, and afterwards keeps only its changes under
        `issues/backlog/`. An Issue the loop started while the pass ran has
        moved to `underway/`, and git would otherwise carry the pass's edit of
        its backlog file onto the file underway.
        """
        if git_ok(self.wt, "merge-base", "--is-ancestor", self.main, "HEAD"):
            return False
        fork = git(self.wt, "merge-base", self.main, "HEAD")
        grooming = st.stage == GROOMING
        if grooming and git(self.wt, "rev-list", "--count", f"{fork}..HEAD") != "1":
            git(self.wt, "reset", "-q", "--soft", fork)
            if not git_ok(self.wt, "diff", "--cached", "--quiet"):
                git(self.wt, "commit", "-q", "-m", "Groom the backlog")
        base = board.show(self.wt, fork, board.ORDER)
        theirs = board.show(self.wt, "HEAD", board.ORDER)
        done = git_ok(self.wt, "rebase", "-q", self.main)
        while not done:
            conflicted = git(self.wt, "diff", "--name-only", "--diff-filter=U")
            if conflicted != board.ORDER:
                git(self.wt, "rebase", "--abort", check=False)
                self.pause(
                    st,
                    f"pair/{st.slug} conflicts with main; "
                    f"resolve it in {self.tree}, then run again",
                    retry=None,
                )
                return None
            ours = board.show(self.wt, self.main, board.ORDER)
            keep = board.order_keeps(self.wt)
            (self.wt / board.ORDER).write_text(
                board.merge_order(ours, base, theirs, keep, rerank=st.rerank)
            )
            git(self.wt, "add", board.ORDER)
            done = git_ok(self.wt, "-c", "core.editor=true", "rebase", "--continue")
        if grooming:
            self.keep_backlog_only()
        st.head = git(self.wt, "rev-parse", "HEAD")
        return True

    def keep_backlog_only(self) -> None:
        """Put back from `main` each path outside `issues/backlog/` the pass changed."""
        changed = git(self.wt, "diff", "--name-only", self.main, "HEAD").splitlines()
        stray = [p for p in changed if not p.startswith(f"{board.ISSUES}/backlog/")]
        if not stray:
            return
        for path in stray:
            if git_ok(self.wt, "cat-file", "-e", f"{self.main}:{path}"):
                git(self.wt, "checkout", "-q", self.main, "--", path)
            else:
                git(self.wt, "rm", "-q", "-f", "--", path)
        git(self.wt, "commit", "-q", "-m", "Keep the pass to issues/backlog/")

    def merge(self, st: State, force_gate: bool = False) -> str | None:
        """Squash the branch onto `main` and fast-forward the developer's checkout.

        When the other process lands first, the branch is rebased onto the new
        `main` and landed again, up to `LAND_TRIES` times.
        """
        for _ in range(LAND_TRIES):
            moved = self.rebase(st)
            if moved is None:
                return "paused"
            if (moved or force_gate) and self.touches_code():
                ok, out = self.gate(self.wt)
                if not ok:
                    if st.stage == "done" or (
                        st.stage != GROOMING
                        and not board.at_ref(self.wt, "HEAD", home(st.stage), st.slug)
                    ):
                        return self.pause(
                            st,
                            "main moved and the gate now fails on the squashed issue",
                            "merge",
                        )
                    st.approvals, st.note = (
                        [],
                        f"`just gate` fails:\n```\n{out[-GATE_TAIL:]}\n```",
                    )
                    self.save(st)
                    return None
            force_gate = False
            to = self.retirement(st)
            if to == "desk-check" and st.stage == FLIGHT_CHECK:
                if not self.deliver_flight(st):
                    return "paused"
            if to is not None:
                self.move(st, to)
            sha = self.squash(st)
            if not git_ok(self.repo, "merge-base", "--is-ancestor", self.main, sha):
                continue
            landed = self.land(st, sha)
            if landed == "moved":
                continue
            if landed == "paused":
                return "paused"
            if self.push:
                git(self.repo, "push", "-q", "origin", self.main, check=False)
            if st.stage == GROOMING:
                return self.groomed()
            title = (board.read(self.wt, st.slug) or board.Issue(st.slug, "done")).title
            git(self.wt, "checkout", "-q", "--detach", self.main)
            git(self.wt, "branch", "-q", "-D", f"pair/{st.slug}", check=False)
            self.clear()
            self.notify(f"landed {st.slug}")
            self.say(f"landed {st.slug}: {title} ({sha[:8]})")
            return "landed"
        return self.pause(
            st, "main kept moving while landing; run again", retry="merge"
        )

    def retirement(self, st: State) -> str | None:
        """The stage landing moves the issue to, or None if it stays where it is.

        A Flight with a child outside `done/` goes back from `underway/` to
        `backlog/`: a hard issue just split, or a Flight check that wrote a gap.
        Once it is there, it stays. A Flight that passes
        its check goes to `desk-check/`, and every other issue to `done/`. The
        answer is read from the tree and the stage, so a merge that goes round
        again, or is retried after a pause, decides the same way. A Flight
        already moved to `desk-check/` has children, which tells it apart from
        a `developer` issue, which `accept` merges from there to `done/`.
        """
        if st.stage in ("done", GROOMING):
            return None
        if board.waiting(self.wt, "HEAD", st.slug):
            return "backlog" if board.locations(self.wt, st.slug) == ["underway"] else None
        if st.stage == FLIGHT_CHECK:
            return "desk-check"
        if st.stage == "desk-check" and board.children(self.wt, "HEAD", st.slug):
            return None
        return "done"

    def deliver_flight(self, st: State) -> bool:
        """Run `just deliver` for a Flight about to go to `desk-check/`.

        Where the repository defines the recipe and it passes, a line recording
        it is appended to the Flight file, which ends in the brief, and staged
        so `move` commits it. Where it fails, the loop pauses with
        `retry: merge`, before `move`, so a rerun delivers again. Once `move`
        has run, `retirement` no longer answers `desk-check`, so another pass
        through `merge` does not deliver twice.
        """
        result = self.deliver(self.wt) if self.deliver else None
        if result is None:
            return True
        ok, out = result
        if not ok:
            self.pause(
                st,
                "`just deliver` fails, so the Flight stays out of desk-check/; "
                f"fix it, then run again:\n```\n{out[-DELIVER_TAIL:]}\n```",
                retry="merge",
            )
            return False
        flight = f"{board.ISSUES}/{home(st.stage)}/{st.slug}.md"
        path = self.wt / flight
        sha = git(self.wt, "rev-parse", "--short", self.main)
        line = f"Delivered by `just deliver` from {self.main} at {sha}."
        path.write_text(path.read_text().rstrip() + f"\n\n{line}\n")
        git(self.wt, "add", flight)
        self.say(f"{st.slug}: delivered")
        return True

    def squash(self, st: State) -> str:
        """Commit the rebased branch onto `main` as one commit.

        The same commit drops the slug from `ORDER` when the issue lands in
        `done/`, or a Flight in `desk-check/`; a Flight left waiting keeps its
        place. No earlier commit on the
        branch touches `ORDER`, so a reordering on `main` while the issue runs
        rebases cleanly. A grooming pass has no issue, and so no slug to drop.
        """
        grooming = st.stage == GROOMING
        trailers = "\n".join(f"Seat: {r}" for r in (st.seats_used or ["loop"]))
        if grooming:
            head = ["Groom the backlog"]
        else:
            issue = board.read(self.wt, st.slug) or board.Issue(st.slug, "done")
            head = [issue.title, f"Issue: {issue.path}"]
        git(self.wt, "reset", "-q", "--soft", self.main)
        order = self.wt / board.ORDER
        retired = board.locations(self.wt, st.slug) in (["done"], ["desk-check"])
        if order.is_file() and not grooming and retired:
            text = order.read_text()
            if board.without(text, st.slug) != text:
                order.write_text(board.without(text, st.slug))
                git(self.wt, "add", board.ORDER)
        messages = [arg for part in (*head, trailers) for arg in ("-m", part)]
        if not (grooming and git_ok(self.wt, "diff", "--cached", "--quiet")):
            git(self.wt, "commit", "-q", *messages)
        st.head = git(self.wt, "rev-parse", "HEAD")
        self.save(st)
        return st.head

    def groomed(self) -> str:
        """End a landed grooming pass. A pass that changed nothing lands no commit."""
        sha = git(self.repo, "rev-parse", self.main)
        git(self.wt, "checkout", "-q", "--detach", self.main)
        git(self.wt, "branch", "-q", "-D", f"pair/{GROOMING}", check=False)
        self.clear()
        self.notify("groomed the backlog")
        self.say(f"groomed the backlog ({sha[:8]})")
        return "groomed"

    def land(self, st: State, sha: str, retry: str | None = "merge") -> str:
        """Fast-forward `main` in the developer's checkout; refuse rather than overwrite.

        Answers `landed` when it moved, and `moved` when `main` has moved past
        the commit `sha` was built on because the other process (a grooming
        pass, or the loop working an Issue) landed first; the caller then
        builds again on the new `main`. A fast-forward that meets the other
        process's `index.lock` is tried again after `wait_for_lock`, and
        pauses, naming the lock, if the lock never goes away. Any
        other refusal, such as local edits in the way, pauses the loop with
        `retry` and answers `paused`.
        """
        branch = git(self.repo, "symbolic-ref", "--short", "-q", "HEAD", check=False)
        if branch != self.main:
            self.pause(
                st,
                f"your checkout is on {branch or 'a detached HEAD'}, not {self.main}; "
                f"switch back, then run again",
                retry=retry,
            )
            return "paused"
        lock = self.repo / git(self.repo, "rev-parse", "--git-path", "index.lock")
        locked = False
        for _ in range(LAND_TRIES):
            done = git_run(self.repo, "merge", "--ff-only", "-q", sha)
            if done.returncode == 0:
                return "landed"
            if not git_ok(self.repo, "merge-base", "--is-ancestor", self.main, sha):
                return "moved"
            locked = "index.lock" in done.stderr or lock.exists()
            if not locked:
                break
            self.wait_for_lock()
        why = (
            f"({lock.relative_to(self.repo)} stayed in place); "
            "if no git process holds it, delete it"
            if locked
            else "(local edits in the way?); clear them"
        )
        self.pause(
            st,
            f"could not fast-forward {self.main} in your checkout to {sha[:8]} "
            f"{why}, then run again",
            retry=retry,
        )
        return "paused"

    def wait_for_lock(self) -> None:
        """Give the other process time to finish with the checkout's index."""
        time.sleep(LOCK_WAIT)

    def kick_back(self, st: State, reason: str | None) -> str:
        """Send the issue back to `issues/backlog/` on `main`, without the code.

        The file always carries a `Needs elaboration` section, which keeps
        `next_ripe` from taking it straight back up, and a grooming pass from
        taking it up.
        """
        if st.kick_text is None:
            issue = board.read(self.wt, st.slug)
            text = (self.wt / issue.path).read_text() if issue else f"# {st.slug}\n"
            if issue is None:
                reason = reason or "The issue's file was gone from its branch."
            if reason:
                text = text.rstrip() + f"\n\n# Needs elaboration\n\n{reason}\n"
            st.kick_text = text
        self.save(st)
        landed = "moved"
        for _ in range(LAND_TRIES):
            git(self.wt, "checkout", "-q", "--detach", "--force", self.main)
            for stage in board.STAGES:
                if board.at_ref(self.repo, self.main, stage, st.slug):
                    git(self.wt, "rm", "-q", f"{board.ISSUES}/{stage}/{st.slug}.md")
            home = self.wt / board.ISSUES / "backlog" / f"{st.slug}.md"
            home.parent.mkdir(parents=True, exist_ok=True)
            home.write_text(st.kick_text)
            git(self.wt, "add", str(home.relative_to(self.wt)))
            git(
                self.wt,
                "commit",
                "-q",
                "-m",
                f"Send {st.slug} back for elaboration",
                "-m",
                "Seat: loop",
            )
            landed = self.land(st, git(self.wt, "rev-parse", "HEAD"))
            if landed != "moved":
                break
        if landed != "landed":
            if landed == "moved":
                self.pause(st, "main kept moving while sending back; run again", None)
            st.retry = "kickback"
            self.save(st)
            return "paused"
        self.clear()
        self.notify(f"{st.slug} went back to backlog/ for elaboration")
        self.say(f"sent {st.slug} back to backlog/")
        return "kicked"

    # --- the message -----------------------------------------------------------

    def message(self, st: State, role: str) -> str:
        template = (self.prompts / f"stage-{st.stage}.md").read_text()
        path = (
            f"{board.ISSUES}/backlog/"
            if st.stage == GROOMING
            else f"{board.ISSUES}/{home(st.stage)}/{st.slug}.md"
        )
        fields = {"path": path, "slug": st.slug}
        if st.stage == GROOMING:
            fields["issues"] = (
                "\n".join(f"- {board.ISSUES}/backlog/{t}.md" for t in st.targets)
                or "(none: this pass only ranks)"
            )
            ranking = "grooming-rerank" if st.rerank else "grooming-place"
            fields["ranking"] = (self.prompts / f"{ranking}.md").read_text().strip()
        parts = [template.format(**fields).strip()]
        if st.note:
            parts.append(st.note)
        since = st.seen.get(role)
        if since is None:
            parts.append("This is your first turn here.")
        else:
            diff = git(self.wt, "diff", f"{since}..HEAD")
            if not diff:
                parts.append("Nothing has changed since your last turn.")
            else:
                if len(diff) > DIFF_LIMIT:
                    diff = (
                        diff[:DIFF_LIMIT]
                        + f"\n... (truncated; run `git diff {since[:12]}..HEAD`)"
                    )
                parts.append(f"Changes since your last turn:\n```diff\n{diff}\n```")
        parts.append("If you would change nothing, change nothing and say so.")
        return "\n\n".join(parts)


def status(repo: Path, main: str = "main") -> str:
    """A plain-text view of the board on `main`, the Issue underway and the grooming pass."""
    lines = []
    for stage in ("roadmap", "backlog", "underway", "done"):
        slugs = board.listed(repo, main, stage)
        lines.append(
            f"{stage:12} {len(slugs):3}  {', '.join(slugs[:6])}"
            f"{' ...' if len(slugs) > 6 else ''}"
        )
    underway = False
    for kind in ("pair", "groom"):
        state = runtime_dir(repo, kind) / "state.json"
        if not state.is_file():
            continue
        underway = True
        st: dict[str, Any] = json.loads(state.read_text())
        what = (
            "grooming pass"
            if st["stage"] == GROOMING
            else f"{st['slug']} in its Flight check"
            if st["stage"] == FLIGHT_CHECK
            else f"{st['slug']} in underway/, its backlog stage"
            if st["stage"] == "backlog"
            else f"{st['slug']} in {st['stage']}/"
        )
        lines.append(
            f"\nunderway: {what}, turn {st['turn']}, "
            f"next {st['next_role']}, "
            f"accepted by {st['approvals'] or 'nobody yet'}"
        )
        if st.get("paused"):
            lines.append(f"paused: {st['paused']}")
        for role, sid in st.get("sessions", {}).items():
            lines.append(
                f"{role:9} session {sid}  "
                f"(take over: cd worktrees/{kind} && claude --resume {sid})"
            )
    if not underway:
        lines.append("\nnothing underway")
    rows = []
    for kind in ("pair", "groom"):
        turns = runtime_dir(repo, kind) / "turns.jsonl"
        if turns.is_file():
            rows += [json.loads(row) for row in turns.read_text().splitlines()[-4:]]
    if rows:
        lines.append("\nlast turns:")
        for row in sorted(rows, key=lambda row: row["at"])[-4:]:
            lines.append(
                f"  {row['slug']} {row['stage']} #{row['turn']} {row['role']:8} "
                f"{'quiet' if row['quiet'] else 'changed'}  {row['seconds']}s  "
                f"cache read {row['cache_read']}  write {row['cache_write']}"
            )
    return "\n".join(lines)
