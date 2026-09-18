"""`move claim` at each level, from a run and from a session (solorepo's DR-148).
"""


from collect import check
from probes.harness import (
    FakeIssue,
    environment,
    load_channel,
    run_verb,
)


@check("claim probes", pre=True)
def claim_probes():
    """`move claim` at each level, from a run and from a session (solorepo's DR-148).

    The whole of the refusal is a branch taken on the environment, which is the
    one input a reader cannot see by reading the verb: "this is a session" holds
    on every machine except the one where it matters, or on none, and nothing
    says which. So `ACTOR_SESSION` is set and unset around each case rather than
    stood in for — the variable is the fact — and GitHub is stood in for by
    `FakeIssue`, so that all seven cases are cheap to state. `None` for the
    session is the variable unset, which is a session as much as an
    unrecognised value is.

    The cases: the two levels a loop takes, claimed from a session, are refused
    with nothing assigned, and the refusal names `move difficulty ... hard`, the
    move that takes the Challenge from the loop — a session told only that it
    may not claim is left with the collision and no act. An unrecognised
    `ACTOR_SESSION` is a session too: the mark is what a workflow writes, so
    anything else is nothing saying otherwise, and the unknown falls to the side
    that asks. The levels no loop takes are claimed as before, `human` above
    all, since it is where a loop puts what it could not finish and picking
    that up is what a session is for. A level with no `challenge` beside it
    starts no run (solorepo's #113), so it refuses nobody. And a run's own claim
    is refused by nothing and reads the labels zero times.

    A refusal's text is read, not just its presence: `run_verb` reports an
    exception as text rather than raising it, so a truthy answer alone cannot
    tell the refusal from the fake being asked something it has no answer for.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    problems = []

    def claimed(labels, session):
        """One claim of Issue 7 under `ACTOR_SESSION` set to `session`, as `(what it exited with, the fake)`."""
        fake = FakeIssue(labels)
        with environment(ACTOR_SESSION=session):
            return run_verb(channel, fake, lambda: move.claim("7")), fake

    for level in ("easy", "medium"):
        said, fake = claimed(["challenge", level], None)
        if fake.assignees:
            problems.append(f"claim: a session claiming a `{level}` Challenge was assigned it")
        if not said or "hard" not in said or "difficulty" not in said:
            problems.append(f"claim: a session claiming a `{level}` Challenge was told {said!r}")
    said, fake = claimed(["challenge", "medium"], "whatever-this-is")
    if not said or "hard" not in said or "difficulty" not in said or fake.assignees:
        problems.append(f"claim: an environment carrying no run mark was told {said!r} "
                        f"claiming a `medium` Challenge, and left it assigned to "
                        f"{fake.assignees!r}")
    for level in ("hard", "human"):
        said, fake = claimed(["challenge", level], None)
        if said or fake.assignees != ["o-r-coder"]:
            problems.append(f"claim: a session claiming a `{level}` Challenge said {said!r} "
                            f"and left it assigned to {fake.assignees!r}")
    said, fake = claimed(["medium"], None)
    if said or not fake.assignees:
        problems.append(f"claim: a session claiming a bare `medium` Issue said {said!r}")
    said, fake = claimed(["challenge", "medium"], "gha-1234")
    if said or fake.assignees != ["o-r-coder"]:
        problems.append(f"claim: a run claiming its own `medium` Challenge said {said!r} "
                        f"and left it assigned to {fake.assignees!r}")
    if fake.views:
        problems.append(f"claim: a run's claim read the labels {fake.views} time(s)")
    return problems
