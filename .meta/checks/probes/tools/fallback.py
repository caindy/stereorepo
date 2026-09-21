"""`detect_fallback.py`'s reviewer tool confinement and settings merging probes (solorepo's DR-245, solorepo's #636).
"""
import json
import os
import pathlib
import tempfile
from typing import Any

from checks.collect import META, check
from checks.probes.harness import load_module


def _probe_reviewer_settings(detect_fallback: Any, tmp_dir: pathlib.Path) -> list[str]:
    """Verify configure_reviewer_settings creates expected permissions.deny, tools, and hooks."""
    problems: list[str] = []
    workspace = tmp_dir / "workspace"
    workspace.mkdir()
    settings_file = tmp_dir / "settings.json"

    detect_fallback.configure_reviewer_settings(workspace_dir=workspace, settings_file=settings_file)
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
        hook = before_hooks[0]
        if hook.get("matcher") != detect_fallback.REVIEWER_BEFORE_TOOL_MATCHER:
            problems.append(
                f"fallback probes: hook matcher {hook.get('matcher')!r} != "
                f"{detect_fallback.REVIEWER_BEFORE_TOOL_MATCHER!r}"
            )
        commands = [h.get("command", "") for h in hook.get("hooks", [])]
        expected_cmd = f"{workspace}/.meta/hooks/worktree_only.py"
        if not any(expected_cmd in cmd for cmd in commands):
            problems.append(f"fallback probes: BeforeTool hook command does not invoke {expected_cmd}")

    return problems


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


@check("fallback probes", pre=True)
def fallback_probes() -> list[str]:
    """Reviewer confinement configuration, permission merging, and fallback toggle evaluation in `detect_fallback.py` (solorepo's DR-245, solorepo's #636).

    Proves that `configure_reviewer_settings()` configures `permissions.deny` with
    fine-grained denial patterns (`write_file(*)`, `read_url(*)`, `execute_url(*)`)
    directly in the settings JSON without clobbering credentials, that `merge_settings()`
    safely merges permissions and tools, and that toggle evaluation adheres to accepted
    truthy conventions.
    """
    detect_fallback = load_module(META / "detect_fallback.py", "detect_fallback_module", register=False)
    problems: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = pathlib.Path(tmp)
        problems.extend(_probe_reviewer_settings(detect_fallback, tmp_dir))
        problems.extend(_probe_merge_settings(detect_fallback, tmp_dir))

    problems.extend(_probe_toggle_truthiness(detect_fallback))
    return problems
