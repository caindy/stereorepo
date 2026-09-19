"""The hook's decision for one before-tool event, and the entry that reads the event from stdin and exits with it (solorepo's DR-110).

`blocked` composes the two boundaries: a reader is held to `paths`, a shell
command to `grammar`, and a reader naming no key of `paths.READERS` is refused
outright. The refusal text is written here, with the nearest conforming
command `grammar.plain_form` derives where there is one (solorepo's DR-175),
because the sentence the agent reads is the hook's and not either boundary's.
`main` reads the event, exits 0 to permit and 2 to block, and refuses rather
than guesses when the hook itself fails — including when the payload is one it
cannot read at all, which is the case a harness reading any other exit code as a
non-blocking error would run the tool through. It also leaves one line of
Evidence for each call it decided, where a run asked for the record: an absent
hook fails open silently, so the record of having run is what a run that names a
file for it can read back to tell a confined session from an unconfined one
(solorepo's #645).
"""
import datetime
import json
import os
import pathlib
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


def record_evidence(tool: str, permitted: bool, evidence: str | None = None) -> None:
    """Append one line of Evidence that this hook decided one call, where a run asked for the record.

    The line is `<UTC timestamp, seconds> <tool> permit|refuse`. A run that
    names the file is the reader: it reads the lines back to tell a session this
    hook decided calls for from one it never confined, and `hook_probes` reads
    each line's tool and decision back off a real subprocess. It is one short
    append to a file opened `O_APPEND`, for which POSIX sets the file offset to
    the end of the file prior to each write with no intervening file
    modification operation, so sessions and subagents deciding calls at once
    append after one another rather than over one another.

    Parameters:
        tool: The `tool_name` the before-tool event carried.
        permitted: Whether the hook permitted the call.
        evidence: The file to append to; `SOLOREPO_HOOK_EVIDENCE` names it where
            the caller passes none, read at the call rather than at import so
            that a check can direct the write or turn it off for a block.

    Returns:
        None. Writes nothing where nothing named a file, and drops a write it
        cannot make rather than raising, so a failure to record never changes
        the verdict.
    """
    named = evidence if evidence is not None else os.environ.get("SOLOREPO_HOOK_EVIDENCE")
    if not named:
        return
    try:
        when = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
        record = pathlib.Path(named)
        record.parent.mkdir(parents=True, exist_ok=True)
        with record.open("a", encoding="utf-8") as lines:
            lines.write(f"{when} {tool} {'permit' if permitted else 'refuse'}\n")
    except Exception:
        return


def main() -> int:
    """Execute the before-tool hook entry point reading event JSON from stdin.

    Returns:
        int: Process exit code 0 to permit execution, or 2 to block. A payload
        this entry point cannot read — bytes that are not JSON, JSON that is not
        an object, or a stdin that cannot be read at all — blocks, since a
        harness reads any other exit code as a non-blocking error and runs the
        tool anyway. Records the Evidence of the decision before returning it,
        naming the tool as `?` where the payload had no name to give
        (solorepo's #645).
    """
    tool = None
    try:
        event = json.load(sys.stdin)
        tool = event.get("tool_name")
        problem = blocked(tool, event.get("tool_input") or {})
    except BaseException as exc:
        problem = f"Blocked: the hook failed ({type(exc).__name__}); refusing rather than guessing."
    record_evidence(str(tool or "?"), not problem)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    return 0
