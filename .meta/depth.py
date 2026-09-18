#!/usr/bin/env python3
"""Review depth evaluation for pull requests and specialized portfolios (solorepo's DR-188).

Decides the model, effort, turns, minutes, and agent fan-out ceiling for a
pull request review, replacing inline workflow conditionals with a 4-layer
template method pipeline:

1. **Scaffold Invariant (Hard Baseline):** Changes to the agent harness control
   plane (`.meta/say`, `.meta/hooks`, `.claude`, `.github/workflows`, `check_pr.py`)
   unconditionally trigger the deep path (Opus, high effort, 45m, 3 agents).
2. **Declarative Assertions (Portfolio Extensions):** Matches modified files
   against `critical_paths` asserted on Projects in `structure.yaml`. Matching
   files trigger the deep path (or project-configured tier).
3. **Programmatic Hook (Custom Heuristics):** If `.meta/hooks/depth.py` exists,
   it is invoked with `(pr_meta, files, diff_patch)` to allow dynamic AST or
   metadata-driven depth decisions.
4. **Standard Default:** All other changes receive the standard review tier
   (Sonnet, medium effort, 15m, 1 agent).

Usage:
    python3 .meta/depth.py <pr-number>               # evaluated from GitHub PR diff
    python3 .meta/depth.py --files file1,file2       # evaluated from explicit file list
    python3 .meta/depth.py --files - < files.txt     # evaluated from stdin
"""
from __future__ import annotations

import argparse
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
"""The path prefixes of the control plane: the channel, the hooks, the pull request gate, and the
bodies of the gate and the hooks under `.meta/lib/`, the settings that register them, the instructions every session loads
before it reads anything, and the workflows. A change under one is routed to the deepest review
(Layer 1 of the template method) and `.meta/timing.py` reports it as the critical path.
`.github/workflows/review.yml` restores every prefix but the workflows' from trunk before a
reviewer reads anything, and the gate step `control plane restore` holds each statement of that
set in the workflow to this one. Under `.meta/lib/`, the initialiser is always named, and a
package is named when the script it is the body of is: trunk's `check_pr.py` imports its package
through `lib/__init__.py`, so the initialiser is module-level code trunk's gate executes, and the
restore is no-overlay, so a package restored wholesale deletes the body a pull request adds for a
script outside the envelope (solorepo's DR-219)."""
SCAFFOLD_BOUNDARY = re.compile("^(" + "|".join(re.escape(prefix) for prefix in CONTROL_PLANE) + ")")
"""Matches a repository-relative path inside the control plane."""


class DepthConfig(NamedTuple):
    """The reviewer parameters chosen by the depth pipeline."""

    model: str
    gemini_model: str
    effort: str
    turns: int
    minutes: int
    agents: int
    reason: str

    def to_github_output(self) -> str:
        """Formats the configuration as key=value lines for $GITHUB_OUTPUT."""
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
    """Loads declared projects from structure.yaml, handling pyyaml or minimal fallback.

    The fallback reads `critical_paths` and nothing else, by indentation, and
    exists because this tool runs in the review workflow's container before any
    dependency is installed. A project's other slots are not read there, so the
    parser that would read them is not written.
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
    """Normalizes relative path by stripping leading './' while preserving leading dot in directory names."""
    p = path.strip()
    if p.startswith("./"):
        p = p[2:]
    return p


def check_scaffold_boundary(files: list[str]) -> DepthConfig | None:
    """Layer 1: Verifies whether any file touches the scaffold harness security boundary."""
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
    """Layer 2: Verifies whether any file matches critical_paths declared on projects."""
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
    """Layer 3: Executes custom heuristic callback in .meta/hooks/depth.py if present."""
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
    except Exception as err:
        print(f"depth: error executing programmatic hook {hook_file}: {err}", file=sys.stderr)
    return None


def evaluate(
    files: list[str],
    pr_meta: dict[str, Any] | None = None,
    diff_patch: str = "",
    structure_file: pathlib.Path = STRUCTURE_PATH,
    hook_file: pathlib.Path = HOOK_PATH,
) -> DepthConfig:
    """Executes the 4-layer template method pipeline over a list of changed files.

    The layers answer in order and the first that answers wins, so the scaffold
    boundary cannot be talked out of deep review by an assertion or a hook
    beneath it: the invariant boundary, then the `critical_paths` a project
    declares, then the portfolio's own hook, then the standard default.
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


def resolve_files_for_pr(pr: str, repo: str | None = None) -> tuple[list[str], dict[str, Any], str]:
    """Resolves changed files and metadata for a pull request, accounting for re-reviews.

    The metadata — labels, title and author — is what a portfolio's programmatic
    hook is given to judge on, and a read of it that fails leaves the number and
    the repository alone rather than stopping the evaluation: a hook that sees
    less falls through to the layer beneath it.
    """
    repo_target = repo or os.environ.get("GITHUB_REPOSITORY")
    if not repo_target:
        try:
            out = subprocess.check_output(
                ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                text=True,
            ).strip()
            if out:
                repo_target = out
        except Exception:
            pass

    owner, _, repo_name = (repo_target or "").partition("/")
    reviewer_login = f"{owner}-{repo_name}-reviewer" if owner and repo_name else None

    last_verdict_head = None
    if reviewer_login and repo_target:
        try:
            cmd = [
                "gh",
                "api",
                f"repos/{repo_target}/pulls/{pr}/reviews?per_page=100",
                "--paginate",
                "--jq",
                f'[.[] | select(.user.login == "{reviewer_login}") | '
                'select(.state != "COMMENTED" or (.body // "") != "")] | last | .commit_id',
            ]
            head = subprocess.check_output(cmd, text=True).strip()
            if head and head != "null":
                last_verdict_head = head
        except Exception as err:
            print(f"depth: notice: could not query prior reviews for {reviewer_login}: {err}", file=sys.stderr)

    incremental = False
    if last_verdict_head:
        ret = subprocess.run(["git", "cat-file", "-e", last_verdict_head], capture_output=True)
        if ret.returncode == 0:
            incremental = True

    files: list[str] = []
    if incremental and last_verdict_head:
        print(f"depth: checking incremental delta diff since last verdict head: {last_verdict_head}", file=sys.stderr)
        try:
            diff_out = subprocess.check_output(["git", "diff", "--name-only", last_verdict_head, "HEAD"], text=True)
            files = [line.strip() for line in diff_out.splitlines() if line.strip()]
        except Exception as err:
            print(f"depth: git diff incremental failed ({err}); falling back to cumulative PR files", file=sys.stderr)
            incremental = False

    if not incremental:
        print("depth: checking cumulative PR files", file=sys.stderr)
        view_cmd = ["gh", "pr", "view", pr]
        if repo_target:
            view_cmd.extend(["--repo", repo_target])
        view_cmd.extend(["--json", "files", "-q", ".files[].path"])
        out = subprocess.check_output(view_cmd, text=True)
        files = [line.strip() for line in out.splitlines() if line.strip()]

    meta: dict[str, Any] = {"number": pr, "repo": repo_target, "incremental": incremental}
    try:
        meta_cmd = ["gh", "pr", "view", pr]
        if repo_target:
            meta_cmd.extend(["--repo", repo_target])
        meta_cmd.extend(["--json", "labels,title,author", "-q", "."])
        meta_raw = subprocess.check_output(meta_cmd, text=True)
        meta.update(json.loads(meta_raw))
    except Exception:
        pass

    return files, meta, ""


def main(argv: list[str]) -> int:
    """CLI entrypoint for depth evaluation."""
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
