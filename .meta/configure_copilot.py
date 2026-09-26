#!/usr/bin/env python3
"""Install the Copilot CLI hook that sends shell writes through the signed channel."""
import json
import pathlib
import sys


def configure(
    workspace: pathlib.Path | None = None,
    home: pathlib.Path | None = None,
) -> pathlib.Path:
    """Write the user-level Copilot CLI PreToolUse hook for `workspace`."""
    root = (workspace or pathlib.Path.cwd()).resolve()
    hooks = (home or pathlib.Path.home()) / ".copilot" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    hooks.chmod(0o700)
    destination = hooks / "solorepo-signed-channel.json"
    payload = {
        "version": 1,
        "hooks": {
            "PreToolUse": [{
                "type": "command",
                "exec": sys.executable,
                "args": [str(root / ".meta" / "hooks" / "copilot_signed_channel.py")],
                "matcher": "Bash",
                "timeoutSec": 10,
            }],
        },
    }
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    destination.chmod(0o600)
    return destination


if __name__ == "__main__":
    configure()
