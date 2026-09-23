"""
The reviewer's confinement, held equal across the two harnesses: neither path's
allowlist names a dangerous tool, the fine-grained denials the Antigravity CLI
reads are populated (solorepo's DR-254), `tools.core` and the `BeforeTool`
matcher name the same tools, and the reviewer workflow audits the worktree's
symlinks before it holds a credential (solorepo's DR-251).

History in files.history.md (solorepo's DR-171).
"""

import re
import sys
from typing import Any

from checks.collect import (
    META,
    ROOT,
    CouldNotRun,
    Found,
    Passed,
    StepOutcome,
    check,
)
from checks.files.workflows import REVIEW_WORKFLOW, WORKFLOWS

ALLOWED_TOOLS_LINE = re.compile(r'--allowedTools\s+"([^"]*)"')
"""The Claude path's `--allowedTools` value, inside the `claude_args` block scalar."""


REVIEWER_WORKFLOWS = (REVIEW_WORKFLOW, WORKFLOWS / "triage.yml")
"""The reviewer workflows, bounding the reviewer Role during PR review and Challenge triage."""


DANGEROUS_TOOLS = (
    ("Write", "write_file"),
    ("Edit", "replace"),
    ("WebFetch", "web_fetch"),
    ("WebSearch", "google_web_search"),
)
"""Each entry pairs Claude Code's name for one capability with Gemini CLI's; neither reviewer
path's allowlist may name either half, on its own or alongside the other (solorepo's #454)."""


REQUIRED_DENIED_PERMISSIONS: tuple[str, ...] = (
    "write_file(*)",
    "read_url(*)",
    "execute_url(*)",
    "invoke_subagent(*)",
)
"""Fine-grained permissions required to be denied for Antigravity CLI reviewer confinement (solorepo's DR-110, solorepo's DR-245, solorepo's DR-254, solorepo's #636, solorepo's #637)."""

REQUIRED_CODER_DENIED_PERMISSIONS: tuple[str, ...] = (
    "invoke_subagent(*)",
)
"""Fine-grained permissions required to be denied for Antigravity CLI coder confinement (solorepo's DR-254, solorepo's DR-257, solorepo's #715)."""


def _audit_denied_permissions(detect_fallback: Any) -> list[str]:
    """Verify that detect_fallback.py defines and populates REVIEWER_DENIED_PERMISSIONS and CODER_DENIED_PERMISSIONS."""
    reviewer_denied = getattr(detect_fallback, "REVIEWER_DENIED_PERMISSIONS", None)
    if not reviewer_denied:
        return [
            "detect_fallback.py: `REVIEWER_DENIED_PERMISSIONS` is missing or empty; "
            "Antigravity CLI reviewer confinement requires explicit permissions.deny"
        ]
    problems: list[str] = []
    for required_perm in REQUIRED_DENIED_PERMISSIONS:
        if required_perm not in reviewer_denied:
            problems.append(
                f"detect_fallback.py: `REVIEWER_DENIED_PERMISSIONS` is missing `{required_perm}`; "
                "add it to prevent unconfined file writing or network access"
            )

    coder_denied = getattr(detect_fallback, "CODER_DENIED_PERMISSIONS", None)
    if not coder_denied:
        problems.append(
            "detect_fallback.py: `CODER_DENIED_PERMISSIONS` is missing or empty; "
            "Antigravity CLI coder confinement requires explicit permissions.deny for invoke_subagent(*)"
        )
    else:
        for required_perm in REQUIRED_CODER_DENIED_PERMISSIONS:
            if required_perm not in coder_denied:
                problems.append(
                    f"detect_fallback.py: `CODER_DENIED_PERMISSIONS` is missing `{required_perm}`; "
                    "add it to prevent headless subagent delegation under Antigravity CLI"
                )

    return problems


@check("gemini reviewer allowlist matches claude's")
def gemini_allowlist_matches_claude() -> StepOutcome:
    """The reviewer workflows bound Gemini CLI's tool registry the way they bound Claude Code's (solorepo's #454, solorepo's #636, solorepo's #699).

    The Claude path names what the model may call with `--allowedTools`, so a
    tool it never names is simply not there for the model to reach. Under
    containerized Antigravity CLI (solorepo's DR-245), capability bounds are enforced via
    fine-grained `permissions.deny` (`REVIEWER_DENIED_PERMISSIONS`) alongside the
    hook-guarded `REVIEWER_CORE_TOOLS` allowlist (solorepo's #636, solorepo's #699).
    This step fails when any reviewer workflow's Claude list is missing, when
    `detect_fallback.py` names dangerous tools in `REVIEWER_CORE_TOOLS`, when
    `REVIEWER_DENIED_PERMISSIONS` omits required write/network denials, or when
    either harness names either half of a `DANGEROUS_TOOLS` pair.

    History in files.history.md (solorepo's DR-171).
    """
    sys.path.insert(0, str(META))
    import detect_fallback

    gemini_tools = set(detect_fallback.REVIEWER_CORE_TOOLS)
    problems: list[str] = _audit_denied_permissions(detect_fallback)

    for _claude_name, gemini_name in DANGEROUS_TOOLS:
        if gemini_name in gemini_tools:
            problems.append(
                f"detect_fallback.py: `REVIEWER_CORE_TOOLS` names `{gemini_name}`; no reviewer "
                "path may name this pair, so drop it from `REVIEWER_CORE_TOOLS`"
            )

    scanned = 0
    for workflow_path in REVIEWER_WORKFLOWS:
        if not workflow_path.is_file():
            return CouldNotRun(f"{workflow_path.relative_to(ROOT).as_posix()} is missing")
        text = workflow_path.read_text(encoding="utf-8")
        allowed_match = ALLOWED_TOOLS_LINE.search(text)
        if not allowed_match:
            problems.append(f"{workflow_path.relative_to(ROOT)}: no `--allowedTools` value on the Claude path to compare against")
            continue
        scanned += 1
        claude_tools = {token.split("(", 1)[0] for token in allowed_match.group(1).split(",")}
        for claude_name, _ in DANGEROUS_TOOLS:
            if claude_name in claude_tools:
                problems.append(
                    f"{workflow_path.relative_to(ROOT)}: the Claude path names `{claude_name}`; "
                    "no reviewer path may name this pair, so drop it from `--allowedTools`"
                )
        if "role: reviewer" not in text:
            problems.append(
                f"{workflow_path.relative_to(ROOT)}: does not pass `role: reviewer` to `.meta/actions/agy`"
            )

    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(DANGEROUS_TOOLS)} tool pairs held out of all {scanned} reviewer workflows ({', '.join(p.name for p in REVIEWER_WORKFLOWS)})")


@check("gemini tools.core matches the BeforeTool matcher")
def gemini_core_matches_hook_matcher() -> StepOutcome:
    """`tools.core` and the `BeforeTool` matcher name the same tools, or a call reaches `worktree_only.py` never sees (solorepo's #454, solorepo's #699).

    `tools.core` decides which tools the model may call at all; the `BeforeTool`
    matcher decides which of those calls the worktree-confinement hook
    inspects. The two are unified in `.meta/detect_fallback.py` under
    `REVIEWER_CORE_TOOLS` and `REVIEWER_BEFORE_TOOL_MATCHER` (solorepo's #699)
    and applied by `.meta/actions/agy` when `role == 'reviewer'`. This step fails
    when the two sets differ in either direction, or when `.meta/actions/agy`
    fails to invoke reviewer confinement.

    History in files.history.md (solorepo's DR-171).
    """
    sys.path.insert(0, str(META))
    import detect_fallback

    action_path = META / "actions" / "agy" / "action.yml"
    if not action_path.is_file():
        return CouldNotRun(f"{action_path.relative_to(ROOT).as_posix()} is missing")
    action_text = action_path.read_text(encoding="utf-8")
    if "--configure-reviewer" not in action_text:
        return Found((f"{action_path.relative_to(ROOT)}: does not invoke `detect_fallback.py --configure-reviewer`",))
    if "--configure-coder" not in action_text:
        return Found((f"{action_path.relative_to(ROOT)}: does not invoke `detect_fallback.py --configure-coder`",))
    if "run_agy.py" not in action_text:
        return Found((f"{action_path.relative_to(ROOT)}: does not invoke `python3 .meta/run_agy.py`",))

    core_tools = set(detect_fallback.REVIEWER_CORE_TOOLS)
    raw_matcher = detect_fallback.REVIEWER_BEFORE_TOOL_MATCHER
    matcher_match = re.match(r"^\^\(([^)]+)\)\$$", raw_matcher)
    if not matcher_match:
        return Found((f"detect_fallback.py: REVIEWER_BEFORE_TOOL_MATCHER '{raw_matcher}' does not match expected pattern ^(...) $",))
    matcher_tools = set(matcher_match.group(1).split("|"))

    problems: list[str] = []
    for extra in sorted(core_tools - matcher_tools):
        problems.append(f"detect_fallback.py: `REVIEWER_CORE_TOOLS` names `{extra}`, which the `BeforeTool` "
                        "matcher does not guard; add it there or drop it from `REVIEWER_CORE_TOOLS`")
    for extra in sorted(matcher_tools - core_tools):
        problems.append(f"detect_fallback.py: the `BeforeTool` matcher guards `{extra}`, which "
                        "`REVIEWER_CORE_TOOLS` does not name; the matcher is guarding a tool the model "
                        "cannot call")
    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(core_tools)} tools admitted, all and only the ones the BeforeTool matcher guards")


@check("reviewer symlink verification")
def reviewer_symlinks_verified() -> StepOutcome:
    """The reviewer workflow audits worktree symlinks before credential provisioning, and the worktree holds no outbound symlinks (solorepo's DR-251, solorepo's #458).

    Verifies that `.github/workflows/review.yml` invokes
    `python3 .meta/hooks/worktree_only.py --audit-symlinks` prior to
    `hold the reviewer's credential`. Validates that all symlinks within the
    repository resolve strictly within repository boundaries.

    History in files.history.md (solorepo's DR-171).
    """
    if not REVIEW_WORKFLOW.is_file():
        return CouldNotRun(f"{REVIEW_WORKFLOW.relative_to(ROOT)} is missing")

    text = REVIEW_WORKFLOW.read_text(encoding="utf-8")
    audit_cmd = "python3 .meta/hooks/worktree_only.py --audit-symlinks"
    if audit_cmd not in text:
        return Found((f"review.yml: missing step invoking `{audit_cmd}`",))

    audit_pos = text.find(audit_cmd)
    cred_pos = text.find("hold the reviewer's credential")
    if cred_pos != -1 and audit_pos > cred_pos:
        return Found(("review.yml: `verify worktree symlinks` occurs after `hold the reviewer's credential`",))

    sys.path.insert(0, str(META))
    from lib.worktree_only.paths import audit_symlinks

    violations = audit_symlinks(ROOT)
    if violations:
        return Found(tuple(f"outbound symlink: {v}" for v in violations))

    return Passed("review.yml audits symlinks before credentials, and worktree contains no outbound symlinks")
