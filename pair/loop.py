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

After each turn the loop also keeps the seat's closing message in the issue
file, quoted under `## Pair notes` (`Loop.keep_note`), where the other seat
reads it in its diff. The note is not the seat's change, so it never makes a
turn count as one.

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
import re
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import board
import touched
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
GATE = "gate"
"""The `retry` of a pause for a gate step that could not run: resuming runs the gate again first."""
COULD_NOT = re.compile(r"^\?  (?P<step>\S[^:\n]*): (?P<why>.*)$", re.MULTILINE)
"""A gate step that could not run, in the shape `.meta/gate` reads it in (its `COULD_NOT`).

`.meta/gate` is a script, not a module, so the pattern is copied. The summary
line of `closing_block`, `?  steps that could not run (n) — …`, has no colon
after its step, and its detail lines are indented, so neither matches.
"""
DELIVER_TAIL = 2_000
"""Less than `GATE_TAIL`: a failed delivery's tail goes into a pause reason, which is also notified."""
LAND_TRIES = 5
"""How many times a landing goes round when the other process lands first."""
LOCK_WAIT = 0.5
"""Seconds to wait for the other process's git command (a lock, or a commit in flight)."""
GIT_ERROR_TAIL = 300
"""Characters of git's error that a refused landing's pause reason carries."""
RESTARTED = (
    "(Your session was restarted after an interruption. The working tree is as you "
    "left it; check `git status` and carry on.)\n\n"
)

SeatFactory = Callable[[str, Path, "str | None", "str | None"], Seat]
Gate = Callable[[Path, "Sequence[str] | None"], "tuple[bool, str]"]
"""Runs the gate in a tree over the named Projects, or over every Project for `None`."""
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
    models: dict[str, str | None] = field(default_factory=dict)
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


def event_log(repo: Path) -> Path:
    """`.pair/events.jsonl`, where both loops log their transitions, one JSON object a line."""
    return runtime_dir(repo, "pair") / "events.jsonl"


def append_event(
    repo: Path,
    loop: str,
    kind: str,
    slug: str | None = None,
    *,
    main: str = "main",
    report: Callable[[str], None] = lambda message: print(message, file=sys.stderr),
    **fields: Any,
) -> None:
    """Append one event to the log, as one line in one write, then `publish`.

    An append this small to a local file is not split, so the loop working
    Issues and a grooming pass write the one file without interleaving.
    A publish that fails is told to `report`, and the event stands.
    """
    row: dict[str, Any] = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "kind": kind,
        "loop": loop,
    }
    if slug is not None:
        row["slug"] = slug
    row.update(fields)
    path = event_log(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row) + "\n")
    failed = publish(repo, main)
    if failed:
        report(failed)


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


class GateFailure(str):
    """An unmet requirement that is a failed gate, which the primary seat repairs."""


def gate_fails(out: str, targets: Sequence[str] | None = None) -> GateFailure:
    """The requirement a failed gate leaves: what was gated, and the tail of its output."""
    command = " ".join(["just gate", *(targets or [])])
    return GateFailure(f"`{command}` fails:\n```\n{out[-GATE_TAIL:]}\n```")


class GateUnrunnable(str):
    """A gate that passed with steps that could not run, which only the developer can supply."""


def gate_unrunnable(out: str) -> GateUnrunnable | None:
    """The pause reason naming each step of `out` that could not run, or None when every step ran.

    A seat's sandbox cannot provide what such a step lacks (a Docker daemon,
    say), so the loop holds the landing for the developer rather than handing
    it back to the seats.
    """
    steps = [f"- {m['step']}: {m['why']}" for m in COULD_NOT.finditer(out)]
    if not steps:
        return None
    return GateUnrunnable(
        f"the gate could not run {len(steps)} step(s); "
        "supply what they need, then run again:\n" + "\n".join(steps)
    )


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
        model: str | None = None,
        stage_models: Mapping[str, str | None] | None = None,
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
        self.model = model
        self.stage_models = dict(stage_models or {})
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
        self.publish()

    def clear(self) -> None:
        self.state_file.unlink(missing_ok=True)
        self.publish()

    def publish(self) -> None:
        """Rewrite the published status (`publish`), and `say` why if that fails."""
        failed = publish(self.repo, self.main)
        if failed:
            self.say(failed)

    def event(self, kind: str, slug: str | None = None, **fields: Any) -> None:
        """Log a transition of this loop to `.pair/events.jsonl` (`append_event`)."""
        append_event(
            self.repo, self.kind, kind, slug, main=self.main, report=self.say, **fields
        )

    def pause(
        self, st: State, reason: str, retry: str | None, kind: str = "paused"
    ) -> str:
        """Pause with `reason`, logged as one event of `kind`, and return `kind`.

        A desk check and a stop are pauses too, logged and returned as
        `desk-check` and `stopped` rather than as `paused`.
        """
        st.paused, st.retry = reason, retry
        self.save(st)
        self.event(kind, st.slug, reason=reason, retry=retry)
        self.notify(f"{st.slug}: {reason}")
        self.say(f"paused: {reason}")
        return kind

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
                main = board.resolve(self.repo, self.main)
                within = None
                if flight is not None:
                    below = board.descendants(self.repo, main, flight)
                    within = frozenset(below | {flight})
                slug = board.next_ripe(
                    self.repo, main, skip=groom_targets(self.repo), within=within
                )
                if slug is None:
                    message = self.nothing_ripe(flight)
                    self.event("empty", message=message)
                    self.say(message)
                    return "empty"
                kids = board.children(self.repo, main, slug)
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
            if outcome in ("paused", "stopped", "desk-check") or once:
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
        main = board.resolve(self.repo, self.main)
        underway = board.listed(self.repo, main, "underway")
        if not underway:
            return None
        slug = underway[0]
        kids = board.children(self.repo, main, slug)
        return State(slug=slug, stage=FLIGHT_CHECK if kids else "backlog")

    def flight_refusal(self, flight: str, st: State | None) -> str | None:
        """Why `run` cannot work `flight` from here, or None when it can."""
        main = board.resolve(self.repo, self.main)
        if flight in board.listed(self.repo, main, "desk-check"):
            return (
                f"{flight} is waiting for your desk check: "
                f"`just pair-accept {flight}` or `just pair-resume {flight}`"
            )
        queued = board.listed(self.repo, main, "backlog") + board.listed(
            self.repo, main, "underway"
        )
        if flight not in queued or not board.children(self.repo, main, flight):
            return f"{flight} is not a Flight in issues/backlog/ or issues/underway/"
        below = board.descendants(self.repo, main, flight)
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
        main = board.resolve(self.repo, self.main)
        desk = set(board.listed(self.repo, main, "desk-check"))
        kin = board.families(self.repo, main)
        below = board.descendants(self.repo, main, flight)
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
        main = board.resolve(self.repo, self.main)
        targets = board.to_groom(self.repo, main)
        if not (targets or board.unnamed(self.repo, main) or rerank):
            self.event("empty", message="nothing to groom")
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
        self.send_back(st, st.note)
        return self.work(st)

    def send_back(self, st: State, why: str) -> None:
        """Send an Issue left in `desk-check` or `done` back to the pair.

        A Flight goes back to its Flight check in `underway/`, and any other
        Issue to `in-progress`; no turn runs in `desk-check` or `done`. An
        Issue is left in `done` when its landing is overtaken by another and
        the rebase onto the new `main` then conflicts: `merge` has already
        moved it there. A `developer` Issue sent back from either stage goes
        to its desk check again once the pair agrees `in-progress`. The note
        says where the Issue came back from, followed by `why`, and by the
        developer's edits if there are any. Those are absorbed before the
        move, because `move` resets `st.head`, and a conflict the developer
        resolved and committed would then no longer read as theirs.
        """
        came_from = (
            "its desk check" if st.stage == "desk-check" else f"{home(st.stage)}/"
        )
        absorbed = self.absorb_developer(st)
        to = FLIGHT_CHECK if board.children(self.wt, "HEAD", st.slug) else "in-progress"
        self.move(st, to, into=home(to))
        parts = [
            f"This came back from {came_from} to {home(to)}/ without landing.",
            why,
        ]
        if absorbed:
            parts.append(
                "The developer changed things since the last turn; "
                "see the changes below."
            )
        st.note = "\n\n".join(part for part in parts if part)
        self.save(st)

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
        main = board.resolve(self.repo, self.main)
        if board.at_ref(self.repo, main, "desk-check", slug) is None or not (
            board.children(self.repo, main, slug)
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
        self.publish()
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
        main = board.resolve(self.repo, self.main)
        for part in board.descendants(self.repo, main, slug):
            text = board.without(text, part)
        text = board.without(text, slug)
        flight = board.at_ref(self.repo, main, "desk-check", slug)
        parent = flight and flight.front.get("parent")
        if not (parent and str(parent) in board.listed(self.repo, main, "backlog")):
            text = f"{slug}\n" + text
        order.write_text(text)
        paths = self.commit_move(
            slug, "backlog", f"Send {slug} back from its desk check", board.ORDER
        )
        self.say(f"sent {slug} back to backlog/ with your notes ({paths})")
        self.publish()
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
        self.event("started", st.slug, stage=st.stage)
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
                st.retry = st.paused = None
                outcome = self.merge(st, force_gate=True)
                if outcome:
                    return outcome
                if st.stage in ("desk-check", "done"):
                    self.send_back(st, st.note)
            elif st.retry == GATE:
                st.retry = st.paused = None
                grooming = st.stage == GROOMING
                issue = None if grooming else board.read(self.wt, st.slug)
                outcome = self.close_stage(st, issue)
                if outcome:
                    return outcome
            elif st.retry == "kickback":
                return self.kick_back(st, None)
            elif st.retry == GROOMING:
                st.turn = 0
            if st.stage in ("desk-check", "done"):
                self.send_back(st, st.paused or "")
            st.retry = st.paused = None
            while True:
                if self.stop_requested:
                    return self.pause(
                        st, "stopped by the developer", retry=None, kind="stopped"
                    )
                role = st.next_role
                self.align_model(st, role)
                interrupted = st.in_turn == role
                if not interrupted:
                    self.absorb_developer(st)
                st.in_turn = role
                self.save(st)
                result = self.turn(
                    st,
                    role,
                    self.message(st, role),
                    restarted=interrupted and self.has_session(st, role),
                )
                if result is None:
                    return "paused"
                quiet = self.settle(st, role)
                self.keep_note(st, role, result)
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
        self.align_model(st, role)
        if role not in self.seats:
            resume = st.sessions.get(role) or self.saved_session(role)
            model = self.model_for(st.stage)
            self.seats[role] = self.seat_factory(role, self.wt, resume, model)
            st.models[role] = model
        return self.seats[role]

    def model_for(self, stage: str) -> str | None:
        """The model both seats run in `stage`: the stage's own if it names one, else `model`."""
        return self.stage_models.get(stage) or self.model

    def align_model(self, st: State, role: str) -> None:
        """Start `role` afresh when its session runs another model than the stage names.

        A session keeps the model it started on, so a change of model needs a
        new session, which loses the seat's conversation and writes its prompt
        to the cache again (`pair/README.md` gives the cost). `seat` records
        the model each seat is built on, so a loop restarted with another
        `--model` starts fresh too. A role with no recorded model, as in a
        state file older than `State.models`, counts as started on `model`.
        `work` calls this before it asks `has_session`, so that a seat
        interrupted in a session on the old model is not told it was
        restarted.
        """
        want = self.model_for(st.stage)
        had = st.models.get(role, self.model)
        if had == want:
            return
        seat = self.seats.pop(role, None)
        if seat is not None:
            seat.stop()
        self.forget_session(st, role)
        st.models[role] = want
        self.event("seat-model", st.slug, role=role, **{"from": had, "to": want})
        self.say(f"{role} starts a fresh session on {want or 'the default model'}")

    def has_session(self, st: State, role: str) -> bool:
        """Whether `seat` would resume a session for `role` rather than start one."""
        return bool(st.sessions.get(role) or self.saved_session(role))

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

    def turn(
        self, st: State, role: str, message: str, restarted: bool = False
    ) -> TurnResult | None:
        """Send one turn, and restart the seat once if it fails.

        A seat resuming a session it was interrupted in (`restarted`) is told
        so with `RESTARTED`. A crash or a timeout restarts the seat from its
        session. A refusal restarts it with a fresh session and the plain
        message, because the refused message is in the old session's history
        and resuming it would replay it. A restart that is refused, after
        either kind of failure, pauses with no session kept, so the next run
        starts the seat fresh too.
        """
        result = self.seat(st, role).send(
            RESTARTED + message if restarted else message
        )
        if not result.ok:
            first_refused = result.refused
            if first_refused:
                self.say(f"{role} was refused; restarting it once, fresh")
                self.event("seat-refused", st.slug, role=role, error=result.error)
                self.seats.pop(role).stop()
                self.forget_session(st, role)
                result = self.seat(st, role).send(message)
            else:
                self.say(f"{role} failed ({result.error}); restarting it once")
                if result.session_id:
                    st.sessions[role] = result.session_id
                self.seats.pop(role).stop()
                result = self.seat(st, role).send(RESTARTED + message)
            if result.refused:
                self.seats.pop(role).stop()
                self.forget_session(st, role)
                again = "twice" if first_refused else "on its restart"
                self.pause(
                    st,
                    f"the {role} seat was refused {again}: {result.error}",
                    retry=None,
                )
                return None
            if not result.ok:
                if result.session_id:
                    st.sessions[role] = result.session_id
                self.pause(
                    st, f"the {role} seat failed twice: {result.error}", retry=None
                )
                return None
        if result.session_id:
            st.sessions[role] = result.session_id
        return result

    def forget_session(self, st: State, role: str) -> None:
        """Drop a seat's session from both places `seat` resumes it from."""
        st.sessions.pop(role, None)
        (self.dir / f"{role}.session").unlink(missing_ok=True)

    def absorb_developer(self, st: State) -> bool:
        """Commit edits the developer made in the worktree between turns, as a turn of their own."""
        head, dirty = board.head_and_dirty(self.wt)
        if not dirty and head == st.head:
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
            head = git(self.wt, "rev-parse", "HEAD")
        st.head = head
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
        head, dirty = board.head_and_dirty(self.wt)
        if dirty:
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

    def keep_note(self, st: State, role: str, result: TurnResult) -> None:
        """Append the turn's closing message to the issue file and commit it.

        `settle` has already judged the turn from the seat's own changes, so
        the note never makes a turn count as a change. Moving `st.head` keeps
        `absorb_developer` from taking the note's commit for the developer's,
        and moving `st.seen[role]` past it keeps the seat from being shown its
        own note, while the other seat sees it in its diff. A grooming pass has
        no issue file, and a turn that lost its file is sent back by `decide`.
        """
        if st.stage == GROOMING or not result.text.strip():
            return
        issue = board.read(self.wt, st.slug)
        if issue is None:
            return
        path = self.wt / issue.path
        label = f"{role}, {st.stage} turn {st.turn + 1}"
        path.write_text(board.with_note(path.read_text(), label, result.text))
        git(self.wt, "add", "--", issue.path)
        git(
            self.wt,
            "commit",
            "-q",
            "-m",
            f"{role}: note on {st.stage} turn {st.turn + 1}",
            "-m",
            "Seat: loop",
        )
        st.head = st.seen[role] = git(self.wt, "rev-parse", "HEAD")

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
            "denials": len(result.denied),
            "denied": result.denied,
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
            outcome = self.close_stage(st, issue)
            if outcome:
                return outcome
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

    def close_stage(self, st: State, issue: board.Issue | None) -> str | None:
        """Advance a stage both seats left as it stands, or say what it still lacks.

        A gate step that could not run pauses the loop with `retry` set to
        `GATE`, keeping the approvals, note and next seat, so that resuming
        closes the stage again before any seat takes a turn. Any other unmet
        requirement clears the approvals and becomes the note, and a failed
        gate goes to the primary seat; the result is then None.
        """
        missing = self.requirement(st, issue)
        if missing is None:
            return self.advance(st, issue)
        if missing == "paused":
            return "paused"
        if isinstance(missing, GateUnrunnable):
            return self.pause(st, missing, retry=GATE)
        st.approvals = []
        st.note = (
            "Both of you left this stage as it stands, "
            f"but it is not finished yet: {missing}"
        )
        if isinstance(missing, GateFailure):
            st.next_role = "primary"
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
            return self.run_gate()
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
            return self.run_gate()
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
        before = {
            slug
            for slugs in board.listed_by_stage(self.wt, st.base).values()
            for slug in slugs
        }
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
            return self.run_gate()
        briefs = board.sections(issue.body, BRIEF)
        if not gaps and briefs <= (board.sections(was.body, BRIEF) if was else 0):
            return (
                "check the Flight's \"Done when\" on main, then either write each gap "
                "as a new file in issues/backlog/ with "
                f"`parent: {st.slug}` in its front matter, or add a "
                f"`## {BRIEF}` section to {issue.path}."
            )
        return self.run_gate()

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
                kind="desk-check",
            )
        return self.merge(st)

    def move(self, st: State, to: str, into: str | None = None) -> None:
        """Move the issue to stage `to`, its file to `issues/<into>/` (`to` by default).

        The directory is not `home(to)`, because a Flight that `retirement`
        sends to `backlog` goes to `backlog/` itself.
        """
        into = into or to
        (self.wt / board.ISSUES / into).mkdir(parents=True, exist_ok=True)
        git(
            self.wt,
            "mv",
            f"{board.ISSUES}/{home(st.stage)}/{st.slug}.md",
            f"{board.ISSUES}/{into}/{st.slug}.md",
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
        self.event("moved", st.slug, **{"from": st.stage, "to": to})
        self.say(f"{st.slug}: {st.stage} -> {to}")
        st.stage, st.turn, st.approvals, st.next_role = to, 0, [], "primary"
        st.head = git(self.wt, "rev-parse", "HEAD")
        st.note = f"The pair agreed the previous stage; the issue is now in {to}/."
        self.save(st)

    # --- landing ---------------------------------------------------------------

    def run_gate(self) -> GateFailure | GateUnrunnable | None:
        """Gate what the branch changes against `main`, or None when it passes.

        A gate that passes with a step that could not run is a
        `GateUnrunnable`, not a pass. A gate that fails is a `GateFailure`
        even when its output also holds such a step.

        Only the Projects the change touches and the Products built from them
        are gated (`touched.select`, stereorepo's DR-303); a branch that
        changes nothing passes without running the gate. Renames are listed as
        a deletion and an addition, so a file moved out of a Project still
        gates the Project it left.
        """
        changed = git(
            self.wt, "diff", "--name-only", "--no-renames", f"{self.main}...HEAD"
        ).splitlines()
        if not changed:
            return None
        targets = touched.select(self.wt, changed)
        ok, out = self.gate(self.wt, targets)
        return gate_unrunnable(out) if ok else gate_fails(out, targets)

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
        `main` and landed again, up to `LAND_TRIES` times. Where the gate runs,
        because a rebase moved the branch or `force_gate` is set, and fails
        with the Issue still in its stage, nothing lands: the gate's output
        becomes the note, acceptance is cleared, the primary seat takes the
        next turn, and the result is `None`.

        A landing logs `landed` once it is on `main`. Only a Flight lands in
        `desk-check/`, so that landing also logs `desk-check`; a `developer`
        Issue waits there on its branch, and `advance` logs it.
        """
        for _ in range(LAND_TRIES):
            moved = self.rebase(st)
            if moved is None:
                return "paused"
            if (moved or force_gate) and self.touches_code():
                failure = self.run_gate()
                if isinstance(failure, GateUnrunnable):
                    return self.pause(st, failure, retry="merge")
                if failure is not None:
                    if st.stage == "done" or (
                        st.stage != GROOMING
                        and not board.at_ref(self.wt, "HEAD", home(st.stage), st.slug)
                    ):
                        return self.pause(
                            st,
                            "the gate now fails on the squashed issue",
                            "merge",
                        )
                    st.approvals, st.note, st.next_role = [], failure, "primary"
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
            self.event("landed", st.slug, sha=sha, stage=st.stage)
            if st.stage == "desk-check":
                self.event("desk-check", st.slug, stage=st.stage)
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

        The commit's parent is the `main` the branch was rebased onto, not
        `main` as it is now: the index holds the rebased tree, so a commit made
        on `main` since the rebase would otherwise be reverted. When `main` has
        moved, the commit is then not on it, and `merge` goes round again.

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
        onto = git(self.wt, "merge-base", self.main, "HEAD")
        git(self.wt, "reset", "-q", "--soft", onto)
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
        self.event("groomed", GROOMING, sha=sha)
        self.notify("groomed the backlog")
        self.say(f"groomed the backlog ({sha[:8]})")
        return "groomed"

    def land(self, st: State, sha: str, retry: str | None = "merge") -> str:
        """Fast-forward `main` in the developer's checkout; refuse rather than overwrite.

        Answers `landed` when it moved, and `moved` when `main` has moved past
        the commit `sha` was built on because the other process (a grooming
        pass, or the loop working an Issue) landed first; the caller then
        builds again on the new `main`. Local edits to a path the landing
        changes pause the loop at once with `retry` and answer `paused`. Any
        other refusal, such as a commit on `main` in flight that holds
        `index.lock` or the lock on `main`'s ref, is tried again after
        `wait_for_lock`, up to `LAND_TRIES` times before it pauses. The pause
        reason names a lock still in place, and ends with git's error.

        A try refused at the lock on `main`'s ref has already written the
        landing into the checkout. When `main` then moves instead, `unwrite`
        puts those paths back before `land` answers `moved`, so that the
        checkout does not keep the unlanded paths staged; when the loop pauses
        instead, the reason names them.
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
        locks = [
            self.repo / git(self.repo, "rev-parse", "--git-path", path)
            for path in ("index.lock", f"refs/heads/{self.main}.lock")
        ]
        edits: list[str] = []
        written: set[str] = set()
        for tries in range(1, LAND_TRIES + 1):
            before = git(self.repo, "rev-parse", self.main)
            done = git_run(self.repo, "merge", "--ff-only", "-q", sha)
            if done.returncode == 0:
                return "landed"
            if not git_ok(self.repo, "merge-base", "--is-ancestor", self.main, sha):
                self.unwrite(sha, written)
                return "moved"
            edits = self.edits_in_the_way(sha)
            if edits:
                break
            written |= self.diff_names(before, sha)
            if tries == LAND_TRIES:
                break
            self.wait_for_lock()
        held = [lock for lock in locks if lock.exists()]
        if edits:
            why = f"(local edits in the way: {', '.join(edits)}); clear them"
        elif held:
            why = (
                f"({held[0].relative_to(self.repo)} stayed in place); "
                "if no git process holds it, delete it"
            )
        else:
            why = f"(git refused it {LAND_TRIES} times)"
        half = self.half_landed(sha, written)
        if half:
            why += (
                f"; your checkout holds the half-done landing as staged changes to "
                f"{', '.join(half)}, which the next run finishes "
                f"(or `git restore --staged --worktree` them)"
            )
        self.pause(
            st,
            f"could not fast-forward {self.main} in your checkout to {sha[:8]} "
            f"{why}, then run again (git: {git_error(done.stderr)})",
            retry=retry,
        )
        return "paused"

    def edits_in_the_way(self, sha: str) -> list[str]:
        """The paths the landing of `sha` changes that the checkout has local changes to.

        Untracked files count, since git will not overwrite them either. A
        tracked path whose content already matches `sha` does not: a
        fast-forward refused by the lock on `main`'s ref has already written
        the landing into the checkout, and the next try finishes it. A `git
        status` that fails, as it may while the other process holds the index,
        answers no paths, so that a lock is waited out rather than read as
        edits. In `git status -z`, a rename or copy entry is followed by the
        path it came from, which counts as changed too.
        """
        status = git_run(
            self.repo, "status", "--porcelain=v1", "-z", "--untracked-files=all"
        )
        if status.returncode != 0:
            return []
        changed: set[str] = set()
        untracked: set[str] = set()
        entries = iter(status.stdout.split("\0"))
        for entry in entries:
            if not entry:
                continue
            (untracked if entry[:2] == "??" else changed).add(entry[3:])
            if entry[0] in "RC":
                changed.add(next(entries, ""))
        landing = self.diff_names(self.main, sha)
        return sorted(landing & (untracked | (changed & self.diff_names(sha))))

    def half_landed(self, sha: str, paths: set[str]) -> list[str]:
        """The `paths` whose checkout still holds a refused fast-forward's write of `sha`.

        A path counts when its index entry and working-tree content both
        match `sha` and one of them differs from `HEAD`. A path the developer
        has changed since the try does not match `sha`, and is left out; so is
        a path that an `index.lock` refusal never wrote, and one absent from
        `sha`, `HEAD`, the index and the working tree alike.
        """
        if not paths:
            return []
        unlike_sha = self.diff_names(sha) | self.diff_names("--cached", sha)
        unlike_head = self.diff_names("HEAD") | self.diff_names("--cached", "HEAD")
        return sorted((paths & unlike_head) - unlike_sha)

    def diff_names(self, *args: str) -> set[str]:
        """The paths `git diff` with `args` names in the developer's checkout.

        A rename is two paths, the one it came from and the one it went to:
        `git diff` would name only the second, and a landing that moves a
        file writes both.
        """
        return set(
            git(self.repo, "diff", "--name-only", "--no-renames", "-z", *args).split("\0")
        ) - {""}

    def unwrite(self, sha: str, paths: set[str]) -> None:
        """Put the checkout's half-landed `paths` of `sha` back to `HEAD`, index and working tree.

        A failure, such as the other process holding `index.lock`, leaves the
        checkout as it is rather than stopping the loop.
        """
        half = self.half_landed(sha, paths)
        if half:
            git_run(
                self.repo,
                "restore",
                "--source=HEAD",
                "--staged",
                "--worktree",
                "--",
                *(f":(literal){path}" for path in half),
            )

    def wait_for_lock(self) -> None:
        """Give the other process's git command (a lock, or a commit in flight) time to finish."""
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
            main = board.resolve(self.wt, "HEAD")
            for stage in board.STAGES:
                if board.at_ref(self.repo, main, stage, st.slug):
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
        self.event("sent-back", st.slug, reason=reason)
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


SHOWN = ("roadmap", "backlog", "underway", "desk-check", "done")
"""The stages `status` counts. `todo/` and `in-progress/` only ever hold files on a pair branch."""


def first_line(text: str | None) -> str:
    """The first non-blank line of a section's text, without bold markers, or "" when it has none.

    A brief often opens with a bold lead (`**What was delivered.**`), whose
    markers are noise on a terminal.
    """
    line = next((line.strip() for line in (text or "").splitlines() if line.strip()), "")
    return line.replace("**", "")


def git_error(stderr: str) -> str:
    """Git's error on one line, cut to its last `GIT_ERROR_TAIL` characters.

    It keeps the last three `fatal:` or `error:` lines, or the last three
    lines when there are none, because the advice git prints after a lock's
    error would otherwise push out the line naming the lock.
    """
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    errors = [line for line in lines if line.startswith(("fatal:", "error:"))]
    return " / ".join((errors or lines)[-3:])[-GIT_ERROR_TAIL:] or "no message"


def status_view(repo: Path, main: str = "main") -> dict[str, Any]:
    """What `status` shows, as plain data derived from `main` and `.pair/`, and stored nowhere.

    - `waiting`: what waits on the developer, each `{slug, why, answer}`: a
      backlog Issue with a `Needs elaboration` section, a Flight in
      `desk-check/` with its latest brief, the Issue underway at its desk
      check, and the loop or grooming pass if paused for any other reason.
      A desk check is recorded as a pause; it is listed once.
    - `underway`: each loop with a state, `{kind, slug, stage, turn,
      next_role, approvals}`.
    - `order`: `board.running_tree`, each node `{slug, mark, flight, out,
      parts}`, where `out` holds a Flight's children already out of the
      backlog with their stage.
    - `to_groom`: the backlog Issues with no `difficulty`.
    - `counts`: the slugs in each stage of `SHOWN`.
    - `sessions`: each seat session, `{kind, role, id}`.
    - `turns`: the last four turns of both loops, oldest first.
    """
    states: dict[str, dict[str, Any]] = {}
    for kind in ("pair", "groom"):
        path = runtime_dir(repo, kind) / "state.json"
        if path.is_file():
            states[kind] = json.loads(path.read_text())
    main = board.resolve(repo, main)
    listed = board.listed_by_stage(repo, main)
    done = set(listed["done"])
    kin = board.families(repo, main)
    targets = groom_targets(repo)

    waiting: list[dict[str, Any]] = []
    for slug in listed["backlog"]:
        issue = board.at_ref(repo, main, "backlog", slug)
        if issue and board.needs_elaboration(issue.body):
            why = first_line(board.section(issue.body, "Needs elaboration"))
            waiting.append(
                {"slug": slug, "why": f"needs elaboration: {why}", "answer": []}
            )
    for slug in listed["desk-check"]:
        issue = board.at_ref(repo, main, "desk-check", slug)
        if issue is None or not kin.get(slug):
            continue
        brief = first_line(board.last_section(issue.body, BRIEF))
        waiting.append(
            {
                "slug": slug,
                "why": f"desk check: {brief}",
                "answer": [f"just pair-accept {slug}", f"just pair-resume {slug}"],
            }
        )
    for kind, st in states.items():
        slug = "grooming pass" if st.get("stage") == GROOMING else st.get("slug", "?")
        if kind == "pair" and st.get("retry") == "desk-check":
            waiting.append(
                {
                    "slug": slug,
                    "why": "desk check in worktrees/pair",
                    "answer": ["just pair-accept", "just pair-resume"],
                }
            )
        elif st.get("paused"):
            waiting.append({"slug": slug, "why": f"paused: {st['paused']}", "answer": []})

    def entry(node: board.Node) -> dict[str, Any]:
        held = board.holds(repo, main, node.slug, done, kin)
        mark = (
            "being groomed"
            if node.slug in targets
            else f"waits on {', '.join(held)}"
            if held
            else "ripe"
        )
        out = sorted(
            (kid, stage) for kid, stage in kin.get(node.slug, {}).items() if stage != "backlog"
        )
        return {
            "slug": node.slug,
            "mark": mark,
            "flight": node.slug in kin,
            "out": [{"slug": kid, "stage": stage} for kid, stage in out],
            "parts": [entry(part) for part in node.parts],
        }

    rows: list[dict[str, Any]] = []
    for kind in ("pair", "groom"):
        turns = runtime_dir(repo, kind) / "turns.jsonl"
        if turns.is_file():
            rows += [json.loads(row) for row in turns.read_text().splitlines()[-4:]]
    return {
        "waiting": waiting,
        "underway": [
            {
                "kind": kind,
                "slug": st.get("slug", "?"),
                "stage": st.get("stage", "?"),
                "turn": st.get("turn", 0),
                "next_role": st.get("next_role", "?"),
                "approvals": st.get("approvals", []),
            }
            for kind, st in states.items()
        ],
        "order": [entry(node) for node in board.running_tree(repo, main, kin)],
        "to_groom": board.to_groom(repo, main),
        "counts": {stage: listed[stage] for stage in SHOWN},
        "sessions": [
            {"kind": kind, "role": role, "id": sid}
            for kind, st in states.items()
            for role, sid in st.get("sessions", {}).items()
        ],
        "turns": sorted(rows, key=lambda row: row.get("at", ""))[-4:],
    }


WIDTH = 34
"""The column the marks in `status` start at."""


def status(repo: Path, main: str = "main") -> str:
    """A plain-text rendering of `status_view`, with what waits on the developer first."""
    view = status_view(repo, main)
    lines: list[str] = []
    if view["waiting"]:
        lines.append("waits on you:")
        for item in view["waiting"]:
            lines.append(f"  {item['slug']:{WIDTH - 2}} {item['why']}")
            if item["answer"]:
                lines.append(f"  {'':{WIDTH - 2}} {', or '.join(item['answer'])}")
        lines.append("")
    for st in view["underway"]:
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
            f"underway: {what}, turn {st['turn']}, "
            f"next {st['next_role']}, "
            f"accepted by {', '.join(st['approvals']) or 'nobody yet'}"
        )
    if not view["underway"]:
        lines.append("nothing underway")

    def show(node: dict[str, Any], depth: int) -> None:
        pad = "  " * depth
        if not node["flight"]:
            lines.append(f"{pad}{node['slug']:{WIDTH - len(pad)}} {node['mark']}")
            return
        lines.append(f"{pad}{node['slug']} (Flight)")
        inner = "  " * (depth + 1)
        for kid in node["out"]:
            lines.append(f"{inner}{kid['slug']:{WIDTH - len(inner)}} {kid['stage']}")
        for part in node["parts"]:
            show(part, depth + 1)
        check = f"{node['slug']} check"
        lines.append(f"{inner}{check:{WIDTH - len(inner)}} {node['mark']}")

    lines.append("\nnext:" if view["order"] else "\nnext: nothing in backlog/")
    for node in view["order"]:
        show(node, 1)
    if view["to_groom"]:
        lines.append(f"to groom: {', '.join(view['to_groom'])}  (just groom)")
    lines.append("")
    for stage, slugs in view["counts"].items():
        lines.append(
            f"{stage:12} {len(slugs):3}  {', '.join(slugs[:6])}"
            f"{' ...' if len(slugs) > 6 else ''}"
        )
    if view["sessions"]:
        lines.append("")
    for s in view["sessions"]:
        lines.append(
            f"{s['role']:9} session {s['id']}  "
            f"(take over: cd worktrees/{s['kind']} && claude --resume {s['id']})"
        )
    if view["turns"]:
        lines.append("\nlast turns:")
        for row in view["turns"]:
            denials = row.get("denials")
            lines.append(
                f"  {row['slug']} {row['stage']} #{row['turn']} {row['role']:8} "
                f"{'quiet' if row['quiet'] else 'changed'}  {row['seconds']}s  "
                f"cache read {row['cache_read']}  write {row['cache_write']}"
                + ("" if denials is None else f"  denied {denials}")
            )
    return "\n".join(lines)


def status_json(repo: Path, main: str = "main") -> str:
    """`status_view` as one line of JSON, for a session that drives the loop; `status_view` documents the fields."""
    return json.dumps(status_view(repo, main))


def pairs_dir() -> Path:
    """Where every checkout's loop publishes its status: `PAIRS_DIR`, or `~/.pairs`."""
    named = os.environ.get("PAIRS_DIR")
    return Path(named) if named else Path.home() / ".pairs"


def publish(repo: Path, main: str = "main") -> str | None:
    """Write `status_view` and the checkout's path to `<pairs_dir>/<basename>.json`.

    This is the convention by which a cockpit reads every repository's loop
    without running anything in it. The file is written beside its final
    name under a name unique to this write and renamed into place, so a
    reader never sees half of it and, when the `pair` and `groom` loops
    publish at once, the last whole view wins. Nothing reads it back.

    Return None, or one line saying why the file could not be written.
    """
    here = repo.resolve()
    target = pairs_dir() / f"{here.name}.json"
    temporary: str | None = None
    try:
        text = json.dumps({"repo": str(here), **status_view(repo, main)})
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            dir=target.parent,
            prefix=f".{here.name}.",
            suffix=".tmp",
            delete=False,
        ) as f:
            temporary = f.name
            f.write(text)
        Path(temporary).replace(target)
    except Exception as error:  # noqa: BLE001  # reason: `status_view` raises too, on a board it cannot read or the other loop's `state.json` caught half-written, and the published file must never stop the loop
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
        return f"could not publish {target}: {error}"
    return None
