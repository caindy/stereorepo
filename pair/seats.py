"""Seats: one long-lived harness session per role, driven turn by turn.

A seat adapter hides how a harness is held. The loop only calls `send` and
`stop`, and reads `session_id` so that a crashed or stopped seat can be
resumed. `ClaudeSeat` holds Claude Code headless: one `claude -p` process in
stream-json mode for the whole issue, one user message per turn, and the turn
ends at the `result` event.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

ALLOWED = [
    "Read",
    "Edit",
    "Write",
    "Glob",
    "Grep",
    "NotebookEdit",
    "TodoWrite",
    "WebSearch",
    "WebFetch",
    "Bash(just *)",
    "Bash(uv *)",
    "Bash(uvx *)",
    "Bash(cargo *)",
    "Bash(python3 *)",
    "Bash(python *)",
    "Bash(.venv/bin/*)",
    "Bash(ruff *)",
    "Bash(grep *)",
    "Bash(rg *)",
    "Bash(ls *)",
    "Bash(cat *)",
    "Bash(head *)",
    "Bash(tail *)",
    "Bash(wc *)",
    "Bash(find *)",
    "Bash(sed -n *)",
    "Bash(cd *)",
    "Bash(git status*)",
    "Bash(git diff*)",
    "Bash(git log*)",
    "Bash(git show*)",
    "Bash(git add *)",
    "Bash(git commit *)",
    "Bash(git restore *)",
    "Bash(git stash list*)",
    "Bash(git grep *)",
    "Bash(git blame *)",
    "Bash(git ls-files*)",
    "Bash(git ls-tree*)",
]
DISALLOWED = [
    "Bash(git push*)",
    "Bash(git merge*)",
    "Bash(git rebase*)",
    "Bash(git switch*)",
    "Bash(git checkout*)",
    "Bash(git reset*)",
    "Bash(git branch*)",
    "Bash(git worktree*)",
    "Bash(git mv *)",
    "Bash(git stash*)",
]


@dataclass
class TurnResult:
    """What a seat reports when its turn ends."""

    ok: bool
    text: str = ""
    session_id: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    cost_usd: float | None = None
    seconds: float = 0.0
    error: str | None = None


class Seat(Protocol):
    """The interface the loop drives. Any harness adapter implements it."""

    role: str
    session_id: str | None

    def send(self, text: str) -> TurnResult: ...

    def stop(self) -> None: ...


CONTEXT = ["--setting-sources", "project", "--strict-mcp-config"]
"""What a seat loads beyond the loop's own prompt: the project's settings alone.

The project source gives the seat the repository's `CLAUDE.md`, its skills under
`.claude/skills/` and its `.claude/settings.json`. Leaving out the user and
local sources keeps the developer's own plugins and settings out of the seat, so
its context is the repository's and a fresh session re-uses more of the cached
prefix: in stereorepo, about 7,300 tokens are written per fresh session against
about 12,000 with every source loaded. `--setting-sources ""` writes less still,
but it drops the project's skills too.
"""


def command(system_prompt: str, model: str | None = None, resume: str | None = None) -> list[str]:
    """The command line that starts a Claude Code seat in stream-json mode."""
    argv = [
        "claude",
        "-p",
        "--input-format",
        "stream-json",
        "--output-format",
        "stream-json",
        "--verbose",
        "--permission-mode",
        "acceptEdits",
        *CONTEXT,
        "--append-system-prompt",
        system_prompt,
        "--allowedTools",
        *ALLOWED,
        "--disallowedTools",
        *DISALLOWED,
    ]
    if model:
        argv += ["--model", model]
    if resume:
        argv += ["--resume", resume]
    return argv


class ClaudeSeat:
    """Claude Code, held as one headless stream-json process per issue.

    The process runs in its own session, so a Ctrl-C aimed at the loop does not
    kill the seat mid-turn. Its pid is written to `<role>.pid` in the log
    directory, so the developer or a test can find the process, and its session id
    to `<role>.session` as soon as it is known, so a restart can resume a seat
    that died before its first turn ended.
    """

    def __init__(
        self,
        role: str,
        cwd: Path,
        system_prompt: str,
        log_dir: Path,
        resume: str | None = None,
        timeout: float = 45 * 60,
        model: str | None = None,
    ) -> None:
        self.role = role
        self.session_id = resume
        self.timeout = timeout
        self.log_dir = log_dir
        argv = command(system_prompt, model=model, resume=resume)
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        self.proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            text=True,
            bufsize=1,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"{role}.pid").write_text(f"{self.proc.pid}\n")
        self.lines: queue.Queue[str | None] = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def _log(self, event: dict[str, Any]) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        with (self.log_dir / f"{self.role}.jsonl").open("a") as raw:
            raw.write(json.dumps(event) + "\n")
        readable = _readable(event)
        if readable:
            with (self.log_dir / f"{self.role}.log").open("a") as log:
                log.write(readable + "\n")

    def send(self, text: str) -> TurnResult:
        started = time.monotonic()
        message = {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "text", "text": text}]},
        }
        self._log({"type": "pair/sent", "text": text})
        try:
            assert self.proc.stdin is not None
            self.proc.stdin.write(json.dumps(message) + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            return TurnResult(
                False, error=f"seat process is gone: {exc}", session_id=self.session_id
            )
        while True:
            left = self.timeout - (time.monotonic() - started)
            try:
                line = self.lines.get(timeout=max(left, 0.1))
            except queue.Empty:
                self.stop()
                return TurnResult(
                    False,
                    error=f"turn timed out after {self.timeout:.0f}s",
                    session_id=self.session_id,
                    seconds=time.monotonic() - started,
                )
            if line is None:
                err = self.proc.stderr.read() if self.proc.stderr else ""
                return TurnResult(
                    False,
                    error=f"seat exited mid-turn: {err.strip()[-2000:]}",
                    session_id=self.session_id,
                    seconds=time.monotonic() - started,
                )
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._log(event)
            session = event.get("session_id")
            if session and session != self.session_id:
                self.session_id = session
                (self.log_dir / f"{self.role}.session").write_text(f"{session}\n")
            if event.get("type") == "result":
                return TurnResult(
                    ok=not event.get("is_error", False),
                    text=str(event.get("result") or ""),
                    session_id=self.session_id,
                    usage=event.get("usage") or {},
                    cost_usd=event.get("total_cost_usd"),
                    seconds=time.monotonic() - started,
                    error=None
                    if not event.get("is_error")
                    else str(event.get("result") or event.get("subtype")),
                )

    def stop(self) -> None:
        if self.proc.poll() is None:
            try:
                assert self.proc.stdin is not None
                self.proc.stdin.close()
                self.proc.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                self.proc.kill()


def _readable(event: dict[str, Any]) -> str:
    """One line a person tailing the log can follow, or '' for noise."""
    kind = event.get("type")
    if kind == "pair/sent":
        return f"\n>>> turn message\n{event['text']}\n"
    if kind == "assistant":
        parts = []
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "text" and block.get("text", "").strip():
                parts.append(block["text"].strip())
            elif block.get("type") == "tool_use":
                arg = block.get("input", {})
                hint = (
                    arg.get("command")
                    or arg.get("file_path")
                    or arg.get("pattern")
                    or ""
                )
                parts.append(f"[{block.get('name')}] {str(hint)[:200]}")
        return "\n".join(parts)
    if kind == "result":
        usage = event.get("usage") or {}
        return (
            f"<<< turn ended ({event.get('subtype')}); "
            f"cache read {usage.get('cache_read_input_tokens')}, "
            f"cache write {usage.get('cache_creation_input_tokens')}, "
            f"out {usage.get('output_tokens')}"
        )
    return ""
