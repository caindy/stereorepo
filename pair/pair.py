# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""pair: run issues from issues/backlog/ to main through two paired Claude Code seats.

Run from the root of the repository whose board it works; the loop's own code
stays wherever this file is, outside that repository's tree (see README.md):

    uv run --script <stereorepo>/pair/pair.py run [--once] [--push] [--flight SLUG]
        [--model M] [--STAGE-model M] [--round-cap N]
    uv run --script <stereorepo>/pair/pair.py groom [--rerank] [--push] [--model M] [--round-cap N]
    uv run --script <stereorepo>/pair/pair.py status [--json]
    uv run --script <stereorepo>/pair/pair.py accept [SLUG] [--model M] [--STAGE-model M]
    uv run --script <stereorepo>/pair/pair.py resume [SLUG] [--model M] [--STAGE-model M]
    uv run --script <stereorepo>/pair/pair.py watch --until landed|developer|flight SLUG

With `--flight`, `run` works only that Flight and the Issues below it, and
stops when the Flight reaches its desk check.

`--STAGE-model` names the model both seats run in one stage of an Issue
(`backlog`, `flight-check`, `todo` or `in-progress`), in place of `--model`.

With SLUG, `accept` and `resume` answer the desk check of that Flight on
`main`, in your checkout, and run alongside a running loop.

`groom` runs in its own worktree and holds its own lock, so a grooming pass
runs alongside `run`.

`watch` prints the events both log to `.pair/events.jsonl` until its
condition is met, and exits non-zero if the loops it watches end first.

`run`, `groom`, `accept` and `resume` print their outcome as `pair: <outcome>`
and exit with the code `EXIT` gives it, 0 when nothing more is needed.

In stereorepo itself, `just pair`, `just groom`, `just pair-status`,
`just pair-accept`, `just pair-resume` and `just pair-watch` run the same.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import signal
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import IO

from loop import FLIGHT_CHECK, Loop, append_event, status, status_json
from seats import ClaudeSeat
from watch import CONDITIONS, watch

HERE = Path(__file__).resolve().parent

PROMPTS = HERE / "prompts"

EXIT = {
    "landed": 0,
    "groomed": 0,
    "accepted": 0,
    "resumed": 0,
    "desk-check": 3,
    "paused": 4,
    "stopped": 5,
    "kicked": 6,
    "empty": 7,
    "nothing": 8,
    "refused": 9,
    "none": 10,
}
"""The exit code of each outcome of `run`, `groom`, `accept` and `resume`.

0 means the command did what it was asked and needs nothing more. No code
is 1, which Python gives an uncaught exception, or 2, which `argparse`
gives a usage error.
"""

LOCKED = 11
"""The exit code when another process holds the lock the command needs."""


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


def gate(tree: Path, targets: Sequence[str] | None) -> tuple[bool, str]:
    """`just gate` in the worktree over `targets`, or over every Project for `None`.

    The loop names the Projects the branch touches and the Products built from
    them (`touched.select`), and not every Project: the full gate cost 2 to 2.5
    minutes an Issue, and the developer accepted that a break the path mapping
    cannot see lands unchecked (stereorepo's DR-303).
    """
    command = ["just", "gate", *(targets or [])]
    done = subprocess.run(command, check=False, cwd=tree, capture_output=True, text=True)
    return done.returncode == 0, done.stdout + done.stderr


def recipes(tree: Path) -> list[str]:
    """The names of the recipes the `justfile` in `tree` defines."""
    return subprocess.run(
        ["just", "--summary"], check=False, cwd=tree, capture_output=True, text=True
    ).stdout.split()


def provision(tree: Path) -> None:
    """Run `just setup` in a fresh worktree, where the repository defines one.

    A worktree gets its own environment rather than the main checkout's, so
    the gate tests the branch and not what happens to be installed beside it.
    """
    if "setup" in recipes(tree):
        print(f"provisioning {tree.parent.name}/{tree.name} (just setup) ...", flush=True)
        subprocess.run(["just", "setup"], cwd=tree, check=True)


def deliver(tree: Path) -> tuple[bool, str] | None:
    """`just deliver` in the worktree, or `None` where the repository defines none.

    Delivery is the repository's business, such as a redeployment to a UAT
    environment; the loop knows only whether the recipe passed. The output is
    captured, so the line printed first is what the terminal shows while a
    slow delivery runs.
    """
    if "deliver" not in recipes(tree):
        return None
    print(f"delivering from {tree.parent.name}/{tree.name} (just deliver) ...", flush=True)
    done = subprocess.run(
        ["just", "deliver"], check=False, cwd=tree, capture_output=True, text=True
    )
    return done.returncode == 0, done.stdout + done.stderr


def hold_lock(repo: Path, name: str = "run.lock") -> IO[str] | None:
    """Take one of the repository's locks and write this process's pid into it.

    `run.lock` is held by the loop working Issues, and `groom.lock` by a
    grooming pass, so a pass and an Issue run at once, but never two of either.

    The lock file is opened without truncating, so a second process that is
    refused the lock cannot erase the pid of the one holding it. Returns the
    open file, which holds the lock until the process exits, or `None` when
    another process holds it.
    """
    (repo / ".pair").mkdir(exist_ok=True)
    lock = (repo / ".pair" / name).open("a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        return None
    lock.truncate(0)
    lock.write(f"{os.getpid()}\n")
    lock.flush()
    return lock


STAGE_MODELS = ("backlog", FLIGHT_CHECK, "todo", "in-progress")
"""The stages of an Issue in which seats take turns, each of which may name its own model."""


def arguments() -> argparse.ArgumentParser:
    """The command line of every subcommand."""
    parser = argparse.ArgumentParser(prog="pair", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    seats = argparse.ArgumentParser(add_help=False)
    seats.add_argument("--model", help="model for both seats (default: the CLI's)")
    seats.add_argument(
        "--round-cap",
        type=int,
        help="rounds per stage for every difficulty (default: by difficulty)",
    )
    stages = argparse.ArgumentParser(add_help=False)
    for stage in STAGE_MODELS:
        stages.add_argument(
            f"--{stage}-model",
            metavar="MODEL",
            help=f"model for both seats in {stage} (default: --model)",
        )
    run = sub.add_parser(
        "run",
        parents=[seats, stages],
        help="work issues until the backlog is empty or the developer is needed",
    )
    run.add_argument("--once", action="store_true", help="stop after one issue")
    run.add_argument(
        "--push", action="store_true", help="push main to origin after each landing"
    )
    run.add_argument(
        "--flight",
        metavar="SLUG",
        help="work only this Flight's Issues, and stop at its desk check",
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
    shown = sub.add_parser(
        "status",
        help="what waits on you, what is underway, the running order and the counts",
    )
    shown.add_argument(
        "--json", action="store_true", help="print the same state as one JSON object"
    )
    accept = sub.add_parser(
        "accept", parents=[seats, stages], help="pass the desk check and merge"
    )
    resume = sub.add_parser(
        "resume",
        parents=[seats, stages],
        help="fail the desk check; the pair picks up your notes",
    )
    for desk in (accept, resume):
        desk.add_argument(
            "slug",
            nargs="?",
            help="a Flight in issues/desk-check/, answered on main without the loop",
        )
    follow = sub.add_parser(
        "watch",
        help="print the loop's events until a condition is met; non-zero if the loop ends first",
    )
    follow.add_argument(
        "--until",
        nargs="+",
        required=True,
        metavar="CONDITION",
        help="landed, developer (a desk check, a pause or a send-back), or flight SLUG",
    )
    return parser


def main() -> int:
    parser = arguments()
    args = parser.parse_args()
    if args.command == "watch":
        until = args.until
        if until[0] not in CONDITIONS or len(until) != (2 if until[0] == "flight" else 1):
            parser.error("--until takes landed, developer, or flight SLUG")

    repo = repo_root()
    if args.command == "status":
        print(status_json(repo) if args.json else status(repo))
        return 0
    if args.command == "watch":
        return watch(repo, args.until, out=lambda line: print(line, flush=True))

    kind = "groom" if args.command == "groom" else "pair"
    system = {
        role: (PROMPTS / f"{role}.md").read_text() for role in ("primary", "secondary")
    }
    loop = Loop(
        repo,
        lambda role, cwd, resume, model: ClaudeSeat(
            role, cwd, system[role], loop.dir, resume=resume, model=model
        ),
        gate,
        notify,
        prompts=PROMPTS,
        push=getattr(args, "push", False),
        provision=provision,
        deliver=deliver,
        say=lambda message: print(message, flush=True),
        round_cap=args.round_cap,
        kind=kind,
        model=args.model,
        stage_models={
            stage: getattr(args, f"{stage.replace('-', '_')}_model", None)
            for stage in STAGE_MODELS
        },
    )

    desk = getattr(args, "slug", None)
    if desk:
        answer = loop.accept if args.command == "accept" else loop.resume
        outcome = answer(desk)
        print(f"pair: {outcome}")
        return EXIT[outcome]

    lock = hold_lock(repo, "groom.lock" if kind == "groom" else "run.lock")
    if lock is None:
        doing = "grooming pass" if kind == "groom" else "loop working Issues"
        print(f"another {doing} is running in this repository")
        return LOCKED

    def stop(_sig: int, _frame: object) -> None:
        if loop.stop_requested:
            raise KeyboardInterrupt
        loop.stop_requested = True
        print(
            "\nstopping after the current turn (Ctrl-C again to abandon it)", flush=True
        )

    signal.signal(signal.SIGINT, stop)
    work = {
        "run": lambda: loop.run(once=args.once, flight=args.flight),
        "groom": lambda: loop.groom(rerank=args.rerank),
        "accept": loop.accept,
        "resume": loop.resume,
    }[args.command]
    outcome = supervise(repo, kind, work)
    print(f"pair: {outcome}")
    return EXIT[outcome]


def supervise(repo: Path, kind: str, work: Callable[[], str]) -> str:
    """Run a supervisor's `work` and log its end, which a watcher waits for.

    The `ended` event carries the outcome `work` answers, `abandoned` on a
    second Ctrl-C, and `crashed` on any other exception, which is raised
    again.
    """
    outcome = "crashed"
    try:
        outcome = work()
    except KeyboardInterrupt:
        outcome = "abandoned"
        raise
    finally:
        append_event(repo, kind, "ended", outcome=outcome)
    return outcome


if __name__ == "__main__":
    sys.exit(main())
