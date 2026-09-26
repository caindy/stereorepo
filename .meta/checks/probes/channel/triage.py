"""`move triage`: the reviewer's verdict posted before the level lands, refused where it names no check, and never posted twice (solorepo's DR-230).
"""
from typing import Any

from checks.collect import check
from checks.probes.harness import (
    FakeIssue,
    environment,
    load_channel,
    run_verb,
)

VERDICT = ("**Worth doing.** A cost that will land.\n\n**Waits on.** Nothing.\n\n"
           "**Already answered.** No.\n\n**Decision owed.** No.\n")


@check("triage probes", pre=True)
def triage_probes() -> list[str]:
    """`move triage` against an unread Challenge, a read one, a bare Issue, a body that names no check, and a retry.

    An unread Challenge takes the level and the verdict is posted on the Issue
    before the label lands, so the coder loop's door opens on an Issue already
    carrying the reading. A Challenge whose level stands is refused naming
    `difficulty`, the verb that moves one, with nothing posted and nothing
    relabelled; one whose level stands beside this channel's own verdict is
    refused saying nothing more is owed. An Issue that is not a Challenge
    becomes one at the level, its `roadmap` label gone. A body lacking a
    heading of the verdict form is refused naming the heading, before anything
    is written: a level landed without a reading shows as one. A retry after
    the label failed to land posts no second verdict and lands the level
    (solorepo's DR-221); a second reading by another Actor, which is what a
    Challenge handed back gets, posts its own.

    The posting is counted rather than believed: `Recorder` wraps the fake and
    keeps every call, so the probe reads that the comment went out and that it
    went out before the label, which is the order the door depends on.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    return reading_probes(channel, move) + retry_probes(channel, move)


def triaged(channel: Any, move: Any, fake: FakeIssue, level: str, body: str) -> tuple[str | None, "Recorder"]:
    """One `triage` of Issue 7 against `fake` with `body` signed as this Actor, as `(what it exited with, the recording fake)`.

    The fake speaks as the reviewer, because every case here is the reading
    itself and the verb refuses a run on any other account (solorepo's DR-235).
    Who may type it is asked in `probes/channel/level.py`, where the rule is;
    what the verdict does is asked here.
    """
    fake.login = "o-r-reviewer"
    recorder = Recorder(fake)
    with environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe"):
        signed = channel.signed(body)
        verb = run_verb(
            channel, recorder, lambda: move.challenges.triage("7", level, signed)
        )
        return verb, recorder


def by(channel: Any, actor: str) -> dict[str, Any]:
    """A verdict comment as `actor` signed it, for seeding an Issue."""
    run_id = actor.removeprefix("gha-") if actor.startswith("gha-") else None
    with environment(GITHUB_RUN_ID=run_id, ACTOR_SESSION=actor, ACTOR_AGENT="probe"):
        return {"body": channel.signed(VERDICT)}


def reading_probes(channel: Any, move: Any) -> list[str]:
    """`triage` reading: the unread Challenge, the read one, the bare Issue, and the body naming no check."""
    problems: list[str] = []

    said, rec = triaged(channel, move, FakeIssue(["challenge"]), "medium", VERDICT)
    if said or "medium" not in rec.issue.labels or "challenge" not in rec.issue.labels:
        problems.append(f"triage: an unread Challenge said {said!r} and is labelled {rec.issue.labels!r}")
    if not rec.posted():
        problems.append("triage: the verdict was not posted on the Issue")
    elif not rec.labelled() or rec.posted()[0] > rec.labelled()[0]:
        problems.append("triage: the level landed before the verdict was posted; the door opens on an unread Issue")

    said, rec = triaged(channel, move, FakeIssue(["challenge", "easy"]), "medium", VERDICT)
    if not said or "difficulty" not in said or "easy" not in rec.issue.labels or "medium" in rec.issue.labels:
        problems.append(f"triage: a Challenge whose level stands said {said!r} and is labelled {rec.issue.labels!r}")
    if rec.posted():
        problems.append("triage: a refused verdict was posted anyway")

    said, rec = triaged(channel, move, FakeIssue(["roadmap"]), "hard", VERDICT)
    if said or "roadmap" in rec.issue.labels or "challenge" not in rec.issue.labels or "hard" not in rec.issue.labels:
        problems.append(f"triage: a roadmap Issue said {said!r} and is labelled {rec.issue.labels!r}")

    thin = VERDICT.replace("**Already answered.** No.\n\n", "")
    said, rec = triaged(channel, move, FakeIssue(["challenge"]), "medium", thin)
    if not said or "Already answered" not in said or "medium" in rec.issue.labels:
        problems.append(f"triage: a verdict naming no check said {said!r} and is labelled {rec.issue.labels!r}")
    if rec.posted() or rec.labelled():
        problems.append("triage: a verdict naming no check wrote something before it was refused")
    return problems


def retry_probes(channel: Any, move: Any) -> list[str]:
    """`triage` repeated: after the label landed, after it failed to land, and by another Actor."""
    problems: list[str] = []

    read = FakeIssue(["challenge", "medium"], comments=[by(channel, "gha-1")])
    said, rec = triaged(channel, move, read, "medium", VERDICT)
    if not said or "nothing more is owed" not in said or rec.posted():
        problems.append(f"triage: a retry after the label landed said {said!r} and posted {len(rec.posted())}")

    half = FakeIssue(["challenge"], comments=[by(channel, "gha-1")])
    said, rec = triaged(channel, move, half, "medium", VERDICT)
    if said or "medium" not in rec.issue.labels or rec.posted() or len(rec.issue.comments) != 1:
        problems.append(f"triage: a retry after the label failed to land said {said!r}, is labelled "
                        f"{rec.issue.labels!r} and carries {len(rec.issue.comments)} verdict(s)")

    again = FakeIssue(["challenge"], comments=[by(channel, "gha-0")])
    said, rec = triaged(channel, move, again, "hard", VERDICT)
    if said or "hard" not in rec.issue.labels or not rec.posted() or len(rec.issue.comments) != 2:
        problems.append(f"triage: a second reading by another Actor said {said!r}, is labelled "
                        f"{rec.issue.labels!r} and carries {len(rec.issue.comments)} verdict(s)")
    return problems


class Recorder:
    """A fake with every call it was asked kept, in order, so a probe reads what went out and when."""

    def __init__(self, issue: FakeIssue) -> None:
        self.issue: FakeIssue = issue
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *args: str, **kwargs: Any) -> Any:
        """One `gh` call, recorded and answered by the wrapped fake."""
        self.calls.append(tuple(args))
        return self.issue(*args, **kwargs)

    def posted(self) -> list[int]:
        """The positions of the calls that posted a comment."""
        return [i for i, c in enumerate(self.calls) if c[:1] == ("api",) and "comments" in c[1] and "-f" in c]

    def labelled(self) -> list[int]:
        """The positions of the calls that edited the labels."""
        return [i for i, c in enumerate(self.calls) if c[:2] == ("issue", "edit")]
