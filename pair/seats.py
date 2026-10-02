"""Seats: one long-lived harness session per role, driven turn by turn.

A seat adapter hides how a harness is held. The loop only calls `send` and
`stop`, and reads `session_id` so that a crashed or stopped seat can be
resumed. `ClaudeSeat` holds Claude Code headless: one `claude -p` process in
stream-json mode for the whole issue, one user message per turn, and the turn
ends at the first `result` event that leaves no background task outstanding.

A background task is a command, subagent or monitor that the session runs while
its turn goes on. Claude Code reports one with a `system` event of subtype
`task_started` and, once the task has finished or been stopped, one of subtype
`task_notification`, both carrying its `task_id` (read from the seats' logs on
2026-10-01; not a documented contract). A task that finishes after its turn's
`result` wakes the session, which runs a turn of its own and ends it with
another `result`. Ending the turn at the first `result` let that later turn
edit the worktree after the loop had judged and committed the turn.
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

ALLOWED = [
    "Read",
    "Glob",
    "Grep",
    "TodoWrite",
    "WebSearch",
    "WebFetch",
]
"""The tools a seat uses without a prompt.

Bash is not listed, because it runs in the sandbox. Edit, Write and
NotebookEdit are not listed either: a bare entry allows them anywhere, while
`acceptEdits` allows them only in the working directory.
"""
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
"""The git commands the loop owns, refused even inside a compound command."""

SETTLE = (
    "Your turn ends only when these background tasks have finished or been"
    " stopped:\n\n{tasks}\n\n"
    "Wait for any you still need, and stop any you do not with `TaskStop`."
)
"""The message sent, once per turn, when a turn's `result` leaves background tasks running."""


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
    refused: bool = False
    denied: list[str] = field(default_factory=list)
    """The tool calls the harness refused during the turn, one `denied` string each."""


def denied(entry: object) -> str:
    """One entry of a `result` event's `permission_denials`, as a short string.

    Claude Code lists each tool call it refused as
    `{"tool_name", "tool_use_id", "tool_input"}` (the Agent SDK's
    `SDKPermissionDenial`). A refused `Bash` call reads as its command, which
    says which shape of command the sandbox could not analyse; any other call
    reads as its tool's name. A `Bash` entry whose command is not where this
    expects reads as `Bash`, and an entry of no recognisable shape as `?`, so
    the count stays right and an odd entry never costs the turn.
    """
    if not isinstance(entry, dict):
        return "?"
    name = str(entry.get("tool_name") or "?")
    tool_input = entry.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    return command if name == "Bash" and isinstance(command, str) else name


def is_refusal(error: str | None) -> bool:
    """Whether a turn's error is the model refusing the message, not a failure.

    Claude Code reports a refusal as the `result` text of a `result` event with
    `is_error` set, in this shape (2026-10-01):

        API Error: Opus 5.5's safeguards flagged this message
        (https://www.anthropic.com/legal/aup). This sometimes happens with safe,
        normal conversations. Claude Code can't respond to this message with Opus 5.5.
        [...]
        Details: `[reasoning_extraction]`

    The refused message stays in the session's history, so resuming the
    session replays it. When the harness rewords the error, update the match
    here; nothing else in the loop reads the text.
    """
    return error is not None and "safeguards flagged this message" in error


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


GIT_DENIED = ["HEAD", "config", "hooks", "info", "index", "packed-refs", "modules"]
"""Entries of the git common directory a seat may not write, whether or not they exist yet."""

GIT_ALLOWED = {"objects", "refs", "logs", "worktrees"}
"""Entries of the git common directory a commit in a worktree writes under."""

GNUPG_DENIED = [
    "common.conf",
    "dirmngr.conf",
    "gpg-agent.conf",
    "gpg.conf",
    "gpgsm.conf",
    "keyboxd.conf",
    "scdaemon.conf",
    "sshcontrol",
    "private-keys-v1.d",
    "public-keys.d",
    "pubring.kbx",
    "trustdb.gpg",
]
"""Entries of the GnuPG home a seat may not write: its configuration and its keys."""


def versioned_gpg_conf() -> list[str]:
    """The versioned names `gpg` reads its options from before `gpg.conf`.

    For version 2.5.21, `gpg` reads `gpg.conf-2.5.21`, `gpg.conf-2.5` or
    `gpg.conf-2` in preference to `gpg.conf` (observed 2026-10-01), so denying
    `gpg.conf` alone leaves its options, among them `agent-program`, writable.
    """
    try:
        first = subprocess.run(
            ["gpg", "--version"], capture_output=True, text=True, check=True
        ).stdout.splitlines()[0]
    except (OSError, subprocess.CalledProcessError, IndexError):
        return []
    parts = first.split()[-1].split(".")
    return [f"gpg.conf-{'.'.join(parts[:n])}" for n in range(1, len(parts) + 1)]


@dataclass
class Confinement:
    """Where a seat's shell commands may write, beyond the working directory.

    `allow` and `deny` become the sandbox's `filesystem.allowWrite` and
    `filesystem.denyWrite`; a denied path wins over an allowed one that holds
    it. `sockets` become `network.allowUnixSockets`, and `env` is added to the
    seat's environment. `gitconfig` is the text of the file the seat's
    `GIT_CONFIG_GLOBAL` names; the seat's owner writes it where the seat
    cannot.
    """

    allow: list[Path]
    deny: list[Path]
    env: dict[str, str]
    sockets: list[Path] = field(default_factory=list)
    gitconfig: str = ""


SEAT_GPG = Path(__file__).resolve().parent / "seat-gpg"
"""The gpg program git runs for a seat: the real gpg with `--trust-model always`.

It is the loop's copy, in the developer's checkout, so a seat that edits its
worktree's copy does not change what it runs. Only git runs it: a `gpg` the
seat runs by name still opens the trust database and hangs.
"""


def quoted(value: str) -> str:
    """`value` as a git config value, double-quoted with `\\` and `"` escaped."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def real_gpg(cwd: Path) -> str | None:
    """The gpg that git in `cwd` runs to sign and verify, or None if there is none.

    git reads `gpg.program` and `gpg.openpgp.program` into one setting, and the
    last one read wins, so this takes the last line git lists for either. In a
    seat started by a seat, that is `SEAT_GPG` itself, and the real gpg is the
    outer seat's `PAIR_SEAT_GPG`.
    """
    listed = subprocess.run(
        ["git", "config", "--get-regexp", r"^gpg\.(openpgp\.)?program$"],
        cwd=cwd,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    program = listed[-1].split(" ", 1)[1] if listed else None
    if program and Path(program).expanduser() == SEAT_GPG:
        program = os.environ.get("PAIR_SEAT_GPG")
    return program or shutil.which("gpg")


def global_includes() -> list[Path]:
    """The global git config files git reads, in order, as absolute paths.

    That is `GIT_CONFIG_GLOBAL` alone when it is set. A relative path is made
    absolute, because git resolves an included relative path against the file
    that includes it, not the working directory.
    """
    if "GIT_CONFIG_GLOBAL" in os.environ:
        return [Path(os.environ["GIT_CONFIG_GLOBAL"]).absolute()]
    xdg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return [xdg / "git" / "config", Path.home() / ".gitconfig"]


def confinement(cwd: Path) -> Confinement:
    """The write confinement for a seat whose working directory is the worktree `cwd`.

    Claude Code's sandbox grants a worktree's git common directory on its own,
    less `hooks/` and `config`, so that `git commit` works (observed with
    Claude Code on 2026-10-01). Everything else there is code or state that
    git commands outside the sandbox act on: the loop's in this worktree, and
    the developer's in the main checkout. So `deny` names every entry of the
    common directory except the object store, the refs and reflogs of `pair/`
    branches, and this worktree's own git directory; every local branch
    outside `pair/` (read from git, so a branch held only in `packed-refs` is
    covered); and every other worktree.

    `allow` names the caches `just gate` writes to. `uv`'s tool directory is
    moved into its cache through `UV_TOOL_DIR`, so the seat cannot change a
    tool the developer installed. Of `cargo`'s home, only the downloaded
    registry and git sources are allowed, not its `bin/`.

    When the repository signs commits with GnuPG, `gpg` must reach its agent
    and `keyboxd` through their sockets and write lock files in the root of
    its home directory. That root is allowed, and every entry in it is
    denied except the sockets, so that its configuration (which can name a
    program for the agent to run) and its keys stay out of reach.

    In the sandbox, `trustdb.gpg` is read-only, and `gpg --verify` opens it
    for writing, fails, and then never exits; a `git show` or `git log` that
    shows signatures hangs with it, and killing git leaves the gpg behind
    (observed 2026-10-01). So the seat's git runs `SEAT_GPG`, which adds
    `--trust-model always`, under which gpg does not open the trust database,
    and `PAIR_SEAT_GPG` in `env` names the real gpg. The seat's git also has
    `log.showSignature` off, so a developer's `log.showSignature = true`
    does not run a verify on every `git show` and `git log`.

    Both settings are in `gitconfig`, which includes the developer's own
    global files and then overrides them; `env` points `GIT_CONFIG_GLOBAL` at
    it. A `GIT_CONFIG_COUNT` entry would outrank every file, but Claude
    Code's sandboxed Bash replaces the `GIT_CONFIG_*` entries with its own
    `safe.directory` ones (observed 2026-10-01), so the seat's shell never
    saw one. A repository's own `gpg.program` or `log.showSignature`
    outranks the global file. Signing a commit runs `SEAT_GPG` too, and does
    not consult trust.
    """

    def out(*argv: str) -> str:
        return subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()

    common = Path(out("git", "rev-parse", "--path-format=absolute", "--git-common-dir"))
    gitdir = Path(out("git", "rev-parse", "--absolute-git-dir"))
    if gitdir == common:
        raise ValueError(f"{cwd} is not a linked worktree; a seat runs in one")
    refs = common / "refs"
    deny = {common / name for name in GIT_DENIED}
    deny |= {p for p in common.iterdir() if p.name not in GIT_ALLOWED}
    deny |= {refs / "tags", refs / "remotes"}
    deny |= {p for p in refs.iterdir() if p.name != "heads"}
    branches = out("git", "for-each-ref", "--format=%(refname:lstrip=2)", "refs/heads")
    deny |= {refs / "heads" / b.split("/")[0] for b in branches.splitlines()}
    deny |= {p for p in (refs / "heads").iterdir()}
    deny.discard(refs / "heads" / "pair")
    deny |= {p for p in (common / "worktrees").iterdir() if p != gitdir}

    allow = [
        common / "objects",
        gitdir,
        refs / "heads" / "pair",
        common / "logs" / "refs" / "heads" / "pair",
    ]
    env: dict[str, str] = {}
    gitconfig = ["[include]"]
    gitconfig += [f"\tpath = {quoted(str(p))}" for p in global_includes()]
    gitconfig += ["[log]", "\tshowSignature = false"]
    gpg = real_gpg(cwd)
    if gpg:
        env["PAIR_SEAT_GPG"] = gpg
        program = f"\tprogram = {quoted(str(SEAT_GPG))}"
        gitconfig += ["[gpg]", program, '[gpg "openpgp"]', program]
    if shutil.which("uv"):
        cache = Path(out("uv", "cache", "dir"))
        allow.append(cache)
        env["UV_TOOL_DIR"] = str(cache / "seat-tools")
    cargo = Path(os.environ.get("CARGO_HOME", Path.home() / ".cargo"))
    allow += [cargo / "registry", cargo / "git"]

    sockets = []
    signs = subprocess.run(
        ["git", "config", "--bool", "commit.gpgsign"], cwd=cwd, capture_output=True, text=True
    ).stdout.strip()
    if signs == "true":
        gnupg = Path(os.environ.get("GNUPGHOME", Path.home() / ".gnupg"))
        allow.append(gnupg)
        deny |= {gnupg / name for name in GNUPG_DENIED}
        deny |= {gnupg / name for name in versioned_gpg_conf()}
        if gnupg.is_dir():
            deny |= {p for p in gnupg.iterdir() if not p.name.startswith(("S.", ".#lk"))}
            deny -= {p for p in deny if p.name.endswith(".lock")}
        sockets += [gnupg / "S.gpg-agent", gnupg / "S.keyboxd"]
    return Confinement(allow, sorted(deny), env, sockets, "\n".join(gitconfig) + "\n")


def command(
    system_prompt: str,
    confined: Confinement,
    model: str | None = None,
    resume: str | None = None,
) -> list[str]:
    """The command line that starts a Claude Code seat in stream-json mode.

    Bash runs in Claude Code's sandbox rather than under an allow-list of
    command prefixes, which cannot express a compound command built from
    allowed parts (DR-302). The sandbox lets every command run without a
    prompt, confines its writes as `confined` says, and lets it reach any
    domain, as the allow-list did. `DISALLOWED` still
    applies to each part of a compound command. Edit and Write are not in
    `ALLOWED`, so `acceptEdits` holds them to the working directory: in `-p`
    mode, the prompt a write elsewhere needs is a denial.
    """
    sandbox = {
        "enabled": True,
        "autoAllowBashIfSandboxed": True,
        "allowUnsandboxedCommands": False,
        "failIfUnavailable": True,
        "filesystem": {
            "allowWrite": [str(p) for p in confined.allow],
            "denyWrite": [str(p) for p in confined.deny],
        },
        "network": {
            "allowedDomains": ["*"],
            "allowUnixSockets": [str(p) for p in confined.sockets],
        },
    }
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
        "--settings",
        json.dumps({"sandbox": sandbox}),
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
        confined = confinement(cwd)
        argv = command(system_prompt, confined, model=model, resume=resume)
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        env.update(confined.env)
        log_dir.mkdir(parents=True, exist_ok=True)
        gitconfig = log_dir / f"{role}.gitconfig"
        gitconfig.write_text(confined.gitconfig)
        env["GIT_CONFIG_GLOBAL"] = str(gitconfig)
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
        (log_dir / f"{role}.pid").write_text(f"{self.proc.pid}\n")
        self.lines: queue.Queue[str | None] = queue.Queue()
        self.tasks: dict[str, str] = {}
        """Each background task started and not yet reported, by id, with its description."""
        self.pump = threading.Thread(target=self._pump, daemon=True)
        self.pump.start()

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

    def _write(self, text: str) -> str | None:
        """Log and send one user message; the error if the process is gone."""
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
            return f"seat process is gone: {exc}"
        return None

    def _take(self, line: str) -> dict[str, Any] | None:
        """Log one line of output and note its session and tasks; the event, if it parses."""
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return None
        self._log(event)
        session = event.get("session_id")
        if session and session != self.session_id:
            self.session_id = session
            (self.log_dir / f"{self.role}.session").write_text(f"{session}\n")
        task = event.get("task_id")
        if event.get("type") == "system" and task:
            if event.get("subtype") == "task_started":
                self.tasks[task] = str(event.get("description") or "")
            elif event.get("subtype") == "task_notification":
                self.tasks.pop(task, None)
        return event

    def _exited(self, started: float) -> TurnResult:
        err = self.proc.stderr.read() if self.proc.stderr else ""
        return TurnResult(
            False,
            error=f"seat exited mid-turn: {err.strip()[-2000:]}",
            session_id=self.session_id,
            seconds=time.monotonic() - started,
        )

    def send(self, text: str) -> TurnResult:
        """Send `text` as a turn, and wait until the session is idle.

        Output already waiting is logged and dropped first, because a
        `result` there answers no message of this turn. The turn then ends at
        a `result` that leaves no background task outstanding. The first
        `result` that leaves some outstanding is answered, once, with
        `SETTLE`, so that the seat can stop a task it no longer needs rather
        than hold the turn open until the timeout. `usage` is summed, and
        `denied` gathered, over every `result` of the turn; the rest of the
        outcome is the last `result`'s.
        """
        started = time.monotonic()
        while True:
            try:
                line = self.lines.get_nowait()
            except queue.Empty:
                break
            if line is None:
                return self._exited(started)
            self._take(line)
        gone = self._write(text)
        if gone:
            return TurnResult(False, error=gone, session_id=self.session_id)
        usage: dict[str, Any] = {}
        refusals: list[str] = []
        settling = False
        while True:
            left = self.timeout - (time.monotonic() - started)
            try:
                line = self.lines.get(timeout=max(left, 0.1))
            except queue.Empty:
                self.stop()
                running = ", ".join(self.tasks)
                return TurnResult(
                    False,
                    error=f"turn timed out after {self.timeout:.0f}s"
                    + (f"; background tasks still running: {running}" if running else ""),
                    session_id=self.session_id,
                    seconds=time.monotonic() - started,
                )
            if line is None:
                return self._exited(started)
            event = self._take(line)
            if event is None or event.get("type") != "result":
                continue
            for key, value in (event.get("usage") or {}).items():
                if isinstance(value, int | float) and not isinstance(value, bool):
                    usage[key] = usage.get(key, 0) + value
                else:
                    usage[key] = value
            refusals += [denied(entry) for entry in event.get("permission_denials") or []]
            if self.tasks:
                if not settling:
                    settling = True
                    self._write(SETTLE.format(tasks=self._outstanding()))
                continue
            error = (
                str(event.get("result") or event.get("subtype"))
                if event.get("is_error")
                else None
            )
            return TurnResult(
                ok=error is None,
                text=str(event.get("result") or ""),
                session_id=self.session_id,
                usage=usage,
                cost_usd=event.get("total_cost_usd"),
                seconds=time.monotonic() - started,
                error=error,
                refused=is_refusal(error),
                denied=refusals,
            )

    def _outstanding(self) -> str:
        """The outstanding background tasks, one Markdown list item each."""
        return "\n".join(
            f"- `{task}`: {description}" if description else f"- `{task}`"
            for task, description in self.tasks.items()
        )

    def stop(self) -> None:
        """End the process, then close its output pipes.

        A child the seat left running can hold stdout open after the seat has
        exited. Stdout is then left to the reader thread, not closed under it.
        """
        if self.proc.poll() is None:
            try:
                assert self.proc.stdin is not None
                self.proc.stdin.close()
                self.proc.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                self.proc.kill()
                self.proc.wait()
        self.pump.join(timeout=5)
        if not self.pump.is_alive() and self.proc.stdout:
            self.proc.stdout.close()
        if self.proc.stderr:
            self.proc.stderr.close()


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
    if kind == "system" and event.get("subtype") == "task_started":
        return f"[task {event.get('task_id')} started] {event.get('description', '')}"
    if kind == "system" and event.get("subtype") == "task_notification":
        return f"[task {event.get('task_id')} {event.get('status') or 'ended'}]"
    if kind == "result":
        usage = event.get("usage") or {}
        return (
            f"<<< result ({event.get('subtype')}); "
            f"cache read {usage.get('cache_read_input_tokens')}, "
            f"cache write {usage.get('cache_creation_input_tokens')}, "
            f"out {usage.get('output_tokens')}"
        )
    return ""
