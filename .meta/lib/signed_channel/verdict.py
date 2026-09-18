"""The hook's entry: the event read from stdin, the command line judged, and the exit code the harness reads (solorepo's DR-069).

`main` reads the event, exits 0 to permit and 2 to block, and permits an event
that is not a `Bash` call or that is not JSON, which is not the hook's to judge.
"""
import json
import sys

from lib.signed_channel import reach


def main() -> int:
    """Execute the before-tool hook entry point reading event JSON from stdin.

    Returns:
        int: Process exit code 0 to permit execution, or 2 to block, the
        refusal printed to stderr for the agent to read.
    """
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if event.get("tool_name") != "Bash":
        return 0
    problem = reach.blocked(event.get("tool_input", {}).get("command", ""))
    if problem:
        print(problem, file=sys.stderr)
        return 2
    return 0
