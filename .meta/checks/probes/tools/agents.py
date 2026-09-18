"""`agents.py`'s count of agents against the fan-out ceiling (solorepo's DR-191).
"""
import json

from checks.collect import META, check
from checks.probes.harness import load_module, written


@check("agents probes", pre=True)
def agents_probes():
    """`agents.py` counts the `Agent` calls a review transcript records, in each shape a transcript takes, and holds the count to the ceiling (solorepo's DR-191).

    Nothing — an empty string, whitespace, an empty dict, an empty list —
    counts no agent. One assistant turn holding an `Agent` call beside a
    `Read` call counts one, with the call's own id and name. Three `Agent`
    calls in one turn, which is the concurrent dispatch solorepo's DR-189
    asks for, count three. A `tool_use` id a stream emits twice counts once.
    A JSON Lines stream and a raw log quoting `tool_use` blocks between plain
    lines each count their two. The ceiling passes a count at or under it,
    passes any count when there is none, and refuses one over it naming the
    breach. A path that does not exist reads as empty, quietly, and a
    transcript written to a file reads back to the count it held.
    """
    agents = load_module(META / "agents.py", "agents_module")
    problems = []
    for case, given in (("an empty string", ""), ("a whitespace string", "   \n\t  "),
                        ("an empty dict", {}), ("an empty list", [])):
        if agents.parse_agents(given) != []:
            problems.append(f"agents: expected [] for {case}")

    single_turn = {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "Dispatching agents"},
            {"type": "tool_use", "id": "toolu_01", "name": "Agent",
             "input": {"description": "Review boundary path", "subagent_type": "general-purpose"}},
            {"type": "tool_use", "id": "toolu_02", "name": "Read",
             "input": {"file_path": "README.md"}},
        ],
    }
    found = agents.parse_agents(single_turn)
    if len(found) != 1 or found[0].id != "toolu_01" or found[0].name != "Agent":
        problems.append(f"agents: expected 1 agent for one turn with one Agent call, got {found}")

    concurrent_turn = [{
        "role": "assistant",
        "content": [
            {"type": "tool_use", "id": "toolu_01", "name": "Agent",
             "input": {"description": "Review boundary hooks"}},
            {"type": "tool_use", "id": "toolu_02", "name": "Agent",
             "input": {"description": "Review timing metrics"}},
            {"type": "tool_use", "id": "toolu_03", "name": "Agent",
             "input": {"description": "Review assertions"}},
        ],
    }]
    duplicate_turn = [
        {"type": "tool_use", "id": "toolu_dup", "name": "Agent", "input": {"description": "First emission"}},
        {"type": "tool_use", "id": "toolu_dup", "name": "Agent", "input": {"description": "Stream update"}},
        {"type": "tool_use", "id": "toolu_other", "name": "Agent", "input": {"description": "Distinct agent"}},
    ]
    ndjson = (
        '{"event": "start"}\n'
        '{"type": "tool_use", "id": "toolu_ndjson_1", "name": "Agent", "input": {"description": "Line 1"}}\n'
        '{"type": "tool_use", "id": "toolu_ndjson_2", "name": "Agent", "input": {"description": "Line 2"}}\n'
    )
    raw_log = (
        "Runner log output:\n"
        '{"type": "tool_use", "id": "toolu_log_1", "name": "Agent"}\n'
        "Some intervening non-json log lines\n"
        '{"type": "tool_use", "id": "toolu_log_2", "name": "Agent"}\n'
    )
    for case, transcript, count in (
        ("three concurrent Agent calls in one turn", concurrent_turn, 3),
        ("a tool_use id emitted twice", duplicate_turn, 2),
        ("a JSON Lines stream", ndjson, 2),
        ("a raw log quoting tool_use blocks", raw_log, 2),
    ):
        seen = agents.parse_agents(transcript)
        if len(seen) != count:
            problems.append(f"agents: expected {count} agents for {case}, got {len(seen)}")

    for count, ceiling, passes, says in ((2, 3, True, ""), (3, 3, True, ""),
                                         (4, 3, False, "breaching the fan-out ceiling of 3"),
                                         (5, None, True, "")):
        ok, message = agents.evaluate_ceiling(count, ceiling)
        if ok != passes or says not in message:
            wanted = f"{passes} saying {says!r}" if says else f"{passes}"
            problems.append(f"agents: evaluate_ceiling({count}, {ceiling}) expected {wanted}, "
                            f"got {ok}, {message!r}")

    missing = agents.read_content("/nonexistent/file/path/here.json", quiet=True)
    if missing != "":
        problems.append(f"agents: read_content on a missing file expected '', got {missing!r}")
    with written(".json", json.dumps(single_turn)) as transcript_file:
        from_file = agents.parse_agents(agents.read_content(str(transcript_file)))
        if len(from_file) != 1:
            problems.append(f"agents: read_content from a written file expected 1 agent, got {len(from_file)}")
    return problems
