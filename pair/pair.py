# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""pair: run issues from issues/backlog/ to main through two paired Claude Code seats.

Run from the root of the repository whose board it works; the loop's own code
stays wherever this file is, outside that repository's tree (see README.md):

    uv run --script <stereorepo>/pair/pair.py run [--once] [--push] [--model M] [--round-cap N]
    uv run --script <stereorepo>/pair/pair.py groom [--rerank] [--push] [--model M] [--round-cap N]
    uv run --script <stereorepo>/pair/pair.py status
    uv run --script <stereorepo>/pair/pair.py accept
    uv run --script <stereorepo>/pair/pair.py resume

In stereorepo itself, `just pair`, `just groom`, `just pair-status`,
`just pair-accept` and `just pair-resume` run the same.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import IO

from loop import Loop, status
from seats import ClaudeSeat

HERE = Path(__file__).resolve().parent

PROMPTS = HERE / "prompts"


def repo_root() -> Path:
    common = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return Path(common).parent


def notify(message: str) -> None:
    print("\a", end="", flush=True)
    script = f'display notification {json_quote(message)} with title "pair"'
    subprocess.run(["osascript", "-e", script], capture_output=True, check=False)


def json_quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def gate(tree: Path) -> tuple[bool, str]:
    """`just gate` in the worktree: the repository's whole pre-merge gate.

    The whole gate and not a fast subset, because a check a seat asks for and
    the loop does not run is a request that addresses nobody.
    """
    done = subprocess.run(["just", "gate"], cwd=tree, capture_output=True, text=True)
    return done.returncode == 0, done.stdout + done.stderr


def provision(tree: Path) -> None:
    """Run `just setup` in a fresh worktree, where the repository defines one.

    A worktree gets its own environment rather than the main checkout's, so
    the gate tests the branch and not what happens to be installed beside it.
    """
    recipes = subprocess.run(
        ["just", "--summary"], cwd=tree, capture_output=True, text=True
    ).stdout.split()
    if "setup" in recipes:
        print("provisioning worktrees/pair (just setup) ...", flush=True)
        subprocess.run(["just", "setup"], cwd=tree, check=True)


def hold_lock(repo: Path) -> IO[str] | None:
    """Take the repository's run lock and write this process's pid into it.

    The lock file is opened without truncating, so a second process that is
    refused the lock cannot erase the pid of the one holding it. Returns the
    open file, which holds the lock until the process exits, or `None` when
    another process holds it.
    """
    (repo / ".pair").mkdir(exist_ok=True)
    lock = (repo / ".pair" / "run.lock").open("a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        return None
    lock.truncate(0)
    lock.write(f"{os.getpid()}\n")
    lock.flush()
    return lock


def main() -> int:
    parser = argparse.ArgumentParser(prog="pair", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    seats = argparse.ArgumentParser(add_help=False)
    seats.add_argument("--model", help="model for both seats (default: the CLI's)")
    seats.add_argument(
        "--round-cap",
        type=int,
        help="rounds per stage for every difficulty (default: by difficulty)",
    )
    run = sub.add_parser(
        "run",
        parents=[seats],
        help="work issues until the backlog is empty or the developer is needed",
    )
    run.add_argument("--once", action="store_true", help="stop after one issue")
    run.add_argument(
        "--push", action="store_true", help="push main to origin after each landing"
    )
    groom = sub.add_parser(
        "groom",
        parents=[seats],
        help="groom the backlog issues that are not groomed, and place them in ORDER",
    )
    groom.add_argument(
        "--rerank",
        action="store_true",
        help="rank the whole order below the marker again",
    )
    groom.add_argument(
        "--push", action="store_true", help="push main to origin after the pass lands"
    )
    sub.add_parser("status", help="the board on main and the issue in flight")
    sub.add_parser("accept", parents=[seats], help="pass the desk check and merge")
    sub.add_parser(
        "resume",
        parents=[seats],
        help="fail the desk check; the pair picks up your notes",
    )
    args = parser.parse_args()

    repo = repo_root()
    if args.command == "status":
        print(status(repo))
        return 0

    lock = hold_lock(repo)
    if lock is None:
        print("another pair process is running in this repository")
        return 1

    model = getattr(args, "model", None)
    system = {
        role: (PROMPTS / f"{role}.md").read_text() for role in ("primary", "secondary")
    }
    loop = Loop(
        repo,
        lambda role, cwd, resume: ClaudeSeat(
            role, cwd, system[role], repo / ".pair", resume=resume, model=model
        ),
        gate,
        notify,
        prompts=PROMPTS,
        push=getattr(args, "push", False),
        provision=provision,
        say=lambda message: print(message, flush=True),
        round_cap=args.round_cap,
    )

    def stop(_sig: int, _frame: object) -> None:
        if loop.stop_requested:
            raise KeyboardInterrupt
        loop.stop_requested = True
        print(
            "\nstopping after the current turn (Ctrl-C again to abandon it)", flush=True
        )

    signal.signal(signal.SIGINT, stop)
    if args.command == "run":
        outcome = loop.run(once=args.once)
    elif args.command == "groom":
        outcome = loop.groom(rerank=args.rerank)
    elif args.command == "accept":
        outcome = loop.accept()
    else:
        outcome = loop.resume()
    print(f"pair: {outcome}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
