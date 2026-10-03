"""Follow `.pair/events.jsonl` until a condition is met, or the loops watched have ended.

A watcher watches the supervisors that hold a lock in `.pair/` when it starts:
the loop working Issues (`run.lock`) and a grooming pass (`groom.lock`). It
never outlives them. It exits 0 when its condition is met, `ENDED_FIRST`
(12) when every supervisor it watches has ended first, logged or killed, and
`NOT_RUNNING` (13) at once when none is running. Neither is 1, which Python
gives an uncaught exception, or 2, which `argparse` gives a usage error, nor a
code `pair.py` gives another outcome.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from loop import event_log

LOCKS = {"pair": "run.lock", "groom": "groom.lock"}
"""Each loop's kind, as its events name it, against the lock its supervisor holds."""
DEVELOPER = frozenset({"desk-check", "paused", "sent-back"})
"""The event kinds that leave something waiting on the developer."""
WAITING = frozenset({"desk-check", "paused"})
"""The outcomes of `ended` that mean the run stopped to wait on the developer.

`run` ends with `desk-check` at once, logging nothing else, when the Issue
underway already waits on its desk check."""
CONDITIONS = ("landed", "developer", "flight")
ENDED_FIRST = 12
"""The exit code when every supervisor watched ended without meeting the condition."""
NOT_RUNNING = 13
"""The exit code when no supervisor is running to watch."""


def running(pid: int) -> bool:
    """Whether `pid` is a live process running `pair.py`, and not this one.

    The command line is read because a pid in a lock file outlives its
    process, and the system may give it to another. The watcher runs
    `pair.py` too, so it never counts itself.
    """
    if pid == os.getpid():
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    command = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="], check=False, capture_output=True, text=True
    ).stdout
    return "pair.py" in command


def supervisor(repo: Path, lock: str) -> int | None:
    """The pid in `.pair/<lock>` if a supervisor still runs under it.

    The pid is read rather than the lock probed: a probe takes the lock for
    a moment, and a supervisor starting then would be refused it.
    """
    try:
        pid = int((repo / ".pair" / lock).read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return None
    return pid if running(pid) else None


def meets(until: list[str], event: dict[str, Any]) -> bool:
    """Whether `event` meets the condition `until` names."""
    kind = event.get("kind")
    if until[0] == "landed":
        return kind == "landed"
    if until[0] == "developer":
        return kind in DEVELOPER or (kind == "ended" and event.get("outcome") in WAITING)
    return kind == "desk-check" and event.get("slug") == until[1]


def describe(event: dict[str, Any]) -> str:
    """One line for an event: its time, loop, kind and slug, then its other fields."""
    head = [str(event.get(key, "")) for key in ("at", "loop", "kind", "slug")]
    rest = [
        f"{key}={json.dumps(value) if isinstance(value, str) and ' ' in value else value}"
        for key, value in event.items()
        if key not in ("at", "loop", "kind", "slug")
    ]
    return " ".join(part for part in head + rest if part)


class Tail:
    """The events appended to the log after the tail was opened, whole lines only."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = path.stat().st_size if path.is_file() else 0
        self.partial = b""

    def read(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        with self.path.open("rb") as f:
            f.seek(self.offset)
            chunk = f.read()
        self.offset += len(chunk)
        *lines, self.partial = (self.partial + chunk).split(b"\n")
        events = []
        for line in lines:
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
        return events


def watch(
    repo: Path,
    until: list[str],
    poll: float = 0.5,
    out: Callable[[str], None] = print,
) -> int:
    """Print events as they are appended until `until` is met; answer the exit code.

    Each poll looks for supervisors that have gone before it reads the new
    events, so whatever a supervisor wrote before it died is read, and a
    matching event wins over the `ended` that follows it.
    """
    watched = {
        loop: pid for loop, lock in LOCKS.items() if (pid := supervisor(repo, lock))
    }
    if not watched:
        out("no pair loop or grooming pass is running")
        return NOT_RUNNING
    tail = Tail(event_log(repo))
    while True:
        watched = {loop: pid for loop, pid in watched.items() if running(pid)}
        for event in tail.read():
            out(describe(event))
            if meets(until, event):
                return 0
            if event.get("kind") == "ended":
                watched.pop(event.get("loop"), None)
        if not watched:
            out("the loop ended without meeting the condition")
            return ENDED_FIRST
        time.sleep(poll)
