"""The before-tool events each harness sends, and which the worktree hook must refuse or permit from the payload alone.
"""

from typing import Any

from checks.collect import ROOT

EVENTS: tuple[tuple[str, tuple[tuple[str, Any], ...]], ...] = (
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
    ("a payload that is JSON but not an object is refused, rather than raising past the entry "
     "point into an exit code both harnesses read as a non-blocking error (solorepo's #645)", (
        ("refuse", []),
        ("refuse", "PreToolUse"),
        ("refuse", 5),
        ("refuse", None),
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

An event is any JSON value a harness could put on stdin, not only an object. The
entry point refuses what it cannot read rather than guessing, and a row for each
of the other JSON kinds holds that much of it: an exception escaping it exits 1,
which both harnesses read as a non-blocking error and run the tool anyway, so
the whole boundary fails open on a payload it never had to understand
(solorepo's #645). What this table cannot reach is a payload that is not JSON at
all, since every row gets to the hook through `json.dumps` and so is a JSON
value by construction; `registration.UNREADABLE` carries that case, to a real
subprocess whose stdin takes bytes.
"""
