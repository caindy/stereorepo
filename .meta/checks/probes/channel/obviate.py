"""`move obviate`: the refusals that keep an Issue's close an answer rather than a tidy-up (solorepo's DR-232).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""

from collections.abc import Callable
from typing import Any

from checks.collect import check
from checks.probes.harness import (
    FakeObviation,
    environment,
    load_channel,
    outcome,
    stood_in,
)

ISSUE, ANSWER = "93", "94"
"""The two numbers every case is about: the Issue being closed, and what is offered as its answer.

Held as names so that the sentences below read as names. A quoted number in a
probe is the string it greps its own output for, which is the shape
solorepo's DR-132 exempts from the inherited-citation rule, so nothing would
catch a bare literal here; the names are for the reader.
"""

ANSWERED = {ISSUE: {"kind": "issue", "state": "OPEN", "title": "the Issue",
                    "labels": ["challenge"]},
            ANSWER: {"kind": "issue", "state": "OPEN", "title": "what owns it now",
                     "labels": ["challenge", "medium"]}}
"""The pair every case starts from: an open Challenge closed against an open Challenge."""

WENT = "the finding went elsewhere"
"""The caller's account of where the work went, which the comment on the Issue must carry."""

Obviated = Callable[..., tuple[Any, FakeObviation]]
"""One `obviate` run against a fake GitHub: what it came to, and the fake to read afterwards."""

REFUSED = (
    ("an answer that is closed",
     {ANSWER: {"kind": "issue", "state": "CLOSED", "title": "t", "labels": ["challenge"]}},
     "closed"),
    ("an answer no run will take",
     {ANSWER: {"kind": "issue", "state": "OPEN", "title": "t", "labels": []}}, "triage"),
    ("an answer still in flight",
     {ANSWER: {"kind": "pull request", "state": "OPEN", "title": "t"}}, "merged"),
    ("a target that is a pull request",
     {ISSUE: {"kind": "pull request", "state": "OPEN", "title": "t"}}, "supersede"),
    ("a target closed already",
     {ISSUE: {"kind": "issue", "state": "CLOSED", "title": "t", "labels": ["challenge"]}},
     "closed already"),
)
"""Each state GitHub could be in that no close may go through: what it is, what it puts over `ANSWERED`, and the word its refusal owes."""


@check("obviate probes", pre=True)
def obviate_probes() -> list[str]:
    """`obviate` over what `--by` may name, what the target may be, and the close that went through.

    The evidence for closing an Issue without a merge is the same shape as
    `supersede`'s (solorepo's DR-232): the work is owned somewhere else, and
    either an open Challenge holds it or a merged pull request landed it, which
    is read off GitHub rather than asked of the caller. Two refusals are read
    off the arguments alone — a `--by` that is not a number, and one naming
    the Issue itself. Each case in `REFUSED` is a state GitHub could be in that
    no close may go through, and each is checked for the word its refusal owes
    — a reader told only that the close was refused is left with the Issue and
    no act.

    The close that went through is read for three things a refusal cannot show:
    the reason GitHub records, which must be `not planned` and not the
    `completed` a merge leaves; the comment on the Issue, which is the only
    record of where each part of it went; and the comment on what answered it,
    which is the backlink that makes the pair readable from either end.

    `channel.signed` is reached whichever way a comment goes and exits where the
    environment does not say who is speaking, which no gate run outside a coder
    or reviewer job does, so the environment is supplied rather than assumed.
    """
    channel, _, programs = load_channel()
    move = programs["move"]

    def obviated(items: dict[str, dict[str, Any]], issue: str = ISSUE, by: str = ANSWER,
                 reason: str = WENT) -> tuple[Any, FakeObviation]:
        """One `obviate` against a GitHub holding `items`, as `(what it came to, the fake)`."""
        fake = FakeObviation(items)
        with (environment(ACTOR_SESSION="gha-1", AI_AGENT="probe"),
              stood_in(channel, gh=fake)):
            return outcome(lambda: move.obviate(issue, by, reason)), fake

    return went_through(obviated) + refusals(obviated)


def went_through(obviated: Obviated) -> list[str]:
    """The closes that are answered — by an open Challenge, by a merged pull request, and by an answer written with the hash — read for the reason, the comment and the backlink."""
    problems = []
    ended, fake = obviated(ANSWERED)
    said = dict(fake.comments)
    if ended.code is not None:
        problems.append(f"obviate: closing against an open Challenge failed with: {ended.code}")
    if fake.closed != [(ISSUE, "not planned")]:
        problems.append(f"obviate: the close left {fake.closed!r}, not Issue {ISSUE} closed as "
                        "not planned")
    if f"**Obviated by #{ANSWER}" not in said.get(ISSUE, ""):
        problems.append(f"obviate: the comment on Issue {ISSUE} was {said.get(ISSUE)!r} and "
                        "names no answer")
    if f"#{ISSUE}" not in said.get(ANSWER, ""):
        problems.append(f"obviate: the backlink on Issue {ANSWER} was {said.get(ANSWER)!r} and "
                        "names no Issue")
    if WENT not in said.get(ISSUE, ""):
        problems.append(f"obviate: the comment on Issue {ISSUE} dropped the caller's account of "
                        "where the work went")

    landed = dict(ANSWERED, **{ANSWER: {"kind": "pull request", "state": "MERGED",
                                        "title": "the change that answered it"}})
    ended, fake = obviated(landed)
    if ended.code is not None or not fake.closed:
        problems.append(f"obviate: closing against a merged pull request came to {ended.code!r} "
                        f"and closed {fake.closed!r}")

    ended, fake = obviated(ANSWERED, by="#" + ANSWER)
    if ended.code is not None or not fake.closed:
        problems.append("obviate: an answer written the way GitHub writes one, with the hash, "
                        f"came to {ended.code!r} and closed {fake.closed!r}")
    return problems


def refusals(obviated: Obviated) -> list[str]:
    """Every state that must refuse, read for the word its refusal owes and for nothing said or closed on the way out."""
    problems = []
    for what, over, names in REFUSED:
        ended, fake = obviated(dict(ANSWERED, **over))
        if ended.code is None or names not in ended.code:
            problems.append(f"obviate: {what} came to {ended.code!r}, which does not refuse "
                            f"naming {names!r}")
        if fake.closed or fake.comments:
            problems.append(f"obviate: {what} closed {fake.closed!r} and said {fake.comments!r} "
                            "before refusing")

    for what, by in (("the Issue itself", ISSUE),
                     ("a Decision, which `supersede` takes and this does not", "DR-" + "232")):
        ended, fake = obviated(ANSWERED, by=by)
        if ended.code is None or fake.closed:
            problems.append(f"obviate: a `--by` naming {what} came to {ended.code!r} and closed "
                            f"{fake.closed!r}")
    return problems
