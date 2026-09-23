"""What the Agent is: `channel.agent()` over the names a run owns and the one the harness does.
"""
import collections

from checks.collect import check
from checks.probes.harness import (
    answered,
    environment,
    load_channel,
)


@check("agent probes", pre=True)
def agent_probes() -> list[str]:
    """`channel.agent()` records what the run says is speaking, and in a run
    reads nothing the agent's own shell owns (solorepo's DR-233).

    `AI_AGENT` is the harness's name for itself and the harness overwrites it,
    so inside a run a value put there by the agent's shell cannot be told from
    the ordinary one and is not read at all. `ACTOR_AGENT` is what the workflow
    wrote before the harness started; where a run carries none, the workflow and
    step GitHub names say what spoke, and where a run carries neither, `agent()`
    refuses rather than falling back to the name it does not trust. Outside a
    run `AI_AGENT` is the answer, verbatim; where it is unset and either
    `ANTIGRAVITY_AGENT` or `ANTIGRAVITY_CONVERSATION_ID` is set the answer is
    `antigravity-cli`, the name `on.HARNESSES` gives that door
    (solorepo's DR-245); where none of the three is set, `agent()` refuses.

    A case is `(name, run, actor_agent, ai_agent, workflow, step,
    antigravity_agent, antigravity_session, answer)`: the seven variables,
    `None` for unset; and `answer`, what `agent()` returns, or `None` where it
    refuses. Every case sets `GITHUB_RUN_ID` rather than inheriting it, because
    the gate itself runs in a run and a case meaning a laptop has to say so.
    """
    channel, _, _ = load_channel()
    Case = collections.namedtuple(
        "Case",
        "name run actor_agent ai_agent workflow step antigravity_agent antigravity_session answer",
    )
    typed = "an-agent-typed-this"
    cases = (
        Case("a session, the harness naming its own build",
             None, None, "claude-code_2-1-276_agent", None, None, None, None,
             "claude-code_2-1-276_agent"),
        Case("a session whose environment says nothing",
             None, None, None, None, None, None, None, None),
        Case("a run, the workflow's name beside a typed one",
             "7", "anthropics/claude-code-action@v1", typed, "coder", "take_claude", None, None,
             "anthropics/claude-code-action@v1"),
        Case("a run the workflow wrote no name in",
             "7", None, typed, "coder", "take_gemini", None, None, "coder/take_gemini"),
        Case("a run with neither the workflow's name nor GitHub's",
             "7", None, typed, None, None, None, None, None),
        Case("an antigravity session falling back from ANTIGRAVITY_AGENT",
             None, None, None, None, None, "1", None, "antigravity-cli"),
        Case("an antigravity session falling back from ANTIGRAVITY_CONVERSATION_ID",
             None, None, None, None, None, None, "agy-uuid-789", "antigravity-cli"),
        Case("AI_AGENT takes precedence over antigravity environment",
             None, None, "custom-agent", None, None, "1", "agy-uuid-789", "custom-agent"),
    )
    problems = []
    for case in cases:
        with environment(GITHUB_RUN_ID=case.run, ACTOR_AGENT=case.actor_agent,
                         AI_AGENT=case.ai_agent, GITHUB_WORKFLOW=case.workflow,
                         GITHUB_ACTION=case.step, ACTOR_SESSION=None,
                         ANTIGRAVITY_AGENT=case.antigravity_agent,
                         ANTIGRAVITY_CONVERSATION_ID=case.antigravity_session):
            got, code, exited = answered(channel.agent)
            if case.answer is None:
                if not exited:
                    problems.append(f"agent: {case.name}: expected a refusal, got {got!r} "
                                    f"returned and {code!r} exited")
            elif code is not None:
                problems.append(f"agent: {case.name}: exited with {code}")
            elif got != case.answer:
                problems.append(f"agent: {case.name}: expected {case.answer!r}, got {got!r}")
    return problems
