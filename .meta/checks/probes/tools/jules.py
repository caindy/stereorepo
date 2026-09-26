"""Probes for Jules Challenge verdict parsing and channel posting."""

import os
import pathlib
import tempfile
from typing import Any

from checks.collect import check
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
