"""The before-tool events each harness sends, and which the worktree hook must refuse or permit from the payload alone.
"""

from collect import ROOT

EVENTS = (
    ("both harnesses' before-tool payloads are read as one, and refused with the exit code each "
     "reads as a block (solorepo's #451)", (
        ("refuse", {"session_id": "s", "transcript_path": "/tmp/session.json", "cwd": str(ROOT),
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Read", "tool_input": {"file_path": "/etc/passwd"}}),
        ("refuse", {"session_id": "s", "transcript_path": "/tmp/session.json", "cwd": str(ROOT),
                    "hook_event_name": "BeforeTool", "timestamp": "2026-09-15T00:00:00Z",
                    "tool_name": "read_file", "tool_input": {"file_path": "/etc/passwd"}}),
        ("allow", {"session_id": "s", "transcript_path": "/tmp/session.json", "cwd": str(ROOT),
                   "hook_event_name": "BeforeTool", "timestamp": "2026-09-15T00:00:00Z",
                   "tool_name": "run_shell_command", "tool_input": {"command": "git status --porcelain"}}),
        ("allow", {"session_id": "s", "transcript_path": "/tmp/session.json", "cwd": str(ROOT),
                   "hook_event_name": "BeforeTool", "timestamp": "2026-09-15T00:00:00Z",
                   "tool_name": "write_todos", "tool_input": {"todos": []}}),
    )),
)
"""Each before-tool event with the verdict the hook's entry point owes it (solorepo's #451).

A group is `(name, rows)` and a row is `(want, event)`: the event as a harness
writes it to the hook's stdin, whole rather than as `blocked()`'s two arguments.
Claude Code's `PreToolUse` and Gemini CLI's `BeforeTool` carry the same
`tool_name` and `tool_input` beside different envelopes, and both read exit code
2 as a block with stderr as the reason, so the rows stand for the claim that one
reader serves both. A tool neither harness's matcher should send here is allowed
rather than refused: the hook answers on the tools it knows and does not guess.
"""
