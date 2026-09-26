#!/usr/bin/env python3
"""Adapt Copilot CLI PreToolUse events to the signed-channel gate."""
import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from lib.signed_channel import verdict


def decision(event: object) -> dict[str, str]:
    """Return Copilot's permission decision for one PreToolUse event."""
    try:
        if not isinstance(event, dict):
            raise TypeError
        tool = event.get("tool_name")
        tool_input = event.get("tool_input")
        if not isinstance(tool, str) or not isinstance(tool_input, dict):
            raise TypeError
        problem = verdict.blocked(tool, tool_input)
    except BaseException as exc:  # noqa: BLE001  # reason: an unreadable hook event must deny the tool call
        tool = "?"
        problem = f"Blocked: the hook failed ({type(exc).__name__}); refusing rather than guessing."
    verdict.record_evidence(tool, not problem)
    if problem:
        return {"permissionDecision": "deny", "permissionDecisionReason": problem}
    return {"permissionDecision": "allow"}


def main() -> int:
    """Read one Copilot PreToolUse event and write its permission decision."""
    try:
        event: Any = json.load(sys.stdin)
    except BaseException as exc:  # noqa: BLE001  # reason: an unreadable hook event must deny the tool call
        event = exc
    print(json.dumps(decision(event)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
