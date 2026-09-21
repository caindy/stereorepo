"""`detect_fallback.py`'s reviewer and coder tool confinement, settings merging, and `run_agy.py` probes (solorepo's DR-245, solorepo's DR-257, solorepo's #636, solorepo's #715).
"""
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

from checks.collect import META, check
from checks.probes.harness import environment, load_module


def _probe_hooks_section(hooks_file: pathlib.Path, section: str, expected_cmd: str, matcher: str) -> list[str]:
    """Verify generated hooks.json contains expected PreToolUse configuration for a named section."""
    if not hooks_file.is_file():
        return [f"fallback probes: configure settings failed to produce a hooks.json file for {section}"]
    try:
        hooks_data = json.loads(hooks_file.read_text(encoding="utf-8"))
    except Exception as e:
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
    except Exception as e:
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
    except Exception as e:
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
            except Exception as e:
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
    except Exception as e:
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

    def write(self, s: str) -> int:
        """Write string to buffer or raise BrokenPipeError when broken."""
        if self.broken:
            raise BrokenPipeError("Broken pipe")
        return self.buffer.write(s)

    def flush(self) -> None:
        """Flush buffer."""

    def close(self) -> None:
        """Close buffer."""


class FakePopen:
    """Mock subprocess.Popen for testing run_agy streaming NDJSON processing (solorepo's DR-257)."""

    def __init__(self, stdout_lines: list[str], returncode: int = 0, broken_pipe: bool = False) -> None:
        self.stdin = _FakeStdin(broken=broken_pipe)
        self.stdout = stdout_lines
        self.stderr = io.StringIO()
        self.returncode = returncode

    def wait(self) -> int:
        """Wait for subprocess termination and return the returncode."""
        return self.returncode


def _probe_run_agy(run_agy: Any) -> list[str]:
    """Verify run_agy's command builder, tool formatter, and stream runner (solorepo's DR-257)."""
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
        problems.append(f"fallback probes: run_agy.build_command produced {cmd!r}, expected {expected_args!r}")

    tool_cases = [
        ("run_command", {"parameters": {"CommandLine": "just gate"}}, "run_command: just gate"),
        ("view_file", {"parameters": {"AbsolutePath": "/a/b.py"}}, "view_file: /a/b.py"),
        ("replace_file_content", {"parameters": {"TargetFile": "/a/b.py"}}, "replace_file_content: /a/b.py"),
        ("unknown_tool", {}, "unknown_tool"),
    ]
    for tool_name, info, expected_str in tool_cases:
        formatted = run_agy.format_tool_call(tool_name, info)
        if formatted != expected_str:
            problems.append(f"fallback probes: format_tool_call({tool_name}) produced {formatted!r}, expected {expected_str!r}")

    orig_popen = run_agy.subprocess.Popen
    try:
        run_agy.subprocess.Popen = lambda *args, **kwargs: FakePopen(
            [
                json.dumps({"event": "init", "conversation_id": "test-123"}) + "\n",
                json.dumps({"event": "step_update", "step_update": {"step_type": "tool", "state": "ACTIVE", "tool_name": "run_command", "tool_info": {"parameters": {"CommandLine": "just gate"}}}}) + "\n",
                json.dumps({"event": "step_update", "step_update": {"step_type": "tool", "state": "DONE", "tool_name": "run_command", "duration_seconds": 12}}) + "\n",
                json.dumps({"event": "result", "result": {"status": "SUCCESS", "response": "Done"}}) + "\n",
            ],
            returncode=0,
        )
        code = run_agy.run_session(prompt="Test prompt", add_dir="/tmp/test", options=run_agy.SessionOptions())
        if code != 0:
            problems.append(f"fallback probes: run_session returned {code}, expected 0 on SUCCESS")

        run_agy.subprocess.Popen = lambda *args, **kwargs: FakePopen(
            [
                json.dumps({"event": "result", "result": {"status": "ERROR"}}) + "\n",
            ],
            returncode=0,
        )
        code = run_agy.run_session(prompt="Test prompt", add_dir="/tmp/test", options=run_agy.SessionOptions())
        if code != 1:
            problems.append(f"fallback probes: run_session returned {code}, expected 1 on ERROR")

        run_agy.subprocess.Popen = lambda *args, **kwargs: FakePopen(
            [
                json.dumps({"event": "init", "conversation_id": "test-123"}) + "\n",
            ],
            returncode=0,
        )
        code = run_agy.run_session(prompt="Test prompt", add_dir="/tmp/test", options=run_agy.SessionOptions())
        if code != 1:
            problems.append(f"fallback probes: run_session returned {code}, expected 1 when result event is missing")

        run_agy.subprocess.Popen = lambda *args, **kwargs: FakePopen([], returncode=1, broken_pipe=True)
        code = run_agy.run_session(prompt="Test prompt", add_dir="/tmp/test", options=run_agy.SessionOptions())
        if code != 1:
            problems.append(f"fallback probes: run_session returned {code}, expected 1 on BrokenPipeError")
    finally:
        run_agy.subprocess.Popen = orig_popen

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
