"""Copilot CLI configuration, command construction, and credential materialization probes."""
import json
import pathlib
import tempfile
from typing import Any

from checks.collect import META, check
from checks.probes.harness import environment, load_module


def _hook_problems(configure: Any, adapter: Any, root: pathlib.Path) -> list[str]:
    """Verify the user hook registers the adapter and preserves gate evidence."""
    workspace = root / "workspace"
    (workspace / ".meta" / "hooks").mkdir(parents=True)
    hook = json.loads(configure.configure(workspace=workspace, home=root).read_text())
    entry = hook.get("hooks", {}).get("PreToolUse", [{}])[0]
    expected = str(workspace / ".meta" / "hooks" / "copilot_signed_channel.py")
    problems = [] if entry.get("matcher") == "Bash" and entry.get("args") == [expected] else [
        f"Copilot hook registration is {entry!r}, not the signed-channel adapter"
    ]
    evidence = root / "evidence"
    with environment(SOLOREPO_HOOK_EVIDENCE=str(evidence)):
        allowed = adapter.decision({"tool_name": "Bash",
                                    "tool_input": {"command": "git status --porcelain"}})
        denied = adapter.decision({"tool_name": "Bash",
                                   "tool_input": {"command": "gh issue close 1"}})
    if allowed != {"permissionDecision": "allow"}:
        problems.append(f"Copilot hook allowed shell input as {allowed!r}")
    if denied.get("permissionDecision") != "deny" or not denied.get("permissionDecisionReason"):
        problems.append(f"Copilot hook refused GitHub mutation as {denied!r}")
    if not evidence.is_file() or len(evidence.read_text(encoding="utf-8").splitlines()) != 2:
        problems.append("Copilot hook wrote no evidence for both decisions")
    return problems


def _command_problems(runner: Any) -> list[str]:
    """Verify the headless Copilot invocation has the selected model and no prompt pause."""
    command = runner.build_command("Repair the probe.", "gpt-5.3-codex")
    expected = ["copilot", "-p", "Repair the probe.", "--no-ask-user", "--allow-all",
                "--model", "gpt-5.3-codex"]
    return [] if command == expected else [f"Copilot command is {command!r}, not {expected!r}"]


def _secret_problems(deploy: Any, root: pathlib.Path) -> list[str]:
    """Verify ARC reads and applies the Copilot token without exposing it as an argument."""
    token_file = root / "copilot.env"
    token_file.write_text("COPILOT_GITHUB_TOKEN=from-file\n", encoding="utf-8")
    token_file.chmod(0o600)
    original_file, original_run = deploy.COPILOT_TOKEN_FILE, deploy.subprocess.run
    deploy.COPILOT_TOKEN_FILE, applied = token_file, []

    def capture_secret(*_args: Any, **kwargs: Any) -> None:
        applied.append(deploy.yaml.safe_load(kwargs["input"]))

    deploy.subprocess.run = capture_secret
    try:
        with environment(COPILOT_GITHUB_TOKEN=None):
            file_token = deploy.copilot_token()
            deploy.apply_copilot_secret()
        with environment(COPILOT_GITHUB_TOKEN="from-environment"):
            environment_token = deploy.copilot_token()
    finally:
        deploy.COPILOT_TOKEN_FILE, deploy.subprocess.run = original_file, original_run
    secret = applied[0] if applied else {}
    problems = [] if file_token == "from-file" else [
        "ARC did not read the mode-600 Copilot token file"
    ]
    if environment_token != "from-environment":
        problems.append("ARC did not prefer COPILOT_GITHUB_TOKEN")
    if secret.get("stringData") != {"COPILOT_GITHUB_TOKEN": "from-file"}:
        problems.append(f"ARC applied the Copilot Secret as {secret!r}")
    return problems


@check("Copilot CLI probes", pre=True)
def copilot_probes() -> list[str]:
    """Prove Copilot CLI's signed hook, command arguments, and ARC credential source."""
    configure = load_module(META / "configure_copilot.py", "configure_copilot", register=False)
    adapter = load_module(META / "hooks" / "copilot_signed_channel.py", "copilot_hook",
                          register=False)
    runner = load_module(META / "run_copilot.py", "run_copilot", register=False)
    deploy: Any = load_module(META / "arc" / "deploy", "arc_deploy", register=False)
    with tempfile.TemporaryDirectory() as temporary:
        root = pathlib.Path(temporary).resolve()
        return (_hook_problems(configure, adapter, root) + _command_problems(runner)
                + _secret_problems(deploy, root))
