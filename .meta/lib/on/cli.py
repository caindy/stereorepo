"""Command-line parser and dispatch for the reviewer door (solorepo's DR-217, DR-264)."""

import argparse

import channel
from lib.on import common, review

DESCRIPTION = ""
"""The entry-point documentation shown by the command-line parser."""

RAN = ("claude", "agy", "jules", "none")
"""What `--ran` may say: a harness step, or that none ran."""

NOT_ONE_OF = "{text!r} is not one of {choices}"
"""The parser's refusal of a flag whose value is none of the words it takes."""

OUTCOMES = ("success", "failure", "cancelled", "skipped")
"""The four conclusions a workflow step may end with."""


def count(text: str) -> int | None:
    """A flag's number, or `None` where the workflow handed an empty string.

    A step output that never arrived, from a step that failed or was skipped,
    reaches the door as `""` rather than as a missing flag, and it is the
    door's refusal that must name it, not the parser's.
    """
    return int(text) if text.strip() else None


def rung_outcome(text: str) -> str | None:
    """A rung's outcome, or `None` where the workflow handed an empty string.

    Between two rungs an outcome is what decides whether the next runs, so
    an empty one is refused there by the door's `fallback` and not by the
    parser, which also serves the phases that take none.

    Raises:
        argparse.ArgumentTypeError: Where the text is no outcome a step has.
    """
    if not text.strip():
        return None
    if text not in OUTCOMES:
        raise argparse.ArgumentTypeError(
            NOT_ONE_OF.format(text=text, choices=", ".join(OUTCOMES))
        )
    return text


def between_flags(p: argparse.ArgumentParser) -> None:
    """The two flags `between` takes on either Role: which rung ended, and how."""
    p.add_argument(
        "--attempt",
        type=count,
        default=None,
        help="between two rungs: which rung has just ended, counted from one; "
        "absent, the phase answers the older two-step question",
    )
    p.add_argument(
        "--outcome",
        type=rung_outcome,
        default=None,
        help="between two rungs: how that rung ended; required beside --attempt",
    )


def harness(text: str) -> str | None:
    """A flag's harness, or `None` where the workflow handed an empty string.

    Raises:
        argparse.ArgumentTypeError: Where the text names no harness step.
    """
    if not text.strip():
        return None
    if text not in RAN:
        raise argparse.ArgumentTypeError(NOT_ONE_OF.format(text=text, choices=", ".join(RAN)))
    return text


def build_parser() -> argparse.ArgumentParser:
    """Builds the argument parser: the reviewer verb taking the phase and the number."""
    ap = channel.parser(DESCRIPTION or __doc__)
    sub = ap.add_subparsers(dest="verb", required=True)
    p = sub.add_parser("reviewer")
    p.add_argument(
        "phase",
        choices=("before", "between", "after"),
        help="before the harness session, between two rungs of its ladder, or after it",
    )
    p.add_argument("number", help="the Challenge or the pull request the run is for")
    between_flags(p)
    p.add_argument(
        "--verdicts",
        type=count,
        help="after a review session: the verdicts `before` counted; required there, "
        "and an empty string is absent",
    )
    p.add_argument(
        "--agents",
        type=count,
        help="after a review session: the fan-out ceiling `before` chose; required "
        "there, and an empty string is absent",
    )
    p.add_argument(
        "--ran",
        type=harness,
        help="after a review session: which harness step ran it, `none` being a "
        "finding; required there, and an empty string is absent",
    )
    p.add_argument(
        "--transcript", default="", help="after a review session: where Claude Code's transcript is"
    )
    return ap


def main() -> None:
    """Parses arguments and runs the door's phase as the Role."""
    args = build_parser().parse_args()
    channel.speak_as(args.role)
    if args.verb == "reviewer":
        review.reviewer(
            args.phase,
            args.number,
            common.Session(args.verdicts, args.agents, args.ran, args.transcript),
            common.Attempt(args.attempt, args.outcome, args.transcript),
        )
