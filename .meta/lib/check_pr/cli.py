"""The argument surface of `.meta/check_pr.py`, apart from the script that names it.

Every mode is one flag, and each dispatches to the module that owns it. The
script passes its own docstring in as the description so `--help` reads the
same as it always did.
"""
import argparse
import json
import pathlib
import sys
from collections.abc import Callable

from lib.check_pr import branch, form, github, polling, review, sweep, verdict


def parser(description: str) -> argparse.ArgumentParser:
    """The command line: one positional pull request and the flags that each name a mode.

    Args:
        description: The script's docstring, shown by `--help`.
    """
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("pr", nargs="?", help="pull request number, URL or branch")
    ap.add_argument("--file", help="read a body from disk instead of GitHub")
    ap.add_argument("--title", default="a real title", help="title to use with --file")
    ap.add_argument("--threads", action="store_true",
                    help="print the threads owed, held, and answered, and each verdict "
                         "with the head it was given on; check nothing")
    ap.add_argument("--unresolved-count", action="store_true",
                    help="print the count of unresolved review threads on this pull request; check nothing")
    ap.add_argument("--resume", action="store_true",
                    help="what an arriving Job needs, read from GitHub")
    ap.add_argument("--handoff", action="store_true",
                    help="A18: a dirty worktree, or a branch ahead of its remote. "
                         "Beside it: a generated page this branch left un-rendered, or "
                         "an artifact it edits that no decision it settles names")
    ap.add_argument("--base", default="origin/main",
                    help="what --handoff reads this branch against (default origin/main); "
                         "a layer of a stack is read against the layer below")
    ap.add_argument("--hand-back", metavar="ISSUE",
                    help="as JSON, what a dead run's hand-back needs about the pull "
                         "request on a Challenge's branch: whether anybody holds it, "
                         "whether it is green, and whether it conflicts")
    ap.add_argument("--sweep", action="store_true",
                    help="every open pull request you own, and what each still owes")
    ap.add_argument("--watch", action="store_true",
                    help="one line per change on the pull request, exiting on actionable events or when it closes")
    ap.add_argument("--every", type=int, default=60, help="seconds between polls under --watch")
    ap.add_argument("--retries", type=int, default=5,
                    help="maximum retry attempts after a failed poll under --watch before circuit breaker trips")
    ap.add_argument("--all", action="store_true",
                    help="the check on every open pull request, one line each, and who "
                         "holds each one next")
    ap.add_argument("--publish", action="store_true",
                    help="with --all: post each result as the required check run")
    return ap


def print_sweep() -> None:
    """What this branch owns and what each open pull request still owes, then the branches that outlived their pull request.

    The two halves fail apart. What GitHub answers for is asked first and is
    reported unreadable when it will not, naming what it refused with, because
    a silent empty list here reads as a branch that owns nothing. The residue
    below reads the tree, so the branches an operator came to remove print
    either way.
    """
    try:
        head, found = branch.owned_and_open()
    except SystemExit as unreadable:
        print("?  open pull requests are not readable from here; "
              "what this branch owns is unchecked")
        print(f"   {github.reason(unreadable)}")
    else:
        if not found:
            print(f"no open pull request for branch '{head}'" if head
                  else "no open pull requests")
        for number, title, owed in found:
            notice = branch.advance_notice(number)
            tag = " (advance notice standing)" if notice else ""
            if owed is None:
                print(f"#{number} {title} — open, and not this branch's{tag}")
                if notice:
                    print(f"    advance: {notice}")
                continue
            print(f"#{number} {title} — {len(owed)} unaddressed{tag}")
            if notice:
                print(f"    advance: {notice}")
            for item in owed:
                print(item)
    left = branch.residue()
    if left:
        print(f"\n--- residue: {sum(1 for line in left if not line.startswith('    '))} "
              "branch(es) outlived their pull request ---")
        print("\n".join(left))


def print_threads(ref: str) -> None:
    """The threads of `ref` owed, held for promotion and answered, under each verdict with the head it was given on."""
    held = github.pull(ref)
    nodes = held["reviewThreads"]["nodes"]
    owed, parked, done = (review.unaddressed(nodes, limit=None),
                           review.unaddressed(nodes, parked=True, limit=None),
                           review.settled(nodes, limit=None))
    given = review.verdicts(held["reviews"]["nodes"])
    if given:
        print(f"--- {len(given)} verdict(s), newest first, each on the head GitHub recorded it against ---")
        print("\n".join(given))
        print()
    print("\n".join(owed) if owed else "nothing unaddressed")
    if parked:
        print(f"\n--- {len(parked)} noticed and not done, held for promotion at approval (solorepo's DR-159) ---")
        print("\n".join(parked))
    if done:
        print(f"\n--- {len(done)} answered and resolved: a re-review reads each answer against the diff it claims ---")
        print("\n".join(done))


def main(description: str) -> None:
    """Parses the command line and runs the one mode it names.

    Args:
        description: The script's docstring, shown by `--help`.
    """
    ap = parser(description)
    args = ap.parse_args()
    modes: tuple[tuple[bool, str | bool, Callable[[], None]], ...] = (
        (args.all, False, lambda: sys.exit(sweep.sweep_all(args.publish))),
        (args.hand_back, False, lambda: print(json.dumps(sweep.hand_back(args.hand_back)))),
        (args.sweep, False, print_sweep),
        (args.handoff, False, lambda: sys.exit(branch.handoff(args.base))),
        (args.watch, "--watch",
         lambda: polling.watch(args.pr, args.every, max_retries=args.retries)),
        (args.resume, "--resume", lambda: print(polling.resume(args.pr))),
        (args.threads, "--threads", lambda: print_threads(args.pr)),
        (args.unresolved_count, "--unresolved-count",
         lambda: print(len([t for t in github.threads(args.pr) if not t.get("isResolved")]))),
    )
    for chosen, needs_pr, run in modes:
        if not chosen:
            continue
        if needs_pr and not args.pr:
            ap.error(f"{needs_pr} needs a pull request")
        run()
        sys.exit(0)

    if args.file:
        title, body = args.title, pathlib.Path(args.file).read_text()
    elif args.pr:
        title, body = github.from_github(args.pr)
    else:
        ap.error("give a pull request, or --file")

    problems = verdict.gate(args.pr) if args.pr else form.check(title, body)
    for p in problems:
        print(f"x  {p}")
    print(f"{'x  ' if problems else 'ok '}pull request"
          + (f" ({len(problems)})" if problems else ""))
    sys.exit(1 if problems else 0)
