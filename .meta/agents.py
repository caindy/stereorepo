#!/usr/bin/env python3
"""Transcript parser and subagent fan-out ceiling validator.

Counts subagent invocations recorded in review session execution transcripts
across single-document JSON, JSON Lines (NDJSON), and formatted log representations,
verifying compliance with the fan-out ceiling (solorepo's DR-166, solorepo's DR-188,
solorepo's DR-189, solorepo's DR-191).

History in agents.history.md (solorepo's DR-171).
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
    """Extracts an Agent invocation from a Claude Code tool_use block.

    Args:
        node: Dictionary representing a message block or event node.

    Returns:
        SpawnedAgent | None: SpawnedAgent instance if the block invokes the Agent tool, else None.
    """
    if node.get("type") != "tool_use":
        return None
    if str(node.get("name") or node.get("tool")).strip().lower() != "agent":
        return None
    given = node.get("input")
    supplied: dict[str, Any] = given if isinstance(given, dict) else {}
    return SpawnedAgent(
        id=node.get("id"),
        name="Agent",
        description=str(supplied.get("description") or supplied.get("prompt") or "")[:120].strip(),
        subagent_type=str(supplied.get("subagent_type") or supplied.get("type") or "").strip(),
    )


def _openai_function_call(node: dict[str, Any]) -> SpawnedAgent | None:
    """Extracts an Agent invocation from an OpenAI function call block.

    Args:
        node: Dictionary representing a message block or function call node.

    Returns:
        SpawnedAgent | None: SpawnedAgent instance if the call targets the Agent function, else None.
    """
    if node.get("type") != "function" or not isinstance(node.get("function"), dict):
        return None
    if str(node["function"].get("name")).strip().lower() != "agent":
        return None
    return SpawnedAgent(id=node.get("id"), name="Agent")


def _extract_from_dict(d: dict[str, Any], seen_ids: set[str], agents: list[SpawnedAgent]) -> None:
    """Extracts agent calls from a dictionary node and recursively inspects values.

    Args:
        d: JSON dictionary node.
        seen_ids: Set of deduplicated tool call identifiers.
        agents: Destination list accumulating discovered SpawnedAgent instances.
    """
    spawned = _claude_tool_use(d) or _openai_function_call(d)
    if spawned and not (spawned.id and spawned.id in seen_ids):
        if spawned.id:
            seen_ids.add(spawned.id)
        agents.append(spawned)

    for val in d.values():
        _walk(val, seen_ids, agents)


def _walk(node: Any, seen_ids: set[str], agents: list[SpawnedAgent]) -> None:
    """Recursively traverses nested JSON structures collecting Agent invocations.

    Args:
        node: Arbitrary JSON data structure (dict, list, or scalar).
        seen_ids: Set of deduplicated tool call identifiers.
        agents: Destination list accumulating discovered SpawnedAgent instances.
    """
    if isinstance(node, dict):
        _extract_from_dict(node, seen_ids, agents)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _walk(item, seen_ids, agents)


def _from_document(text: str) -> list[SpawnedAgent] | None:
    """Parses a transcript represented as a single JSON document.

    Args:
        text: JSON document string.

    Returns:
        list[SpawnedAgent] | None: List of discovered agents, or None if JSON decoding fails.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    seen_ids: set[str] = set()
    agents: list[SpawnedAgent] = []
    _walk(data, seen_ids, agents)
    return agents


def _from_ndjson(text: str) -> list[SpawnedAgent] | None:
    """Parses a transcript represented as a newline-delimited JSON stream.

    Args:
        text: Multi-line JSON Lines string.

    Returns:
        list[SpawnedAgent] | None: List of discovered agents, or None if no valid line parsed.
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
    """Extracts agent invocations from raw text logs using regex patterns.

    Args:
        text: Raw log text string.

    Returns:
        list[SpawnedAgent]: List of extracted SpawnedAgent instances.
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
    """Parses raw text, JSON data, or event streams to extract spawned agents.

    Args:
        content: Input transcript as text, bytes, parsed JSON dict, or list.

    Returns:
        list[SpawnedAgent]: List of discovered SpawnedAgent instances.
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

    Args:
        count: Number of spawned subagents discovered.
        ceiling: Maximum permitted subagent ceiling, or None for unconstrained.

    Returns:
        tuple[bool, str]: A pair containing pass/fail boolean and a status message.
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
    """Reads execution transcript content from a file path or standard input.

    Args:
        target: File path string, '-' for stdin, or None.
        quiet: If True, suppresses missing file warnings on stderr.

    Returns:
        str: Transcript text content, or empty string on missing input.
    """
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
    """CLI entrypoint for counting subagent invocations against the fan-out ceiling."""
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
