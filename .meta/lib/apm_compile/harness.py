"""The harness roots reconciled: `CLAUDE.md` and `GEMINI.md` as symlinks to `AGENTS.md`, and the skills every harness finds in the same place (solorepo's DR-201).
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

from lib.apm_compile import META, ROOT


def check_root_symlinks(root_dir: pathlib.Path = ROOT) -> list[str]:
    """Checks that root harness documentation symlinks point to AGENTS.md (solorepo's DR-172)."""
    problems = []
    agents_md = root_dir / "AGENTS.md"
    claude_md = root_dir / "CLAUDE.md"
    gemini_md = root_dir / "GEMINI.md"

    if not agents_md.is_file():
        problems.append("AGENTS.md is missing from repository root")
        return problems

    for link_path in (claude_md, gemini_md):
        if not link_path.is_symlink():
            problems.append(f"{link_path.name} is not a symlink to AGENTS.md")
        else:
            try:
                target = link_path.resolve()
                if target != agents_md.resolve():
                    problems.append(f"{link_path.name} resolves to {target}, expected {agents_md}")
            except Exception as e:
                problems.append(f"{link_path.name} broken symlink: {e}")

    return problems


def reconcile_root(root_dir: pathlib.Path = ROOT) -> list[str]:
    """Reconciles harness root files ensuring AGENTS.md single-source invariance (solorepo's DR-172).

    `CLAUDE.md` and `GEMINI.md` are symlinks to `AGENTS.md` and this restores
    them as such, including where one has been replaced by a regular file: an
    external compiler that writes its own copy is the way that happens, and a
    copy is the drift the symlink exists to rule out.
    """
    actions = []
    agents_md = root_dir / "AGENTS.md"
    claude_md = root_dir / "CLAUDE.md"
    gemini_md = root_dir / "GEMINI.md"

    if not agents_md.is_file():
        actions.append("ERROR: AGENTS.md is missing from repository root")
        return actions

    for link_path in (claude_md, gemini_md):
        if link_path.is_symlink():
            target = link_path.resolve()
            if target != agents_md.resolve():
                link_path.unlink()
                link_path.symlink_to("AGENTS.md")
                actions.append(f"Fixed symlink {link_path.name} -> AGENTS.md")
        elif link_path.exists():
            link_path.unlink()
            link_path.symlink_to("AGENTS.md")
            actions.append(f"Restored symlink {link_path.name} -> AGENTS.md from file")
        else:
            link_path.symlink_to("AGENTS.md")
            actions.append(f"Created symlink {link_path.name} -> AGENTS.md")

    meta_path = root_dir / ".meta"
    if not meta_path.is_dir():
        meta_path = META
    actions.extend(reconcile_harnesses(meta_path, root_dir))

    return actions


def reconcile_harnesses(meta_dir: pathlib.Path = META, root_dir: pathlib.Path = ROOT) -> list[str]:
    """Projects single-source APM cognitive assets to multi-harness target directories (solorepo's DR-172, solorepo's DR-201, solorepo's #430).

    When Microsoft APM CLI is present, invokes `apm install ./.meta --target antigravity,codex,gemini`
    to deploy skills, agents, and hooks into `.agents/`, `.gemini/`, and `.codex/`.
    When APM CLI is absent, projects `.meta/.apm/skills/` into `.agents/skills/` directly.
    """
    actions = []
    apm_bin = shutil.which("apm")
    if apm_bin:
        res = subprocess.run(
            [apm_bin, "install", "./.meta", "--target", "antigravity,codex,gemini"],
            cwd=str(root_dir),
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            actions.append("Materialized multi-harness cognitive assets via APM CLI (.agents/, .gemini/, .codex/)")
            return actions

    src_skills = meta_dir / ".apm" / "skills"
    dest_skills = root_dir / ".agents" / "skills"
    if src_skills.is_dir():
        dest_skills.mkdir(parents=True, exist_ok=True)
        for item in sorted(src_skills.iterdir()):
            if not item.is_dir():
                continue
            dest_skill_dir = dest_skills / item.name
            dest_skill_dir.mkdir(parents=True, exist_ok=True)
            for skill_file in item.iterdir():
                if skill_file.is_file():
                    target_file = dest_skill_dir / skill_file.name
                    target_file.write_bytes(skill_file.read_bytes())
        actions.append("Projected skills from .meta/.apm/skills/ into .agents/skills/")

    return actions
