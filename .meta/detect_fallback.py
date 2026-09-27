#!/usr/bin/env python3
"""Antigravity CLI confinement and settings, and the quota scan `between` reads (solorepo's DR-281).

`--configure-reviewer` and `--configure-coder` write the confinement each Role's
Antigravity session runs under; `--merge-settings` merges tool allowances and hook
registrations from `~/.gemini/settings.json` into
`~/.gemini/antigravity-cli/settings.json` while preserving mounted subscription
credentials. Whether a fallback rung runs is not decided here: the door's `between`
phase reads the chain the routing policy resolved and the toggles solorepo's DR-240,
solorepo's DR-245 and solorepo's DR-246 name, and calls `has_quota_error` for the advisory
scan of Claude Code's transcript where the next rung is the Antigravity CLI
(solorepo's DR-245).
"""

import contextlib
import json
import os
import pathlib
import re
import sys
import time
from typing import Any

_META = pathlib.Path(__file__).resolve().parent
if str(_META) not in sys.path:
    sys.path.insert(0, str(_META))
_SAY = _META / "say"
if str(_SAY) not in sys.path:
    sys.path.insert(0, str(_SAY))

import channel  # noqa: E402  # reason: sys.path resolution required for local modules
from lib.on import routing  # noqa: E402  # reason: sys.path resolution required for local modules

DEFAULT_COOLDOWN_SECONDS: int = 18000
"""Fallback quota exhaustion cooldown duration in seconds (5 hours) under solorepo's DR-294."""

DURATION_COMPONENT_PATTERN = re.compile(
    r"(?P<hours>\d+(?:\.\d+)?)\s*(?:h(?:ours?|rs?)?)(?=\b|\d|\s|$)|"
    r"(?P<minutes>\d+(?:\.\d+)?)\s*(?:m(?:in(?:ute)?s?)?)(?=\b|\d|\s|$)|"
    r"(?P<seconds>\d+(?:\.\d+)?)\s*(?:s(?:ec(?:ond)?s?)?)(?=\b|\d|\s|$)",
    re.IGNORECASE,
)
"""Components of textual duration intervals (hours, minutes, seconds)."""

RETRY_HEADER_PATTERN = re.compile(
    r"(?i)\b(?:resets?(?:\s+(?:in|after|at))?|retry(?:[-_]after|\s+after)?|try\s+again\s+in|retry\s+in)\s*[:=]?\s*([^\n,;.]+)",
)
"""Pattern detecting explicit retry or quota reset delay phrases in error output."""


def _find_delay_in_data(obj: Any) -> int | None:
    """Traverse parsed JSON structure for explicit delay or retry-after fields."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            norm = k.lower().replace("-", "").replace("_", "").replace(" ", "")
            if norm in ("retryafter", "retryafterseconds", "retryinseconds", "retryin"):
                try:
                    return int(float(v))
                except (ValueError, TypeError):
                    pass
            res = _find_delay_in_data(v)
            if res is not None:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = _find_delay_in_data(item)
            if res is not None:
                return res
    return None


def _parse_duration(text: str) -> int | None:
    """Parse retry delay duration from textual error messages."""
    match = RETRY_HEADER_PATTERN.search(text)
    if not match:
        return None
    raw_val = match.group(1).strip()
    if raw_val.isdigit():
        return int(raw_val)
    total = 0.0
    matched = False
    for m in DURATION_COMPONENT_PATTERN.finditer(raw_val):
        matched = True
        if m.group("hours"):
            total += float(m.group("hours")) * 3600
        elif m.group("minutes"):
            total += float(m.group("minutes")) * 60
        elif m.group("seconds"):
            total += float(m.group("seconds"))
    return int(total) if matched else None


def extract_retry_after(raw_text: str, data: Any = None) -> int | None:
    """Extract a retry delay in seconds from structured error data or raw text.

    Args:
        raw_text: Raw error text or transcript string to inspect with regexes.
        data: Optional parsed JSON object or decoded structure to inspect for delay keys.

    Returns:
        int | None: Parsed delay in seconds if detected, or None if no delay was found.
    """
    if data is not None:
        delay = _find_delay_in_data(data)
        if delay is not None:
            return delay

    return _parse_duration(raw_text)


def calculate_cooldown_expiration(
    execution_file: str | pathlib.Path,
    default_seconds: int = DEFAULT_COOLDOWN_SECONDS,
    now: float | None = None,
) -> int:
    """Calculate the Unix timestamp when quota cooldown expires for an execution failure.

    Reads the execution file, inspects parsed JSON entries and raw text for explicit
    retry delays using extract_retry_after, and offsets the reference timestamp.

    Args:
        execution_file: Path to the execution output file or raw text content.
        default_seconds: Cooldown duration in seconds to apply when no explicit delay is parsed.
        now: Optional reference timestamp in seconds; defaults to current Unix epoch.

    Returns:
        int: Future Unix timestamp representing the cooldown expiration boundary.
    """
    ref_time = time.time() if now is None else now
    path = pathlib.Path(execution_file)
    raw = ""
    if path.is_file():
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"Error reading {path}: {e}", file=sys.stderr)
            return int(ref_time + default_seconds)
    else:
        raw = str(execution_file)

    data: Any = None
    with contextlib.suppress(json.JSONDecodeError):
        data = json.loads(raw)

    delay = extract_retry_after(raw, data)
    duration = delay if delay is not None else default_seconds
    return int(ref_time + duration)


def record_cooldown(
    harness: str = "claude",
    execution_file: str | pathlib.Path | None = None,
    default_seconds: int = DEFAULT_COOLDOWN_SECONDS,
    now: float | None = None,
) -> int | None:
    """Persist the cooldown expiration timestamp for a harness to repository variables.

    Resolves the target GitHub repository variable from routing.COOLDOWNS, determines
    the expiration timestamp from execution_file or default duration, and writes the
    variable via channel.gh.

    Args:
        harness: Identifier of the harness experiencing quota exhaustion.
        execution_file: Optional path to the execution output file containing error details.
        default_seconds: Fallback cooldown duration in seconds if no delay is found.
        now: Optional reference timestamp in seconds.

    Returns:
        int | None: Unix timestamp of the recorded expiration, or None if the harness
            has no configured cooldown variable.
    """
    var_name = routing.COOLDOWNS.get(harness)
    if not var_name:
        return None

    if execution_file is not None:
        expiration = calculate_cooldown_expiration(
            execution_file, default_seconds=default_seconds, now=now
        )
    else:
        ref_time = time.time() if now is None else now
        expiration = int(ref_time + default_seconds)

    channel.gh("variable", "set", var_name, "--body", str(expiration), parse=False, default="")
    return expiration


def is_toggle_enabled(name: str, default: bool = False) -> bool:
    """Check whether an environment variable matches an accepted truthy allowlist.

    Args:
        name: The environment variable name holding the toggle value.
        default: Default value when the variable is unset or empty.

    Returns:
        bool: True if the stripped, lowercased value matches one of ('true', '1',
            'yes', 'on', 'enable', 'enabled'); default if unset or empty; False for
            all other values.
    """
    val = os.environ.get(name)
    if val is None or not val.strip():
        return default
    return val.strip().lower() in ("true", "1", "yes", "on", "enable", "enabled")


def has_quota_error(execution_file: str | pathlib.Path) -> bool:
    """Perform an advisory scan of Claude Code execution output for quota indicators.

    Parses the JSON execution log when valid, checking for HTTP 429 status codes,
    'rate_limit' error fields, or 'limit'/'quota'/'rate' keywords in result fields.
    If JSON parsing fails or finds no match, scans the lowercased raw text for
    substrings ('429', 'rate_limit', 'weekly limit', 'hit your').

    Args:
        execution_file: Path to the execution output file generated by Claude Code.

    Returns:
        bool: True if rate limiting, HTTP 429, or quota exhaustion indicators were
            found; False otherwise.
    """
    path = pathlib.Path(execution_file)
    if not path.is_file():
        return False

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        return False

    try:
        data = json.loads(raw)
        entries = data if isinstance(data, list) else [data]
        for item in entries:
            if isinstance(item, dict) and (
                item.get("api_error_status") == 429
                or item.get("error") == "rate_limit"
                or any(k in str(item.get("result", "")).lower() for k in ("limit", "quota", "rate"))
            ):
                return True
    except json.JSONDecodeError as e:
        print(f"Error parsing {path}: {e}", file=sys.stderr)

    lowered = raw.lower()
    return any(token in lowered for token in ("429", "rate_limit", "weekly limit", "hit your"))


def merge_settings(source_path: pathlib.Path | None = None, dest_path: pathlib.Path | None = None) -> None:
    """Merge permissions, tools, and hook settings from source JSON into Antigravity CLI configuration without overwriting credentials."""
    home = pathlib.Path.home()
    src = source_path or (home / ".gemini" / "settings.json")
    dest = dest_path or (home / ".gemini" / "antigravity-cli" / "settings.json")
    if not src.is_file():
        return
    try:
        src_data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading source settings {src}: {e}", file=sys.stderr)
        return
    try:
        dest_data = json.loads(dest.read_text(encoding="utf-8")) if dest.is_file() else {}
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading destination settings {dest}: {e}", file=sys.stderr)
        dest_data = {}
    if "permissions" in src_data:
        dest_perms = dest_data.setdefault("permissions", {})
        for kind in ("deny", "ask", "allow"):
            if kind in src_data["permissions"]:
                existing = dest_perms.setdefault(kind, [])
                for item in src_data["permissions"][kind]:
                    if item not in existing:
                        existing.append(item)
    if "tools" in src_data:
        dest_data["tools"] = src_data["tools"]
    if "hooks" in src_data:
        dest_data["hooks"] = src_data["hooks"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(dest_data, indent=2) + "\n", encoding="utf-8")


REVIEWER_DENIED_PERMISSIONS: list[str] = [
    "write_file(*)",
    "read_url(*)",
    "execute_url(*)",
    "invoke_subagent(*)",
]
"""Fine-grained permissions denied for the reviewer Role under Antigravity CLI (solorepo's DR-110, solorepo's DR-245, solorepo's DR-254)."""

REVIEWER_CORE_TOOLS: list[str] = [
    "read_file",
    "read_many_files",
    "grep_search",
    "search_file_content",
    "glob",
    "list_directory",
    "run_shell_command",
    "run_command",
    "view_file",
]
"""Core toolset admitted for the reviewer Role under Antigravity CLI (solorepo's DR-110, solorepo's DR-245, solorepo's #682)."""

REVIEWER_BEFORE_TOOL_MATCHER: str = (
    "^(run_shell_command|read_file|read_many_files|grep_search|search_file_content|glob|list_directory|run_command|view_file)$"
)
"""Pre-tool hook matcher guarding admitted reviewer tools via worktree_only.py (solorepo's #454, solorepo's #682)."""

REVIEWER_HOOK_COMMAND: str = "$GEMINI_PROJECT_DIR/.meta/hooks/worktree_only.py"
"""Command path invoking the worktree-confinement hook under Antigravity CLI (solorepo's #454, solorepo's #456, solorepo's #682)."""


SIGNED_CHANNEL_BEFORE_TOOL_MATCHER: str = "^(run_command|run_shell_command|Bash)$"
"""Pre-tool hook matcher guarding shell tool execution via signed_channel.py (solorepo's DR-260)."""

SIGNED_CHANNEL_HOOK_COMMAND: str = "$GEMINI_PROJECT_DIR/.meta/hooks/signed_channel.py"
"""Command path invoking the signed-channel hook under Antigravity CLI (solorepo's DR-260)."""


def configure_reviewer_settings(
    workspace_dir: pathlib.Path | None = None,
    settings_file: pathlib.Path | None = None,
    hooks_file: pathlib.Path | None = None,
) -> None:
    """Configure tool confinement and hook registration for the reviewer Role (solorepo's DR-110, solorepo's DR-245, solorepo's DR-260, solorepo's #682).

    Writes `permissions.deny`, `tools.core`, and `BeforeTool` hook settings directly to
    `~/.gemini/antigravity-cli/settings.json` while preserving mounted credentials, and
    registers `PreToolUse` lifecycle hooks under the `worktree-only` and `signed-channel`
    keys in `~/.gemini/config/hooks.json` while preserving any existing hook configurations.

    Args:
        workspace_dir: Optional root directory of the workspace. Defaults to GEMINI_PROJECT_DIR,
            GITHUB_WORKSPACE, or current working directory.
        settings_file: Optional path to settings JSON file. Defaults to
            ~/.gemini/antigravity-cli/settings.json.
        hooks_file: Optional path to hooks JSON file. Defaults to
            ~/.gemini/config/hooks.json.
    """
    home = pathlib.Path.home()
    dest = settings_file or (home / ".gemini" / "antigravity-cli" / "settings.json")
    hooks_dest = hooks_file or (home / ".gemini" / "config" / "hooks.json")
    if workspace_dir is None:
        env_ws = os.environ.get("GEMINI_PROJECT_DIR") or os.environ.get("GITHUB_WORKSPACE")
        workspace_dir = pathlib.Path(env_ws) if env_ws else pathlib.Path.cwd()
    hook_command = f"{workspace_dir.resolve()}/.meta/hooks/worktree_only.py"
    hook_channel_command = f"{workspace_dir.resolve()}/.meta/hooks/signed_channel.py"

    dest_data: dict[str, Any] = {}
    if dest.is_file():
        try:
            dest_data = json.loads(dest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error reading destination settings {dest}: {e}", file=sys.stderr)
            dest_data = {}

    perms = dest_data.setdefault("permissions", {})
    denied = perms.setdefault("deny", [])
    for p in REVIEWER_DENIED_PERMISSIONS:
        if p not in denied:
            denied.append(p)

    dest_data.setdefault("tools", {})["core"] = REVIEWER_CORE_TOOLS

    dest_data.setdefault("hooks", {})["BeforeTool"] = [
        {
            "matcher": REVIEWER_BEFORE_TOOL_MATCHER,
            "hooks": [
                {
                    "type": "command",
                    "name": "worktree-only",
                    "command": hook_command,
                }
            ],
        },
        {
            "matcher": SIGNED_CHANNEL_BEFORE_TOOL_MATCHER,
            "hooks": [
                {
                    "type": "command",
                    "name": "signed-channel",
                    "command": hook_channel_command,
                }
            ],
        },
    ]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(dest_data, indent=2) + "\n", encoding="utf-8")

    hooks_data: dict[str, Any] = {}
    if hooks_dest.is_file():
        try:
            hooks_data = json.loads(hooks_dest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error reading destination hooks {hooks_dest}: {e}", file=sys.stderr)
            hooks_data = {}

    hooks_data.setdefault("worktree-only", {})["PreToolUse"] = [
        {
            "matcher": REVIEWER_BEFORE_TOOL_MATCHER,
            "hooks": [
                {
                    "type": "command",
                    "name": "worktree-only",
                    "command": hook_command,
                }
            ],
        }
    ]
    hooks_data.setdefault("signed-channel", {})["PreToolUse"] = [
        {
            "matcher": SIGNED_CHANNEL_BEFORE_TOOL_MATCHER,
            "hooks": [
                {
                    "type": "command",
                    "name": "signed-channel",
                    "command": hook_channel_command,
                }
            ],
        }
    ]
    hooks_dest.parent.mkdir(parents=True, exist_ok=True)
    hooks_dest.write_text(json.dumps(hooks_data, indent=2) + "\n", encoding="utf-8")


CODER_DENIED_PERMISSIONS: list[str] = [
    "invoke_subagent(*)",
]
"""Fine-grained permissions denied for the coder Role under Antigravity CLI (solorepo's DR-257, solorepo's DR-260)."""


def configure_coder_settings(
    workspace_dir: pathlib.Path | None = None,
    settings_file: pathlib.Path | None = None,
    hooks_file: pathlib.Path | None = None,
) -> None:
    """Configure permissions denial and signed channel hook for the coder Role under Antigravity CLI (solorepo's DR-257, solorepo's DR-260).

    Denies subagent invocation (`invoke_subagent(*)`) in `~/.gemini/antigravity-cli/settings.json`
    to enforce single-session evaluation during autonomous coder fallback, and registers
    PreToolUse lifecycle hooks for `signed_channel.py` under the `signed-channel` key in
    `~/.gemini/config/hooks.json` to prevent unmediated GitHub mutation writes.

    Args:
        workspace_dir: Optional root directory of the workspace. Defaults to GEMINI_PROJECT_DIR,
            GITHUB_WORKSPACE, or current working directory.
        settings_file: Optional path to settings JSON file. Defaults to
            ~/.gemini/antigravity-cli/settings.json.
        hooks_file: Optional path to hooks JSON file. Defaults to
            ~/.gemini/config/hooks.json.
    """
    home = pathlib.Path.home()
    dest = settings_file or (home / ".gemini" / "antigravity-cli" / "settings.json")
    hooks_dest = hooks_file or (home / ".gemini" / "config" / "hooks.json")
    if workspace_dir is None:
        env_ws = os.environ.get("GEMINI_PROJECT_DIR") or os.environ.get("GITHUB_WORKSPACE")
        workspace_dir = pathlib.Path(env_ws) if env_ws else pathlib.Path.cwd()
    hook_command = f"{workspace_dir.resolve()}/.meta/hooks/signed_channel.py"

    dest_data: dict[str, Any] = {}
    if dest.is_file():
        try:
            dest_data = json.loads(dest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error reading destination settings {dest}: {e}", file=sys.stderr)
            dest_data = {}

    perms = dest_data.setdefault("permissions", {})
    denied = perms.setdefault("deny", [])
    for p in CODER_DENIED_PERMISSIONS:
        if p not in denied:
            denied.append(p)

    before_tools = dest_data.setdefault("hooks", {}).setdefault("BeforeTool", [])
    if not any(h.get("name") == "signed-channel" for entry in before_tools for h in entry.get("hooks", [])):
        before_tools.append({
            "matcher": SIGNED_CHANNEL_BEFORE_TOOL_MATCHER,
            "hooks": [
                {
                    "type": "command",
                    "name": "signed-channel",
                    "command": hook_command,
                }
            ],
        })

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(dest_data, indent=2) + "\n", encoding="utf-8")

    hooks_data: dict[str, Any] = {}
    if hooks_dest.is_file():
        try:
            hooks_data = json.loads(hooks_dest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error reading destination hooks {hooks_dest}: {e}", file=sys.stderr)
            hooks_data = {}

    hooks_data.setdefault("signed-channel", {})["PreToolUse"] = [
        {
            "matcher": SIGNED_CHANNEL_BEFORE_TOOL_MATCHER,
            "hooks": [
                {
                    "type": "command",
                    "name": "signed-channel",
                    "command": hook_command,
                }
            ],
        }
    ]
    hooks_dest.parent.mkdir(parents=True, exist_ok=True)
    hooks_dest.write_text(json.dumps(hooks_data, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    """Configure a Role's Antigravity confinement, or merge the settings (solorepo's DR-254, solorepo's DR-257).

    `--configure-reviewer` configures reviewer tool confinement in
    `~/.gemini/antigravity-cli/settings.json` and registers PreToolUse lifecycle hooks in
    `~/.gemini/config/hooks.json` (solorepo's #682, solorepo's #699); `--configure-coder`
    denies the coder subagent spawning (solorepo's DR-257); `--merge-settings` merges
    `~/.gemini/settings.json` into the Antigravity settings, keeping mounted credentials.

    Returns:
        int: 0 on each of the three flag paths, and 2 where no flag named what to do.
    """
    if "--configure-reviewer" in sys.argv:
        configure_reviewer_settings()
        return 0
    if "--configure-coder" in sys.argv:
        configure_coder_settings()
        return 0
    if "--merge-settings" in sys.argv:
        merge_settings()
        return 0
    print("detect_fallback: name --configure-reviewer, --configure-coder or --merge-settings",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
