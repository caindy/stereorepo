#!/usr/bin/env python3
"""Client and CLI interface for the Google Labs Jules REST API (jules.googleapis.com/v1alpha).

Provides programmatic access to Jules Sources, Sessions, and Activities for autonomous
coding loop integration and spike validation (solorepo's DR-246, solorepo's #678, solorepo's #681).
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any

API_BASE = "https://jules.googleapis.com/v1alpha"
ENV_API_KEY = "JULES_API_KEY"
CONFIG_ENV = pathlib.Path("~/.config/solorepo/jules.env").expanduser()


def get_api_key(explicit_key: str | None = None) -> str:
    """Retrieves the Jules API key from an argument, environment, or ~/.config/solorepo/jules.env."""
    if explicit_key:
        return explicit_key
    key = os.environ.get(ENV_API_KEY, "").strip()
    if key:
        return key
    if CONFIG_ENV.exists():
        for line in CONFIG_ENV.read_text().splitlines():
            line = line.strip().removeprefix("export ").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in (ENV_API_KEY, "API_KEY"):
                val = v.strip().strip("\"'")
                if val:
                    return val
    sys.exit(f"jules: no API key provided — set ${ENV_API_KEY}, pass --api-key, "
             f"or write it to {CONFIG_ENV} (generate one at https://jules.google.com/settings)")


def http_request(
    endpoint: str,
    api_key: str,
    method: str = "GET",
    body: Mapping[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Dispatches an authenticated HTTP request to the Jules REST API."""
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    headers = {
        "X-Goog-Api-Key": api_key,
        "Accept": "application/json",
    }
    data: bytes | None = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    if dry_run:
        print(f"[DRY-RUN] {method} {url}", file=sys.stderr)
        print(f"[DRY-RUN] Headers: {list(headers.keys())}", file=sys.stderr)
        if body:
            print(f"[DRY-RUN] Body:\n{json.dumps(body, indent=2)}", file=sys.stderr)
        return {"dry_run": True, "method": method, "url": url, "body": body}

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            res: dict[str, Any] = json.loads(content) if content else {}
            return res
    except urllib.error.HTTPError as err:
        if err.code == 404 and method == "GET" and "activities" in endpoint:
            return {}
        err_msg = err.read().decode("utf-8")
        sys.exit(f"jules: HTTP {err.code} {err.reason} from {url}\n{err_msg}")
    except urllib.error.URLError as err:
        sys.exit(f"jules: connection error to {url}: {err.reason}")


def list_sources(api_key: str, dry_run: bool = False) -> dict[str, Any]:
    """Lists connected GitHub repository sources available to the authenticated account."""
    return http_request("sources", api_key=api_key, dry_run=dry_run)


def list_sessions(api_key: str, page_size: int = 10, dry_run: bool = False) -> dict[str, Any]:
    """Lists recent coding task sessions for the authenticated account."""
    return http_request(f"sessions?pageSize={page_size}", api_key=api_key, dry_run=dry_run)


def get_session(session_id: str, api_key: str, dry_run: bool = False) -> dict[str, Any]:
    """Retrieves metadata and status for a specific Jules session."""
    clean_id = session_id.removeprefix("sessions/")
    return http_request(f"sessions/{clean_id}", api_key=api_key, dry_run=dry_run)


def list_activities(
    session_id: str,
    api_key: str,
    page_size: int = 20,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Lists activities for a specific Jules session."""
    clean_id = session_id.removeprefix("sessions/")
    return http_request(
        f"sessions/{clean_id}/activities?pageSize={page_size}",
        api_key=api_key,
        dry_run=dry_run,
    )


def create_session(
    prompt: str,
    api_key: str,
    repo_full_name: str | None = None,
    options: Mapping[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Initiates a new coding task session in Google Labs Jules.

    Supports both repoless sessions (operating as cloud sandbox functions without
    a repository) and source-bound sessions targeting a specific GitHub repository.
    """
    opts = options or {}
    payload: dict[str, Any] = {
        "prompt": prompt,
    }
    if repo_full_name:
        starting_branch = str(opts.get("starting_branch", "main"))
        payload["sourceContext"] = {
            "source": f"sources/github/{repo_full_name}",
            "githubRepoContext": {
                "startingBranch": starting_branch,
            },
        }
        auto_create_pr = bool(opts.get("auto_create_pr", False))
        payload["automationMode"] = "AUTO_CREATE_PR" if auto_create_pr else "AUTOMATION_MODE_UNSPECIFIED"

    require_plan_approval = bool(opts.get("require_plan_approval", False))
    payload["requirePlanApproval"] = require_plan_approval
    return http_request("sessions", api_key=api_key, method="POST", body=payload, dry_run=dry_run)


def poll_session_activities(
    session_id: str,
    api_key: str,
    timeout_seconds: int = 180,
    poll_interval: float = 3.0,
) -> list[dict[str, Any]]:
    """Polls a session until agent activities are generated or timeout occurs."""
    clean_id = session_id.removeprefix("sessions/")
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            res = list_activities(clean_id, api_key=api_key)
            raw_activities = res.get("activities")
            if isinstance(raw_activities, list):
                activities: list[dict[str, Any]] = [
                    item for item in raw_activities if isinstance(item, dict)
                ]
                agent_activities = [
                    a for a in activities
                    if a.get("originator") == "agent" or "agentMessaged" in a
                ]
                if agent_activities:
                    return activities
        except Exception:
            pass
        time.sleep(poll_interval)
    sys.exit(f"jules: timed out waiting for session {clean_id} activities after {timeout_seconds}s")


def extract_agent_text(activities: list[dict[str, Any]]) -> str:
    """Extract and concatenate textual response messages produced by the Jules agent."""
    messages: list[str] = []
    for act in activities:
        if act.get("originator") == "agent" or "agentMessaged" in act:
            agent_msg = act.get("agentMessaged", {})
            text = agent_msg.get("text") or agent_msg.get("message") or act.get("text") or ""
            if text:
                messages.append(str(text))
    return "\n\n".join(messages).strip()


FINDING_PATTERN = re.compile(
    r"FINDING:\s*([^\s:\n]+):(\d+)\s*\n(.*?)\nEND_FINDING",
    re.DOTALL,
)


def extract_findings(text: str) -> list[tuple[str, int, str]]:
    """Extract anchored file/line findings from Jules review text."""
    findings = []
    for match in FINDING_PATTERN.finditer(text):
        path_str, line_str, body = match.groups()
        try:
            line_no = int(line_str)
            findings.append((path_str.strip(), line_no, body.strip()))
        except ValueError:
            continue
    return findings


def check_pr_ci_status(pr_number: str) -> tuple[bool, str]:
    """Check whether any completed GitHub CI check on the pull request has failed."""
    cmd = ["gh", "pr", "checks", pr_number, "--json", "name,state,bucket"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return False, "Checks pending or status query unavailable."
    try:
        checks = json.loads(res.stdout)
        if not isinstance(checks, list):
            return False, res.stdout.strip()
        failed_checks = []
        for c in checks:
            if not isinstance(c, dict):
                continue
            name = str(c.get("name", "unknown"))
            state = str(c.get("state", "")).upper()
            bucket = str(c.get("bucket", "")).lower()
            if bucket == "fail" or state in ("FAILURE", "FAILED", "ERROR"):
                failed_checks.append(f"{name} ({state})")
        if failed_checks:
            return True, f"Failed CI checks: {', '.join(failed_checks)}"
        return False, "All completed CI checks passed."
    except Exception as e:
        return False, f"Could not parse checks JSON: {e}"


def determine_verdict(
    form_passed: bool,
    has_failed_ci: bool,
    unresolved_count: int,
    findings_count: int,
    review_body: str,
) -> str:
    """Determine the review verdict flag based on gate checks, CI state, and model recommendation."""
    if not form_passed or has_failed_ci or unresolved_count > 0 or findings_count > 0:
        return "--request-changes"
    if "RECOMMENDED_VERDICT: REQUEST_CHANGES" in review_body or "RECOMMENDED_VERDICT: REQUEST CHANGES" in review_body:
        return "--request-changes"
    if "RECOMMENDED_VERDICT: APPROVE" in review_body:
        return "--approve"
    return "--comment"


def post_review_and_findings(
    clean_pr: str,
    verdict: str,
    review_body: str,
    findings: list[tuple[str, int, str]],
) -> None:
    """Post anchored line findings and the overall review verdict to GitHub via .meta/say/post."""
    for path_str, line_no, finding_body in findings:
        raise_cmd = [".meta/say/post", "--role", "reviewer", "raise", clean_pr, path_str, str(line_no)]
        subprocess.run(raise_cmd, input=finding_body + "\n", text=True, check=True)

    post_cmd = [".meta/say/post", "--role", "reviewer", "review", clean_pr, verdict]
    subprocess.run(post_cmd, input=review_body + "\n", text=True, check=True)


def review_pr(
    pr_number: int | str,
    api_key: str,
    caller_prompt: str = "",
    timeout_seconds: int = 300,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute automated pull request review via repoless Jules REST API and post signed verdict (solorepo's DR-246)."""
    clean_pr = str(pr_number).strip().lstrip("#")
    diff_path = pathlib.Path(".review/diff.patch")
    diff_text = ""
    if diff_path.is_file():
        diff_text = diff_path.read_text(encoding="utf-8", errors="replace")
    else:
        diff_cmd = subprocess.run(["git", "diff", "origin/main...HEAD"], capture_output=True, text=True)
        diff_text = diff_cmd.stdout if diff_cmd.returncode == 0 else ""

    check_pr_res = subprocess.run(["python3", ".meta/check_pr.py", clean_pr], capture_output=True, text=True)
    form_passed = check_pr_res.returncode == 0
    checks_summary = f"check_pr exit code: {check_pr_res.returncode}\n{check_pr_res.stdout}\n{check_pr_res.stderr}".strip()

    has_failed_ci, ci_summary = check_pr_ci_status(clean_pr)

    unresolved_res = subprocess.run(
        ["python3", ".meta/check_pr.py", clean_pr, "--unresolved-count"],
        capture_output=True,
        text=True,
    )
    unresolved_count = 0
    with contextlib.suppress(ValueError):
        unresolved_count = int(unresolved_res.stdout.strip())

    threads_res = subprocess.run(
        ["python3", ".meta/check_pr.py", clean_pr, "--threads"],
        capture_output=True,
        text=True,
    )
    threads_summary = threads_res.stdout.strip() if threads_res.returncode == 0 else "None."

    caller_block = f"\nCaller Instructions:\n{caller_prompt}\n" if caller_prompt else ""

    prompt = f"""You are the reviewer Role in solorepo (solorepo's DR-107, DR-194, DR-198).
Your Personality is work:personality/reviewer: Analytical and thorough. Holds the diff to the Disciplines and the Charter strictly. Clear and precise in identification of issues; concise yet unambiguous in argument.

You are evaluating Pull Request #{clean_pr}.
Review Invariants:
1. Technical Writer register: Spelled out, self-contained, citations dereferenced (solorepo's DR-198).
2. Diátaxis Compass: Docstrings are dry Reference contracts without reviewer litigation (solorepo's DR-175). Past defect narratives belong in <module>.history.md (solorepo's DR-171).
3. No inline Python in workflows or actions (solorepo's DR-241).
4. Commits must name their Actor and Agent in trailers (Article 19, solorepo's DR-233).
5. Mandatory 7-heading PR description template (PR First, verified by check_pr.py).
6. Every review thread must be answered; do not approve if open threads remain unresolved (PR First step 8, solorepo's DR-161).
7. Do not approve if GitHub CI checks have failed (solorepo's DR-161).
{caller_block}
Current PR Form Verification Status:
{checks_summary}

GitHub CI Checks Status:
{ci_summary}

Open Review Threads ({unresolved_count} unresolved):
{threads_summary}

Pull Request Diff:
```diff
{diff_text}
```

If you identify specific actionable defects or violations on the diff, anchor each finding to its path and line using this format:
FINDING: <path>:<line>
<Detailed explanation of the objection citing relevant Disciplines or Articles>
END_FINDING

Analyze the diff and existing threads, and provide your review in two sections:
### What was checked
<Summary of items evaluated against Disciplines and Charter>

### What was found
<Findings, observations, or confirmation of clean diff>

Conclude with your verdict recommendation on the final line:
RECOMMENDED_VERDICT: APPROVE
or
RECOMMENDED_VERDICT: REQUEST_CHANGES
or
RECOMMENDED_VERDICT: COMMENT
"""
    res = create_session(prompt=prompt, api_key=api_key, repo_full_name=None, dry_run=dry_run)
    if dry_run:
        print(f"[DRY-RUN] Created repoless review session for PR #{clean_pr}")
        return {"dry_run": True, "verdict": "--approve", "body": "Clean review"}

    session_id = str(res.get("id") or res.get("name", "").removeprefix("sessions/"))
    activities = poll_session_activities(session_id, api_key=api_key, timeout_seconds=timeout_seconds)
    review_body = extract_agent_text(activities)
    if not review_body.strip():
        raise RuntimeError(f"Jules session {session_id} returned an empty review response; aborting verdict.")

    findings = extract_findings(review_body)
    verdict = determine_verdict(
        form_passed=form_passed,
        has_failed_ci=has_failed_ci,
        unresolved_count=unresolved_count,
        findings_count=len(findings),
        review_body=review_body,
    )

    post_review_and_findings(clean_pr=clean_pr, verdict=verdict, review_body=review_body, findings=findings)
    return {
        "session_id": session_id,
        "verdict": verdict,
        "body": review_body,
        "findings": findings,
    }


def dispatch_action(
    role: str,
    api_key: str,
    kwargs: Mapping[str, Any],
    dry_run: bool = False,
) -> None:
    """Dispatch action from .meta/actions/jules composite action to reviewer workflow."""
    if role != "reviewer":
        sys.exit(
            f"jules: unsupported role '{role}'; Google Labs Jules is configured exclusively "
            "as an autonomous reviewer fallback harness (solorepo's DR-246)."
        )
    pr = kwargs.get("pr")
    if not pr:
        sys.exit("jules: --pr is required when role is reviewer")
    timeout_minutes = int(kwargs.get("timeout_minutes") or 15)
    timeout_seconds = timeout_minutes * 60
    caller_prompt = str(kwargs.get("prompt") or "")
    review_pr(
        pr,
        api_key=api_key,
        caller_prompt=caller_prompt,
        timeout_seconds=timeout_seconds,
        dry_run=dry_run,
    )


def build_parser() -> argparse.ArgumentParser:
    """Constructs the command-line argument parser."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--api-key", help="Jules API key (default: $JULES_API_KEY)")
    common.add_argument("--dry-run", action="store_true", help="Print request without executing")

    parser = argparse.ArgumentParser(
        parents=[common],
        description="CLI client for Google Labs Jules REST API (jules.googleapis.com/v1alpha)",
    )

    sub = parser.add_subparsers(dest="subcommand", required=True)

    sub.add_parser("sources", parents=[common], help="List connected repository sources")

    p_list = sub.add_parser("sessions", parents=[common], help="List recent sessions")
    p_list.add_argument("--page-size", type=int, default=10, help="Number of sessions to fetch")

    p_get = sub.add_parser("session", parents=[common], help="Get session details")
    p_get.add_argument("session_id", help="Session ID (e.g. sessions/12345 or 12345)")

    p_act = sub.add_parser("activities", parents=[common], help="List activities for a session")
    p_act.add_argument("session_id", help="Session ID")
    p_act.add_argument("--page-size", type=int, default=20, help="Number of activities to fetch")

    p_create = sub.add_parser("create", parents=[common], help="Create a new Jules session")
    p_create.add_argument("--repo", default=None, help="GitHub repo owner/name for source-bound mode (defaults to repoless sandbox mode)")
    p_create.add_argument("--branch", default="main", help="Starting branch for source-bound mode")
    p_create.add_argument("--prompt", help="Direct prompt text")
    p_create.add_argument("--prompt-file", type=pathlib.Path, help="File containing prompt text")
    p_create.add_argument("--auto-pr", action="store_true", default=False, help="Automatically create a PR in source-bound mode (defaults to False)")
    p_create.add_argument("--require-approval", action="store_true", help="Require plan approval")
    p_create.add_argument("--wait", action="store_true", help="Wait and poll for agent response")
    p_create.add_argument("--timeout", type=int, default=180, help="Poll timeout in seconds (default 180)")

    p_rev = sub.add_parser("review-pr", parents=[common], help="Run Jules automated PR review")
    p_rev.add_argument("pr_number", help="Pull request number to review")
    p_rev.add_argument("--prompt", default="", help="Optional instructions to include in reviewer prompt")
    p_rev.add_argument("--timeout-seconds", type=int, default=300, help="Timeout in seconds")

    p_disp = sub.add_parser("dispatch", parents=[common], help="Dispatch role execution from composite action")
    p_disp.add_argument("--role", default="reviewer", choices=["reviewer"], help="Role to execute (reviewer only; solorepo's DR-246)")
    p_disp.add_argument("--pr", help="Pull request number")
    p_disp.add_argument("--prompt", help="Direct prompt instructions")
    p_disp.add_argument("--timeout-minutes", type=int, default=15, help="Timeout in minutes")

    return parser


def handle_query(
    subcommand: str,
    args: argparse.Namespace,
    api_key: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Execute query subcommands (sources, sessions, session, activities)."""
    if subcommand == "sources":
        return list_sources(api_key, dry_run=dry_run)
    if subcommand == "sessions":
        return list_sessions(api_key, page_size=args.page_size, dry_run=dry_run)
    if subcommand == "session":
        return get_session(args.session_id, api_key, dry_run=dry_run)
    if subcommand == "activities":
        return list_activities(args.session_id, api_key, page_size=args.page_size, dry_run=dry_run)
    return {}


def handle_create(
    args: argparse.Namespace,
    api_key: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Execute session creation subcommand."""
    prompt_text = args.prompt
    if not prompt_text and args.prompt_file:
        prompt_text = args.prompt_file.read_text(encoding="utf-8")
    if not prompt_text:
        sys.exit("jules: specify --prompt or --prompt-file to create a session")

    opts = {
        "starting_branch": args.branch,
        "auto_create_pr": args.auto_pr,
        "require_plan_approval": args.require_approval,
    }
    repo_name = args.repo
    res = create_session(
        prompt=prompt_text,
        api_key=api_key,
        repo_full_name=repo_name,
        options=opts,
        dry_run=dry_run,
    )
    if getattr(args, "wait", False) and not dry_run:
        session_id = str(res.get("id") or res.get("name", "").removeprefix("sessions/"))
        if session_id:
            print(f"[jules] waiting for session {session_id} agent response...", file=sys.stderr)
            acts = poll_session_activities(session_id, api_key=api_key, timeout_seconds=args.timeout)
            res["activities"] = acts
    return res


def main() -> None:
    """Dispatches CLI commands for the Jules client."""
    parser = build_parser()
    args = parser.parse_args()

    dry_run = bool(args.dry_run or "--dry-run" in sys.argv)
    api_key = get_api_key(args.api_key) if not dry_run else (args.api_key or "dry-run-key")

    if args.subcommand in ("sources", "sessions", "session", "activities"):
        res = handle_query(args.subcommand, args=args, api_key=api_key, dry_run=dry_run)
        print(json.dumps(res, indent=2))
    elif args.subcommand == "create":
        res = handle_create(args=args, api_key=api_key, dry_run=dry_run)
        print(json.dumps(res, indent=2))
    elif args.subcommand == "review-pr":
        res = review_pr(
            args.pr_number,
            api_key=api_key,
            caller_prompt=args.prompt,
            timeout_seconds=args.timeout_seconds,
            dry_run=dry_run,
        )
        print(json.dumps(res, indent=2))
    elif args.subcommand == "dispatch":
        dispatch_action(
            role=args.role,
            api_key=api_key,
            kwargs={
                "pr": args.pr,
                "prompt": args.prompt,
                "timeout_minutes": args.timeout_minutes,
            },
            dry_run=dry_run,
        )


if __name__ == "__main__":
    main()
