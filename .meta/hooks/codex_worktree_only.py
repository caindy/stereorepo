#!/usr/bin/env python3
"""Adapt Codex PreToolUse events to reviewer worktree confinement."""
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import codex_hooks

from lib.worktree_only import paths, shell, verdict


def decision(event: object) -> dict[str, object]:
    """Return Codex's nested hook decision for one reviewer tool event."""
    return codex_hooks.decision(event, _evaluate, verdict.record_evidence)


def _evaluate(tool: str, tool_input: dict[str, Any]) -> str | None:
    """Apply Codex reviewer tool, write, and worktree policies."""
    if tool in {"apply_patch", "ApplyPatch"}:
        return "Blocked: the reviewer cannot write to the worktree."
    if tool not in {"Bash", "Read", "Grep", "Glob", *paths.TOOLS}:
        return f"Blocked: the reviewer does not have a permitted {tool!r} tool."
    if tool == "Bash" and _local_read(tool_input):
        return None
    return verdict.blocked(tool, tool_input)


def _local_read(tool_input: dict[str, Any]) -> bool:
    """Allow one plain cat command when its target and working directory are contained."""
    words = shell.words_of(tool_input.get("command", ""))
    if not isinstance(words, list) or len(words) != 2 or words[0] != "cat" \
            or words[1].startswith("-"):
        return False
    where = tool_input.get("Cwd") or tool_input.get("dir_path")
    return (not where or not paths.elsewhere(where)) and not paths.outside(words[1])


def main() -> int:
    """Read one Codex event and print its decision."""
    return codex_hooks.main(_evaluate, verdict.record_evidence)


if __name__ == "__main__":
    sys.exit(main())
