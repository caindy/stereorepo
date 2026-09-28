"""The harness roots reconciled: `CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md` as symlinks to `AGENTS.md`, and the skills every harness finds in the same place (stereorepo's DR-201).
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess

from lib.apm_compile import META, ROOT


def check_root_symlinks(root_dir: pathlib.Path = ROOT) -> list[str]:
    """Checks that root harness documentation symlinks point to AGENTS.md (stereorepo's DR-172)."""
    problems = []
    agents_md = root_dir / "AGENTS.md"
    claude_md = root_dir / "CLAUDE.md"
    gemini_md = root_dir / "GEMINI.md"
    copilot_md = root_dir / ".github" / "copilot-instructions.md"

    if not agents_md.is_file():
        problems.append("AGENTS.md is missing from repository root")
        return problems

    for link_path in (claude_md, gemini_md, copilot_md):
        display = (link_path.name if link_path.parent == root_dir
                   else str(link_path.relative_to(root_dir)))
        if not link_path.is_symlink():
            problems.append(f"{display} is not a symlink to AGENTS.md")
        else:
            try:
                target = link_path.resolve()
                if target != agents_md.resolve():
                    problems.append(f"{display} resolves to {target}, expected {agents_md}")
            except OSError as e:
                problems.append(f"{display} broken symlink: {e}")

    return problems


def reconcile_root(root_dir: pathlib.Path = ROOT) -> list[str]:
    """Reconciles harness root files ensuring AGENTS.md single-source invariance (stereorepo's DR-172).

    `CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md` are
    symlinks to `AGENTS.md` and this restores them as such, including where one
    has been replaced by a regular file: an external compiler that writes its
    own copy is the way that happens, and a copy is the drift the symlink exists
    to rule out.
    """
    actions = []
    agents_md = root_dir / "AGENTS.md"
    claude_md = root_dir / "CLAUDE.md"
    gemini_md = root_dir / "GEMINI.md"
    copilot_md = root_dir / ".github" / "copilot-instructions.md"

    if not agents_md.is_file():
        actions.append("ERROR: AGENTS.md is missing from repository root")
        return actions

    for link_path in (claude_md, gemini_md, copilot_md):
        display = (link_path.name if link_path.parent == root_dir
                   else str(link_path.relative_to(root_dir)))
        rel_target = os.path.relpath(agents_md, link_path.parent)
        if link_path.is_symlink():
            target = link_path.resolve()
            if target != agents_md.resolve():
                link_path.unlink()
                link_path.symlink_to(rel_target)
                actions.append(f"Fixed symlink {display} -> {rel_target}")
        elif link_path.exists():
            link_path.unlink()
            link_path.symlink_to(rel_target)
            actions.append(f"Restored symlink {display} -> {rel_target} from file")
        else:
            link_path.parent.mkdir(parents=True, exist_ok=True)
            link_path.symlink_to(rel_target)
            actions.append(f"Created symlink {display} -> {rel_target}")

    meta_path = root_dir / ".meta"
    if not meta_path.is_dir():
        meta_path = META
    actions.extend(reconcile_harnesses(meta_path, root_dir))

    return actions


def reconcile_harnesses(meta_dir: pathlib.Path = META, root_dir: pathlib.Path = ROOT) -> list[str]:
    """Projects single-source APM cognitive assets to multi-harness target directories (stereorepo's DR-172, stereorepo's DR-201, solorepo's #430, solorepo's #1075).

    When Microsoft APM CLI is present, invokes `apm install ./.meta --target antigravity,codex`
    to deploy skills, agents, and hooks into `.agents/` and `.codex/`.
    When APM CLI is absent, projects `.meta/.apm/skills/` into `.agents/skills/` directly.
    """
    actions = []
    apm_bin = shutil.which("apm")
    if apm_bin:
        res = subprocess.run(
            [apm_bin, "install", "./.meta", "--target", "antigravity,codex"],
            check=False, cwd=str(root_dir),
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            actions.append("Materialized multi-harness cognitive assets via APM CLI (.agents/, .codex/)")
            return actions

    src_skills = meta_dir / ".apm" / "skills"
    dest_skills = root_dir / ".agents" / "skills"
    if src_skills.is_dir():
        dest_skills.mkdir(parents=True, exist_ok=True)
        for item in sorted(src_skills.iterdir()):
            if not item.is_dir():
                continue
            dest_skill_dir = dest_skills / item.name
            shutil.copytree(item, dest_skill_dir, dirs_exist_ok=True)
        actions.append("Projected skills from .meta/.apm/skills/ into .agents/skills/")

    return actions
