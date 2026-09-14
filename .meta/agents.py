#!/usr/bin/env python3
"""Count the agents a review spawns against the fan-out ceiling (solorepo's DR-191).

A ceiling that is not checked is a wish, not a bound. solorepo's DR-166 established
an agent fan-out ceiling chosen with review depth (evaluated via solorepo's DR-188):
three subagents on the boundary path, and one on standard paths. solorepo's DR-189
instructs foreground review subagents to be dispatched concurrently in a single message.
However, allowed tools granted `Agent` without limit, leaving passes that exceeded the
depth ceiling detectable only through manual transcript inspection.

Following solorepo's DR-122's principle of verifying execution facts rather than accepting
prompt claims, this tool counts the subagents spawned in a review session from the
execution transcript and fails closed (exit code 1, red run) if the fan-out ceiling is breached.

Usage:
    python3 .meta/agents.py --file path/to/claude-execution-output.json --ceiling 3
    python3 .meta/agents.py < path/to/transcript.json
    just agents --ceiling 1 path/to/execution.json
"""

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class SpawnedAgent:
    """A subagent invocation recorded during the review session."""

    id: str | None
    name: str
    description: str = ""
    subagent_type: str = ""


def _claude_tool_use(node: dict[str, Any]) -> SpawnedAgent | None:
    """The `Agent` call a Claude Code `tool_use` block records, or `None` for any other block.

    The tool's name is read from `name`, falling back to `tool`, and matched
    case-insensitively. The description is the call's `description`, falling
    back to its `prompt`, truncated to 120 characters.
    """
    if node.get("type") != "tool_use":
        return None
    if str(node.get("name") or node.get("tool")).strip().lower() != "agent":
        return None
    supplied = node.get("input") if isinstance(node.get("input"), dict) else {}
    return SpawnedAgent(
        id=node.get("id"),
        name="Agent",
        description=str(supplied.get("description") or supplied.get("prompt") or "")[:120].strip(),
        subagent_type=str(supplied.get("subagent_type") or supplied.get("type") or "").strip(),
    )


def _openai_function_call(node: dict[str, Any]) -> SpawnedAgent | None:
    """The `Agent` call an OpenAI-style function block records, or `None` for any other block.

    Carries neither description nor subagent type: the representation holds a
    call's arguments as a JSON string rather than a mapping, and the ceiling
    counts calls rather than reading them.
    """
    if node.get("type") != "function" or not isinstance(node.get("function"), dict):
        return None
    if str(node["function"].get("name")).strip().lower() != "agent":
        return None
    return SpawnedAgent(id=node.get("id"), name="Agent")


def _extract_from_dict(d: dict[str, Any], seen_ids: set[str], agents: list[SpawnedAgent]) -> None:
    """Appends the `Agent` call a JSON dictionary records, if any, then walks its values.

    A call carrying an `id` is appended once and its id added to `seen_ids`, so
    a block a stream emits twice counts once. A call with no id is appended
    every time, having nothing to be recognised by.
    """
    spawned = _claude_tool_use(d) or _openai_function_call(d)
    if spawned and not (spawned.id and spawned.id in seen_ids):
        if spawned.id:
            seen_ids.add(spawned.id)
        agents.append(spawned)

    for val in d.values():
        _walk(val, seen_ids, agents)


def _walk(node: Any, seen_ids: set[str], agents: list[SpawnedAgent]) -> None:
    """Traverses nested JSON structures collecting Agent invocations."""
    if isinstance(node, dict):
        _extract_from_dict(node, seen_ids, agents)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _walk(item, seen_ids, agents)


def _from_document(text: str) -> list[SpawnedAgent] | None:
    """The agents of a transcript that is one JSON document, or `None` when it is not one."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    seen_ids: set[str] = set()
    agents: list[SpawnedAgent] = []
    _walk(data, seen_ids, agents)
    return agents


def _from_ndjson(text: str) -> list[SpawnedAgent] | None:
    """The agents of a transcript that is a JSON Lines event stream, or `None` when no line parses.

    A line that is not a self-contained object is skipped rather than fatal: a
    harness writes its events interleaved with plain log output.
    """
    seen_ids: set[str] = set()
    agents: list[SpawnedAgent] = []
    parsed_a_line = False
    for line in text.splitlines():
        candidate = line.strip()
        if not (candidate.startswith("{") and candidate.endswith("}")):
            continue
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        parsed_a_line = True
        _walk(data, seen_ids, agents)
    return agents if parsed_a_line else None


def _from_log(text: str) -> list[SpawnedAgent]:
    """The agents named by the `tool_use` blocks a raw log transcript quotes.

    The last reader, for a transcript that parses neither as a document nor as
    a stream. It matches only blocks holding no nested object, so a call whose
    `input` survived into the log is not found; what is left of the transcript
    at this point is text a runner wrapped, and the count is a floor.
    """
    seen_ids: set[str] = set()
    agents: list[SpawnedAgent] = []
    for match in re.finditer(
        r'\{[^{}]*?"type"\s*:\s*"tool_use"[^{}]*?"name"\s*:\s*"Agent"[^{}]*?\}',
        text,
        re.DOTALL | re.IGNORECASE,
    ):
        found = re.search(r'"id"\s*:\s*"([^"]+)"', match.group(0))
        call_id = found.group(1) if found else None
        if not (call_id and call_id in seen_ids):
            if call_id:
                seen_ids.add(call_id)
            agents.append(SpawnedAgent(id=call_id, name="Agent"))
    return agents


def parse_agents(content: str | bytes | dict[str, Any] | list[Any]) -> list[SpawnedAgent]:
    """Parses raw text, JSON data, or message event streams to extract spawned agents.

    Supports:
    - Structured Python dicts or lists.
    - Full JSON documents (single object or array).
    - JSON Lines (NDJSON) event streams.
    - Fallback regex extraction from raw log transcripts.

    The three text readers are tried in that order and the first that recognises
    the transcript answers it, so a stream of events is never re-read as the log
    text it also is.
    """
    if isinstance(content, (dict, list)):
        seen_ids: set[str] = set()
        agents: list[SpawnedAgent] = []
        _walk(content, seen_ids, agents)
        return agents

    if isinstance(content, bytes):
        text = content.decode("utf-8", errors="replace")
    else:
        text = str(content)

    if not text.strip():
        return []

    for reader in (_from_document, _from_ndjson):
        found = reader(text)
        if found is not None:
            return found
    return _from_log(text)


def evaluate_ceiling(count: int, ceiling: int | None) -> tuple[bool, str]:
    """Evaluates whether the agent count satisfies the fan-out ceiling.

    Returns a tuple of (passed, message).
    """
    if ceiling is None:
        return True, f"Spawned {count} subagent(s) (no ceiling enforced)."

    if count <= ceiling:
        return True, f"Spawned {count} subagent(s) within the fan-out ceiling of {ceiling}."

    return False, (
        f"::error::Spawned {count} subagent(s), breaching the fan-out ceiling of {ceiling} "
        "(solorepo's DR-166, solorepo's DR-191)."
    )


def read_content(target: str | None, quiet: bool = False) -> str:
    """Reads execution transcript content from a file path or stdin."""
    if not target or target == "-":
        if not sys.stdin.isatty():
            return sys.stdin.read()
        return ""

    path = pathlib.Path(target)
    if not path.exists():
        if not quiet:
            sys.stderr.write(f"Note: execution file '{target}' does not exist; treating as 0 agents.\n")
        return ""

    return path.read_text(encoding="utf-8", errors="replace")


def main() -> None:
    """Entry point for parsing agent invocations and checking the fan-out ceiling."""
    parser = argparse.ArgumentParser(
        description="Count review subagent invocations against the depth fan-out ceiling (solorepo's DR-191)."
    )
    parser.add_argument("pos_file", nargs="?", default=None, help="Execution transcript file path")
    parser.add_argument("--file", "-f", default=None, help="Execution transcript file path")
    parser.add_argument("--ceiling", "-c", type=int, default=None, help="Maximum allowed subagent count")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress verbose listing of spawned agents")

    args = parser.parse_args()
    target_file = args.file or args.pos_file

    raw_content = read_content(target_file)
    spawned = parse_agents(raw_content)
    count = len(spawned)

    passed, message = evaluate_ceiling(count, args.ceiling)

    if not args.quiet:
        print(message)
        for idx, agent in enumerate(spawned, 1):
            ident = f" [{agent.id}]" if agent.id else ""
            desc = f": {agent.description}" if agent.description else ""
            sub_type = f" ({agent.subagent_type})" if agent.subagent_type else ""
            print(f"  {idx}. {agent.name}{ident}{sub_type}{desc}")

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
