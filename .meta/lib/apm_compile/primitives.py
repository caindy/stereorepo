"""Every primitive a compile writes, by the path it lands on under `.meta/.apm/`, and the two readers of that table: the writer, and the staleness check the gate runs.
"""
from __future__ import annotations

import pathlib

from lib.apm_compile import META, ROOT, agents, bootstrap, harness, instructions, skills


def rendered_primitives(meta_dir: pathlib.Path = META) -> dict[str, str | bytes]:
    """All generated APM primitive paths relative to .meta/, mapped to content."""
    primitives: dict[str, str | bytes] = {}
    primitives["apm.yml"] = instructions.apm_manifest()
    primitives[".apm/instructions/ubiquitous-language.instructions.md"] = instructions.ubiquitous_language_instructions(meta_dir)
    primitives.update(instructions.discipline_instructions(meta_dir))
    primitives.update(agents.agent_primitives(meta_dir))
    primitives.update(skills.skill_primitives(meta_dir))
    primitives.update(skills.hook_primitives())
    primitives.update(bootstrap.python_bootstrap_primitives(meta_dir.parent))
    return primitives


def write_primitives(meta_dir: pathlib.Path = META, root_dir: pathlib.Path = ROOT) -> int:
    """Writes all compiled APM primitives to .meta/.apm/ and reconciles root files."""
    prims = rendered_primitives(meta_dir)
    for rel_path, content in prims.items():
        full_path = meta_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            full_path.write_bytes(content)
        else:
            full_path.write_text(content, encoding="utf-8")

    harness.reconcile_root(root_dir)
    return len(prims)


def check_primitives(meta_dir: pathlib.Path = META, root_dir: pathlib.Path = ROOT) -> list[str]:
    """Checks that on-disk APM primitives match compiled output without drift."""
    stale = []
    prims = rendered_primitives(meta_dir)
    for rel_path, content in prims.items():
        full_path = meta_dir / rel_path
        if not full_path.is_file():
            stale.append(f"{rel_path} is missing")
        elif isinstance(content, bytes):
            if full_path.read_bytes() != content:
                stale.append(f"{rel_path} has drifted from assertions")
        elif full_path.read_text(encoding="utf-8") != content:
            stale.append(f"{rel_path} has drifted from assertions")

    stale.extend(harness.check_root_symlinks(root_dir))
    return stale
