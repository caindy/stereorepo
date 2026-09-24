"""Command-line parser and dispatch for `.meta/coder_door.py` (solorepo's DR-284)."""

import argparse

import channel
from lib.coder_door import coder_door
from lib.on import common

DESCRIPTION = ""
"""The entry-point documentation shown by the command-line parser."""

NOT_ONE_OF = "{text!r} is not one of {choices}"
"""The parser's refusal of a flag whose value is none of the words it takes."""

DID_NOT_ARRIVE = (
    "an outcome that did not arrive: a step id renamed, or an expression that "
    "resolved to nothing, is a red run and not a pass that was skipped"
)
"""The parser's refusal of an `--outcomes` list with an empty entry; a list not given at all
is `None`, which the door's `after` refuses in its own words."""


def count(text: str) -> int | None:
    """A flag's number, or `None` where the workflow handed an empty string.

    A step output that never arrived, from a step that failed or was skipped,
    reaches the door as `""` rather than as a missing flag, and it is the
    door's refusal that must name it, not the parser's.
    """
    return int(text) if text.strip() else None


def step_outcome(text: str) -> str:
    """A step's outcome as the workflow reports it; an empty string is refused.

    A step that never ran reports `skipped`, so an empty outcome is one the
    workflow did not hand over, and the hand-back that would have run on it
    must not be skipped quietly.

    Raises:
        argparse.ArgumentTypeError: Where the text is empty or no outcome a step has.
    """
    if not text.strip():
        raise argparse.ArgumentTypeError(DID_NOT_ARRIVE)
    if text not in coder_door.OUTCOMES:
        raise argparse.ArgumentTypeError(
            NOT_ONE_OF.format(text=text, choices=", ".join(coder_door.OUTCOMES))
        )
    return text


def rung_outcomes(text: str) -> tuple[str, ...]:
    """How each rung of the pass ended, comma-separated in rung order; an empty entry is refused.

    A rung that never ran reports `skipped`, so an entry that is empty is
    one the workflow did not hand over, and the hand-back that would have
    run on it must not be skipped quietly (solorepo's DR-281).

    Raises:
        argparse.ArgumentTypeError: Where any entry is empty or no outcome a step has.
    """
    return tuple(step_outcome(entry.strip()) for entry in text.split(","))


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
    if text not in coder_door.OUTCOMES:
        raise argparse.ArgumentTypeError(
            NOT_ONE_OF.format(text=text, choices=", ".join(coder_door.OUTCOMES))
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


def build_parser() -> argparse.ArgumentParser:
    """Builds the argument parser: the coder verb taking the phase and the number."""
    ap = channel.parser(DESCRIPTION or __doc__)
    sub = ap.add_subparsers(dest="verb", required=True)
    c = sub.add_parser("coder")
    c.add_argument(
        "phase",
        choices=("before", "between", "after"),
        help="before the harness session, between two rungs of its ladder, or after "
        "the session",
    )
    c.add_argument("number", help="the Challenge on a take, the pull request on any other pass")
    between_flags(c)
    c.add_argument(
        "--pass",
        dest="task",
        choices=coder_door.PASSES,
        required=True,
        help="which pass the event opened",
    )
    c.add_argument(
        "--event",
        required=True,
        help="the event the delivery arrived on, as github.event_name names it",
    )
    c.add_argument(
        "--harness", default="", help="the harness a dispatch asked for, empty on any other event"
    )
    c.add_argument(
        "--outcomes",
        type=rung_outcomes,
        default=None,
        help="after the session: how each rung of the pass ended, comma-separated in "
        "rung order; required there, and an empty entry is refused",
    )
    c.add_argument(
        "--branch-prefix",
        default="",
        help="after a take: the harness `before` chose, naming the loop's branch",
    )
    c.add_argument(
        "--execution-file",
        dest="execution",
        default="",
        help="after a take, or between two rungs: where Claude Code wrote the pass's "
        "transcript, which is where the turn cap is said",
    )
    return ap


def main() -> None:
    """Parses arguments and runs the coder door's phase as the Role."""
    args = build_parser().parse_args()
    channel.speak_as(args.role)
    if args.verb == "coder":
        coder_door.coder(
            args.phase,
            args.number,
            coder_door.Delivery(args.task, args.event, args.harness),
            coder_door.Ended(args.outcomes, args.branch_prefix, args.execution),
            common.Attempt(args.attempt, args.outcome, args.execution),
        )
