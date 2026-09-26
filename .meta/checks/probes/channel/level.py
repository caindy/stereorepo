"""The level a run may land, the level a session lands with the solo's words behind it (solorepo's DR-278), the level `move reread` takes off (solorepo's DR-235), and roadmap transitions (solorepo's #421).
"""


import sys
from typing import Any

from checks.collect import META, check
from checks.probes.harness import (
    FakeFiling,
    FakeIssue,
    environment,
    exit_of,
    load_channel,
    load_module,
    run_verb,
    stood_in,
)

TITLE = "A Challenge a run filed"
BODY = "**Waits on.** Nothing.\n\nWhat was noticed.\n"

RUN = "gha-1234"
"""An `ACTOR_SESSION` carrying the mark a workflow writes and nothing else does, which is what `channel.in_a_run()` reads (solorepo's DR-148)."""

SESSION = "a-session-beside-it"
"""An `ACTOR_SESSION` carrying no run mark, for a case that reads its own Trailer and so needs an Actor to name. Unset is a session too, and is what the cases that never reach a Trailer use."""


@check("level probes", pre=True)
def level_probes() -> list[str]:
    """The level a run may land and the level `move reread` takes off (solorepo's DR-235),
    and the level a session lands with a mandate behind it (solorepo's DR-278).

    The refusal is a branch taken on the environment, which is the one input a
    reader cannot see by reading the verb, so `ACTOR_SESSION` is set and unset
    around each case rather than stood in for — the variable is the fact, as
    `probes/channel/claim.py` says of the same mark. `None` is the variable
    unset, which is a session as much as an unrecognised value is.

    A refusal's text is read, not just its presence: `run_verb` reports an
    exception as text rather than raising it, so a truthy answer alone cannot
    tell the refusal from the fake being asked something it has no answer for.

    `mandate_probes` is the exception to the environment paragraph above: the
    mandate refusal is a branch on its two arguments and on nothing else, so
    those cases carry no environment and no fake, and `wiring_probes` is what
    observes it at the two call sites that read the flags.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    return (moving_probes(channel, move) + filing_probes(channel, move)
            + mandate_probes(move) + wiring_probes(channel, programs)
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

    A Challenge with no level standing is refused whoever asks, naming `triage`
    (solorepo's DR-278). This verb asks for no mandate, so landing a first level
    here would be `move file` followed by `move difficulty` — a level on a
    Challenge with nothing behind it, reached one command past the refusal that
    stops it at filing.
    """
    problems: list[str] = []

    def moved(level: str, session: str | None,
              labels: tuple[str, ...] = ("challenge", "medium")) -> tuple[str | None, FakeIssue]:
        """One `difficulty` of a Challenge holding `labels` under `ACTOR_SESSION` set to `session`, as `(what it exited with, the fake)`."""
        fake = FakeIssue(list(labels))
        run_id = session.removeprefix("gha-") if session and session.startswith("gha-") else None
        with environment(GITHUB_RUN_ID=run_id, ACTOR_SESSION=session):
            return run_verb(channel, fake, lambda: move.challenges.difficulty("7", level)), fake

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
    said, fake = moved("hard", None, labels=("challenge",))
    if not said or "triage" not in said or fake.labels != ["challenge"]:
        problems.append(f"level: a session moving an unread Challenge to `hard` was told "
                        f"{said!r} and left it labelled {fake.labels!r}")
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
            file_issue = move.challenges.file_issue
            return run_verb(channel, fake, lambda: file_issue(TITLE, BODY, level=level)), fake

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


def mandate_probes(move: Any) -> list[str]:
    """`refuse_a_level_and_a_mandate_apart` over the levels and the mandates (solorepo's DR-278).

    The helper is a branch on its arguments: it reads no environment and
    touches no channel, so these cases stand it up on its arguments alone and
    say nothing about where it is read. `wiring_probes` is what observes the two
    verbs that read it.

    Blank is not a mandate. A caller that reaches for the flag and puts nothing
    in it has said no more than one that omitted it, and the whitespace case is
    the one a shell produces by accident. Every level but `RUN_LEVEL` is
    refused, and `RUN_LEVEL` and no level at all both pass.

    The pair is read the other way round too, so the mandate is asked what level
    it stands behind: quoted words with none are refused, and blank ones pass
    here for the same reason they are refused above, being no mandate either
    way. `RUN_LEVEL` is exempt from the first direction and not from the second,
    a mandate quoted beside it standing behind a level like any other.

    `instead` names the flag that excluded the level, and the case carrying it
    asks that the refusal name it back. The two verbs hold different surfaces
    round this pair, so a message naming a flag its caller does not have would
    be a worse answer than one naming none, and the case with no `instead` asks
    for the negative half: `--roadmap` absent from what a bare mandate is told,
    since the route sentence carries `--difficulty` either way and nothing else
    would tell the two messages apart.
    """
    problems: list[str] = []

    def against(level: str | None, mandate: str | None, instead: str | None = None) -> str | None:
        """One `refuse_a_level_and_a_mandate_apart`, as what it exited with."""
        return exit_of(
            lambda: move.common.refuse_a_level_and_a_mandate_apart(level, mandate, instead))

    for mandate in (None, "", "   "):
        said = against("hard", mandate)
        if not said or "--mandate" not in said:
            problems.append(f"level: a level of `hard` with {mandate!r} behind it was "
                            f"told {said!r}")
    said = against("hard", "he said hard, twice")
    if said:
        problems.append(f"level: a level of `hard` with the solo's words quoted was "
                        f"told {said!r}")
    for level in (None, "human"):
        said = against(level, None)
        if said:
            problems.append(f"level: a level of {level!r} with no mandate was told {said!r}")
    said = against("human", "he said human")
    if said:
        problems.append(f"level: `human` with the solo's words quoted was told {said!r}")
    said = against(None, "he said hard, twice")
    if not said or "--difficulty" not in said or "--roadmap" in said:
        problems.append(f"level: a mandate with no level behind it was told {said!r}")
    said = against(None, "he said hard, twice", instead="--roadmap")
    if not said or "--roadmap" not in said:
        problems.append(f"level: a mandate beside a flag that excludes the level was "
                        f"told {said!r}")
    for mandate in ("", "   "):
        said = against(None, mandate)
        if said:
            problems.append(f"level: a blank mandate of {mandate!r} with no level was "
                            f"told {said!r}")
    return problems


def wiring_probes(channel: Any, programs: dict[str, Any]) -> list[str]:
    """The two verbs that read the pair of flags, each asked for either one without the other.

    `mandate_probes` observes the helper and could not tell a caller that reads
    it from one that does not, and `filing_probes` enters at `file_issue`, which
    sits below the guard and lands the label as it always did. So neither would
    notice the call at `move`'s `_dispatch_issue_verb` or the one in `post`'s
    `main` being deleted. These cases enter where the flags are parsed, by the
    argument vector, so deleting either call fails one of them
    (solorepo's DR-278).

    The mandate with no level is asked of both verbs rather than of `move file`
    alone, which is what says the two surfaces read the pair alike: one verb
    refusing the combination while its twin accepts it is a worse surface than
    both accepting it. `--roadmap` is the third case and is `move file`'s own,
    since the flag excludes `--difficulty` and so is where a mandate can be
    typed beside a filing no level can reach. The two bare-mandate cases ask
    that `--roadmap` be absent from what they are told, which is what holds a
    flag `post promote` has no surface for out of its refusal.

    Every case is refused with the fake asked to create nothing, which is what
    says the refusal is read before the filing rather than after it.
    `stdin_body` is stood in rather than piped because `post promote` signs the
    body before it reads the level, and the Agent variables are set for the same
    reason: signing is ahead of the guard on that path and refuses where the
    environment names no Agent.
    """
    problems: list[str] = []
    move, post = programs["move"], programs["post"]

    def dispatched(argv: list[str], call: Any) -> tuple[str | None, FakeFiling]:
        """One verb run from a session over `argv`, as `(what it exited with, the fake)`."""
        fake = FakeFiling()
        with environment(GITHUB_RUN_ID=None, ACTOR_SESSION=SESSION,
                         AI_AGENT="probe", ACTOR_AGENT="probe"), \
                stood_in(sys, argv=argv), stood_in(channel, stdin_body=lambda: BODY):
            return run_verb(channel, fake, call), fake

    said, fake = dispatched(["move", "file", "--title", TITLE, "--difficulty", "hard"],
                            lambda: move.cli.main(None))
    if not said or "--mandate" not in said or fake.created:
        problems.append(f"level: `move file --difficulty hard` with no mandate was told {said!r} "
                        f"and created {len(fake.created)}")
    said, fake = dispatched(["post", "promote", "PRRT_1", "--title", TITLE, "--difficulty", "hard"],
                            post.main)
    if not said or "--mandate" not in said or fake.created:
        problems.append(f"level: `post promote --difficulty hard` with no mandate was told "
                        f"{said!r} and created {len(fake.created)}")
    said, fake = dispatched(["move", "file", "--title", TITLE, "--mandate", "he said hard"],
                            lambda: move.cli.main(None))
    if not said or "--difficulty" not in said or "--roadmap" in said or fake.created:
        problems.append(f"level: `move file --mandate` with no level was told {said!r} "
                        f"and created {len(fake.created)}")
    said, fake = dispatched(["move", "file", "--title", TITLE, "--roadmap",
                             "--mandate", "he said hard"], lambda: move.cli.main(None))
    if not said or "--roadmap" not in said or fake.created:
        problems.append(f"level: `move file --roadmap --mandate` was told {said!r} "
                        f"and created {len(fake.created)}")
    said, fake = dispatched(["post", "promote", "PRRT_1", "--title", TITLE,
                             "--mandate", "he said hard"], post.main)
    if not said or "--difficulty" not in said or "--roadmap" in said or fake.created:
        problems.append(f"level: `post promote --mandate` with no level was told {said!r} "
                        f"and created {len(fake.created)}")
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
                            lambda: move.challenges.ensure_autonomous_level("7", level)), fake

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
                            lambda: move.challenges.triage("7", "medium", VERDICT_BODY)), fake

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
            return run_verb(channel, fake, lambda: move.challenges.reread("7")), fake

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
            return run_verb(channel, fake, lambda: move.challenges.roadmap("7")), fake

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
