"""Who the Actor is: `channel.actor()` and `check_pr.mine()` agreeing on the session a Trailer signs with.
"""
import collections
from collections.abc import Callable
from typing import Any

from checks.collect import META, check
from checks.probes.harness import (
    answered,
    environment,
    load_channel,
    load_module,
)


@check("actor probes", pre=True)
def actor_probes() -> list[str]:
    """`channel.actor()` and `check_pr.mine()` agree on which session is
    speaking, over the precedence of the two variables and the fallback when
    neither is set (solorepo's #301).

    `GITHUB_RUN_ID` answers first wherever it is set, since it is GitHub's own
    name for the run and the number the workflows compose `ACTOR_SESSION` from
    (solorepo's DR-233): in a run the Trailer has one legitimate value, an
    `ACTOR_SESSION` naming any other is refused rather than signed with, and a
    session id beside it is not read. Outside a run `ACTOR_SESSION` wins when it
    carries the run's mark, `gha-`, and `CLAUDE_CODE_SESSION_ID` wins otherwise:
    the mark winning, not mere presence, is the half of the rule the code does
    not say out loud. `mine()` reads a Trailer as its own exactly when it names
    the session `actor()` answers, so each case checks both, over one Trailer
    that is the session's own and one that is not. With nothing set, `actor()`
    refuses and `mine()` answers `False` for any Trailer.

    A case is `(name, run, actor_session, claude_session, answer, own,
    not_own)`: the three variables, `None` for unset; `answer`, what `actor()`
    returns, or `None` where it refuses; `own`, the session a Trailer must read
    as mine, or `None` where none does; and `not_own`, a session a Trailer must
    not. Every case sets `GITHUB_RUN_ID` rather than inheriting it, because the
    gate itself runs in a run and a case meaning a laptop has to say so.
    """
    channel, _, _ = load_channel()
    check_pr = load_module(META / "check_pr.py", "check_pr")
    Case = collections.namedtuple("Case", "name run actor_session claude_session answer own not_own")
    cases = (
        Case("both set, the run's mark beside the harness's uuid",
             None, "gha-7", "uuid-123", "gha-7", "gha-7", "uuid-123"),
        Case("`ACTOR_SESSION` unmarked beside the uuid",
             None, "not-marked-session", "uuid-456", "uuid-456", "uuid-456", "not-marked-session"),
        Case("neither set", None, None, None, None, None, "uuid-123"),
        Case("a run, its mark composed from the run id",
             "7", "gha-7", "uuid-123", "gha-7", "gha-7", "uuid-123"),
        Case("a run carrying a session id and no mark",
             "7", None, "uuid-123", "gha-7", "gha-7", "uuid-123"),
        Case("a run whose `ACTOR_SESSION` names another Job",
             "7", "uuid-123", None, None, None, "uuid-123"),
    )
    problems = []
    for case in cases:
        with environment(GITHUB_RUN_ID=case.run, ACTOR_SESSION=case.actor_session,
                         CLAUDE_CODE_SESSION_ID=case.claude_session):
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
    problems.extend(_probe_signed_integrity(channel))
    problems.extend(_probe_comment_trailer_audit(check_pr))
    return problems


def _probe_signed_integrity(channel: Any) -> list[str]:
    """Verify channel.signed appends attested trailers, preserves matching trailers, and refuses foreign trailers (solorepo's DR-260)."""
    problems: list[str] = []
    with environment(GITHUB_RUN_ID=None, ACTOR_SESSION="sess-123", AI_AGENT="test-agent", CLAUDE_CODE_SESSION_ID=None):
        got = channel.signed("hello world")
        want = "hello world\n\nActor: sess-123\nAgent: test-agent\n"
        if got != want:
            problems.append(f"signed: expected {want!r}, got {got!r}")

        got_idem = channel.signed(want)
        if got_idem.rstrip("\n") != want.rstrip("\n"):
            problems.append(f"signed idempotent: expected matching trailer, got {got_idem!r}")

        foreign_bodies = (
            "hello\n\nActor: gha-999\nAgent: coder/take_gemini",
            "hello\n\nAgent: coder/take_gemini\nActor: gha-999",
            "hello\n\nActor: fake-actor",
            "hello\n\nAgent: coder/take_gemini",
        )
        def sign_call(body: str) -> Callable[[], Any]:
            return lambda: channel.signed(body)

        for fb in foreign_bodies:
            got_f, _, exited_f = answered(sign_call(fb))
            if not exited_f:
                problems.append(f"signed foreign trailer: expected refusal for {fb!r}, got {got_f!r}")

        prose_body = "See trailer example:\nActor: gha-999\nAgent: coder/take_gemini\nEnd of note."
        got_p = channel.signed(prose_body)
        want_p = f"{prose_body}\n\nActor: sess-123\nAgent: test-agent\n"
        if got_p != want_p:
            problems.append(f"signed prose reference: expected {want_p!r}, got {got_p!r}")

    return problems


def _probe_comment_trailer_audit(check_pr: Any) -> list[str]:
    """Verify audit_comment_trailers validates comment trailer structure for Role accounts (solorepo's DR-260)."""
    problems: list[str] = []
    roles = {"caindy-solorepo-coder", "caindy-solorepo-reviewer"}

    valid_comments = [
        {"author": {"login": "caindy-solorepo-coder"}, "body": "Fixed!\n\nActor: gha-12345\nAgent: test-agent"},
        {"author": {"login": "caindy-solorepo-reviewer"}, "body": "LGTM\n\nActor: sess-abc\nAgent: test-agent"},
        {"author": {"login": "caindy-solorepo-reviewer"},
         "body": "Quoting prior refusal:\n```\nActor: gha-35392391237\nAgent: coder/take_gemini\n```\n\n> Actor: quoted-actor\n\nDone.\n\nActor: gha-12345\nAgent: test-agent"},
        {"author": {"login": "caindy"}, "body": "Human comment without trailers"},
    ]
    got_valid = check_pr.review.audit_comment_trailers(valid_comments, roles)
    if got_valid:
        problems.append(f"audit_comment_trailers unexpectedly flagged valid comments: {got_valid}")

    missing_actor = [{"author": {"login": "caindy-solorepo-coder"}, "body": "Fixed!\n\nAgent: test-agent"}]
    if not check_pr.review.audit_comment_trailers(missing_actor, roles):
        problems.append("audit_comment_trailers failed to flag missing Actor trailer on role comment")

    dup_actor = [{"author": {"login": "caindy-solorepo-coder"},
                  "body": "Fixed!\n\nActor: gha-111\nAgent: a\n\nActor: gha-222\nAgent: a"}]
    if not check_pr.review.audit_comment_trailers(dup_actor, roles):
        problems.append("audit_comment_trailers failed to flag duplicate Actor trailers")

    missing_agent = [{"author": {"login": "caindy-solorepo-coder"}, "body": "Fixed!\n\nActor: gha-12345"}]
    if not check_pr.review.audit_comment_trailers(missing_agent, roles):
        problems.append("audit_comment_trailers failed to flag missing Agent trailer on role comment")

    dup_agent = [{"author": {"login": "caindy-solorepo-coder"},
                  "body": "Fixed!\n\nActor: gha-111\nAgent: a\nAgent: b"}]
    if not check_pr.review.audit_comment_trailers(dup_agent, roles):
        problems.append("audit_comment_trailers failed to flag duplicate Agent trailers")

    malformed_actor = [{"author": {"login": "caindy-solorepo-coder"},
                        "body": "Fixed!\n\nActor: gha-not-digits\nAgent: a"}]
    if not check_pr.review.audit_comment_trailers(malformed_actor, roles):
        problems.append("audit_comment_trailers failed to flag malformed gha-* Actor trailer")

    return problems
