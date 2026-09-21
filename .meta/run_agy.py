#!/usr/bin/env python3
"""Execution driver for headless Antigravity CLI via streaming NDJSON (solorepo's DR-257).

Drives `agy` sessions through `--input-format stream-json --output-format stream-json`
to eliminate premature 5-second background task idle exit timeouts, streams real-time
progress to stdout, and propagates session exit codes.

History in run_agy.history.md (solorepo's DR-171).
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass
class SessionOptions:
    """Options for executing an Antigravity CLI session (solorepo's DR-257)."""

    mode: str | None = None
    model: str | None = None
    effort: str | None = None
    timeout_minutes: int | str | None = None


def build_command(
    add_dir: str | pathlib.Path,
    options: SessionOptions | None = None,
) -> list[str]:
    """Construct the command-line argument list for invoking agy in stream-json mode.

    Parameters:
        add_dir (str | pathlib.Path): Workspace root path to mount.
        options (SessionOptions | None): Execution configuration options.

    Returns:
        list[str]: Argument vector for subprocess execution.
    """
    cmd = [
        "agy",
        "--output-format",
        "stream-json",
        "--input-format",
        "stream-json",
        "--dangerously-skip-permissions",
        "--add-dir",
        str(add_dir),
    ]
    if options:
        if options.mode:
            cmd.extend(["--mode", options.mode])
        if options.model:
            cmd.extend(["--model", options.model])
        if options.effort:
            cmd.extend(["--effort", options.effort])
        if options.timeout_minutes:
            cmd.extend(["--print-timeout", f"{options.timeout_minutes}m"])
    return cmd


def format_tool_call(tool_name: str, info: dict[str, Any]) -> str:
    """Format a human-readable summary of an active tool invocation.

    Parameters:
        tool_name (str): The name of the tool being executed.
        info (dict[str, Any]): Dictionary containing tool arguments and metadata.

    Returns:
        str: Concise single-line summary of the tool call.
    """
    params = info.get("parameters") or {}
    if tool_name == "run_command":
        cmd = params.get("CommandLine", "")
        return f"run_command: {cmd}"
    if tool_name in ("view_file", "read_file"):
        path = params.get("AbsolutePath") or params.get("file_path", "")
        return f"{tool_name}: {path}"
    if tool_name in ("replace_file_content", "write_to_file"):
        target = params.get("TargetFile", "")
        return f"{tool_name}: {target}"
    if tool_name == "grep_search":
        pattern = params.get("pattern", "")
        return f"grep_search: {pattern}"
    return f"{tool_name}"


def process_step_update(step: dict[str, Any]) -> None:
    """Print formatted output for an agent or tool step update event.

    Parameters:
        step (dict[str, Any]): Dictionary containing step metadata.
    """
    step_type = step.get("step_type")
    state = step.get("state")
    if step_type == "tool" and state == "ACTIVE":
        tool_name = str(step.get("tool_name", "tool"))
        info = step.get("tool_info") or {}
        summary = format_tool_call(tool_name, info)
        print(f"[agy:tool] >> {summary}", flush=True)
    elif step_type == "tool" and state == "DONE":
        tool_name = str(step.get("tool_name", "tool"))
        dur = step.get("duration_seconds", "")
        suffix = f" in {dur}s" if dur else ""
        print(f"[agy:tool] << {tool_name} completed{suffix}", flush=True)
    elif step_type == "agent_response":
        text_delta = step.get("text_delta")
        if text_delta:
            print(text_delta, end="", flush=True)


def stream_events(stdout: Iterable[str]) -> str | None:
    """Consume and parse streaming NDJSON events from an agy subprocess stdout.

    Parameters:
        stdout (Iterable[str]): Line iterator yielding stdout lines from agy.

    Returns:
        str | None: Terminal status string from the result event, or None if omitted.
    """
    terminal_status: str | None = None
    for raw_line in stdout:
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            print(f"[agy:raw] {line}", flush=True)
            continue

        ev_name = event.get("event")
        if ev_name == "init":
            conv_id = event.get("conversation_id", "")
            print(f"[agy] Initialized session (conversation_id={conv_id})", flush=True)
        elif ev_name == "step_update":
            process_step_update(event.get("step_update") or {})
        elif ev_name == "result":
            res = event.get("result") or {}
            terminal_status = str(res.get("status", "UNKNOWN"))
            resp = res.get("response", "")
            if resp:
                print(f"\n[agy:result] {resp.strip()}", flush=True)
            print(f"[agy] Session completed with status: {terminal_status}", flush=True)
    return terminal_status


def run_session(
    prompt: str,
    add_dir: str | pathlib.Path,
    options: SessionOptions | None = None,
) -> int:
    """Execute a single-prompt Antigravity CLI session in streaming NDJSON mode.

    Passes GEMINI_PROJECT_DIR set to add_dir into the subprocess environment if
    unset, merges standard error into stdout to eliminate pipe buffer deadlocks,
    and requires an explicit terminal SUCCESS event from the agy session.

    Parameters:
        prompt (str): Full prompt instructions to deliver on stdin.
        add_dir (str | pathlib.Path): Workspace root directory.
        options (SessionOptions | None): Execution configuration options.

    Returns:
        int: Subprocess exit code (0 on SUCCESS, non-zero on error or failure).
    """
    cmd = build_command(add_dir=add_dir, options=options)
    env = dict(os.environ)
    env.setdefault("GEMINI_PROJECT_DIR", str(add_dir))

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )

    if proc.stdin is None or proc.stdout is None:
        print("error: failed to bind stdin/stdout for agy subprocess", file=sys.stderr)
        return 1

    message_payload = {"event": "user", "message": {"content": prompt}}
    try:
        proc.stdin.write(json.dumps(message_payload) + "\n")
        proc.stdin.flush()
        proc.stdin.close()
    except BrokenPipeError:
        print("error: agy exited before prompt payload was delivered", file=sys.stderr)
        proc.wait()
        return proc.returncode if proc.returncode != 0 else 1

    terminal_status = stream_events(proc.stdout)
    proc.wait()

    if proc.returncode != 0:
        return proc.returncode
    if terminal_status != "SUCCESS":
        return 1
    return 0


def main() -> int:
    """Parse CLI options and execute the Antigravity streaming session."""
    parser = argparse.ArgumentParser(
        description="Drive headless Antigravity CLI via streaming NDJSON (solorepo's DR-257)."
    )
    parser.add_argument(
        "--prompt",
        default=os.environ.get("PROMPT", ""),
        help="Prompt text (defaults to PROMPT environment variable)",
    )
    parser.add_argument(
        "--add-dir",
        default=os.environ.get("GITHUB_WORKSPACE", str(pathlib.Path.cwd())),
        help="Workspace directory to mount",
    )
    parser.add_argument(
        "--mode",
        default=os.environ.get("MODE", ""),
        help="Agent execution mode (e.g., accept-edits)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("MODEL", ""),
        help="Target model identifier",
    )
    parser.add_argument(
        "--effort",
        default=os.environ.get("EFFORT", ""),
        help="Reasoning effort level",
    )
    parser.add_argument(
        "--timeout-minutes",
        default=os.environ.get("TIMEOUT_MINUTES", ""),
        help="Print timeout in minutes",
    )
    args = parser.parse_args()

    if not args.prompt.strip():
        print("error: prompt text must be provided via --prompt or PROMPT env", file=sys.stderr)
        return 1

    options = SessionOptions(
        mode=args.mode if args.mode else None,
        model=args.model if args.model else None,
        effort=args.effort if args.effort else None,
        timeout_minutes=args.timeout_minutes if args.timeout_minutes else None,
    )
    return run_session(
        prompt=args.prompt,
        add_dir=args.add_dir,
        options=options,
    )


if __name__ == "__main__":
    sys.exit(main())
