"""The hook's decision for one before-tool event, and the entry that reads the event from stdin and exits with it (solorepo's DR-110).

`blocked` composes the two boundaries: a reader is held to `paths`, a shell
command to `grammar`, and a reader naming no key of `paths.READERS` is refused
outright. The refusal text is written here, with the nearest conforming
command `grammar.plain_form` derives where there is one (solorepo's DR-175),
because the sentence the agent reads is the hook's and not either boundary's.
`main` reads the event across two protocol regimes: Claude Code and Gemini CLI
signal decisions via exit codes (0 to permit, 2 to block with refusal on
stderr), while Antigravity CLI expects a structured JSON decision object
`{"decision": "allow"}` or `{"decision": "deny", "reason": "..."}` on stdout
with exit code 0 (solorepo's #682). `main` refuses rather than guesses when the
hook itself fails: an Antigravity payload or unreadable stream emits a deny
decision on stdout, and legacy exit code 2 is preserved with stderr diagnostics,
ensuring no harness fails open. It also leaves one line of Evidence for each
call it decided, where a run asked for the record: an absent hook fails open
silently, so the record of having run is what a run that names a file for it can
read back to tell a confined session from an unconfined one (solorepo's #645).
"""
import datetime
import json
import os
import pathlib
import sys
from typing import Any

from lib.worktree_only import grammar, paths

NOT_AN_OBJECT = "expected JSON object, got {got}"
"""What reading the event raises where the harness sent valid JSON that is not an object."""


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
            if tool in paths.SEARCHES:
                admitted = set(paths.READERS[tool]) | paths.NON_PATH_SEARCH_KEYS
                unknown_keys = set(tool_input.keys()) - admitted
                if unknown_keys:
                    keys = ", ".join(f"`{k}`" for k in sorted(unknown_keys))
                    return (f"Blocked: this call names unrecognized search argument {keys}. "
                            "The reviewer reads the worktree and nothing else.")
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
            where = tool_input.get("dir_path") or tool_input.get("Cwd")
            problem = paths.elsewhere(where) if where else None
            if problem:
                return f"Blocked: {problem}. The reviewer runs its commands in the worktree and nowhere else."
            command = tool_input.get("command") or tool_input.get("CommandLine") or ""
            problem = grammar.command_allowed(command)
            if problem:
                plain = grammar.plain_form(command)
                return (f"Blocked: {problem}. The reviewer runs one plain command at a time: "
                        "`git log|show|diff|status|grep|ls-files|ls-tree` with plain options, "
                        "`gh pr view|diff|checks`, "
                        "`just pr`, `python3 .meta/check_pr.py`, or a program of `.meta/say/` "
                        "with a quoted heredoc. "
                        "No pipes, redirects, chaining, or anything the shell would expand — "
                        "quoting is what stops it, and the four a double quote does not stop "
                        "here are `$`, a backtick, `\\` and `!`: a pattern holding one of them "
                        "goes in single quotes, which is most regexes — `'\\bdef\\b'`."
                        + (f" This one would be taken as: {plain}" if plain else ""))
        return None
    except BaseException as exc:  # noqa: BLE001  # reason: a hook that dies admits the call, so anything raised here — a recursion limit or an interrupt included — becomes a refusal
        return f"Blocked: hook evaluation failed ({type(exc).__name__}: {exc}); refusing rather than guessing."


def record_evidence(tool: str, permitted: bool, evidence: str | pathlib.Path | None = None) -> None:
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
        path = pathlib.Path(named)
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
        verdict = "permit" if permitted else "refuse"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {tool} {verdict}\n")
    except OSError:
        return


def main() -> int:
    """Execute the before-tool hook entry point reading event JSON from stdin.

    Returns:
        int: Process exit code 0 to permit execution under all harnesses. Under
        Claude Code and Gemini CLI, exits 2 to block with an explanatory refusal
        on stderr. Under Antigravity CLI, exits 0 to block with a JSON decision
        `{"decision": "deny", "reason": "..."}` on stdout (solorepo's #682).
        A payload that cannot be parsed as JSON or read from stdin is blocked across
        all harnesses: if an Antigravity envelope is identified, outputs a JSON
        refusal on stdout with exit 0; otherwise, outputs both a JSON refusal on
        stdout and an explanatory diagnostic on stderr with exit 2, ensuring no
        harness fails open. Records the Evidence of the decision before returning,
        naming the tool as `?` where the payload had no name to give (solorepo's #645).
    """
    tool: str = ""
    is_antigravity = False
    raw = ""
    try:
        raw = sys.stdin.read()
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise TypeError(NOT_AN_OBJECT.format(got=type(event).__name__))
        if "toolCall" in event:
            is_antigravity = True
            tool_call = event.get("toolCall") or {}
            tool = tool_call.get("name") or ""
            tool_input = tool_call.get("args") or {}
        else:
            tool = event.get("tool_name") or ""
            tool_input = event.get("tool_input") or {}
        problem = blocked(tool, tool_input)
    except BaseException as exc:  # noqa: BLE001  # reason: a hook that dies admits the call, so anything raised while reading the event — a recursion limit or an interrupt included — becomes a refusal
        if "toolCall" in raw:
            is_antigravity = True
        problem = f"Blocked: the hook failed ({type(exc).__name__}); refusing rather than guessing."
    record_evidence(tool or "?", not problem)
    if is_antigravity:
        decision = {"decision": "deny", "reason": problem} if problem else {"decision": "allow"}
        print(json.dumps(decision))
        return 0
    if problem:
        print(json.dumps({"decision": "deny", "reason": problem}))
        print(problem, file=sys.stderr)
        return 2
    return 0
