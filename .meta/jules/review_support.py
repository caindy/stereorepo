"""Parsing and posting helpers for a Jules pull request review."""

import json
import re
import subprocess

FINDING_PATTERN = re.compile(
    r"FINDING:\s*([^\s:\n]+):(\d+)\s*\n(.*?)\nEND_FINDING",
    re.DOTALL,
)


def extract_findings(text: str) -> list[tuple[str, int, str]]:
    """Extract anchored file and line findings from review text."""
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
    """Report whether any completed pull request check failed."""
    cmd = ["gh", "pr", "checks", pr_number, "--json", "name,state,bucket"]
    res = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if res.returncode != 0:
        return False, "Checks pending or status query unavailable."
    try:
        checks = json.loads(res.stdout)
        if not isinstance(checks, list):
            return False, res.stdout.strip()
        failed_checks = []
        for check in checks:
            if not isinstance(check, dict):
                continue
            name = str(check.get("name", "unknown"))
            state = str(check.get("state", "")).upper()
            bucket = str(check.get("bucket", "")).lower()
            if bucket == "fail" or state in ("FAILURE", "FAILED", "ERROR"):
                failed_checks.append(f"{name} ({state})")
        if failed_checks:
            return True, f"Failed CI checks: {', '.join(failed_checks)}"
        return False, "All completed CI checks passed."
    except json.JSONDecodeError as error:
        return False, f"Could not parse checks JSON: {error}"


def determine_verdict(
    form_passed: bool,
    has_failed_ci: bool,
    unresolved_count: int,
    findings_count: int,
    review_body: str,
) -> str:
    """Choose the channel's review flag from checks and the recommendation."""
    if not form_passed or has_failed_ci or unresolved_count > 0 or findings_count > 0:
        return "--request-changes"
    if ("RECOMMENDED_VERDICT: REQUEST_CHANGES" in review_body
            or "RECOMMENDED_VERDICT: REQUEST CHANGES" in review_body):
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
    """Post line findings and the review through the reviewer channel."""
    for path_str, line_no, finding_body in findings:
        raise_cmd = [".meta/say/post", "--role", "reviewer", "raise", clean_pr,
                     path_str, str(line_no)]
        subprocess.run(raise_cmd, input=finding_body + "\n", text=True, check=True)

    post_cmd = [".meta/say/post", "--role", "reviewer", "review", clean_pr, verdict]
    subprocess.run(post_cmd, input=review_body + "\n", text=True, check=True)
