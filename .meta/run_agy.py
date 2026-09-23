#!/usr/bin/env python3
"""Execution driver for headless Antigravity CLI via streaming NDJSON (solorepo's DR-257).

Drives `agy` sessions through `--input-format stream-json --output-format stream-json`
to eliminate premature 5-second background task idle exit timeouts, streams real-time
progress to stdout, retries transient API errors with bounded backoff and jitter,
and propagates session exit codes.

History in run_agy.history.md (solorepo's DR-171).
"""

import argparse
import contextlib
import json
import os
import pathlib
import random
import re
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

FATAL_401 = "fatal_401"
TRANSIENT_503 = "transient_503"
TRANSIENT_429 = "transient_429"

FATAL_401_PATTERN = re.compile(
    r"(?:\b401\b|\bUNAUTHENTICATED\b|unauthenticated|missing or invalid credentials)",
    re.IGNORECASE,
)
TRANSIENT_503_PATTERN = re.compile(
    r"(?:\b503\b|\bUNAVAILABLE\b|service is currently unavailable|service unavailable)",
    re.IGNORECASE,
)
TRANSIENT_429_PATTERN = re.compile(
    r"(?:\b429\b|\bRESOURCE_EXHAUSTED\b|rate limit|quota burst|quota exceeded)",
    re.IGNORECASE,
)


@dataclass
class SessionOptions:
    """Options for executing an Antigravity CLI session (solorepo's DR-257)."""

    mode: str | None = None
    model: str | None = None
    effort: str | None = None
    timeout_minutes: int | str | None = None
    max_attempts: int = 3
    initial_delay: float = 2.0
    backoff_factor: float = 2.0
    max_delay: float = 60.0
    jitter: float = 1.0


@dataclass
class StreamResult:
    """Outcome of streaming events from an agy session subprocess (solorepo's DR-257)."""

    terminal_status: str | None = None
    diagnostic_lines: list[str] = field(default_factory=list)


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


def classify_error(diagnostic_lines: Iterable[str]) -> str | None:
    """Classify failure mode from diagnostic output lines.

    Parameters:
        diagnostic_lines (Iterable[str]): Unparsed lines and error payloads from session.

    Returns:
        str | None: FATAL_401, TRANSIENT_503, TRANSIENT_429, or None if unclassified.
    """
    found_transient_503 = False
    found_transient_429 = False

    for line in diagnostic_lines:
        if FATAL_401_PATTERN.search(line):
            return FATAL_401
        if TRANSIENT_503_PATTERN.search(line):
            found_transient_503 = True
        if TRANSIENT_429_PATTERN.search(line):
            found_transient_429 = True

    if found_transient_503:
        return TRANSIENT_503
    if found_transient_429:
        return TRANSIENT_429
    return None


def stream_events(stdout: Iterable[str]) -> StreamResult:
    """Consume and parse streaming NDJSON events from an agy subprocess stdout.

    Parameters:
        stdout (Iterable[str]): Line iterator yielding stdout lines from agy.

    Returns:
        StreamResult: Terminal status and collected diagnostic output lines.
    """
    terminal_status: str | None = None
    diagnostic_lines: list[str] = []
    for raw_line in stdout:
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            print(f"[agy:raw] {line}", flush=True)
            diagnostic_lines.append(line)
            continue

        ev_name = event.get("event")
        if ev_name == "init":
            conv_id = event.get("conversation_id", "")
            print(f"[agy] Initialized session (conversation_id={conv_id})", flush=True)
        elif ev_name == "step_update":
            process_step_update(event.get("step_update") or {})
        elif ev_name == "error":
            err = str(event.get("error", ""))
            if err:
                diagnostic_lines.append(err)
        elif ev_name == "result":
            res = event.get("result") or {}
            terminal_status = str(res.get("status", "UNKNOWN"))
            resp = str(res.get("response", ""))
            err = str(res.get("error", ""))
            if resp:
                print(f"\n[agy:result] {resp.strip()}", flush=True)
                if terminal_status != "SUCCESS":
                    diagnostic_lines.append(resp)
            if err:
                diagnostic_lines.append(err)
            print(f"[agy] Session completed with status: {terminal_status}", flush=True)
    return StreamResult(terminal_status=terminal_status, diagnostic_lines=diagnostic_lines)


def _cleanup_process(proc: subprocess.Popen[str]) -> None:
    """Safely reap subprocess and close open streams without leaking handles."""
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    if proc.stdin and not getattr(proc.stdin, "closed", False) and hasattr(proc.stdin, "close"):
        with contextlib.suppress(OSError):
            proc.stdin.close()
    if proc.stdout and not getattr(proc.stdout, "closed", False) and hasattr(proc.stdout, "close"):
        with contextlib.suppress(OSError):
            proc.stdout.close()


@dataclass
class _RetryContext:
    """Execution context and policies for session retries."""

    opts: SessionOptions
    sleep_fn: Callable[[float], None]
    random_fn: Callable[[float, float], float]


def _evaluate_retry(
    classification: str | None,
    attempt: int,
    ctx: _RetryContext,
    current_delay: float,
) -> tuple[bool, float]:
    """Determine whether to retry a failed session attempt with backoff."""
    if classification not in (TRANSIENT_503, TRANSIENT_429):
        return False, current_delay

    err_label = "503 UNAVAILABLE" if classification == TRANSIENT_503 else "429 RESOURCE_EXHAUSTED"
    if attempt >= ctx.opts.max_attempts:
        print(
            f"error: agy exhausted all {ctx.opts.max_attempts} attempts "
            f"due to transient error ({err_label})",
            file=sys.stderr,
            flush=True,
        )
        return False, current_delay

    jitter_val = ctx.random_fn(0, ctx.opts.jitter) if ctx.opts.jitter > 0 else 0.0
    delay = min(ctx.opts.max_delay, current_delay) + jitter_val
    print(
        f"warning: agy encountered transient error ({err_label}); "
        f"retrying in {delay:.1f}s (attempt {attempt}/{ctx.opts.max_attempts})...",
        file=sys.stderr,
        flush=True,
    )
    ctx.sleep_fn(delay)
    return True, current_delay * ctx.opts.backoff_factor


def run_session(
    prompt: str,
    add_dir: str | pathlib.Path,
    options: SessionOptions | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    random_fn: Callable[[float, float], float] = random.uniform,
) -> int:
    """Execute an Antigravity CLI session in streaming NDJSON mode with retry backoff.

    Passes GEMINI_PROJECT_DIR set to add_dir into the subprocess environment if
    unset, merges standard error into stdout to eliminate pipe buffer deadlocks,
    requires an explicit terminal SUCCESS event from the agy session, and executes
    bounded exponential backoff with jitter on transient 503 and 429 API errors
    while failing fast on fatal 401 authentication errors.

    Parameters:
        prompt (str): Full prompt instructions to deliver on stdin.
        add_dir (str | pathlib.Path): Workspace root directory.
        options (SessionOptions | None): Execution configuration options.
        sleep_fn (Callable[[float], None]): Sleep function for backoff intervals.
        random_fn (Callable[[float, float], float]): Uniform random generator for jitter.

    Returns:
        int: Subprocess exit code (0 on SUCCESS, non-zero on error or failure).
    """
    opts = options or SessionOptions()
    cmd = build_command(add_dir=add_dir, options=opts)
    env = dict(os.environ)
    env.setdefault("GEMINI_PROJECT_DIR", str(add_dir))

    max_attempts = max(1, opts.max_attempts)
    current_delay = opts.initial_delay
    retry_ctx = _RetryContext(opts=opts, sleep_fn=sleep_fn, random_fn=random_fn)
    message_payload = {"event": "user", "message": {"content": prompt}}
    payload_text = json.dumps(message_payload) + "\n"

    for attempt in range(1, max_attempts + 1):
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

        broken_pipe = False
        try:
            proc.stdin.write(payload_text)
            proc.stdin.flush()
            proc.stdin.close()
        except BrokenPipeError:
            broken_pipe = True
            print("error: agy exited before prompt payload was delivered", file=sys.stderr)

        stream_result = stream_events(proc.stdout)
        _cleanup_process(proc)

        terminal_status = stream_result.terminal_status
        if proc.returncode == 0 and terminal_status == "SUCCESS" and not broken_pipe:
            return 0

        classification = classify_error(stream_result.diagnostic_lines)
        if classification == FATAL_401:
            print(
                "[agy] Fatal authentication error (401 UNAUTHENTICATED); "
                "failing fast without retry",
                file=sys.stderr,
                flush=True,
            )
            return proc.returncode if proc.returncode != 0 else 1

        should_retry, current_delay = _evaluate_retry(
            classification=classification,
            attempt=attempt,
            ctx=retry_ctx,
            current_delay=current_delay,
        )
        if should_retry:
            continue

        return proc.returncode if proc.returncode != 0 else 1

    return 1


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
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=int(os.environ.get("MAX_ATTEMPTS") or os.environ.get("MAX_RETRIES", "3")),
        help="Maximum attempts on transient API errors (defaults to MAX_ATTEMPTS env or 3)",
    )
    parser.add_argument(
        "--initial-delay",
        type=float,
        default=float(os.environ.get("INITIAL_DELAY", "2.0")),
        help="Initial backoff delay in seconds (defaults to INITIAL_DELAY env or 2.0)",
    )
    parser.add_argument(
        "--backoff-factor",
        type=float,
        default=float(os.environ.get("BACKOFF_FACTOR", "2.0")),
        help="Multiplicative backoff factor (defaults to BACKOFF_FACTOR env or 2.0)",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=float(os.environ.get("MAX_DELAY", "60.0")),
        help="Maximum backoff delay in seconds (defaults to MAX_DELAY env or 60.0)",
    )
    parser.add_argument(
        "--jitter",
        type=float,
        default=float(os.environ.get("JITTER", "1.0")),
        help="Maximum random jitter in seconds (defaults to JITTER env or 1.0)",
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
        max_attempts=args.max_attempts,
        initial_delay=args.initial_delay,
        backoff_factor=args.backoff_factor,
        max_delay=args.max_delay,
        jitter=args.jitter,
    )
    return run_session(
        prompt=args.prompt,
        add_dir=args.add_dir,
        options=options,
    )


if __name__ == "__main__":
    sys.exit(main())
