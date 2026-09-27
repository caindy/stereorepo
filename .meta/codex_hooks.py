"""Codex PreToolUse event parsing and response protocol."""
import json
import sys
from collections.abc import Callable
from typing import Any

Evaluator = Callable[[str, dict[str, Any]], str | None]
Recorder = Callable[[str, bool], None]


def decision(event: object, evaluate: Evaluator, record: Recorder) -> dict[str, object]:
    """Return a fail-closed Codex decision and record its Evidence."""
    tool = "?"
    try:
        if isinstance(event, str):
            event = json.loads(event)
        if not isinstance(event, dict):
            raise TypeError
        raw_tool = event.get("tool_name")
        tool_input = event.get("tool_input")
        if not isinstance(raw_tool, str) or not isinstance(tool_input, dict):
            raise TypeError
        tool = raw_tool
        problem = evaluate(tool, tool_input)
    except BaseException as exc:  # noqa: BLE001  # reason: a malformed event must deny its tool call
        problem = f"Blocked: the hook failed ({type(exc).__name__}); refusing rather than guessing."
    record(tool, not problem)
    specific: dict[str, str] = {"hookEventName": "PreToolUse"}
    if problem:
        specific.update(permissionDecision="deny", permissionDecisionReason=problem)
    else:
        specific["permissionDecision"] = "allow"
    return {"hookSpecificOutput": specific}


def main(evaluate: Evaluator, record: Recorder) -> int:
    """Read one event from standard input and print its permission decision."""
    print(json.dumps(decision(sys.stdin.read(), evaluate, record)))
    return 0
