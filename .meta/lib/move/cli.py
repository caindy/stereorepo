"""The argument surface `.meta/say/move` delegates to, verb by verb (solorepo's DR-264)."""
import argparse
from collections.abc import Callable
from typing import Any

import channel
from lib.move import (
    advance,
    challenges,
    common,
    concepts,
    decisions,
    drafts,
    handoff,
    manager,
    pull_requests,
    reconcile,
)


def numbers(text: str) -> list[int]:
    """Issue numbers from a comma-separated argument, as `gh` spells its own.

    Parameters:
        text (str): Comma-separated Issue numbers, each optionally written `#<n>`.

    Returns:
        list[int]: The numbers, in the order given.

    Raises:
        argparse.ArgumentTypeError: If an item is not a number.
    """
    found = []
    for item in text.split(","):
        item = item.strip().lstrip("#")
        if not item.isdigit():
            raise argparse.ArgumentTypeError(challenges.NOT_AN_ISSUE.format(item=item))
        found.append(int(item))
    return found


def _add_issue_parsers(sub: Any) -> None:
    """Configure subparsers for Issue lifecycle verbs: filed, triage, waits, claim, obviate."""
    p = sub.add_parser("file")
    p.add_argument("--title", required=True)
    what = p.add_mutually_exclusive_group()
    what.add_argument("--difficulty", choices=common.DIFFICULTIES, dest="level",
                      help="a Challenge at this level: the solo's verdict given in advance, which "
                           "skips the reviewer; without it, `challenge` alone, for the reviewer to "
                           f"read. A run lands `{common.RUN_LEVEL}` and no other, and every other "
                           "level needs `--mandate`")
    what.add_argument("--roadmap", action="store_true", help="a roadmap Issue: intended and deferred")
    p.add_argument("--mandate", help="the solo's own words asking for `--difficulty`, quoted; "
                                     "without them a level is an inference and is refused, and "
                                     "without a level — beside `--roadmap`, or alone — they "
                                     "reach nobody and are refused too")
    p.add_argument("--blocked-by", dest="blocked_by", type=numbers, default=[],
                   help="the Issues this one waits on, as `<n>[,<n>]`; the `**Waits on.**` "
                        "line describes them and does not set them")
    p = sub.add_parser("waits")
    p.add_argument("issue")
    upon = p.add_mutually_exclusive_group(required=True)
    upon.add_argument("--on", type=numbers, help="the Issues this one waits on, as `<n>[,<n>]`")
    upon.add_argument("--off", type=numbers, help="the Issues to drop, as `<n>[,<n>]`")
    upon.add_argument("--clear", action="store_true", help="this Issue waits on nothing")
    p = sub.add_parser("triage")
    p.add_argument("issue")
    p.add_argument("level", choices=common.DIFFICULTIES)
    p = sub.add_parser("difficulty")
    p.add_argument("issue")
    p.add_argument("level", choices=common.DIFFICULTIES)
    p = sub.add_parser("reread")
    p.add_argument("issue")
    p = sub.add_parser("roadmap")
    p.add_argument("issue")
    p = sub.add_parser("claim")
    p.add_argument("issue")
    p = sub.add_parser("stop")
    p.add_argument("issue")
    p = sub.add_parser("obviate")
    p.add_argument("issue")
    p.add_argument("--by", required=True,
                   help="what answered it already: an open Challenge, or a merged pull request")
    p = sub.add_parser("milestone")
    p.add_argument("issue")
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--set", dest="title", help="the Milestone's title; created if new")
    target.add_argument("--clear", action="store_true", help="take the Issue out of its Milestone")
    p = sub.add_parser("delegate")
    p.add_argument("number")
    p.add_argument("--level", choices=common.LOOP_LEVELS, help="ensure Challenge difficulty level")


def _add_pr_parsers(sub: Any) -> None:
    """Configure subparsers for Pull Request lifecycle verbs: open, layer, merge, advance, dispatch."""
    p = sub.add_parser("open")
    p.add_argument("--title", required=True)
    where = p.add_mutually_exclusive_group()
    where.add_argument("--base", default="main")
    where.add_argument("--on", help="open as a layer on this pull request, and link the stack")
    p.add_argument("--draft", action="store_true",
                   help="open as a draft, which merge, advance and the reconciler pass over; "
                        "move ready takes it out")
    p = sub.add_parser("ready")
    p.add_argument("pr")
    p = sub.add_parser("layer")
    p.add_argument("pr")
    p.add_argument("--on", required=True)
    p = sub.add_parser("revise")
    p.add_argument("number")
    p.add_argument("--title")
    p = sub.add_parser("merge")
    p.add_argument("pr")
    p.add_argument("--stack", action="store_true")
    p.add_argument("--auto", action="store_true", help="arm GitHub to merge when green")
    p = sub.add_parser("merge-manager")
    p.add_argument("--dry-run", action="store_true", help="evaluate eligibility and leverage order without merging")
    p.add_argument("--no-advance", action="store_true",
                   help="leave a pull request stranded behind trunk to `advance.yml`, which a "
                        "push to `main` runs alongside this")
    p = sub.add_parser("reconcile")
    p.add_argument("--live", action="store_true",
                   help="perform what is owed; without it, report what would be performed")
    p.add_argument("--dry-run", action="store_true",
                   help="the merge manager's dry run too: name its winner and merge nothing")
    p.add_argument("--minutes", type=float, default=None,
                   help="how long a pull request or Issue must have sat idle before an act "
                        "is owed on it (default RECONCILE_MINUTES)")
    p = sub.add_parser("advance")
    p.add_argument("pr", nargs="?", help="one pull request; every armed one by default")
    p = sub.add_parser("dispatch")
    p.add_argument("pr")
    p.add_argument("--task", required=True, choices=("review", "rebase"),
                   help="which pass: `review` answers a verdict that stands, `rebase` puts a "
                        "conflicting branch back where a review can run")
    p = sub.add_parser("supersede")
    p.add_argument("pr")
    p.add_argument("--by", required=True,
                   help="what answered the Challenge already: a merged pull request, or a "
                        "landed Decision as DR-nnn")
    p = sub.add_parser("request-review")
    p.add_argument("pr")
    p.add_argument("--to", default="reviewer")
    p = sub.add_parser("mint")
    p.add_argument("--concept", metavar="IDENT",
                   help="reserve a Concept of the Ubiquitous Language instead of a Decision "
                        "number, named by the identifier its row will carry, as the say-so "
                        "that row stands on; refused to a run")


def build_parser(description: str | None = None) -> argparse.ArgumentParser:
    """Construct and return the command-line argument parser for state transition verbs.

    Parameters:
        description (str | None): The script's docstring, shown by `--help`; a probe
            that only parses passes none.

    Returns:
        argparse.ArgumentParser: Configured parser for issues, pull requests, and decisions.
    """
    ap = channel.parser(description or "")
    sub = ap.add_subparsers(dest="verb", required=True)
    _add_issue_parsers(sub)
    _add_pr_parsers(sub)
    return ap


def _dispatch_issue_verb(args: argparse.Namespace) -> bool:
    """Dispatch an Issue-specific state transition verb."""
    if args.verb == "triage":
        challenges.triage(args.issue, args.level, channel.signed(channel.stdin_body()))
    elif args.verb == "difficulty":
        challenges.difficulty(args.issue, args.level)
    elif args.verb == "reread":
        challenges.reread(args.issue)
    elif args.verb == "roadmap":
        challenges.roadmap(args.issue)
    elif args.verb == "claim":
        challenges.claim(args.issue)
    elif args.verb == "delegate":
        challenges.delegate(args.number, level=args.level)
    elif args.verb == "milestone":
        challenges.milestone(args.issue, args.title, clear=args.clear)
    elif args.verb == "file":
        common.refuse_a_level_and_a_mandate_apart(args.level, args.mandate,
                                                  instead="--roadmap" if args.roadmap else None)
        challenges.file_issue(args.title, channel.signed(channel.stdin_body()), level=args.level,
                   roadmap=args.roadmap, blocked_by=args.blocked_by)
    elif args.verb == "waits":
        challenges.waits(args.issue, on=args.on, off=args.off, clear=args.clear)
    elif args.verb == "stop":
        challenges.stop(args.issue, channel.signed(channel.stdin_body()))
    elif args.verb == "obviate":
        challenges.obviate(args.issue, args.by, channel.stdin_body())
    else:
        return False
    return True


def _mint(ident: str | None) -> None:
    """Reserve the Concept `ident` names, and the next Decision number where the flag is absent."""
    if ident is None:
        decisions.mint()
    else:
        concepts.mint_concept(ident)


def _dispatch_pr_verb(args: argparse.Namespace) -> None:
    """Dispatch a Pull Request or Decision state transition verb."""
    plain: dict[str, Callable[[], object]] = {
        "advance": lambda: advance.advance(args.pr),
        "dispatch": lambda: advance.dispatch_pass(args.pr, args.task),
        "request-review": lambda: handoff.request_review(args.pr, args.to),
        "mint": lambda: _mint(args.concept),
        "ready": lambda: drafts.ready(args.pr),
    }
    if args.verb in plain:
        plain[args.verb]()
    elif args.verb == "layer":
        pull_requests.layer(args.pr, args.on)
    elif args.verb == "merge":
        pull_requests.merge(args.pr, stack=args.stack, auto=args.auto)
    elif args.verb == "merge-manager":
        manager.merge_manager(dry_run=args.dry_run, stranded=not args.no_advance)
    elif args.verb == "reconcile":
        reconcile.reconcile(live=args.live, dry_run=args.dry_run, minutes=args.minutes)
    elif args.verb == "revise":
        text = channel.piped()
        pull_requests.revise(args.number, body=channel.signed(text) if text else None,
                             title=args.title)
    elif args.verb == "supersede":
        pull_requests.supersede(args.pr, args.by, channel.stdin_body())
    elif args.verb == "open":
        pull_requests.open_pull_request(args.title, channel.signed(channel.stdin_body()),
                                        base=args.base, on=args.on, draft=args.draft)


def main(description: str | None) -> None:
    """Parses arguments and dispatches state transition verbs on GitHub.

    Parameters:
        description (str | None): The script's docstring, shown by `--help`.
    """
    args = build_parser(description).parse_args()
    channel.speak_as(args.role)
    if not _dispatch_issue_verb(args):
        _dispatch_pr_verb(args)
