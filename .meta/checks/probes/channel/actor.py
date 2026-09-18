"""Who the Actor is: `channel.actor()` and `check_pr.mine()` agreeing on the session a Trailer signs with.
"""
import collections

from collect import META, check
from probes.harness import (
    answered,
    environment,
    load_channel,
    load_module,
)


@check("actor probes", pre=True)
def actor_probes():
    """`channel.actor()` and `check_pr.mine()` agree on which session is
    speaking, over the precedence of the two variables and the fallback when
    neither is set (solorepo's #301).

    `ACTOR_SESSION` wins when it carries the run's mark, `gha-`, and
    `CLAUDE_CODE_SESSION_ID` wins otherwise: the mark winning, not mere
    presence, is the half of the rule the code does not say out loud. `mine()`
    reads a Trailer as its own exactly when it names the session `actor()`
    answers, so each case checks both, over one Trailer that is the session's
    own and one that is not. With neither variable set, `actor()` refuses and
    `mine()` answers `False` for any Trailer.

    A case is `(name, actor_session, claude_session, answer, own, not_own)`:
    the two variables, `None` for unset; `answer`, what `actor()` returns, or
    `None` where it refuses; `own`, the session a Trailer must read as mine, or
    `None` where none does; and `not_own`, a session a Trailer must not.
    """
    channel, _, _ = load_channel()
    check_pr = load_module(META / "check_pr.py", "check_pr")
    Case = collections.namedtuple("Case", "name actor_session claude_session answer own not_own")
    cases = (
        Case("both set, the run's mark beside the harness's uuid",
             "gha-7", "uuid-123", "gha-7", "gha-7", "uuid-123"),
        Case("`ACTOR_SESSION` unmarked beside the uuid",
             "not-marked-session", "uuid-456", "uuid-456", "uuid-456", "not-marked-session"),
        Case("neither set", None, None, None, None, "uuid-123"),
    )
    problems = []
    for case in cases:
        with environment(ACTOR_SESSION=case.actor_session, CLAUDE_CODE_SESSION_ID=case.claude_session):
            got, code, exited = answered(channel.actor)
            if case.answer is None:
                if not exited:
                    problems.append(f"actor: {case.name}: expected a refusal, got {got!r} "
                                    f"returned and {code!r} exited")
            elif code is not None:
                problems.append(f"actor: {case.name}: exited with {code}")
            elif got != case.answer:
                problems.append(f"actor: {case.name}: expected {case.answer!r}, got {got!r}")
            if case.own is not None and not check_pr.mine(f"Actor: {case.own}\nAgent: cli"):
                problems.append(f"mine: {case.name}: expected True for the {case.own!r} Trailer")
            if check_pr.mine(f"Actor: {case.not_own}\nAgent: cli"):
                problems.append(f"mine: {case.name}: expected False for the {case.not_own!r} Trailer")
    return problems
