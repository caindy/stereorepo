"""The hook's entry: the event read from stdin, the command line judged, and the exit code the harness reads (solorepo's DR-069, solorepo's DR-260).

`main` reads the event from stdin, exits 0 to permit execution across all harnesses,
or on refusal writes a JSON refusal to stdout and exits 2 with an explanatory message on stderr
under Claude Code and Gemini CLI, or writes a JSON decision object to stdout with exit 0 under
Antigravity CLI (solorepo's DR-260). Appends decision evidence to `SOLOREPO_HOOK_EVIDENCE` if set.
"""
import datetime
import json
import os
import pathlib
import sys
from typing import Any

from lib.signed_channel import reach

SHELL_TOOLS: set[str] = {"Bash", "run_shell_command", "run_command"}
"""Shell execution tool names intercepted by the signed channel hook."""


def record_evidence(tool: str, permitted: bool, evidence: str | pathlib.Path | None = None) -> None:
    """Records one line of hook decision evidence to the designated evidence file.

    Parameters:
        tool: Tool name evaluated by the hook.
        permitted: True if allowed, False if refused.
        evidence: The file to append to; `SOLOREPO_HOOK_EVIDENCE` names it where
            the caller passes none. Writes nothing if unset.
    """
    named = evidence if evidence is not None else os.environ.get("SOLOREPO_HOOK_EVIDENCE")
    if not named:
        return
    try:
        path = pathlib.Path(named)
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
        verdict = "permit" if permitted else "refuse"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {tool} {verdict}\n")
    except Exception:
        return


def blocked(tool: str, tool_input: dict[str, Any]) -> str | None:
    """Determines whether a tool call reaches GitHub without going through the channel.

    Parameters:
        tool: Tool name being invoked.
        tool_input: Arguments passed to the tool.

    Returns:
        str | None: Refusal message if blocked, or None if permitted.
    """
    if tool not in SHELL_TOOLS:
        return None
    command = tool_input.get("command") or tool_input.get("CommandLine") or ""
    return reach.blocked(command)


def main() -> int:
    """Execute the before-tool hook entry point reading event JSON from stdin.

    Returns:
        int: Process exit code 0 to permit execution under all harnesses. Under
        Claude Code and Gemini CLI, exits 2 to block with an explanatory refusal
        on stderr. Under Antigravity CLI, exits 0 to block with a JSON decision
        `{"decision": "deny", "reason": "..."}` on stdout (solorepo's DR-260).
        A payload that cannot be parsed as JSON or read from stdin is blocked across
        all harnesses: if an Antigravity envelope is identified, outputs a JSON
        refusal on stdout with exit 0; otherwise, outputs both a JSON refusal on
        stdout and an explanatory diagnostic on stderr with exit 2, ensuring no
        harness fails open.
    """
    tool: str = ""
    is_antigravity = False
    raw = ""
    try:
        raw = sys.stdin.read()
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise TypeError(f"expected JSON object, got {type(event).__name__}")
        if "toolCall" in event:
            is_antigravity = True
            tool_call = event.get("toolCall") or {}
            tool = tool_call.get("name") or ""
            tool_input = tool_call.get("args") or {}
        else:
            tool = event.get("tool_name") or ""
            tool_input = event.get("tool_input") or {}
        problem = blocked(tool, tool_input)
    except BaseException as exc:
        if "toolCall" in raw:
            is_antigravity = True
        problem = f"Blocked: the hook failed ({type(exc).__name__}); refusing rather than guessing."
    record_evidence(tool or "?", not problem)
    if is_antigravity:
        decision = {"decision": "deny", "reason": problem} if problem else {"decision": "allow"}
        print(json.dumps(decision))
        return 0
    if problem:
        print(json.dumps({"decision": "deny", "reason": problem}))
        print(problem, file=sys.stderr)
        return 2
    return 0
