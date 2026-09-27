#!/usr/bin/env python3
"""Run Codex CLI with the ARC-provisioned ChatGPT login."""
import json
import os
import pathlib
import subprocess
import sys


def chatgpt_login(path: pathlib.Path) -> bool:
    """Accept only Codex's file-backed ChatGPT login, never API-key auth."""
    try:
        auth = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(auth, dict) and auth.get("auth_mode") == "chatgpt" and \
        isinstance(auth.get("tokens"), dict)


def build_command(model: str, effort: str, role: str, workspace: pathlib.Path) -> list[str]:
    """Build a non-interactive Codex command with the Role's sandbox policy."""
    command = [
        "codex", "exec", "--json", "--sandbox",
        "read-only" if role == "reviewer" else "workspace-write",
        "--cd", str(workspace), "--config", 'approval_policy="never"',
    ]
    if model:
        command.extend(["--model", model])
    if effort:
        command.extend(["--config", f"model_reasoning_effort={json.dumps(effort)}"])
    command.append("-")
    return command


def main() -> int:
    """Run Codex, preserve its JSONL telemetry, and propagate its exit code."""
    prompt = os.environ.get("PROMPT", "")
    home = pathlib.Path(os.environ.get("CODEX_HOME", ""))
    role = os.environ.get("ROLE", "coder")
    if not prompt:
        print("run_codex: PROMPT is required", file=sys.stderr)
        return 2
    if role not in {"coder", "reviewer"}:
        print("run_codex: ROLE must be coder or reviewer", file=sys.stderr)
        return 2
    if not home.is_dir() or not chatgpt_login(home / "auth.json"):
        print("run_codex: CODEX_HOME must contain a ChatGPT-authenticated auth.json",
              file=sys.stderr)
        return 2

    environment = os.environ.copy()
    environment.pop("OPENAI_API_KEY", None)
    environment.pop("CODEX_API_KEY", None)
    result = subprocess.run(
        build_command(os.environ.get("MODEL", ""), os.environ.get("EFFORT", ""),
                      role, pathlib.Path.cwd()),
        input=prompt, text=True, capture_output=True, check=False, env=environment,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
