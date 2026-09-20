"""The level a run may land, the level `move reread` takes off (solorepo's DR-235), and roadmap transitions (solorepo's #421).
"""


from typing import Any

from checks.collect import META, check
from checks.probes.harness import (
    FakeFiling,
    FakeIssue,
    environment,
    load_channel,
    load_module,
    run_verb,
)

TITLE = "A Challenge a run filed"
BODY = "**Waits on.** Nothing.\n\nWhat was noticed.\n"

RUN = "gha-1234"
"""An `ACTOR_SESSION` carrying the mark a workflow writes and nothing else does, which is what `channel.in_a_run()` reads (solorepo's DR-148)."""

SESSION = "a-session-beside-it"
"""An `ACTOR_SESSION` carrying no run mark, for a case that reads its own Trailer and so needs an Actor to name. Unset is a session too, and is what the cases that never reach a Trailer use."""


@check("level probes", pre=True)
def level_probes() -> list[str]:
    """The level a run may land, and the level `move reread` takes off (solorepo's DR-235).

    The refusal is a branch taken on the environment, which is the one input a
    reader cannot see by reading the verb, so `ACTOR_SESSION` is set and unset
    around each case rather than stood in for — the variable is the fact, as
    `probes/channel/claim.py` says of the same mark. `None` is the variable
    unset, which is a session as much as an unrecognised value is.

    A refusal's text is read, not just its presence: `run_verb` reports an
    exception as text rather than raising it, so a truthy answer alone cannot
    tell the refusal from the fake being asked something it has no answer for.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    return (moving_probes(channel, move) + filing_probes(channel, move)
            + delegating_probes(channel, move) + triaging_probes(channel, move)
            + reread_probes(channel, move) + roadmap_probes(channel, move)
            + next_unlabelled_probes())


def moving_probes(channel: Any, move: Any) -> list[str]:
    """`move difficulty` from a run and from a session.

    Each level that is a verdict is refused to a run with the labels untouched,
    and the refusal names `human`, since a run told only that it may not land a
    level is left with no act. `human` itself lands, because it starts no Job
    and asks for the solo, which is what a run that cannot finish or has found
    a decision owed has to be able to say. A session lands `hard`, which is the
    takeover `move claim` names and solorepo's DR-142 rests on.
    """
    problems: list[str] = []

    def moved(level: str, session: str | None) -> tuple[str | None, FakeIssue]:
        """One `difficulty` of a `medium` Challenge under `ACTOR_SESSION` set to `session`, as `(what it exited with, the fake)`."""
        fake = FakeIssue(["challenge", "medium"])
        run_id = session.removeprefix("gha-") if session and session.startswith("gha-") else None
        with environment(GITHUB_RUN_ID=run_id, ACTOR_SESSION=session):
            return run_verb(channel, fake, lambda: move.difficulty("7", level)), fake

    for level in ("easy", "medium", "hard"):
        said, fake = moved(level, RUN)
        if not said or "human" not in said or fake.labels != ["challenge", "medium"]:
            problems.append(f"level: a run moving a Challenge to `{level}` was told {said!r} "
                            f"and left it labelled {fake.labels!r}")
    said, fake = moved("human", RUN)
    if said or "human" not in fake.labels or "medium" in fake.labels:
        problems.append(f"level: a run moving a Challenge to `human` said {said!r} and left it "
                        f"labelled {fake.labels!r}")
    said, fake = moved("hard", None)
    if said or "hard" not in fake.labels:
        problems.append(f"level: a session moving a Challenge to `hard` said {said!r} and left "
                        f"it labelled {fake.labels!r}")
    return problems


def filing_probes(channel: Any, move: Any) -> list[str]:
    """`file_issue` from a run and from a session, which is the path `post promote` takes.

    A run filing at a level is refused before anything reaches GitHub — the
    listing is never read, which is what says the refusal is the first thing
    the verb does and not a check after the act — and a run filing with no
    level lands `challenge` alone, which is the reviewer's queue. `human`
    files, as it moves.
    """
    problems: list[str] = []

    def filed(level: str | None, session: str | None) -> tuple[str | None, FakeFiling]:
        """One `file_issue` under `ACTOR_SESSION` set to `session`, as `(what it exited with, the fake)`."""
        fake = FakeFiling()
        run_id = session.removeprefix("gha-") if session and session.startswith("gha-") else None
        with environment(GITHUB_RUN_ID=run_id, ACTOR_SESSION=session):
            return run_verb(channel, fake, lambda: move.file_issue(TITLE, BODY, level=level)), fake

    def landed(fake: FakeFiling) -> list[str]:
        """The labels on the one Issue the fake was asked to create, or none where it was asked for none."""
        return next(iter(fake.created.values()), ("", "", []))[2]

    said, fake = filed("hard", RUN)
    if not said or "human" not in said or fake.created or fake.listings:
        problems.append(f"level: a run filing at `hard` was told {said!r}, created "
                        f"{len(fake.created)} and read the listing {fake.listings} time(s)")
    said, fake = filed(None, RUN)
    if said or landed(fake) != ["challenge"]:
        problems.append(f"level: a run filing with no level said {said!r} and landed "
                        f"{landed(fake)!r}")
    said, fake = filed("human", RUN)
    if said or landed(fake) != ["challenge", "human"]:
        problems.append(f"level: a run filing at `human` said {said!r} and landed "
                        f"{landed(fake)!r}")
    said, fake = filed("hard", None)
    if said or landed(fake) != ["challenge", "hard"]:
        problems.append(f"level: a session filing at `hard` said {said!r} and landed "
                        f"{landed(fake)!r}")
    return problems


def delegating_probes(channel: Any, move: Any) -> list[str]:
    """`ensure_autonomous_level`, which is the level `move delegate` lands.

    The fourth caller, and the one the Decision first left out: it writes a
    level straight through `relabel`, and the level it writes is `medium` by
    default, so a run typing `move delegate <n>` on an unread Challenge would
    route its own work to the loop in one act. `ensure_autonomous_level` is the
    subject rather than `delegate`, because the level is the whole of what this
    rule is about and the verb around it dispatches workflows this probe would
    otherwise have to stand in for; `probes/loops/delegate.py` holds the verb's
    own cases, from a session.

    Both the level a caller names and the one the default settles on are
    refused, with nothing edited, and a session delegates as it always did.
    """
    problems: list[str] = []

    def delegating(labels: list[str], level: str | None,
                   session: str | None) -> tuple[str | None, FakeIssue]:
        """One `ensure_autonomous_level` under `ACTOR_SESSION` set to `session`, as `(what it exited with, the fake)`."""
        fake = FakeIssue(labels)
        run_id = session.removeprefix("gha-") if session and session.startswith("gha-") else None
        with environment(GITHUB_RUN_ID=run_id, ACTOR_SESSION=session):
            return run_verb(channel, fake,
                            lambda: move.ensure_autonomous_level("7", level)), fake

    said, fake = delegating(["challenge"], None, RUN)
    if not said or "human" not in said or fake.labels != ["challenge"]:
        problems.append(f"level: a run delegating an unread Challenge was told {said!r} and left "
                        f"it labelled {fake.labels!r}")
    said, fake = delegating(["challenge", "hard"], "medium", RUN)
    if not said or "human" not in said or fake.labels != ["challenge", "hard"]:
        problems.append(f"level: a run delegating at `medium` was told {said!r} and left it "
                        f"labelled {fake.labels!r}")
    said, fake = delegating(["challenge"], None, None)
    if said or "medium" not in fake.labels:
        problems.append(f"level: a session delegating an unread Challenge said {said!r} and left "
                        f"it labelled {fake.labels!r}")
    return problems


VERDICT_BODY = ("**Worth doing.** Yes.\n\n**Waits on.** Nothing.\n\n"
                "**Already answered.** No.\n\n**Decision owed.** No.\n")
"""A verdict carrying all four headings `move triage` holds a body to, so a case is refused for who typed it and not for what it said."""


def triaging_probes(channel: Any, move: Any) -> list[str]:
    """`move triage`, the one verb that lands a level in a run.

    Guarded on identity and not on location: the reading door is a workflow,
    so `channel.in_a_run()` alone would refuse the reviewer its own verb. The
    account is the fact — in a run, the reviewer's and no other — so a coder
    run cannot type a verdict on the Challenge it has just filed and then take
    it, which is the refusal on `file_issue` reached by a longer road.

    The body carries all four headings in every case, so a refusal here is
    about who is speaking and never about what was written.

    The environment is set for the two cases that **pass** the guard. Past it,
    `triage` asks `verdict_posted`, which reads this Actor's own Trailer
    through `channel.trailers()` to tell its own verdict from another's among
    the Issue's comments, and `channel.agent()` refuses where the environment
    names no Agent. `gate.yml` sets neither `ACTOR_SESSION` nor `AI_AGENT`, so
    these cases pass on a laptop that has both and fail in the container that
    has neither unless they carry their own. The refused case needs nothing:
    the guard is the verb's first statement, so it never reaches the Trailer.
    `SESSION` is a session id with no run mark, since unset would leave
    `channel.actor()` with nothing to name; `probes/channel/claim.py` reads an
    unrecognised value as a session for the same reason.
    """
    problems: list[str] = []

    def triaging(login: str, session: str) -> tuple[str | None, FakeIssue]:
        """One `triage` of an unread Challenge as `login` under `ACTOR_SESSION` set to `session`, as `(what it exited with, the fake)`."""
        fake = FakeIssue(["challenge"])
        fake.login = login
        run_id = session.removeprefix("gha-") if session.startswith("gha-") else None
        with environment(GITHUB_RUN_ID=run_id,
                         ACTOR_SESSION=session, AI_AGENT="probe", ACTOR_AGENT="probe"):
            return run_verb(channel, fake,
                            lambda: move.triage("7", "medium", VERDICT_BODY)), fake

    said, fake = triaging("o-r-coder", RUN)
    if not said or "reviewer" not in said or fake.labels != ["challenge"] or fake.comments:
        problems.append(f"level: a coder run triaging a Challenge was told {said!r}, left it "
                        f"labelled {fake.labels!r} and posted {len(fake.comments)} comment(s)")
    said, fake = triaging("o-r-reviewer", RUN)
    if said or "medium" not in fake.labels or not fake.comments:
        problems.append(f"level: the reviewer's run triaging a Challenge said {said!r}, left it "
                        f"labelled {fake.labels!r} and posted {len(fake.comments)} comment(s)")
    said, fake = triaging("o-r-coder", SESSION)
    if said or "medium" not in fake.labels:
        problems.append(f"level: a session triaging a Challenge said {said!r} and left it "
                        f"labelled {fake.labels!r}")
    return problems


def reread_probes(channel: Any, move: Any) -> list[str]:
    """`move reread`, which delivers the event the reading door runs on.

    A session's reread of an unclaimed, open Challenge takes the level off and
    keeps `challenge`. A run is refused it outright, since stripping a level
    and letting the door land another is what the refusal on `difficulty`
    denies in one act. A claimed one is refused naming `move stop`, because a
    level leaving would ask the reader to route work a Job is standing on; a
    closed one is refused because the reading door declines it, so the level
    would go with no reader queued; a Challenge with no level is refused as the
    no-op it is.

    Every case reads the refusal's text and not merely its presence, this one
    included. Asserting `not said` alone cannot fail here: with the guard
    removed, `relabel` is reached with nothing to remove, the fake is handed an
    `issue edit` carrying neither `--add-label` nor `--remove-label` and raises,
    and `run_verb` returns that as the text of an exit that never happened.
    """
    problems: list[str] = []

    def rereading(labels: list[str], assignees: list[str] | None = None,
                  state: str = "OPEN",
                  session: str | None = None) -> tuple[str | None, FakeIssue]:
        """One `reread` of an Issue holding `labels`, `assignees` and `state`, under `ACTOR_SESSION` set to `session`, as `(what it exited with, the fake)`."""
        fake = FakeIssue(labels, assignees=assignees)
        fake.state = state
        run_id = session.removeprefix("gha-") if session and session.startswith("gha-") else None
        with environment(GITHUB_RUN_ID=run_id, ACTOR_SESSION=session):
            return run_verb(channel, fake, lambda: move.reread("7")), fake

    said, fake = rereading(["challenge", "hard"])
    if said or fake.labels != ["challenge"]:
        problems.append(f"level: rereading an unclaimed Challenge said {said!r} and left it "
                        f"labelled {fake.labels!r}")
    said, fake = rereading(["challenge", "hard"], session=RUN)
    if not said or "stop" not in said or fake.labels != ["challenge", "hard"] or fake.views:
        problems.append(f"level: a run rereading a Challenge was told {said!r}, left it labelled "
                        f"{fake.labels!r} and read the labels {fake.views} time(s)")
    said, fake = rereading(["challenge", "hard"], assignees=["o-r-coder"])
    if not said or "stop" not in said or fake.labels != ["challenge", "hard"]:
        problems.append(f"level: rereading a claimed Challenge was told {said!r} and left it "
                        f"labelled {fake.labels!r}")
    said, fake = rereading(["challenge", "hard"], state="CLOSED")
    if not said or "closed" not in said or fake.labels != ["challenge", "hard"]:
        problems.append(f"level: rereading a closed Challenge was told {said!r} and left it "
                        f"labelled {fake.labels!r}")
    said, fake = rereading(["challenge"])
    if not said or "carries no level" not in said or fake.labels != ["challenge"]:
        problems.append(f"level: rereading a Challenge with no level was told {said!r}")
    return problems


def roadmap_probes(channel: Any, move: Any) -> list[str]:
    """`move roadmap`, which moves an unlabelled or challenge Issue onto the roadmap.

    Args:
        channel: The channel module.
        move: The move program module.

    Returns:
        list[str]: Discrepancies found during probe execution.
    """
    problems: list[str] = []

    def roadmapping(labels: list[str], assignees: list[str] | None = None,
                    state: str = "OPEN",
                    session: str | None = None) -> tuple[str | None, FakeIssue]:
        """One `roadmap` of an Issue holding `labels`, `assignees` and `state`, under `ACTOR_SESSION` set to `session`, as `(what it exited with, the fake)`."""
        fake = FakeIssue(labels, assignees=assignees)
        fake.state = state
        run_id = session.removeprefix("gha-") if session and session.startswith("gha-") else None
        with environment(GITHUB_RUN_ID=run_id, ACTOR_SESSION=session):
            return run_verb(channel, fake, lambda: move.roadmap("7")), fake

    said, fake = roadmapping([])
    if said or fake.labels != ["roadmap"]:
        problems.append(f"roadmap: roadmapping an unlabelled Issue said {said!r} and left it "
                        f"labelled {fake.labels!r}")

    said, fake = roadmapping(["challenge", "hard"])
    if said or fake.labels != ["roadmap"]:
        problems.append(f"roadmap: roadmapping a Challenge said {said!r} and left it "
                        f"labelled {fake.labels!r}")

    said, fake = roadmapping(["roadmap"])
    if not said or "already" not in said or fake.labels != ["roadmap"]:
        problems.append(f"roadmap: roadmapping an Issue already on the roadmap said {said!r} and left it "
                        f"labelled {fake.labels!r}")

    said, fake = roadmapping(["challenge"], session=RUN)
    if not said or "solo's" not in said or fake.labels != ["challenge"]:
        problems.append(f"roadmap: a run roadmapping an Issue was told {said!r} and left it "
                        f"labelled {fake.labels!r}")

    said, fake = roadmapping(["challenge"], assignees=["o-r-coder"])
    if not said or "claimed" not in said or fake.labels != ["challenge"]:
        problems.append(f"roadmap: roadmapping a claimed Issue was told {said!r} and left it "
                        f"labelled {fake.labels!r}")

    said, fake = roadmapping(["challenge"], state="CLOSED")
    if not said or "closed" not in said or fake.labels != ["challenge"]:
        problems.append(f"roadmap: roadmapping a closed Issue was told {said!r} and left it "
                        f"labelled {fake.labels!r}")

    return problems


def next_unlabelled_probes() -> list[str]:
    """Verification of next.py unlabelled issue classification and row formatting.

    Returns:
        list[str]: Discrepancies found during next unlabelled issue checks.
    """
    problems: list[str] = []
    screen = load_module(META / "next.py", "next_screen", register=False)
    issue = {"number": 22, "title": "An unlabelled issue", "labels": [], "createdAt": "2026-09-04T00:00:00Z"}
    classified = screen.classify(issue, {22}, {})
    if classified["kind"] != "-":
        problems.append(f"next: expected kind '-' for unlabelled issue, got {classified['kind']!r}")
    if screen.unlabelled([classified]) != [classified]:
        problems.append("next: unlabelled() did not return the unlabelled issue")
    row_text = screen.row(classified)
    if "unlabelled" not in row_text:
        problems.append(f"next: row() did not format level as 'unlabelled', got: {row_text!r}")
    return problems

