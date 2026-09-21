#!/usr/bin/env python3
"""Review depth evaluation pipeline for pull requests and specialized portfolios.

Determines model tier, reasoning effort, agent turn budget, execution timeout,
and concurrent subagent fan-out ceiling across four evaluation layers (solorepo's DR-188,
solorepo's DR-219):
scaffold control plane invariants, declared project critical paths, programmatic hooks,
and standard defaults.

History in depth.history.md (solorepo's DR-171).
"""
from __future__ import annotations

import argparse
import contextlib
import fnmatch
import importlib.machinery
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any, NamedTuple

META = pathlib.Path(__file__).resolve().parent
ROOT = META.parent
STRUCTURE_PATH = META / "assertions" / "structure.yaml"
HOOK_PATH = META / "hooks" / "depth.py"

CONTROL_PLANE: tuple[str, ...] = (
    ".meta/say", ".meta/hooks/", ".meta/check_pr.py", ".meta/lib/__init__.py", ".meta/lib/check_pr/",
    ".meta/lib/worktree_only/", ".meta/lib/signed_channel/",
    ".claude/", "AGENTS.md", "CLAUDE.md", "GEMINI.md", ".github/workflows/",
)
"""Path prefixes defining the agent harness control plane and security boundary (solorepo's DR-219)."""
SCAFFOLD_BOUNDARY = re.compile("^(" + "|".join(re.escape(prefix) for prefix in CONTROL_PLANE) + ")")
"""Matches a repository-relative path inside the control plane."""


class DepthConfig(NamedTuple):
    """Reviewer runtime parameters determined by depth evaluation.

    Attributes:
        model: Claude model name to dispatch.
        gemini_model: Gemini model name for fallback passes.
        effort: Reasoning effort level ('high' or 'medium').
        turns: Maximum turn limit for the reviewer agent.
        minutes: Execution timeout in minutes.
        agents: Maximum concurrent subagent fan-out ceiling.
        reason: Explanation justifying the selected review tier.
    """

    model: str
    gemini_model: str
    effort: str
    turns: int
    minutes: int
    agents: int
    reason: str

    def to_github_output(self) -> str:
        """Formats the configuration as key=value lines for $GITHUB_OUTPUT.

        Returns:
            str: Multi-line string formatted for GitHub Actions step output.
        """
        return (
            f"model={self.model}\n"
            f"gemini_model={self.gemini_model}\n"
            f"effort={self.effort}\n"
            f"turns={self.turns}\n"
            f"minutes={self.minutes}\n"
            f"agents={self.agents}\n"
            f"reason={self.reason}\n"
        )


DEEP_CONFIG = DepthConfig(
    model="claude-opus-5",
    gemini_model="gemini-3.8-flash",
    effort="high",
    turns=120,
    minutes=45,
    agents=3,
    reason="deep path",
)

STANDARD_CONFIG = DepthConfig(
    model="claude-sonnet-5",
    gemini_model="gemini-3.8-flash",
    effort="medium",
    turns=120,
    minutes=15,
    agents=1,
    reason="standard path",
)


def load_structure_projects(structure_file: pathlib.Path = STRUCTURE_PATH) -> list[dict[str, Any]]:
    """Loads declared projects from structure.yaml with minimal fallback parser.

    Args:
        structure_file: Path to structure.yaml definition.

    Returns:
        list[dict[str, Any]]: Project dictionaries with 'id' and 'critical_paths'.
    """
    if not structure_file.is_file():
        return []
    text = structure_file.read_text(encoding="utf-8")
    try:
        import yaml
        data = yaml.safe_load(text) or {}
        return list(data.get("projects") or [])
    except ImportError:
        projects = []
        curr_project: dict[str, Any] | None = None
        in_critical_paths = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- id:"):
                if curr_project:
                    projects.append(curr_project)
                curr_project = {"id": stripped.split(":", 1)[1].strip(), "critical_paths": []}
                in_critical_paths = False
            elif curr_project and stripped.startswith("critical_paths:"):
                in_critical_paths = True
            elif curr_project and in_critical_paths:
                if stripped.startswith("- "):
                    path_glob = stripped[2:].strip().strip("\"'")
                    curr_project["critical_paths"].append(path_glob)
                elif stripped and not stripped.startswith("#"):
                    in_critical_paths = False
        if curr_project:
            projects.append(curr_project)
        return projects


def normalize_path(path: str) -> str:
    """Normalizes a file path by stripping leading './' prefixes.

    Args:
        path: Path string to normalize.

    Returns:
        str: Normalized repository-relative path string.
    """
    p = path.strip()
    if p.startswith("./"):
        p = p[2:]
    return p


def check_scaffold_boundary(files: list[str]) -> DepthConfig | None:
    """Evaluates Layer 1: checks if modified files touch harness control plane paths.

    Args:
        files: List of repository-relative file paths.

    Returns:
        DepthConfig | None: Deep review configuration if a control plane path matched, else None.
    """
    for path in files:
        norm = normalize_path(path)
        if SCAFFOLD_BOUNDARY.search(norm):
            return DepthConfig(
                model=DEEP_CONFIG.model,
                gemini_model=DEEP_CONFIG.gemini_model,
                effort=DEEP_CONFIG.effort,
                turns=DEEP_CONFIG.turns,
                minutes=DEEP_CONFIG.minutes,
                agents=DEEP_CONFIG.agents,
                reason=f"scaffold boundary: {path}",
            )
    return None


def check_declarative_assertions(files: list[str], projects: list[dict[str, Any]]) -> DepthConfig | None:
    """Evaluates Layer 2: matches files against declared project critical_paths.

    Args:
        files: List of repository-relative file paths.
        projects: List of declared project configurations from structure.yaml.

    Returns:
        DepthConfig | None: Deep review configuration if a declared critical path matched, else None.
    """
    for proj in projects:
        proj_id = proj.get("id", "project")
        critical_globs = proj.get("critical_paths") or []
        for pat in critical_globs:
            for path in files:
                norm = normalize_path(path)
                if fnmatch.fnmatch(norm, pat) or fnmatch.fnmatch(path, pat):
                    return DepthConfig(
                        model=DEEP_CONFIG.model,
                        gemini_model=DEEP_CONFIG.gemini_model,
                        effort=DEEP_CONFIG.effort,
                        turns=DEEP_CONFIG.turns,
                        minutes=DEEP_CONFIG.minutes,
                        agents=DEEP_CONFIG.agents,
                        reason=f"declared critical path: {proj_id} ({pat})",
                    )
    return None


def check_programmatic_hook(
    pr_meta: dict[str, Any],
    files: list[str],
    diff_patch: str,
    hook_file: pathlib.Path = HOOK_PATH,
) -> DepthConfig | None:
    """Evaluates Layer 3: executes custom heuristic hook in .meta/hooks/depth.py.

    Args:
        pr_meta: Pull request metadata mapping (labels, title, author).
        files: List of modified file paths.
        diff_patch: Unified diff string of the pull request changes.
        hook_file: Path to the depth hook script.

    Returns:
        DepthConfig | None: Custom DepthConfig if returned by hook, else None.
    """
    if not hook_file.is_file():
        return None
    try:
        loader = importlib.machinery.SourceFileLoader("custom_depth_hook", str(hook_file))
        spec = importlib.util.spec_from_file_location("custom_depth_hook", hook_file, loader=loader)
        if not spec or not spec.loader:
            return None
        hook_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hook_mod)
        if not hasattr(hook_mod, "evaluate_depth"):
            return None
        res = hook_mod.evaluate_depth(pr_meta, files, diff_patch)
        if isinstance(res, DepthConfig):
            return res
        if hasattr(res, "_asdict") and callable(res._asdict):
            res = res._asdict()
        elif hasattr(res, "__dict__") and not isinstance(res, dict):
            res = res.__dict__
        if isinstance(res, dict):
            return DepthConfig(
                model=res.get("model", DEEP_CONFIG.model),
                gemini_model=res.get("gemini_model", DEEP_CONFIG.gemini_model),
                effort=res.get("effort", DEEP_CONFIG.effort),
                turns=int(res.get("turns", DEEP_CONFIG.turns)),
                minutes=int(res.get("minutes", DEEP_CONFIG.minutes)),
                agents=int(res.get("agents", DEEP_CONFIG.agents)),
                reason=res.get("reason", "programmatic hook"),
            )
    except Exception as err:  # noqa: BLE001  # reason: a portfolio's depth hook is arbitrary code loaded from its own tree, and a broken one falls back to the declared depth rather than stopping the review
        print(f"depth: error executing programmatic hook {hook_file}: {err}", file=sys.stderr)
    return None


def evaluate(
    files: list[str],
    pr_meta: dict[str, Any] | None = None,
    diff_patch: str = "",
    structure_file: pathlib.Path = STRUCTURE_PATH,
    hook_file: pathlib.Path = HOOK_PATH,
) -> DepthConfig:
    """Evaluates the 4-layer template method pipeline over modified files.

    Args:
        files: List of modified file paths in the change.
        pr_meta: Optional pull request metadata dictionary.
        diff_patch: Optional unified diff patch text.
        structure_file: Path to structure.yaml definition.
        hook_file: Path to custom depth hook script.

    Returns:
        DepthConfig: Selected reviewer execution configuration.
    """
    meta = pr_meta or {}

    cfg = check_scaffold_boundary(files)
    if cfg:
        return cfg

    projects = load_structure_projects(structure_file)
    cfg = check_declarative_assertions(files, projects)
    if cfg:
        return cfg

    cfg = check_programmatic_hook(meta, files, diff_patch, hook_file)
    if cfg:
        return cfg

    return STANDARD_CONFIG


def repo_target(repo: str | None = None) -> str | None:
    """Resolves target GitHub repository slug as owner/repo.

    Args:
        repo: Optional repository slug override.

    Returns:
        str | None: Repository slug, or None if unresolved.
    """
    target = repo or os.environ.get("GITHUB_REPOSITORY")
    if target:
        return target
    try:
        out = subprocess.check_output(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return out or None


def last_verdict_head(pr: str, target: str | None) -> str | None:
    """Retrieves the commit SHA evaluated by the reviewer Role's latest verdict.

    Args:
        pr: Pull request number.
        target: Repository slug as owner/repo.

    Returns:
        str | None: Commit SHA if found, or None if no prior review verdict exists.
    """
    owner, _, repo_name = (target or "").partition("/")
    if not (owner and repo_name):
        return None
    reviewer_login = f"{owner}-{repo_name}-reviewer"
    try:
        head = subprocess.check_output([
            "gh", "api", f"repos/{target}/pulls/{pr}/reviews?per_page=100", "--paginate", "--jq",
            f'[.[] | select(.user.login == "{reviewer_login}") | '
            'select(.state != "COMMENTED" or (.body // "") != "")] | last | .commit_id',
        ], text=True).strip()
    except (OSError, subprocess.CalledProcessError) as err:
        print(f"depth: notice: could not query prior reviews for {reviewer_login}: {err}", file=sys.stderr)
        return None
    return head if head and head != "null" else None


def incremental_files(head: str | None) -> list[str] | None:
    """Computes file paths changed since the specified commit SHA.

    Args:
        head: Base commit SHA of previous review verdict.

    Returns:
        list[str] | None: List of changed file paths, or None if head commit is inaccessible.
    """
    if not head or subprocess.run(["git", "cat-file", "-e", head], check=False, capture_output=True).returncode != 0:
        return None
    print(f"depth: checking incremental delta diff since last verdict head: {head}", file=sys.stderr)
    try:
        diff_out = subprocess.check_output(["git", "diff", "--name-only", head, "HEAD"], text=True)
    except (OSError, subprocess.CalledProcessError) as err:
        print(f"depth: git diff incremental failed ({err}); falling back to cumulative PR files", file=sys.stderr)
        return None
    return [line.strip() for line in diff_out.splitlines() if line.strip()]


def pull_view(pr: str, target: str | None, fields: str, query: str) -> str:
    """Queries GitHub CLI for pull request metadata fields.

    Args:
        pr: Pull request number.
        target: Optional repository slug.
        fields: Comma-separated list of JSON field names.
        query: JQ extraction query.

    Returns:
        str: Raw output string from gh pr view.
    """
    cmd = ["gh", "pr", "view", pr]
    if target:
        cmd.extend(["--repo", target])
    cmd.extend(["--json", fields, "-q", query])
    return subprocess.check_output(cmd, text=True)


def resolve_files_for_pr(pr: str, repo: str | None = None) -> tuple[list[str], dict[str, Any], str]:
    """Resolves changed files and review metadata for a pull request.

    Args:
        pr: Pull request number.
        repo: Optional repository slug.

    Returns:
        tuple: (changed_files, pr_metadata, diff_patch).
    """
    target = repo_target(repo)
    files = incremental_files(last_verdict_head(pr, target))
    incremental = files is not None
    if files is None:
        print("depth: checking cumulative PR files", file=sys.stderr)
        out = pull_view(pr, target, "files", ".files[].path")
        files = [line.strip() for line in out.splitlines() if line.strip()]

    meta: dict[str, Any] = {"number": pr, "repo": target, "incremental": incremental}
    with contextlib.suppress(Exception):
        meta.update(json.loads(pull_view(pr, target, "labels,title,author", ".")))
    return files, meta, ""


def main(argv: list[str]) -> int:
    """CLI entrypoint for evaluating review depth.

    Args:
        argv: Command-line arguments starting with the script name.

    Returns:
        int: Exit status code (0 on success, 2 on missing arguments).
    """
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pr", nargs="?", help="Pull request number to evaluate")
    parser.add_argument("--files", help="Comma-separated list of files, or '-' to read from stdin")
    parser.add_argument("--repo", help="Optional owner/repo slug when querying GitHub")
    parser.add_argument("--json", action="store_true", help="Output result as JSON instead of GITHUB_OUTPUT format")

    args = parser.parse_args(argv[1:])

    files: list[str] = []
    pr_meta: dict[str, Any] = {}
    diff_patch = ""

    if args.files:
        if args.files == "-":
            files = [line.strip() for line in sys.stdin if line.strip()]
        else:
            files = [f.strip() for f in args.files.split(",") if f.strip()]
    elif args.pr:
        files, pr_meta, diff_patch = resolve_files_for_pr(args.pr, repo=args.repo)
    else:
        env_pr = os.environ.get("PR")
        if env_pr:
            files, pr_meta, diff_patch = resolve_files_for_pr(env_pr, repo=args.repo)
        else:
            parser.print_help(file=sys.stderr)
            return 2

    config = evaluate(files, pr_meta=pr_meta, diff_patch=diff_patch)

    if args.json:
        print(json.dumps(config._asdict(), indent=2))
    else:
        sys.stdout.write(config.to_github_output())

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
