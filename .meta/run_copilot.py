#!/usr/bin/env python3
"""Run GitHub Copilot CLI non-interactively in the repository workspace."""
import os
import pathlib
import subprocess
import sys


def build_command(prompt: str, model: str = "") -> list[str]:
    """Build the Copilot CLI command for one non-interactive coder session."""
    command = ["copilot", "-p", prompt, "--no-ask-user", "--allow-all"]
    if model:
        command.extend(["--model", model])
    return command


def main() -> int:
    """Execute the prompt and propagate Copilot CLI's exit status."""
    prompt = os.environ.get("PROMPT", "")
    if not prompt:
        print("run_copilot: PROMPT is required", file=sys.stderr)
        return 2
    return subprocess.run(build_command(prompt, os.environ.get("MODEL", "")),
                          cwd=pathlib.Path.cwd(), check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
