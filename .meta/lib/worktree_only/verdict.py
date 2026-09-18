"""The hook's decision for one before-tool event, and the entry that reads the event from stdin and exits with it (solorepo's DR-110).

`blocked` composes the two boundaries: a reader is held to `paths`, a shell
command to `grammar`, and a reader naming no key of `paths.READERS` is refused
outright. The refusal text is written here, with the nearest conforming
command `grammar.plain_form` derives where there is one (solorepo's DR-175),
because the sentence the agent reads is the hook's and not either boundary's.
`main` reads the event, exits 0 to permit and 2 to block, and refuses rather
than guesses when the hook itself fails.
"""
import json
import sys
from typing import Any

from lib.worktree_only import grammar, paths


def blocked(tool: str, tool_input: dict[str, Any]) -> str | None:
    """Determine whether a tool invocation violates filesystem or confinement boundaries.

    Parameters:
        tool: Tool identifier, canonical ('Read', 'Grep', 'Glob', 'Bash') or a
            harness name `paths.TOOLS` maps onto one.
        tool_input: Input arguments passed to the tool call.

    Returns:
        str | None: Refusal message detailing the policy violation if blocked; None if permitted.
    """
    try:
        tool = paths.TOOLS.get(tool, tool)
        if tool in paths.READERS:
            named = paths.targets(tool_input, paths.READERS[tool])
            if not named and tool not in paths.SEARCHES:
                keys = ", ".join(f"`{key}`" for key in paths.READERS[tool])
                return (f"Blocked: this call names no path under {keys}. The reviewer reads the "
                        "worktree and nothing else, and an argument this hook cannot bound is "
                        "refused rather than taken for the worktree.")
            for value, kind in named:
                problem = paths.outside(value) if kind == paths.PATH else paths.outside_pattern(value)
                if problem:
                    return f"Blocked: {problem}. The reviewer reads the worktree and nothing else."
            return None
        if tool == "Bash":
            where = tool_input.get("dir_path")
            problem = paths.elsewhere(where) if where else None
            if problem:
                return f"Blocked: {problem}. The reviewer runs its commands in the worktree and nowhere else."
            command = tool_input.get("command", "")
            problem = grammar.command_allowed(command)
            if problem:
                plain = grammar.plain_form(command)
                return (f"Blocked: {problem}. The reviewer runs one plain command at a time: "
                        "`git log|show|diff|status|grep|ls-files|ls-tree` with plain options, "
                        "`gh pr view|diff|checks`, "
                        "`python3 .meta/check_pr.py`, or a program of `.meta/say/` with a quoted heredoc. "
                        "No pipes, redirects, chaining, or anything the shell would expand — "
                        "quoting is what stops it, and the four a double quote does not stop "
                        "here are `$`, a backtick, `\\` and `!`: a pattern holding one of them "
                        "goes in single quotes, which is most regexes — `'\\bdef\\b'`."
                        + (f" This one would be taken as: {plain}" if plain else ""))
        return None
    except Exception as exc:
        return f"Blocked: the hook could not read this call ({type(exc).__name__}: {exc}); refusing rather than guessing."


def main() -> int:
    """Execute the before-tool hook entry point reading event JSON from stdin.

    Returns:
        int: Process exit code 0 to permit execution, or 2 to block.
    """
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    try:
        problem = blocked(event.get("tool_name"), event.get("tool_input") or {})
    except BaseException as exc:
        problem = f"Blocked: the hook failed ({type(exc).__name__}); refusing rather than guessing."
    if problem:
        print(problem, file=sys.stderr)
        return 2
    return 0
