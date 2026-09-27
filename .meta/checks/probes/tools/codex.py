"""OpenAI Codex hooks, runner selection, and ARC credential provisioning probes."""
import json
import pathlib
import tempfile
from typing import Any

from checks.collect import META, ROOT, check
from checks.probes.harness import environment, load_module


def _hook_problems(signed: Any, confined: Any, root: pathlib.Path) -> list[str]:
    evidence = root / "evidence"
    with environment(SOLOREPO_HOOK_EVIDENCE=str(evidence)):
        allowed = signed.decision({"tool_name": "Bash",
                                   "tool_input": {"command": "git status --porcelain"}})
        denied = signed.decision({"tool_name": "Bash",
                                  "tool_input": {"command": "gh issue close 1"}})
        patch = confined.decision({"tool_name": "apply_patch", "tool_input": {"patch": ""}})
        unknown = confined.decision({"tool_name": "mcp__anything", "tool_input": {}})
        local_read = confined.decision({"tool_name": "Bash",
                                        "tool_input": {"command": "cat .review/constraints.md"}})
        outside_read = confined.decision({"tool_name": "Bash",
                                         "tool_input": {"command": "cat /etc/passwd"}})
    problems = []
    if allowed.get("hookSpecificOutput", {}).get("permissionDecision") != "allow":
        problems.append(f"Codex signed-channel hook refused a permitted read: {allowed!r}")
    reason = denied.get("hookSpecificOutput", {}).get("permissionDecisionReason")
    if denied.get("hookSpecificOutput", {}).get("permissionDecision") != "deny" or not reason:
        problems.append(f"Codex signed-channel hook allowed a GitHub mutation: {denied!r}")
    for name, answer in (("apply_patch", patch), ("unknown tool", unknown),
                         ("outside file read", outside_read)):
        specific = answer.get("hookSpecificOutput", {})
        refused = specific.get("permissionDecision") == "deny"
        if not refused or not specific.get("permissionDecisionReason"):
            problems.append(f"Codex reviewer hook did not refuse {name}: {answer!r}")
    if local_read.get("hookSpecificOutput", {}).get("permissionDecision") != "allow":
        problems.append(f"Codex reviewer hook refused a worktree file read: {local_read!r}")
    if not evidence.is_file() or len(evidence.read_text(encoding="utf-8").splitlines()) != 6:
        problems.append("Codex hooks did not record each decision as evidence")
    return problems


def _credential_problems(deploy: Any, runner: Any, root: pathlib.Path) -> list[str]:
    auth_file = root / "auth.json"
    auth = {"auth_mode": "chatgpt", "tokens": {"access_token": "test"}}
    auth_file.write_text(json.dumps(auth), encoding="utf-8")
    auth_file.chmod(0o600)
    original_file, original_run = deploy.CODEX_AUTH_FILE, deploy.subprocess.run
    applied = []

    def capture(*_args: Any, **kwargs: Any) -> None:
        applied.append(deploy.yaml.safe_load(kwargs["input"]))

    deploy.CODEX_AUTH_FILE, deploy.subprocess.run = auth_file, capture
    try:
        credential = deploy.codex_chatgpt_auth()
        with environment():
            deploy.apply_codex_secret()
    finally:
        deploy.CODEX_AUTH_FILE, deploy.subprocess.run = original_file, original_run
    secret = applied[0] if applied else {}
    problems = []
    if credential != auth_file.read_text(encoding="utf-8"):
        problems.append("ARC did not read the local Codex ChatGPT login")
    if secret.get("metadata", {}).get("name") != "arc-codex-credentials" or \
            secret.get("stringData") != {"auth.json": credential}:
        problems.append(f"ARC applied the Codex Secret as {secret!r}")
    auth_file.write_text('{"auth_mode":"apikey","OPENAI_API_KEY":"test"}',
                         encoding="utf-8")
    if runner.chatgpt_login(auth_file):
        problems.append("Codex runner accepted a non-ChatGPT credential")
    if runner.chatgpt_login(root / "missing-auth.json"):
        problems.append("Codex runner accepted a missing credential")
    command = runner.build_command("gpt-5.3-codex", "high", "reviewer", ROOT)
    expected = ["codex", "exec", "--json", "--sandbox", "read-only", "--cd",
                str(ROOT), "--config", 'approval_policy="never"', "--model",
                "gpt-5.3-codex", "--config", 'model_reasoning_effort="high"', "-"]
    if command != expected:
        problems.append(f"Codex runner command is {command!r}, not {expected!r}")
    return problems


@check("Codex CLI probes", pre=True)
def codex_probes() -> list[str]:
    """Check Codex hook protocols, the action boundary, and local ARC credentials."""
    signed = load_module(META / "hooks" / "codex_signed_channel.py", "codex_signed", register=False)
    confined = load_module(META / "hooks" / "codex_worktree_only.py",
                           "codex_confined", register=False)
    deploy: Any = load_module(META / "arc" / "deploy", "arc_deploy_codex", register=False)
    runner = load_module(META / "run_codex.py", "run_codex", register=False)
    action = (META / "actions" / "harness" / "action.yml").read_text(encoding="utf-8")
    docker = (META / "arc" / "Dockerfile").read_text(encoding="utf-8")
    values = (META / "arc" / "values-runnerset.yaml").read_text(encoding="utf-8")
    problems = []
    workflows = "".join(path.read_text(encoding="utf-8")
                         for path in (ROOT / ".github" / "workflows").glob("*.yml"))
    for required in ("run_codex.py", "CODEX_HOME", "auth.json",
                     "codex_worktree_only.py", "codex_signed_channel.py"):
        if required not in action + values:
            problems.append(f"Codex action configuration omits {required!r}")
    if "openai-api-key" in action.lower() or "codex-api-key" in action.lower():
        problems.append("Codex harness exposes an API-key input")
    if "CODEX_FALLBACK" not in workflows:
        problems.append("Codex fallback is not wired into the loop workflows")
    if "@openai/codex@0.157.0" not in docker:
        problems.append("ARC image does not pin the Codex CLI")
    if "arc-codex-credentials" not in values or "/home/runner/.codex" not in values:
        problems.append("ARC runner does not mount the local Codex home")
    if "auth_mode\"" not in (META / "run_codex.py").read_text(encoding="utf-8"):
        problems.append("Codex runner does not require ChatGPT authentication")
    with tempfile.TemporaryDirectory() as temporary:
        root = pathlib.Path(temporary)
        problems.extend(_hook_problems(signed, confined, root))
        problems.extend(_credential_problems(deploy, runner, root))
    return problems
