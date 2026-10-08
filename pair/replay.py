"""Replay an Issue that has landed, in a scratch clone, in either mode.

A replay runs a landed Issue again from the commit it started from, so that
`single` and `pair` mode are compared on the same Issue and the same code.
The clone has no remote, so nothing it does reaches `main`. Its files stay
under `.pair/replays/<slug>-<mode>/`:

- `replay-<slug>-<mode>/`, the clone itself, kept for inspection;
- `turns.jsonl` and `events.jsonl`, the clone's loop logs;
- `landed.diff`, what the replay landed on the clone's `main`;
- `outcome.json`, the outcome (`landed`, `sent-back`, `paused` or
  `clashed`), the mode, the start commit and the seconds the loop ran;
- `clash.txt`, for a `clashed` replay only: the output of the gate that the
  `Replay <slug>` commit failed with no seat's work.

The loop that runs the replay is the current one, from this checkout, run
in-process against the clone. For an Issue that changes `pair/`, the seats
edit the clone's own old `pair/`, not the loop that runs them.

Today's loop writes into the clone's tree and calls the clone's recipes,
whose code and checks are those of the replayed Issue's era. Each place it
does so is kept out of the old code's way, or cannot reach it:

- The runtime state, `.pair/`, and the loop's worktrees, `worktrees/`, are
  excluded from git in the clone (`IGNORED`), since a start commit's
  `.gitignore` may predate them. No code of the clone's era reads `.pair/`
  once the gate is called one target at a time: an older `gate` recipe took
  one target and ran the rest as recipes, so `just gate meta pair` ran the
  clone's own `pair` recipe, its old loop, which read today's
  `.pair/state.json` and crashed.
- The gate is called once per target (`era_gate`), a form every era's
  `gate` recipe accepts, or once with no target for the whole gate. The
  failure the seats are handed still names `just gate` with every target
  (`gate_fails` in `loop.py`), which a seat rerunning it in an old era would
  clash on; the output's headings name each single-target command to rerun
  instead.
- The notes (`Loop.keep_note`, `Loop.restore_notes`) and the supervisor's
  gate lines (`Loop.keep_gate`) stay in the Issue file, where the seats read
  and write them as they do outside a replay, so the comparison measures
  the same seats. While the gate runs, `era_gate` takes them out of the
  Issue file (`board.without_notes`) and afterwards writes the file back
  byte for byte, so the clone's checks see the file as its era wrote it,
  whatever a note quotes. This is done in place, not in a copy of the
  worktree, because a copy would lack what `just setup` built there, and
  the supervisor gates only between turns, when no seat is writing.
- `just setup` is the clone's own era provisioning its own worktree, and
  `just --summary` only lists recipes, so both are left as they are. `just
  deliver` is never run: a replay's loop has no delivery, so no recipe of
  any era delivers from a scratch clone.

A replay that ends other than `landed`, after a last gate that failed or
could not run, gates its `Replay <slug>` commit on the same targets with no
seat's work (`clash`). If that fails too, the failure is the era's and not
the seats', and the outcome is `clashed`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import board
from board import git
from loop import NOTE_STOPS, Gate, Loop, event_log, gate_unrunnable, pairs_dir, supervise

KEPT = ("done", "roadmap")
"""The stage directories whose Issues a replay's clone keeps: the history it starts from."""

IDENTITY = ("user.name", "user.email", "commit.gpgsign")
"""The source's local git settings the clone copies, so its commits are made as the source's are."""

IGNORED = ("/.pair/", "/worktrees/")
"""What the loop writes in a checkout, which a start commit's `.gitignore` may not yet ignore."""

CLASHED = "clashed"
"""The outcome of a replay whose `Replay <slug>` commit fails the gate its seats' work failed."""

LOGS = ("turns.jsonl", "events.jsonl")
"""The clone's loop logs, from its `.pair/`, that a replay keeps."""


REFUSALS = {
    "unstarted": "{slug}: no commit on main has the subject `Start {slug}`",
    "flight": "{slug} is a Flight: its work landed in its parts; replay those",
    "absent": "{slug}: not on the board at {start}, the commit it started from",
    "replayed": "{slug} has a {mode} replay in {home} already; --force replaces it",
}
"""Why a replay cannot be made, by reason, each naming the slug."""


class RefusalError(Exception):
    """A replay that cannot be made: one of `REFUSALS`, filled in from `fields`."""

    def __init__(self, reason: str, **fields: object) -> None:
        super().__init__(REFUSALS[reason].format(**fields))
        self.reason = reason


def replays_dir(source: Path) -> Path:
    """Where `source` keeps its replays, inside its ignored `.pair/`."""
    return source / ".pair" / "replays"


def replay_dir(source: Path, slug: str, mode: str) -> Path:
    """The directory one replay of `slug` in `mode` keeps its clone and files in."""
    return replays_dir(source) / f"{slug}-{mode}"


def start_commit(source: Path, slug: str) -> str:
    """The commit `slug` started from: the parent of its last `Start <slug>` commit on `main`.

    The subject must be exactly `Start <slug>`, because commits that are not
    the loop's also begin with `Start `. The last such commit is taken,
    because an Issue sent back and started again has one for each start, and
    only the last led to its landing. A Flight is refused: its work landed in
    its parts. Its children are read on `main`, since a `hard` Issue is split
    after its `Start` commit.
    """
    subject = f"Start {slug}"
    for line in git(source, "log", "main", "--format=%H%x00%s").splitlines():
        sha, _, said = line.partition("\0")
        if said == subject:
            break
    else:
        raise RefusalError("unstarted", slug=slug)
    if board.children(source, "main", slug):
        raise RefusalError("flight", slug=slug)
    return git(source, "rev-parse", f"{sha}^")


def prepare(source: Path, start: str, slug: str, clone: Path) -> str:
    """Clone `source` into `clone` with `main` at `start` and only `slug` in the backlog.

    The clone has no remote. One commit, `Replay <slug>`, moves the Issue's
    file into `issues/backlog/` where it sits elsewhere, removes every other
    Issue file in a stage directory but `done/` and `roadmap/`, keeping each
    `README.md`, and drops the removed slugs from `ORDER`. Returns that
    commit, from which the replay's landed diff is taken.
    """
    git(source, "clone", "-q", "--no-checkout", str(source), str(clone))
    git(clone, "remote", "remove", "origin")
    for key in IDENTITY:
        value = git(source, "config", "--local", "--get", key, check=False)
        if value:
            git(clone, "config", key, value)
    git(clone, "checkout", "-q", "-B", "main", start)
    exclude = clone / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with exclude.open("a") as f:
        f.write("".join(f"{path}\n" for path in IGNORED))
    found = [s for s in board.locations(clone, slug) if s not in KEPT]
    if not found:
        raise RefusalError("absent", slug=slug, start=start[:12])
    backlog = f"{board.ISSUES}/backlog"
    if found[0] != "backlog":
        (clone / backlog).mkdir(parents=True, exist_ok=True)
        git(clone, "mv", f"{board.ISSUES}/{found[0]}/{slug}.md", f"{backlog}/{slug}.md")
    keep = f"{backlog}/{slug}.md"
    removed = []
    for stage in sorted(p for p in (clone / board.ISSUES).iterdir() if p.is_dir()):
        if stage.name in KEPT:
            continue
        for path in sorted(stage.glob("*.md")):
            rel = path.relative_to(clone).as_posix()
            if path.name != "README.md" and rel != keep:
                git(clone, "rm", "-q", rel)
                removed.append(path.stem)
    order = clone / board.ORDER
    if order.is_file():
        text = order.read_text()
        for gone in removed:
            text = board.without(text, gone)
        order.write_text(text)
        git(clone, "add", board.ORDER)
    git(clone, "commit", "-q", "--allow-empty", "-m", f"Replay {slug}")
    return git(clone, "rev-parse", "HEAD")


def outcome_of(answer: str) -> str:
    """The replay's outcome for what the loop last answered.

    The loop answers `kicked` when it sends an Issue back for elaboration,
    which it logs as `sent-back`. Anything that is neither a landing nor a
    send-back left the Issue waiting on the developer.
    """
    return {"landed": "landed", "kicked": "sent-back"}.get(answer, "paused")


def era_gate(gate: Gate, slug: str) -> Gate:
    """`gate`, called in a form any era's `gate` recipe accepts, past the loop's notes.

    Each target is gated by a call of its own, so a `gate` recipe that takes
    one target never runs a second as a recipe; with no targets, the whole
    gate is one call, as before. The result passes only if every call
    passed. Each call's output comes under a heading naming its command
    (`=== just gate <target> ===`), and a failed call's output comes after
    every passed one's, because the seats are handed only the tail of the
    output (`gate_fails` in `loop.py`), which a long passing target would
    otherwise fill.

    During the calls, `slug`'s Issue file in the tree is without its `Pair
    notes` and gate lines (`board.without_notes`); afterwards it is written
    back exactly as it was.
    """

    def gated(
        tree: Path, targets: Sequence[str] | None, env: Mapping[str, str]
    ) -> tuple[bool, str]:
        issue = board.read(tree, slug)
        path = None if issue is None else tree / issue.path
        kept = None if path is None else path.read_bytes()
        try:
            if path is not None and kept is not None:
                text = kept.decode()
                stripped = board.without_notes(text, NOTE_STOPS)
                if stripped != text:
                    path.write_text(stripped)
            if targets is None:
                return gate(tree, None, env)
            passed: list[str] = []
            failed: list[str] = []
            for target in targets:
                ok, out = gate(tree, [target], env)
                (passed if ok else failed).append(f"=== just gate {target} ===\n{out}")
            return not failed, "\n".join(passed + failed)
        finally:
            if path is not None and kept is not None:
                path.write_bytes(kept)

    return gated


def last_gate(events: Path, slug: str) -> dict[str, Any] | None:
    """The last `gated` event for `slug` in the event log `events`, or None."""
    found = None
    lines = events.read_text().splitlines() if events.is_file() else []
    for line in lines:
        event = json.loads(line) if line.strip() else {}
        if event.get("kind") == "gated" and event.get("slug") == slug:
            found = event
    return found


def clash(loop: Loop, clone: Path, base: str, targets: Sequence[str] | None) -> str | None:
    """The output of the gate that `base` fails on `targets` with no seat's work, or None.

    `base` is checked out in a detached worktree outside the clone, so the
    kept clone stays as the seats left it, provisioned as the loop's own
    worktree is (`loop.provision`), and gated through the loop's gate. A
    provisioning that fails is the era failing, and its error is the output.
    A gate that passes with a step that could not run counts as failed, as
    it does for the loop.
    """
    with tempfile.TemporaryDirectory(prefix="replay-base-") as tmp:
        tree = Path(tmp) / "base"
        git(clone, "worktree", "add", "-q", "--detach", str(tree), base)
        try:
            if loop.provision:
                try:
                    loop.provision(tree)
                except subprocess.CalledProcessError as failed:
                    return f"provisioning the Replay commit failed: {failed}\n"
            ok, out = loop.gate(tree, targets, loop.gate_env())
            return None if ok and gate_unrunnable(out) is None else out
        finally:
            git(clone, "worktree", "remove", "--force", str(tree), check=False)
            git(clone, "worktree", "prune", check=False)


def replay(
    source: Path,
    slug: str,
    mode: str,
    make_loop: Callable[[Path, str], Loop],
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Replay `slug` in `mode` in a scratch clone of `source`, and return its outcome.

    `make_loop` builds the loop for the clone in `mode`. The loop runs one
    Issue, and a desk check it stops at is accepted, so a `developer` Issue
    completes. An earlier replay of the same slug and mode is refused unless
    `force`, which deletes it, but only once the slug is known to replay. A
    clone that `prepare` refuses or fails to finish is deleted, so it does
    not stand in the way of the next replay as an earlier one.

    The loop's gate is wrapped in `era_gate` and its delivery taken away, and
    a replay that did not land on a failed gate is checked for a clash
    (`clash`), as the module docstring says.

    `publish` names a loop's status after its checkout, so the clone's status
    would show the replay as a portfolio in a cockpit. It is removed however
    the replay ends.
    """
    start = start_commit(source, slug)
    home = replay_dir(source, slug, mode)
    if home.exists():
        if not force:
            raise RefusalError("replayed", slug=slug, mode=mode, home=home)
        shutil.rmtree(home)
    clone = home / f"replay-{slug}-{mode}"
    try:
        try:
            base = prepare(source, start, slug, clone)
        except BaseException:
            shutil.rmtree(home, ignore_errors=True)
            raise
        loop = make_loop(clone, mode)
        loop.gate = era_gate(loop.gate, slug)
        loop.deliver = None

        def work() -> str:
            answer = loop.run(once=True)
            return loop.accept() if answer == "desk-check" else answer

        began = time.monotonic()
        answer = supervise(clone, "pair", work)
        seconds = time.monotonic() - began
    finally:
        (pairs_dir() / f"{clone.name}.json").unlink(missing_ok=True)
    for name in LOGS:
        log = clone / ".pair" / name
        if log.is_file():
            shutil.copyfile(log, home / name)
    diff = git(clone, "diff", base, "main")
    (home / "landed.diff").write_text(f"{diff}\n" if diff else "")
    outcome = outcome_of(answer)
    last = last_gate(event_log(clone), slug)
    if outcome != "landed" and last and last.get("outcome") in ("failed", "could-not-run"):
        out = clash(loop, clone, base, last.get("targets"))
        if out is not None:
            outcome = CLASHED
            (home / "clash.txt").write_text(out)
    result = {
        "slug": slug,
        "mode": mode,
        "outcome": outcome,
        "answer": answer,
        "start": start,
        "seconds": round(seconds, 1),
    }
    (home / "outcome.json").write_text(json.dumps(result, indent=1) + "\n")
    return result
