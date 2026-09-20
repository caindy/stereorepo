"""What a run was routed to and why: the model the reviewer ran, the difficulty of the Challenge it served, and the control-plane boundary a change crossed (solorepo's DR-188).
"""
import json
import re
import subprocess
from typing import Any

from depth import CONTROL_PLANE

BOUNDARY_PATTERN = re.compile("^(" + "|".join(re.escape(prefix) for prefix in CONTROL_PLANE) + ")")
"""Matches a repository-relative path inside the control plane, as `depth.CONTROL_PLANE` lists it:
under `.meta/lib/`, the initialiser and the packages of control-plane scripts (solorepo's DR-219)."""
DIFFICULTY_CACHE: dict[str, str] = {}


def model_of(run: dict[str, Any]) -> str:
    """Infers the model family ('opus' vs 'sonnet') used for a review workflow run.

    Args:
        run: Workflow run dictionary containing headSha commit ref.

    Returns:
        str: 'opus', 'sonnet', or 'unknown'.
    """
    sha = run.get("headSha")
    if not sha:
        return "unknown"
    res = subprocess.run(["git", "diff", "--name-only", f"origin/main...{sha}"],
                         capture_output=True, text=True)
    if res.returncode != 0 or not res.stdout.strip():
        res = subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
                             capture_output=True, text=True)
    if res.returncode == 0 and res.stdout.strip():
        if any(BOUNDARY_PATTERN.search(f) for f in res.stdout.splitlines()):
            return "opus"
        return "sonnet"
    return "unknown"


ISSUE_DIFF_BY_NUM: dict[str, str] = {}
ISSUE_DIFF_BY_TITLE: dict[str, str] = {}
ISSUES_FETCHED = False


def _ensure_issues_loaded() -> None:
    global ISSUES_FETCHED
    if ISSUES_FETCHED:
        return
    res = subprocess.run(["gh", "issue", "list", "--state", "all", "--limit", "300", "--json", "number,title,labels"],
                         capture_output=True, text=True)
    if res.returncode == 0:
        try:
            for item in json.loads(res.stdout):
                diff = "unknown"
                for lbl in item.get("labels", []):
                    if lbl.get("name") in ("easy", "medium", "hard", "human"):
                        diff = lbl["name"]
                        break
                ISSUE_DIFF_BY_NUM[str(item["number"])] = diff
                ISSUE_DIFF_BY_TITLE[item.get("title", "").strip().lower()] = diff
        except Exception:
            pass
    ISSUES_FETCHED = True


def difficulty_of(run: dict[str, Any]) -> str:
    """Determines challenge difficulty label associated with a workflow run.

    Args:
        run: Workflow run dictionary.

    Returns:
        str: Difficulty label ('easy', 'medium', 'hard', 'human', or 'unknown').

    The run's head branch names its Issue, and the label is read from there. A
    run whose head branch is `main` — an `issues: labeled` trigger, or a
    `workflow_dispatch` — names no Issue that way, so the number is taken from
    its display title instead, and failing that the title is matched against
    the Issue titles the run listing carries.
    """
    branch = str(run.get("headBranch") or "")
    m = re.search(r"issue-(\d+)", branch)
    if m:
        issue_num = m.group(1)
        if issue_num in DIFFICULTY_CACHE:
            return DIFFICULTY_CACHE[issue_num]
        _ensure_issues_loaded()
        diff = ISSUE_DIFF_BY_NUM.get(issue_num)
        if not diff or diff == "unknown":
            res = subprocess.run(["gh", "issue", "view", issue_num, "--json", "labels"],
                                 capture_output=True, text=True)
            if res.returncode == 0:
                try:
                    data = json.loads(res.stdout)
                    labels = {lbl.get("name") for lbl in data.get("labels", [])}
                    for cand in ("easy", "medium", "hard", "human"):
                        if cand in labels:
                            diff = cand
                            break
                except Exception:
                    pass
        diff = diff or "unknown"
        DIFFICULTY_CACHE[issue_num] = diff
        return diff

    title = str(run.get("displayTitle") or "").strip()
    if title:
        m = re.search(r"#(\d+)", title)
        if m:
            return difficulty_of({"headBranch": f"claude/issue-{m.group(1)}"})
        _ensure_issues_loaded()
        if title.lower() in ISSUE_DIFF_BY_TITLE:
            return ISSUE_DIFF_BY_TITLE[title.lower()]

    return "unknown"


def stratify_run(workflow: str, run: dict[str, Any], stratify: str | None) -> str | None:
    """Categorizes a workflow run by model or difficulty when requested.

    Args:
        workflow: Workflow filename.
        run: Workflow run dictionary.
        stratify: Grouping dimension ('model' or 'difficulty').

    Returns:
        str | None: Category tag or None.
    """
    if stratify == "model" and workflow == "review.yml":
        return model_of(run)
    if stratify == "difficulty" and workflow in ("review.yml", "coder.yml"):
        return difficulty_of(run)
    return None
