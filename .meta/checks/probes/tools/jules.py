"""Probes for Google Labs Jules REST client and Challenge verdict triage."""

import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

from checks.collect import META, check
from checks.probes.harness import load_module

VERDICT = ("**Worth doing.** A concrete cost.\n\n"
           "**Waits on.** Nothing.\n\n"
           "**Already answered.** No matching mechanism.\n\n"
           "**Decision owed.** No decision remains.\n"
           "LEVEL: medium")


@check("Jules Challenge triage probes", pre=True)
def jules_triage_probes() -> list[str]:
    """Require a complete verdict and post it through the reviewer channel."""
    triage: Any = load_module(".meta/jules/triage.py", "jules_triage_probe", register=False)
    problems = []
    level, body = triage.parse_verdict(VERDICT)
    if level != "medium" or "LEVEL:" in body or body.count("**") != 8:
        problems.append(f"Jules parsed the complete verdict as {level!r}, {body!r}")
    malformed = (VERDICT.replace("**Decision owed.** No decision remains.", "**Decision owed.**"),
                 VERDICT.replace("LEVEL: medium", "LEVEL: medium\nLEVEL: easy"),
                 VERDICT.replace("**Waits on.** Nothing.", "**Waits on.**"))
    for response in malformed:
        try:
            triage.parse_verdict(response)
        except ValueError:
            continue
        problems.append(f"Jules accepted a malformed verdict: {response!r}")
    with tempfile.TemporaryDirectory() as temporary:
        original_cwd = pathlib.Path.cwd()
        original_evidence, original_run = triage.repository_evidence, triage.subprocess.run
        calls: list[tuple[list[str], str]] = []
        prompts: list[str] = []

        def create_session(**kwargs: Any) -> dict[str, str]:
            prompts.append(str(kwargs["prompt"]))
            return {"id": "session-7"}

        def post(command: list[str], **kwargs: Any) -> None:
            calls.append((command, str(kwargs["input"])))

        try:
            os.chdir(temporary)
            pathlib.Path(".review").mkdir()
            pathlib.Path(".review/challenge.md").write_text("A concrete Challenge\n")
            pathlib.Path(".review/open.md").write_text("# Open Issues\n")
            triage.repository_evidence = lambda challenge: "tracked evidence"
            triage.subprocess.run = post
            result = triage.read_issue(
                "7", "key", triage.Options("Read Challenge 7", 60, False),
                triage.Api(create_session,
                           lambda *args, **kwargs: {"activities": [
                               {"agentMessaged": {"text": "Working on the Challenge."}},
                               {"agentMessaged": {"text": VERDICT}},
                               {"sessionCompleted": {}},
                           ]}),
            )
        finally:
            triage.repository_evidence, triage.subprocess.run = original_evidence, original_run
            os.chdir(original_cwd)
    expected = [".meta/say/move", "--role", "reviewer", "triage", "7", "medium"]
    if result["level"] != "medium" or calls != [(expected, body + "\n")]:
        problems.append(f"Jules posted {calls!r} and returned {result!r}")
    if not prompts or "tracked evidence" not in prompts[0] \
            or "A concrete Challenge" not in prompts[0]:
        problems.append("Jules received no Challenge and repository context")
    return problems


def _probe_extract_agent_text(client: Any) -> list[str]:
    """Verify extract_agent_text handles agentMessage, text, message, and fallback keys."""
    problems: list[str] = []

    case_agent_message = [
        {
            "name": "act1",
            "originator": "agent",
            "agentMessaged": {"agentMessage": "RECOMMENDED_VERDICT: APPROVE"},
        }
    ]
    if client.extract_agent_text(case_agent_message) != "RECOMMENDED_VERDICT: APPROVE":
        problems.append(
            "jules probes: extract_agent_text failed to extract agentMessaged.agentMessage"
        )

    case_text = [
        {"name": "act2", "originator": "agent", "agentMessaged": {"text": "LGTM from text"}}
    ]
    if client.extract_agent_text(case_text) != "LGTM from text":
        problems.append("jules probes: extract_agent_text failed to extract agentMessaged.text")

    case_message = [
        {"name": "act3", "originator": "agent", "agentMessaged": {"message": "LGTM from message"}}
    ]
    if client.extract_agent_text(case_message) != "LGTM from message":
        problems.append("jules probes: extract_agent_text failed to extract agentMessaged.message")

    case_flat_agent_message = [
        {"name": "act4", "originator": "agent", "agentMessage": "Direct agentMessage"}
    ]
    if client.extract_agent_text(case_flat_agent_message) != "Direct agentMessage":
        problems.append("jules probes: extract_agent_text failed to extract act.agentMessage")

    case_flat_text = [
        {"name": "act5", "originator": "agent", "text": "Direct text"}
    ]
    if client.extract_agent_text(case_flat_text) != "Direct text":
        problems.append("jules probes: extract_agent_text failed to extract act.text")

    case_multi = [
        {"originator": "user", "text": "please review"},
        {"originator": "agent", "agentMessaged": {"agentMessage": "First agent paragraph."}},
        {"originator": "agent", "agentMessaged": {"text": "Second agent paragraph."}},
    ]
    expected_multi = "First agent paragraph.\n\nSecond agent paragraph."
    if client.extract_agent_text(case_multi) != expected_multi:
        problems.append("jules probes: extract_agent_text failed to join multiple agent messages")

    case_empty = [
        {"originator": "user", "text": "hello"},
        {"originator": "agent", "agentMessaged": {}},
    ]
    if client.extract_agent_text(case_empty) != "":
        problems.append(
            "jules probes: extract_agent_text did not return empty string on empty payload"
        )

    return problems


def _probe_poll_session_activities(client: Any) -> list[str]:
    """Verify poll_session_activities waits for agent text or terminates on final state."""
    problems: list[str] = []
    original_list = client.list_activities
    original_get = client.get_session
    original_sleep = client.time.sleep

    try:
        sleeps: list[float] = []
        client.time.sleep = sleeps.append

        poll_count = 0

        def fake_list_activities(session_id: str, api_key: str) -> dict[str, Any]:
            nonlocal poll_count
            poll_count += 1
            if poll_count == 1:
                return {"activities": [{"originator": "user", "text": "start"}]}
            return {
                "activities": [
                    {"originator": "user", "text": "start"},
                    {"originator": "agent", "agentMessaged": {"agentMessage": "Done"}},
                ]
            }

        def fake_get_session(session_id: str, api_key: str) -> dict[str, Any]:
            return {"state": "IN_PROGRESS"}

        client.list_activities = fake_list_activities
        client.get_session = fake_get_session

        acts = client.poll_session_activities(
            "sessions/sess-1", api_key="k", timeout_seconds=10, poll_interval=1.0
        )
        if len(acts) != 2 or client.extract_agent_text(acts) != "Done":
            problems.append(
                "jules probes: poll_session_activities did not return activities once text arrived"
            )
        if len(sleeps) != 1 or sleeps[0] != 1.0:
            problems.append(
                f"jules probes: poll_session_activities sleep count {sleeps!r} != [1.0]"
            )

        sleeps_term: list[float] = []
        client.time.sleep = sleeps_term.append

        for terminal_state in ("COMPLETED", "FAILED", "CANCELLED"):
            client.list_activities = lambda s, api_key: {"activities": [{"originator": "user"}]}
            client.get_session = lambda s, api_key, st=terminal_state: {"state": st}
            term_acts = client.poll_session_activities(
                "sessions/sess-2", api_key="k", timeout_seconds=10
            )
            if len(term_acts) != 1:
                problems.append(
                    f"jules probes: poll_session_activities did not terminate on {terminal_state}"
                )

    finally:
        client.list_activities = original_list
        client.get_session = original_get
        client.time.sleep = original_sleep

    return problems


def _probe_determine_verdict(client: Any) -> list[str]:
    """Verify determine_verdict defaults to --comment on empty text and obeys checks."""
    problems: list[str] = []

    if client.determine_verdict(True, False, 0, 0, "") != "--comment":
        problems.append(
            "jules probes: determine_verdict did not return --comment on empty review text"
        )

    if client.determine_verdict(True, False, 0, 0, "   \n\t  ") != "--comment":
        problems.append(
            "jules probes: determine_verdict did not return --comment on whitespace review text"
        )

    if client.determine_verdict(True, False, 0, 0, "RECOMMENDED_VERDICT: APPROVE") != "--approve":
        problems.append(
            "jules probes: determine_verdict did not return --approve when all conditions pass"
        )

    failure_cases = [
        (False, False, 0, 0, "RECOMMENDED_VERDICT: APPROVE", "failed form check"),
        (True, True, 0, 0, "RECOMMENDED_VERDICT: APPROVE", "failed CI"),
        (True, False, 1, 0, "RECOMMENDED_VERDICT: APPROVE", "unresolved threads"),
        (True, False, 0, 1, "RECOMMENDED_VERDICT: APPROVE", "findings"),
        (False, False, 0, 0, "", "failed form check with empty text"),
        (True, True, 0, 0, "", "failed CI with empty text"),
        (True, False, 1, 0, "", "unresolved threads with empty text"),
        (True, False, 0, 1, "", "findings with empty text"),
        (True, False, 0, 0, "RECOMMENDED_VERDICT: REQUEST_CHANGES", "recommendation"),
    ]
    for form_ok, ci_fail, unres, findings, text, reason in failure_cases:
        verdict = client.determine_verdict(form_ok, ci_fail, unres, findings, text)
        if verdict != "--request-changes":
            problems.append(
                f"jules probes: determine_verdict did not return --request-changes on {reason}"
            )

    return problems


def _probe_review_pr_empty_abort(client: Any) -> list[str]:
    """Verify review_pr aborts with diagnostics when session produces empty review text."""
    problems: list[str] = []
    original_create = client.create_session
    original_poll = client.poll_session_activities
    original_sub = client.subprocess.run

    try:
        client.create_session = lambda *args, **kwargs: {"id": "sess-empty-test"}
        client.poll_session_activities = lambda *args, **kwargs: [
            {"originator": "user", "text": "start review"},
            {"originator": "agent", "agentMessaged": {}},
        ]
        client.subprocess.run = lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0] if args else [],
            returncode=0,
            stdout="0",
            stderr="",
        )

        try:
            client.review_pr(pr_number="999", api_key="dummy-key", dry_run=False)
            problems.append(
                "jules probes: review_pr did not raise RuntimeError on empty review body"
            )
        except RuntimeError as e:
            err_msg = str(e)
            if "(activities=2)" not in err_msg:
                problems.append(
                    f"jules probes: review_pr error message {err_msg!r} missing diagnostics"
                )
            if "Jules session sess-empty-test returned an empty review response" not in err_msg:
                problems.append(
                    f"jules probes: review_pr error message {err_msg!r} missing empty prefix"
                )
    finally:
        client.create_session = original_create
        client.poll_session_activities = original_poll
        client.subprocess.run = original_sub

    return problems


@check("jules client probes", pre=True)
def jules_probes() -> list[str]:
    """Prove Jules activities parsing, polling, verdict determination, and empty review handling."""
    if str(META / "jules") not in sys.path:
        sys.path.insert(0, str(META / "jules"))
    client = load_module(META / "jules" / "client.py", "jules_client", register=False)
    problems: list[str] = []
    problems.extend(_probe_extract_agent_text(client))
    problems.extend(_probe_poll_session_activities(client))
    problems.extend(_probe_determine_verdict(client))
    problems.extend(_probe_review_pr_empty_abort(client))
    return problems
