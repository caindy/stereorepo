"""Replay an Issue that has landed, in a scratch clone, in either mode.

A replay runs a landed Issue again from the commit it started from, so that
`single` and `pair` mode are compared on the same Issue and the same code.
The clone has no remote, so nothing it does reaches `main`. Its files stay
under `.pair/replays/<slug>-<mode>/`:

- `replay-<slug>-<mode>/`, the clone itself, kept for inspection;
- `turns.jsonl` and `events.jsonl`, the clone's loop logs;
- `landed.diff`, what the replay landed on the clone's `main`;
- `outcome.json`, the outcome (`landed`, `sent-back` or `paused`), the mode,
  the start commit and the seconds the loop ran.

The loop that runs the replay is the current one, from this checkout, run
in-process against the clone. For an Issue that changes `pair/`, the seats
edit the clone's own old `pair/`, not the loop that runs them.
"""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import board
from board import git
from loop import Loop, pairs_dir, supervise

KEPT = ("done", "roadmap")
"""The stage directories whose Issues a replay's clone keeps: the history it starts from."""

IDENTITY = ("user.name", "user.email", "commit.gpgsign")
"""The source's local git settings the clone copies, so its commits are made as the source's are."""

IGNORED = ("/.pair/", "/worktrees/")
"""What the loop writes in a checkout, which a start commit's `.gitignore` may not yet ignore."""

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
    result = {
        "slug": slug,
        "mode": mode,
        "outcome": outcome_of(answer),
        "answer": answer,
        "start": start,
        "seconds": round(seconds, 1),
    }
    (home / "outcome.json").write_text(json.dumps(result, indent=1) + "\n")
    return result
