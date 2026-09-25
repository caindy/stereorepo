"""`detect_fallback.py`'s reviewer and coder tool confinement, settings merging, and `run_agy.py` probes (solorepo's DR-245, solorepo's DR-257, solorepo's #636, solorepo's #715).
"""
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from typing import Any

from checks.collect import META, check
from checks.probes.harness import environment, load_module

BROKEN_PIPE = "Broken pipe"
"""What a standard input stood in for as broken raises on a write."""


def _probe_hooks_section(hooks_file: pathlib.Path, section: str, expected_cmd: str, matcher: str) -> list[str]:
    """Verify generated hooks.json contains expected PreToolUse configuration for a named section."""
    if not hooks_file.is_file():
        return [f"fallback probes: configure settings failed to produce a hooks.json file for {section}"]
    try:
        hooks_data = json.loads(hooks_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"fallback probes: failed to parse generated hooks JSON: {e}"]

    pre_hooks = hooks_data.get(section, {}).get("PreToolUse", [])
    if not pre_hooks:
        return [f"fallback probes: hooks.json {section}.PreToolUse is missing or empty"]

    pre_hook = pre_hooks[0]
    problems: list[str] = []
    if pre_hook.get("matcher") != matcher:
        problems.append(
            f"fallback probes: hooks.json {section} matcher {pre_hook.get('matcher')!r} != {matcher!r}"
        )
    commands = [h.get("command", "") for h in pre_hook.get("hooks", [])]
    if not any(expected_cmd in cmd for cmd in commands):
        problems.append(f"fallback probes: {section} PreToolUse hook command does not invoke {expected_cmd}")
    return problems


def _probe_reviewer_settings(detect_fallback: Any, tmp_dir: pathlib.Path) -> list[str]:
    """Verify configure_reviewer_settings creates expected permissions.deny, tools, and hooks."""
    problems: list[str] = []
    workspace = tmp_dir / "workspace"
    workspace.mkdir()
    settings_file = tmp_dir / "settings.json"
    hooks_file = tmp_dir / "hooks.json"

    detect_fallback.configure_reviewer_settings(
        workspace_dir=workspace, settings_file=settings_file, hooks_file=hooks_file
    )
    if not settings_file.is_file():
        return ["fallback probes: configure_reviewer_settings failed to produce a settings file"]

    try:
        data = json.loads(settings_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"fallback probes: failed to parse generated settings JSON: {e}"]

    denied = set(data.get("permissions", {}).get("deny", []))
    for req in detect_fallback.REVIEWER_DENIED_PERMISSIONS:
        if req not in denied:
            problems.append(f"fallback probes: configure_reviewer_settings omitted required denied permission `{req}`")

    core = data.get("tools", {}).get("core", [])
    if core != detect_fallback.REVIEWER_CORE_TOOLS:
        problems.append(f"fallback probes: tools.core {core!r} did not match REVIEWER_CORE_TOOLS")

    before_hooks = data.get("hooks", {}).get("BeforeTool", [])
    if not before_hooks:
        problems.append("fallback probes: hooks.BeforeTool is missing or empty")
    else:
        commands = [h.get("command", "") for entry in before_hooks for h in entry.get("hooks", [])]
        expected_cmd = f"{workspace}/.meta/hooks/worktree_only.py"
        expected_channel_cmd = f"{workspace}/.meta/hooks/signed_channel.py"
        if not any(expected_cmd in cmd for cmd in commands):
            problems.append(f"fallback probes: BeforeTool hook command does not invoke {expected_cmd}")
        if not any(expected_channel_cmd in cmd for cmd in commands):
            problems.append(f"fallback probes: BeforeTool hook command does not invoke {expected_channel_cmd}")

    expected_cmd = f"{workspace}/.meta/hooks/worktree_only.py"
    expected_channel_cmd = f"{workspace}/.meta/hooks/signed_channel.py"
    problems.extend(_probe_hooks_section(hooks_file, "worktree-only", expected_cmd, detect_fallback.REVIEWER_BEFORE_TOOL_MATCHER))
    problems.extend(_probe_hooks_section(hooks_file, "signed-channel", expected_channel_cmd, detect_fallback.SIGNED_CHANNEL_BEFORE_TOOL_MATCHER))

    hooks_file_env = tmp_dir / "hooks_env.json"
    settings_file_env = tmp_dir / "settings_env.json"
    with environment(GEMINI_PROJECT_DIR=str(workspace)):
        detect_fallback.configure_reviewer_settings(
            workspace_dir=None, settings_file=settings_file_env, hooks_file=hooks_file_env
        )
    problems.extend(_probe_hooks_section(hooks_file_env, "worktree-only", expected_cmd, detect_fallback.REVIEWER_BEFORE_TOOL_MATCHER))
    problems.extend(_probe_hooks_section(hooks_file_env, "signed-channel", expected_channel_cmd, detect_fallback.SIGNED_CHANNEL_BEFORE_TOOL_MATCHER))
    return problems


def _probe_coder_settings_api(detect_fallback: Any, tmp_dir: pathlib.Path) -> list[str]:
    """Verify configure_coder_settings programmatic configuration (solorepo's DR-257, solorepo's DR-260)."""
    problems: list[str] = []
    workspace = tmp_dir / "coder_workspace"
    workspace.mkdir()
    settings_file = tmp_dir / "coder_settings.json"
    hooks_file = tmp_dir / "coder_hooks.json"

    detect_fallback.configure_coder_settings(
        workspace_dir=workspace, settings_file=settings_file, hooks_file=hooks_file
    )
    if not settings_file.is_file():
        return ["fallback probes: configure_coder_settings failed to produce a settings file"]

    try:
        data = json.loads(settings_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"fallback probes: failed to parse generated coder settings JSON: {e}"]

    denied = set(data.get("permissions", {}).get("deny", []))
    for req in detect_fallback.CODER_DENIED_PERMISSIONS:
        if req not in denied:
            problems.append(f"fallback probes: configure_coder_settings omitted required denied permission `{req}`")

    before_hooks = data.get("hooks", {}).get("BeforeTool", [])
    expected_channel_cmd = f"{workspace}/.meta/hooks/signed_channel.py"
    found_channel_before = False
    for entry in before_hooks:
        if entry.get("matcher") == detect_fallback.SIGNED_CHANNEL_BEFORE_TOOL_MATCHER:
            for h in entry.get("hooks", []):
                if h.get("name") == "signed-channel" and expected_channel_cmd in h.get("command", ""):
                    found_channel_before = True
    if not found_channel_before:
        problems.append(f"fallback probes: coder settings BeforeTool hook does not invoke {expected_channel_cmd}")

    problems.extend(
        _probe_hooks_section(
            hooks_file,
            "signed-channel",
            expected_channel_cmd,
            detect_fallback.SIGNED_CHANNEL_BEFORE_TOOL_MATCHER,
        )
    )

    hooks_file_env = tmp_dir / "coder_hooks_env.json"
    settings_file_env = tmp_dir / "coder_settings_env.json"
    with environment(GEMINI_PROJECT_DIR=str(workspace)):
        detect_fallback.configure_coder_settings(
            workspace_dir=None, settings_file=settings_file_env, hooks_file=hooks_file_env
        )
    problems.extend(
        _probe_hooks_section(
            hooks_file_env,
            "signed-channel",
            expected_channel_cmd,
            detect_fallback.SIGNED_CHANNEL_BEFORE_TOOL_MATCHER,
        )
    )
    return problems


def _probe_coder_settings_cli(detect_fallback: Any, tmp_dir: pathlib.Path) -> list[str]:
    """Verify detect_fallback.py --configure-coder creates expected permissions.deny via CLI (solorepo's DR-257)."""
    problems: list[str] = []
    coder_home = tmp_dir / "coder_home"
    coder_home.mkdir()
    env = {**os.environ, "HOME": str(coder_home)}

    res = subprocess.run(
        [sys.executable, str(META / "detect_fallback.py"), "--configure-coder"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        problems.append(f"fallback probes: detect_fallback.py --configure-coder exited {res.returncode}: {res.stderr}")
    else:
        cli_settings = coder_home / ".gemini" / "antigravity-cli" / "settings.json"
        if not cli_settings.is_file():
            problems.append("fallback probes: detect_fallback.py --configure-coder failed to produce settings.json")
        else:
            try:
                cli_data = json.loads(cli_settings.read_text(encoding="utf-8"))
                cli_denied = set(cli_data.get("permissions", {}).get("deny", []))
                for req in detect_fallback.CODER_DENIED_PERMISSIONS:
                    if req not in cli_denied:
                        problems.append(f"fallback probes: configure-coder omitted required denied permission `{req}`")
            except (OSError, json.JSONDecodeError) as e:
                problems.append(f"fallback probes: failed to parse generated coder settings JSON: {e}")

    custom_settings = tmp_dir / "custom_coder_settings.json"
    custom_hooks = tmp_dir / "custom_coder_hooks.json"
    detect_fallback.configure_coder_settings(
        settings_file=custom_settings, hooks_file=custom_hooks
    )
    if not custom_settings.is_file():
        problems.append("fallback probes: configure_coder_settings failed to produce custom settings file")

    return problems


def _probe_coder_settings(detect_fallback: Any, tmp_dir: pathlib.Path) -> list[str]:
    """Verify configure_coder_settings creates expected permissions.deny, BeforeTool, and PreToolUse hooks (solorepo's DR-257, solorepo's DR-260)."""
    return _probe_coder_settings_api(detect_fallback, tmp_dir) + _probe_coder_settings_cli(detect_fallback, tmp_dir)


def _probe_merge_settings(detect_fallback: Any, tmp_dir: pathlib.Path) -> list[str]:
    """Verify merge_settings preserves credentials while safely combining permissions and tools."""
    problems: list[str] = []
    dest_file = tmp_dir / "dest_settings.json"
    dest_data = {
        "oauth": "secret_token",
        "permissions": {
            "allow": ["command(git)"],
        },
        "verbosity": "low",
    }
    dest_file.write_text(json.dumps(dest_data), encoding="utf-8")

    src_file = tmp_dir / "src_settings.json"
    src_data = {
        "permissions": {
            "deny": ["write_file(*)", "read_url(*)"],
            "allow": ["command(git)", "command(ls)"],
        },
        "tools": {
            "core": ["read_file"],
        },
    }
    src_file.write_text(json.dumps(src_data), encoding="utf-8")

    detect_fallback.merge_settings(source_path=src_file, dest_path=dest_file)
    try:
        merged = json.loads(dest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"fallback probes: failed to parse merged settings JSON: {e}"]

    if merged.get("oauth") != "secret_token":
        problems.append("fallback probes: merge_settings clobbered existing credentials")

    merged_allow = merged.get("permissions", {}).get("allow", [])
    if "command(git)" not in merged_allow or "command(ls)" not in merged_allow:
        problems.append(f"fallback probes: merge_settings failed to combine permissions.allow: got {merged_allow}")

    merged_deny = merged.get("permissions", {}).get("deny", [])
    if "write_file(*)" not in merged_deny or "read_url(*)" not in merged_deny:
        problems.append(f"fallback probes: merge_settings failed to copy permissions.deny: got {merged_deny}")

    if merged.get("tools", {}).get("core") != ["read_file"]:
        problems.append("fallback probes: merge_settings failed to copy tools.core")

    return problems


def _probe_toggle_truthiness(detect_fallback: Any) -> list[str]:
    """Verify is_toggle_enabled handles truthy and falsy strings predictably."""
    problems: list[str] = []
    env_key = "SOLOREPO_PROBE_TOGGLE_TEST"
    for truthy in ("true", "1", "yes", "on", "enable", "enabled", "  True  "):
        os.environ[env_key] = truthy
        if not detect_fallback.is_toggle_enabled(env_key, default=False):
            problems.append(f"fallback probes: is_toggle_enabled failed to recognize truthy value `{truthy}`")

    for falsy in ("false", "0", "no", "off", "disable", "disabled", "random"):
        os.environ[env_key] = falsy
        if detect_fallback.is_toggle_enabled(env_key, default=False):
            problems.append(f"fallback probes: is_toggle_enabled unexpectedly recognized falsy value `{falsy}` as true")

    if env_key in os.environ:
        del os.environ[env_key]

    return problems


class _FakeStdin:
    """Mock standard input stream for FakePopen."""

    def __init__(self, broken: bool = False) -> None:
        self.broken = broken
        self.buffer = io.StringIO()
        self.closed = False

    def write(self, s: str) -> int:
        """Write string to buffer or raise BrokenPipeError when broken."""
        if self.broken:
            raise BrokenPipeError(BROKEN_PIPE)
        return self.buffer.write(s)

    def flush(self) -> None:
        """Flush buffer."""

    def close(self) -> None:
        """Close buffer."""
        self.closed = True


class _FakeStdout:
    """Mock standard output stream that records closure."""

    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.closed = False

    def __iter__(self) -> Iterable[str]:
        """Iterate over configured output lines."""
        return iter(self.lines)

    def close(self) -> None:
        """Close buffer."""
        self.closed = True


class FakePopen:
    """Mock subprocess.Popen for testing run_agy streaming NDJSON processing (solorepo's DR-257)."""

    def __init__(self, stdout_lines: list[str], returncode: int = 0, broken_pipe: bool = False) -> None:
        self.stdin = _FakeStdin(broken=broken_pipe)
        self.stdout = _FakeStdout(stdout_lines)
        self.stderr = io.StringIO()
        self.returncode = returncode

    def wait(self, timeout: float | None = None) -> int:
        """Wait for subprocess termination and return the returncode."""
        return self.returncode

    def poll(self) -> int | None:
        """Return the exit status."""
        return self.returncode

    def terminate(self) -> None:
        """Terminate mock process."""

    def kill(self) -> None:
        """Kill mock process."""


def _probe_run_agy_builder(run_agy: Any) -> list[str]:
    """Verify run_agy's command builder and tool formatter (solorepo's DR-257)."""
    problems: list[str] = []
    cmd = run_agy.build_command(
        add_dir="/tmp/test",
        options=run_agy.SessionOptions(
            mode="accept-edits",
            model="gemini-3.8-flash",
            effort="medium",
            timeout_minutes=15,
        ),
    )
    expected_args = [
        "agy",
        "--output-format",
        "stream-json",
        "--input-format",
        "stream-json",
        "--dangerously-skip-permissions",
        "--add-dir",
        "/tmp/test",
        "--mode",
        "accept-edits",
        "--model",
        "gemini-3.8-flash",
        "--effort",
        "medium",
        "--print-timeout",
        "15m",
    ]
    if cmd != expected_args:
        problems.append(
            f"fallback probes: run_agy.build_command produced {cmd!r}, expected {expected_args!r}"
        )

    tool_cases = [
        ("run_command", {"parameters": {"CommandLine": "just gate"}}, "run_command: just gate"),
        ("view_file", {"parameters": {"AbsolutePath": "/a/b.py"}}, "view_file: /a/b.py"),
        (
            "replace_file_content",
            {"parameters": {"TargetFile": "/a/b.py"}},
            "replace_file_content: /a/b.py",
        ),
        ("unknown_tool", {}, "unknown_tool"),
    ]
    for tool_name, info, expected_str in tool_cases:
        formatted = run_agy.format_tool_call(tool_name, info)
        if formatted != expected_str:
            problems.append(
                f"fallback probes: format_tool_call({tool_name}) produced {formatted!r}, "
                f"expected {expected_str!r}"
            )
    return problems


def _probe_run_agy_retries(run_agy: Any) -> list[str]:
    """Verify run_agy's transient retry and fast-fail paths (solorepo's DR-257, solorepo's #842)."""
    problems: list[str] = []
    orig_popen = run_agy.subprocess.Popen
    try:
        err_503 = (
            "error: failed to send message: send failed; already reported to the user: "
            "Eligibility check failed: failed to get load code assist response: "
            "UNAVAILABLE (code 503): The service is currently unavailable.\n"
        )
        first_503 = FakePopen(
            [err_503, json.dumps({"event": "result", "result": {"status": "ERROR"}}) + "\n"],
            returncode=0,
        )
        second_503 = FakePopen(
            [
                json.dumps(
                    {"event": "result", "result": {"status": "SUCCESS", "response": "Done"}}
                )
                + "\n",
            ],
            returncode=0,
        )
        attempts_503 = [first_503, second_503]
        sleeps_503: list[float] = []
        run_agy.subprocess.Popen = lambda *args, **kwargs: attempts_503.pop(0)
        code = run_agy.run_session(
            prompt="Test prompt",
            add_dir="/tmp/test",
            options=run_agy.SessionOptions(max_attempts=3, initial_delay=1.0, jitter=0.0),
            sleep_fn=sleeps_503.append,
        )
        if code != 0:
            problems.append(
                f"fallback probes: run_session returned {code}, expected 0 on 503 retry"
            )
        if len(sleeps_503) != 1 or sleeps_503[0] != 1.0:
            problems.append(
                f"fallback probes: transient 503 sleep intervals {sleeps_503!r} != [1.0]"
            )
        if not all(process.stdin.closed and process.stdout.closed for process in (first_503, second_503)):
            problems.append("fallback probes: 503 recovery left a process pipe open")

        sleeps_429: list[float] = []
        run_agy.subprocess.Popen = lambda *args, **kwargs: FakePopen(
            [
                "error: RESOURCE_EXHAUSTED (code 429): Quota exceeded for rate limit\n",
                json.dumps({"event": "result", "result": {"status": "ERROR"}}) + "\n",
            ],
            returncode=0,
        )
        code = run_agy.run_session(
            prompt="Test prompt",
            add_dir="/tmp/test",
            options=run_agy.SessionOptions(
                max_attempts=3, initial_delay=2.0, backoff_factor=2.0, jitter=0.0
            ),
            sleep_fn=sleeps_429.append,
        )
        if code != 1:
            problems.append(
                f"fallback probes: run_session returned {code}, expected 1 on 429 exhaustion"
            )
        if len(sleeps_429) != 2 or sleeps_429 != [2.0, 4.0]:
            problems.append(
                f"fallback probes: transient 429 sleep intervals {sleeps_429!r} != [2.0, 4.0]"
            )

    finally:
        run_agy.subprocess.Popen = orig_popen
    problems.extend(_probe_run_agy_401(run_agy))
    problems.extend(_probe_run_agy_quota(run_agy))
    problems.extend(_probe_run_agy_429_recovery(run_agy))
    return problems


def _probe_run_agy_401(run_agy: Any) -> list[str]:
    """Verify run_agy fast-fails on fatal 401 authentication errors (solorepo's DR-257)."""
    problems: list[str] = []
    orig_popen = run_agy.subprocess.Popen
    try:
        attempt_401_count = 0
        sleeps_401: list[float] = []

        def _make_401_popen(*args: Any, **kwargs: Any) -> FakePopen:
            nonlocal attempt_401_count
            attempt_401_count += 1
            return FakePopen(
                [
                    (
                        "error: UNAUTHENTICATED (code 401): "
                        "Request had invalid authentication credentials.\n"
                    ),
                    json.dumps({"event": "result", "result": {"status": "ERROR"}}) + "\n",
                ],
                returncode=0,
            )

        run_agy.subprocess.Popen = _make_401_popen
        code = run_agy.run_session(
            prompt="Test prompt",
            add_dir="/tmp/test",
            options=run_agy.SessionOptions(max_attempts=3),
            sleep_fn=sleeps_401.append,
        )
        if code != 1:
            problems.append(
                f"fallback probes: run_session returned {code}, expected 1 on fatal 401"
            )
        if attempt_401_count != 1:
            problems.append(
                f"fallback probes: fatal 401 ran {attempt_401_count} attempts, expected 1"
            )
        if sleeps_401:
            problems.append(f"fallback probes: fatal 401 unexpectedly slept: {sleeps_401!r}")
    finally:
        run_agy.subprocess.Popen = orig_popen
    return problems


def _probe_run_agy_quota(run_agy: Any) -> list[str]:
    """Verify run_agy fast-fails on quota exhaustion and long reset delays."""
    problems: list[str] = []
    orig_popen = run_agy.subprocess.Popen
    try:
        attempt_quota_count = 0
        sleeps_quota: list[float] = []

        def _make_quota_popen(*args: Any, **kwargs: Any) -> FakePopen:
            nonlocal attempt_quota_count
            attempt_quota_count += 1
            return FakePopen(
                [
                    (
                        "error: Individual quota reached. Please upgrade your subscription "
                        "to increase your limits. Resets in 44m32s.\n"
                    ),
                    json.dumps({"event": "result", "result": {"status": "ERROR"}}) + "\n",
                ],
                returncode=3,
            )

        run_agy.subprocess.Popen = _make_quota_popen
        code = run_agy.run_session(
            prompt="Test prompt",
            add_dir="/tmp/test",
            options=run_agy.SessionOptions(max_attempts=3),
            sleep_fn=sleeps_quota.append,
        )
        if code != 3:
            problems.append(
                f"fallback probes: run_session returned {code}, expected 3 on fatal 429 quota"
            )
        if attempt_quota_count != 1:
            problems.append(
                f"fallback probes: fatal 429 quota ran {attempt_quota_count} attempts, expected 1"
            )
        if sleeps_quota:
            problems.append(
                f"fallback probes: fatal 429 quota unexpectedly slept: {sleeps_quota!r}"
            )

        attempt_reset_exceeded_count = 0
        sleeps_reset_exceeded: list[float] = []

        def _make_reset_exceeded_popen(*args: Any, **kwargs: Any) -> FakePopen:
            nonlocal attempt_reset_exceeded_count
            attempt_reset_exceeded_count += 1
            return FakePopen(
                [
                    (
                        "error: RESOURCE_EXHAUSTED (code 429): Quota exceeded for rate limit. "
                        "Resets in 15m.\n"
                    ),
                    json.dumps({"event": "result", "result": {"status": "ERROR"}}) + "\n",
                ],
                returncode=1,
            )

        run_agy.subprocess.Popen = _make_reset_exceeded_popen
        code = run_agy.run_session(
            prompt="Test prompt",
            add_dir="/tmp/test",
            options=run_agy.SessionOptions(max_attempts=3, max_delay=60.0),
            sleep_fn=sleeps_reset_exceeded.append,
        )
        if code != 1:
            problems.append(
                f"fallback probes: run_session returned {code}, expected 1 on reset exceeded 429"
            )
        if attempt_reset_exceeded_count != 1:
            problems.append(
                f"fallback probes: reset exceeded 429 ran {attempt_reset_exceeded_count} attempts, "
                "expected 1"
            )
        if sleeps_reset_exceeded:
            problems.append(
                f"fallback probes: reset exceeded 429 unexpectedly slept: {sleeps_reset_exceeded!r}"
            )
    finally:
        run_agy.subprocess.Popen = orig_popen
    return problems


def _probe_run_agy_429_recovery(run_agy: Any) -> list[str]:
    """Verify 429 failures recover in fresh sessions and close their pipes."""
    first = FakePopen(
        [
            "error: RESOURCE_EXHAUSTED (code 429): Quota exceeded for rate limit\n",
            json.dumps({"event": "result", "result": {"status": "ERROR"}}) + "\n",
        ],
        returncode=0,
    )
    second = FakePopen(
        [json.dumps({"event": "result", "result": {"status": "SUCCESS"}}) + "\n"],
        returncode=0,
    )
    attempts = [first, second]
    sleeps: list[float] = []
    original_popen = run_agy.subprocess.Popen
    try:
        run_agy.subprocess.Popen = lambda *args, **kwargs: attempts.pop(0)
        code = run_agy.run_session(
            prompt="Test prompt",
            add_dir="/tmp/test",
            options=run_agy.SessionOptions(max_attempts=3, initial_delay=1.0, jitter=0.0),
            sleep_fn=sleeps.append,
        )
    finally:
        run_agy.subprocess.Popen = original_popen
    problems: list[str] = []
    if code != 0 or attempts or sleeps != [1.0]:
        problems.append("fallback probes: 429 failure did not recover in a fresh session")
    if not all(process.stdin.closed and process.stdout.closed for process in (first, second)):
        problems.append("fallback probes: 429 recovery left a process pipe open")

    first_short_reset = FakePopen(
        [
            (
                "error: RESOURCE_EXHAUSTED (code 429): Quota exceeded for rate limit. "
                "Resets in 1s.\n"
            ),
            json.dumps({"event": "result", "result": {"status": "ERROR"}}) + "\n",
        ],
        returncode=0,
    )
    second_short_reset = FakePopen(
        [json.dumps({"event": "result", "result": {"status": "SUCCESS"}}) + "\n"],
        returncode=0,
    )
    attempts_short = [first_short_reset, second_short_reset]
    sleeps_short: list[float] = []
    try:
        run_agy.subprocess.Popen = lambda *args, **kwargs: attempts_short.pop(0)
        code = run_agy.run_session(
            prompt="Test prompt",
            add_dir="/tmp/test",
            options=run_agy.SessionOptions(max_attempts=3, initial_delay=1.0, jitter=0.0),
            sleep_fn=sleeps_short.append,
        )
    finally:
        run_agy.subprocess.Popen = original_popen
    if code != 0 or attempts_short or sleeps_short != [1.0]:
        problems.append(
            "fallback probes: 429 short reset failure did not recover in a fresh session"
        )
    if not all(
        process.stdin.closed and process.stdout.closed
        for process in (first_short_reset, second_short_reset)
    ):
        problems.append("fallback probes: 429 short reset recovery left a process pipe open")
    return problems


def _probe_run_agy(run_agy: Any) -> list[str]:
    """Verify run_agy's command builder, tool formatter, and stream runner (solorepo's DR-257)."""
    problems: list[str] = _probe_run_agy_builder(run_agy)
    orig_popen = run_agy.subprocess.Popen
    try:
        run_agy.subprocess.Popen = lambda *args, **kwargs: FakePopen(
            [
                json.dumps({"event": "init", "conversation_id": "test-123"}) + "\n",
                json.dumps(
                    {
                        "event": "step_update",
                        "step_update": {
                            "step_type": "tool",
                            "state": "ACTIVE",
                            "tool_name": "run_command",
                            "tool_info": {"parameters": {"CommandLine": "just gate"}},
                        },
                    }
                )
                + "\n",
                json.dumps(
                    {
                        "event": "step_update",
                        "step_update": {
                            "step_type": "tool",
                            "state": "DONE",
                            "tool_name": "run_command",
                            "duration_seconds": 12,
                        },
                    }
                )
                + "\n",
                json.dumps(
                    {"event": "result", "result": {"status": "SUCCESS", "response": "Done"}}
                )
                + "\n",
            ],
            returncode=0,
        )
        code = run_agy.run_session(
            prompt="Test prompt", add_dir="/tmp/test", options=run_agy.SessionOptions()
        )
        if code != 0:
            problems.append(f"fallback probes: run_session returned {code}, expected 0 on SUCCESS")

        run_agy.subprocess.Popen = lambda *args, **kwargs: FakePopen(
            [
                json.dumps({"event": "result", "result": {"status": "ERROR"}}) + "\n",
            ],
            returncode=0,
        )
        code = run_agy.run_session(
            prompt="Test prompt", add_dir="/tmp/test", options=run_agy.SessionOptions()
        )
        if code != 1:
            problems.append(f"fallback probes: run_session returned {code}, expected 1 on ERROR")

        run_agy.subprocess.Popen = lambda *args, **kwargs: FakePopen(
            [
                json.dumps({"event": "init", "conversation_id": "test-123"}) + "\n",
            ],
            returncode=0,
        )
        code = run_agy.run_session(
            prompt="Test prompt", add_dir="/tmp/test", options=run_agy.SessionOptions()
        )
        if code != 1:
            problems.append(
                f"fallback probes: run_session returned {code}, expected 1 when result is missing"
            )

        run_agy.subprocess.Popen = lambda *args, **kwargs: FakePopen([], returncode=1, broken_pipe=True)
        code = run_agy.run_session(
            prompt="Test prompt", add_dir="/tmp/test", options=run_agy.SessionOptions()
        )
        if code != 1:
            problems.append(
                f"fallback probes: run_session returned {code}, expected 1 on BrokenPipeError"
            )
    finally:
        run_agy.subprocess.Popen = orig_popen

    problems.extend(_probe_run_agy_retries(run_agy))
    return problems


@check("fallback probes", pre=True)
def fallback_probes() -> list[str]:
    """Reviewer and coder confinement, permission merging, toggle evaluation, and streaming runner (solorepo's DR-245, solorepo's DR-257, solorepo's DR-260).

    Proves that `configure_reviewer_settings()` configures `permissions.deny` with
    fine-grained denial patterns (`write_file(*)`, `read_url(*)`, `execute_url(*)`, `invoke_subagent(*)`)
    and PreToolUse hooks for worktree-only and signed-channel, that `configure_coder_settings()`
    denies `invoke_subagent(*)` and registers signed-channel PreToolUse hook directly in
    settings and hooks JSON without clobbering credentials, that `merge_settings()` safely
    merges permissions and tools, that toggle evaluation adheres to accepted truthy conventions,
    and that `run_agy.py` builds commands, formats tool updates, and handles streaming NDJSON events.
    """
    detect_fallback = load_module(META / "detect_fallback.py", "detect_fallback_module", register=False)
    run_agy = load_module(META / "run_agy.py", "run_agy_module", register=False)
    problems: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = pathlib.Path(tmp)
        problems.extend(_probe_reviewer_settings(detect_fallback, tmp_dir))
        problems.extend(_probe_coder_settings(detect_fallback, tmp_dir))
        problems.extend(_probe_merge_settings(detect_fallback, tmp_dir))

    problems.extend(_probe_toggle_truthiness(detect_fallback))
    problems.extend(_probe_run_agy(run_agy))
    return problems
