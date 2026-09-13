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


def _extract_from_dict(d: dict[str, Any], seen_ids: set[str], agents: list[SpawnedAgent]) -> None:
    """Recursively extracts Agent tool use calls from a JSON dictionary."""
    tool_type = d.get("type")
    tool_name = d.get("name") or d.get("tool")

    # Claude Code tool_use invocation
    if tool_type == "tool_use" and str(tool_name).strip().lower() == "agent":
        call_id = d.get("id")
        if not call_id or call_id not in seen_ids:
            if call_id:
                seen_ids.add(call_id)
            inp = d.get("input") if isinstance(d.get("input"), dict) else {}
            desc = inp.get("description") or inp.get("prompt") or ""
            sub_type = inp.get("subagent_type") or inp.get("type") or ""
            agents.append(SpawnedAgent(
                id=call_id,
                name="Agent",
                description=str(desc)[:120].strip(),
                subagent_type=str(sub_type).strip(),
            ))

    # OpenAI-style function call representation
    elif tool_type == "function" and isinstance(d.get("function"), dict):
        fn = d["function"]
        if str(fn.get("name")).strip().lower() == "agent":
            call_id = d.get("id")
            if not call_id or call_id not in seen_ids:
                if call_id:
                    seen_ids.add(call_id)
                agents.append(SpawnedAgent(
                    id=call_id,
                    name="Agent",
                    description="",
                    subagent_type="",
                ))

    # Recurse into all dictionary values
    for val in d.values():
        _walk(val, seen_ids, agents)


def _walk(node: Any, seen_ids: set[str], agents: list[SpawnedAgent]) -> None:
    """Traverses nested JSON structures collecting Agent invocations."""
    if isinstance(node, dict):
        _extract_from_dict(node, seen_ids, agents)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _walk(item, seen_ids, agents)


def parse_agents(content: str | bytes | dict[str, Any] | list[Any]) -> list[SpawnedAgent]:
    """Parses raw text, JSON data, or message event streams to extract spawned agents.

    Supports:
    - Structured Python dicts or lists.
    - Full JSON documents (single object or array).
    - JSON Lines (NDJSON) event streams.
    - Fallback regex extraction from raw log transcripts.
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

    # 1. Attempt full document JSON parse
    try:
        data = json.loads(text)
        seen_ids = set()
        agents = []
        _walk(data, seen_ids, agents)
        return agents
    except json.JSONDecodeError:
        pass

    # 2. Attempt line-by-line JSON parsing (NDJSON)
    seen_ids = set()
    agents = []
    has_valid_json_line = False
    for line in text.splitlines():
        line_clean = line.strip()
        if not line_clean or not (line_clean.startswith("{") and line_clean.endswith("}")):
            continue
        try:
            line_data = json.loads(line_clean)
            has_valid_json_line = True
            _walk(line_data, seen_ids, agents)
        except json.JSONDecodeError:
            continue

    if has_valid_json_line:
        return agents

    # 3. Fallback regex search for tool_use blocks referencing Agent
    tool_use_matches = re.finditer(
        r'\{[^{}]*?"type"\s*:\s*"tool_use"[^{}]*?"name"\s*:\s*"Agent"[^{}]*?\}',
        text,
        re.DOTALL | re.IGNORECASE,
    )
    for m in tool_use_matches:
        block = m.group(0)
        id_match = re.search(r'"id"\s*:\s*"([^"]+)"', block)
        call_id = id_match.group(1) if id_match else None
        if not call_id or call_id not in seen_ids:
            if call_id:
                seen_ids.add(call_id)
            agents.append(SpawnedAgent(id=call_id, name="Agent"))

    return agents


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
