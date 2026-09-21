"""The one registered step: the tables run against the hooks loaded from `.meta/hooks/`, and a failure that names the row.
"""
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from checks.collect import META, ROOT, check
from checks.probes.git import events, offers, registration, verdicts
from checks.probes.harness import environment, load_hook, outcome, stood_in

REVIEW_WORKFLOW = ROOT / ".github" / "workflows" / "review.yml"
EVIDENCE_LINE = re.compile(
    r"^(?P<when>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00) (?P<tool>\S+) (?P<decided>permit|refuse)$")
"""One line of the hook's Evidence, as `verdict.record_evidence` writes it and as a run that names the file reads it back: an ISO-8601 UTC instant to the second, the tool, and the decision.

Each of the three fields is matched rather than skipped, so the pattern holds
the whole of the format the hook publishes in its own Input/Output Contract: an
instant at another precision or in another zone, or a decision recorded against
a tool the payload did not name, is not a line (solorepo's #645).
"""


def _decision(line: str) -> tuple[str, str] | None:
    """The tool one line of the hook's Evidence names and the decision it records, or `None` where the line is not one."""
    match = EVIDENCE_LINE.match(line)
    return (match.group("tool"), match.group("decided")) if match else None


def _verdicts(hooks: dict[str, Any]) -> list[str]:
    """The rows of `VERDICTS` a hook did not answer as owed, each line naming the group, the hook and the call."""
    problems = []
    for group, name, rows in verdicts.VERDICTS:
        for want, *arguments in rows:
            answer = hooks[name].blocked(*arguments)
            held = bool(answer) if want == "refuse" else not answer
            if not held:
                shown = ", ".join(repr(argument) for argument in arguments)
                problems.append(f"{group}: {name} should {want} {shown} and did not")
    return problems


def _offers(worktree: Any) -> list[str]:
    """The rows of `OFFERS` whose refusal offered other than the row says, or offered a command the hook itself refuses."""
    problems = []
    for group, rows in offers.OFFERS:
        for command, want in rows:
            got = worktree.plain_form(command)
            if got != want:
                problems.append(f"{group}: the refusal for {command!r} should offer {want!r} and offered {got!r}")
            elif got is not None and worktree.command_allowed(got):
                problems.append(f"{group}: the refusal for {command!r} offers {got!r}, which the hook itself refuses")
    return problems


def _events(worktree: Any) -> list[str]:
    """The rows of `EVENTS` whose payload the hook's entry point did not exit as the row says.

    `main()` returns the code rather than exiting with it, so the call is wrapped
    in the `sys.exit` the program's last line performs, which is what `outcome`
    reads. It is run with no file named for the hook's Evidence: these rows run
    in this process, so a row left to inherit `SOLOREPO_HOOK_EVIDENCE` would
    append to whatever file that names — in a job that sets it for the whole
    run, the very file read back to tell that a session was confined
    (solorepo's #645). A payload that is not an object has no fields to name, so
    the line says what was sent instead. Under Antigravity CLI, the exit code is 0
    and the decision object on stdout (`res.out`) says whether the call was
    allowed or denied, with a non-empty reason on refusal (solorepo's #682).
    """
    problems = []
    for group, rows in events.EVENTS:
        for want, event in rows:
            with environment(SOLOREPO_HOOK_EVIDENCE=None), \
                    stood_in(sys, stdin=io.StringIO(json.dumps(event))):
                res = outcome(lambda: sys.exit(worktree.main()))
            code = res.code
            if isinstance(event, dict) and "toolCall" in event:
                tool_name = (event.get("toolCall") or {}).get("name", "?")
                if code != "0":
                    problems.append(f"{group}: toolCall for {tool_name} should exit 0 and exited {code}")
                    continue
                try:
                    payload = json.loads(res.out)
                    got_decision = payload.get("decision")
                except Exception as exc:
                    problems.append(f"{group}: toolCall for {tool_name} emitted invalid JSON ({exc})")
                    continue
                want_decision = "deny" if want == "refuse" else "allow"
                if got_decision != want_decision:
                    problems.append(f"{group}: toolCall for {tool_name} should {want_decision} and got {got_decision}")
                elif want_decision == "deny":
                    reason = payload.get("reason")
                    if not isinstance(reason, str) or not reason.strip():
                        problems.append(
                            f"{group}: toolCall for {tool_name} denied without a non-empty reason ({payload!r})"
                        )
            else:
                if code != ("2" if want == "refuse" else "0"):
                    sent = (f"a {event['hook_event_name']} for {event['tool_name']}"
                            if isinstance(event, dict) else f"the payload {event!r}")
                    problems.append(f"{group}: {sent} should {want} and exited {code}")

    return problems


def _check_signed_channel_toolcall(signed_channel: Any, want: str, event: dict[str, Any]) -> list[str]:
    """Assert signed_channel.main() handles an Antigravity toolCall payload (solorepo's DR-260)."""
    with environment(SOLOREPO_HOOK_EVIDENCE=None), \
            stood_in(sys, stdin=io.StringIO(json.dumps(event))):
        res = outcome(lambda: sys.exit(signed_channel.main()))
    tool_call: dict[str, Any] = event.get("toolCall") or {}
    tool_name = str(tool_call.get("name", "?"))
    if res.code != "0":
        return [f"signed_channel toolCall {tool_name}: expected exit 0, got {res.code}"]
    try:
        payload = json.loads(res.out)
        got_decision = payload.get("decision")
    except Exception as exc:
        return [f"signed_channel toolCall {tool_name}: emitted invalid JSON ({exc})"]
    want_decision = "deny" if want == "refuse" else "allow"
    if got_decision != want_decision:
        return [f"signed_channel toolCall {tool_name}: expected {want_decision}, got {got_decision}"]
    if want_decision == "deny":
        reason = payload.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            return [f"signed_channel toolCall {tool_name}: denied without a non-empty reason"]
    return []


def _check_signed_channel_claude(signed_channel: Any, want: str, event: dict[str, Any]) -> list[str]:
    """Assert signed_channel.main() handles a standard PreToolUse payload (solorepo's DR-260)."""
    with environment(SOLOREPO_HOOK_EVIDENCE=None), \
            stood_in(sys, stdin=io.StringIO(json.dumps(event))):
        res = outcome(lambda: sys.exit(signed_channel.main()))
    want_code = "2" if want == "refuse" else "0"
    tool_name = str(event.get("tool_name", "?"))
    if res.code != want_code:
        return [f"signed_channel {tool_name}: expected exit {want_code}, got {res.code}"]
    return []


def _check_signed_channel_unparseable(signed_channel: Any) -> list[str]:
    """Assert signed_channel.main() fail-closed behavior on unparseable inputs (solorepo's DR-260)."""
    problems: list[str] = []
    with environment(SOLOREPO_HOOK_EVIDENCE=None), \
            stood_in(sys, stdin=io.StringIO('{"toolCall": {invalid json')):
        res_agy = outcome(lambda: sys.exit(signed_channel.main()))
    if res_agy.code != "0":
        problems.append(f"signed_channel unparseable toolCall: expected exit 0, got {res_agy.code}")
    else:
        try:
            agy_dec = json.loads(res_agy.out).get("decision")
            if agy_dec != "deny":
                problems.append(f"signed_channel unparseable toolCall: expected deny, got {agy_dec}")
        except Exception as exc:
            problems.append(f"signed_channel unparseable toolCall: invalid JSON ({exc})")

    with environment(SOLOREPO_HOOK_EVIDENCE=None), \
            stood_in(sys, stdin=io.StringIO("{not valid json")):
        res_std = outcome(lambda: sys.exit(signed_channel.main()))
    if res_std.code != "2":
        problems.append(f"signed_channel unparseable standard: expected exit 2, got {res_std.code}")

    return problems


def _signed_channel_events(signed_channel: Any) -> list[str]:
    """Assert signed_channel.main() verdicts across Claude Code PreToolUse and Antigravity toolCall events (solorepo's DR-260)."""
    claude_cases = (
        ("refuse", {"session_id": "s", "transcript_path": "/tmp/session.json", "cwd": str(ROOT),
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Bash", "tool_input": {"command": "gh pr comment 1 --body hi"}}),
        ("allow", {"session_id": "s", "transcript_path": "/tmp/session.json", "cwd": str(ROOT),
                   "hook_event_name": "PreToolUse",
                   "tool_name": "Bash", "tool_input": {"command": "git status --porcelain"}}),
    )
    agy_cases = (
        ("refuse", {"conversationId": "c", "stepIdx": 1,
                    "toolCall": {"name": "run_command", "args": {"CommandLine": "gh pr comment 1 --body hi"}}}),
        ("refuse", {"conversationId": "c", "stepIdx": 1,
                    "toolCall": {"name": "run_shell_command", "args": {"command": "curl https://api.github.com/repos/x"}}}),
        ("allow", {"conversationId": "c", "stepIdx": 1,
                   "toolCall": {"name": "run_command", "args": {"CommandLine": "git status --porcelain"}}}),
        ("allow", {"conversationId": "c", "stepIdx": 1,
                   "toolCall": {"name": "view_file", "args": {"AbsolutePath": f"{ROOT}/README.md"}}}),
    )
    problems: list[str] = []
    for want, c_event in claude_cases:
        problems.extend(_check_signed_channel_claude(signed_channel, want, c_event))
    for want, a_event in agy_cases:
        problems.extend(_check_signed_channel_toolcall(signed_channel, want, a_event))
    problems.extend(_check_signed_channel_unparseable(signed_channel))
    return problems


def _instead(worktree: Any) -> list[str]:
    """The rows of `INSTEAD` whose refusal does not name the tool the row says."""
    return [f"the refusal for {command!r} should name {name} as what to use instead"
            for command, name in offers.INSTEAD
            if name not in (worktree.command_allowed(command) or "")]


def _matchers() -> list[str]:
    """Assert what wildcard components do with `..` across harness matchers (solorepo's #457)."""
    problems = []
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        root = tmp / "root"
        root.mkdir()
        (root / "inside.txt").write_text("in")
        (tmp / "outside.txt").write_text("out")

        if [p.resolve() for p in root.glob("../outside.txt")] != [(tmp / "outside.txt").resolve()]:
            problems.append("python glob did not resolve ../outside.txt to parent directory")
        wildcard_patterns = (
            "??/outside.txt",
            "[!a][!a]/outside.txt",
            "..*/outside.txt",
            ".?/outside.txt",
            "[.][.]/outside.txt",
        )
        for pat in wildcard_patterns:
            if list(root.glob(pat)):
                problems.append(f"python glob unexpectedly matched .. with {pat}")

        if shutil.which("node"):
            script = (
                "const fs = require('fs');"
                "const res = {};"
                "if (fs.globSync) {"
                "  res.literal = fs.globSync('../outside.txt', { cwd: process.cwd() });"
                "  res.qmark = fs.globSync('??/outside.txt', { cwd: process.cwd() });"
                "  res.bracket = fs.globSync('[!a][!a]/outside.txt', { cwd: process.cwd() });"
                "  res.dotstar = fs.globSync('..*/outside.txt', { cwd: process.cwd() });"
                "}"
                "console.log(JSON.stringify(res));"
            )
            proc = subprocess.run(["node", "-e", script], cwd=root, capture_output=True, text=True)
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                if data.get("literal") != ["../outside.txt"]:
                    problems.append("node glob did not find ../outside.txt")
                for key in ("qmark", "bracket", "dotstar"):
                    if data.get(key):
                        problems.append(f"node glob unexpectedly matched .. for {key}")

        if shutil.which("rg"):
            for pat in ("??/outside.txt", "[!a][!a]/outside.txt", "..*/outside.txt", "../outside.txt"):
                proc = subprocess.run(["rg", "--files", "--glob", pat], cwd=root, capture_output=True, text=True)
                if proc.stdout.strip():
                    problems.append(f"rg unexpectedly matched with glob {pat}")

    return problems


def _find_hook_registration(harness: str, text: str, pattern: re.Pattern[str]) -> tuple[str, str] | None:
    """Find the registered (matcher, command) pair for a harness from review workflow or fallback logic.

    Args:
        harness: Target harness name (e.g. 'Claude Code' or 'Gemini CLI').
        text: Raw content of .github/workflows/review.yml.
        pattern: Compiled regex to extract (matcher, command) groups from text.

    Returns:
        tuple[str, str] | None: Matched or fallback (matcher, command) pair, or None if unconfigured.
    """
    match = pattern.search(text)
    if match:
        matcher, command = match.groups()
        return matcher, command
    if harness == "Gemini CLI":
        sys.path.insert(0, str(ROOT / ".meta"))
        import detect_fallback
        return detect_fallback.REVIEWER_BEFORE_TOOL_MATCHER, detect_fallback.REVIEWER_HOOK_COMMAND
    return None


def _probe_antigravity_registration(resolved: pathlib.Path, variable: str, harness: str) -> list[str]:
    """Execute real subprocess calls with Antigravity toolCall payloads, asserting decisions and evidence (solorepo's #682).

    Args:
        resolved: Absolute path to the resolved hook script executable.
        variable: Project directory environment variable name (e.g. GEMINI_PROJECT_DIR).
        harness: Display name of the harness for diagnostics.

    Returns:
        list[str]: Diagnostic failure messages, empty if all checks passed.
    """
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as agy_d:
        agy_evidence = pathlib.Path(agy_d) / "hook-agy.evidence"
        agy_env = {**os.environ, variable: str(ROOT), "SOLOREPO_HOOK_EVIDENCE": str(agy_evidence)}
        agy_allow = json.dumps({
            "conversationId": "c",
            "stepIdx": 1,
            "toolCall": {"name": "run_command", "args": {"CommandLine": "git status --porcelain"}},
        }).encode("utf-8")
        agy_proc = subprocess.run([str(resolved)], input=agy_allow, capture_output=True, env=agy_env)
        if agy_proc.returncode != 0:
            problems.append(
                f"{harness}: Antigravity toolCall should exit 0 and exited {agy_proc.returncode}"
            )
        else:
            try:
                agy_out = json.loads(agy_proc.stdout)
            except Exception as e:
                problems.append(
                    f"{harness}: Antigravity toolCall stdout is not JSON ({agy_proc.stdout!r}): {e}"
                )
                agy_out = {}
            if agy_out.get("decision") != "allow":
                problems.append(f"{harness}: Antigravity toolCall should allow and got {agy_out!r}")

        agy_deny = json.dumps({
            "conversationId": "c",
            "stepIdx": 2,
            "toolCall": {"name": "run_command", "args": {"CommandLine": "cat /etc/passwd"}},
        }).encode("utf-8")
        agy_deny_proc = subprocess.run([str(resolved)], input=agy_deny, capture_output=True, env=agy_env)
        if agy_deny_proc.returncode != 0:
            problems.append(
                f"{harness}: Antigravity deny toolCall should exit 0 and exited {agy_deny_proc.returncode}"
            )
        else:
            try:
                agy_deny_out = json.loads(agy_deny_proc.stdout)
            except Exception as e:
                problems.append(
                    f"{harness}: Antigravity deny toolCall stdout is not JSON ({agy_deny_proc.stdout!r}): {e}"
                )
                agy_deny_out = {}
            if agy_deny_out.get("decision") != "deny":
                problems.append(f"{harness}: Antigravity deny toolCall should deny and got {agy_deny_out!r}")
            elif not isinstance(agy_deny_out.get("reason"), str) or not agy_deny_out.get("reason").strip():
                problems.append(
                    f"{harness}: Antigravity deny toolCall missing non-empty reason: {agy_deny_out!r}"
                )

        agy_lines = agy_evidence.read_text(encoding="utf-8").splitlines() if agy_evidence.is_file() else []
        wanted_agy = [("run_command", "permit"), ("run_command", "refuse")]
        if [_decision(line) for line in agy_lines] != wanted_agy:
            problems.append(
                f"{harness}: Antigravity toolCall expected {wanted_agy!r} in evidence, got {agy_lines!r}"
            )
    return problems


def _probe_harness_registration(
    reg: tuple[str, str, re.Pattern[str], dict[str, Any], dict[str, Any]],
    text: str,
) -> list[str]:
    """Assert hook registration, subprocess execution, and evidence recording for one harness.

    Args:
        reg: Registration tuple of (harness, variable, pattern, refuse_event, allow_event).
        text: Content of .github/workflows/review.yml.

    Returns:
        list[str]: Diagnostic messages describing any probe failures.
    """
    harness, variable, pattern, refuse_event, allow_event = reg
    pair = _find_hook_registration(harness, text, pattern)
    if not pair:
        action = registration.OPTIONAL_HARNESS_ACTIONS.get(harness)
        if action and action not in text:
            return []
        return [f"{harness}: no hook registration found in review.yml to resolve"]
    matcher, command = pair
    tool_name = str(refuse_event["tool_name"])
    if not re.fullmatch(matcher, tool_name):
        return [f"{harness}: the registered matcher {matcher!r} does not match "
                f"{tool_name!r}, the tool name its own before-tool event carries"]
    resolved = pathlib.Path(command.replace(f"${variable}", str(ROOT)))
    if not resolved.is_file():
        return [f"{harness}: the registered command resolves to {resolved}, which is not a file"]
    if not os.access(resolved, os.X_OK):
        return [f"{harness}: the registered command {resolved} is not executable"]

    problems: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        evidence = pathlib.Path(d) / "hook.evidence"
        env = {**os.environ, variable: str(ROOT), "SOLOREPO_HOOK_EVIDENCE": str(evidence)}
        calls = (
            ("refuse", json.dumps(refuse_event).encode("utf-8"), repr(refuse_event["tool_input"]),
             (tool_name, "refuse")),
            ("allow", json.dumps(allow_event).encode("utf-8"), repr(allow_event["tool_input"]),
             (tool_name, "permit")),
            ("refuse", registration.UNREADABLE, "a payload that is not JSON at all",
             ("?", "refuse")),
        )
        exited = []
        for want, payload, shown, _ in calls:
            proc = subprocess.run([str(resolved)], input=payload, capture_output=True, env=env)
            code = str(proc.returncode)
            exited.append(code == ("2" if want == "refuse" else "0"))
            if not exited[-1]:
                problems.append(f"{harness}: the registered command should {want} "
                                f"{shown} and exited {code}")
        if all(exited):
            written = evidence.read_text(encoding="utf-8").splitlines() if evidence.is_file() else []
            wanted = [decision for *_, decision in calls]
            if [_decision(line) for line in written] != wanted:
                problems.append(f"{harness}: the registered command {resolved} decided "
                                f"{len(calls)} calls and left {written!r} in the file "
                                f"SOLOREPO_HOOK_EVIDENCE named ({evidence}) rather than a "
                                "`<UTC timestamp, seconds> <tool> permit|refuse` line for each, "
                                f"naming {wanted!r} in that order — which is the record a run that "
                                "names the file reads back to tell a confined session from an "
                                "unconfined one")

    if harness == "Gemini CLI":
        problems.extend(_probe_antigravity_registration(resolved, variable, harness))

    return problems


def _registration() -> list[str]:
    """`REGISTRATIONS`, per harness: the registered matcher against the tool name its own event carries, the registered command resolved and run as a real subprocess over a refused call, a permitted one and a payload that is not JSON at all, and one line of Evidence left per call it decided.

    Under Gemini CLI (Antigravity CLI), also runs `toolCall` payloads against the
    resolved command as a real subprocess, asserting exit 0, the decision object on
    stdout with non-empty refusal text, and Evidence lines (solorepo's #682).

    Harnesses declared in `registration.OPTIONAL_HARNESS_ACTIONS` (such as Gemini CLI when
    `run-gemini-cli` is excised under solorepo's DR-242) are skipped when their action is
    absent from `review.yml`.

    The why is `registration`'s own module docstring (solorepo's #456,
    solorepo's #645); this is the invariant alone.
    """
    if not REVIEW_WORKFLOW.is_file():
        return [f"{REVIEW_WORKFLOW.relative_to(ROOT).as_posix()} is missing"]
    text = REVIEW_WORKFLOW.read_text(encoding="utf-8")
    problems: list[str] = []
    for reg in registration.REGISTRATIONS:
        problems.extend(_probe_harness_registration(reg, text))
    return problems


def _audit_symlinks(worktree: Any) -> list[str]:
    """Assert that audit_symlinks accepts valid symlinks and refuses escaping ones (solorepo's DR-251)."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d).resolve()
        (root / "inner").write_text("ok", encoding="utf-8")
        (root / "valid_link").symlink_to(root / "inner")
        (root / "evil_link").symlink_to("/etc/passwd")
        (root / "git_link").symlink_to(root / ".git")
        (root / "harness_link").symlink_to(pathlib.Path.home() / ".gemini" / "tmp")

        violations = worktree.paths.audit_symlinks(root)
        if len(violations) != 3:
            problems.append(
                f"audit_symlinks: expected 3 violations (evil_link, git_link, harness_link), found {len(violations)}: {violations}"
            )
        if not any("evil_link" in v and "outside" in v for v in violations):
            problems.append(f"audit_symlinks: did not report evil_link as outside: {violations}")
        if not any("git_link" in v and ".git" in v for v in violations):
            problems.append(f"audit_symlinks: did not report git_link entering .git: {violations}")
        if not any("harness_link" in v and "outside" in v for v in violations):
            problems.append(f"audit_symlinks: did not report harness_link without exemption as outside: {violations}")

        hook_path = META / "hooks" / "worktree_only.py"
        res = subprocess.run(
            [sys.executable, str(hook_path), "--audit-symlinks"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            problems.append(f"worktree_only.py --audit-symlinks on clean ROOT exited {res.returncode}: {res.stderr}")
    return problems


@check("hook probes", pre=True)
def hook_probes() -> list[str]:
    """Both hooks' predicates against the calls they exist to refuse and the calls they must let through, what a `worktree_only` refusal offers instead, matcher invariants across harnesses, and each harness's own registration run as a real subprocess.

    Loads `signed_channel` and `worktree_only` afresh and runs five tables in
    order: `VERDICTS`, each call with the verdict its hook owes it; `OFFERS`,
    each refused command with the nearest command its refusal names, or `None`
    where none is derivable; `EVENTS`, each before-tool payload with the code
    the entry point owes it, Claude Code's envelope beside Gemini CLI's;
    `INSTEAD`, each program off the list with the tool
    its refusal names in its place; `REGISTRATIONS`, each harness's own matcher
    and command line as `review.yml` registers them, resolved against this
    checkout and run as a subprocess rather than assumed (solorepo's #456),
    leaving the Evidence a live run reads back to tell that the hook ran at all
    (solorepo's #645).
    Asserts that wildcard components do not match parent directories across
    the harnesses' own matchers (solorepo's #457).
    A line names the group and the call that gave way, so the report says which
    case a predicate no longer holds. Each refused call sits beside the innocent
    neighbour the predicate must not catch (solorepo's #86, solorepo's #98), so an
    edit to either predicate meets both before a run does (solorepo's DR-110).
    """
    hooks = {name: load_hook(name) for name in ("signed_channel", "worktree_only")}
    worktree = hooks["worktree_only"]
    return (_verdicts(hooks) + _offers(worktree) + _events(worktree)
            + _signed_channel_events(hooks["signed_channel"]) + _instead(worktree)
            + _matchers() + _registration() + _audit_symlinks(worktree))

