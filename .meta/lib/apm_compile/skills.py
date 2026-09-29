"""The skill and hook primitives: Capabilities of kind SKILL compiled to `skills/`, and the gate as a hook.
"""
from __future__ import annotations

import json
import pathlib
import textwrap

from lib.apm_compile import BANNER, META, instructions


def skill_primitives(meta_dir: pathlib.Path = META) -> dict[str, str]:
    """Compiles Capabilities of kind SKILL and operational skills into skills/ primitives.

    Three sources, each yielding only what the ones before it did not: the
    Capabilities the authority asserts, then the operational skills `render`
    generates, then whatever `.claude/skills/` still holds that neither
    produced. The order is the precedence — an asserted Capability is the
    authority on its own slug — and the mirror exists so that a skill written
    for the harness before it was asserted still reaches the package.
    """
    authority_file = meta_dir / "assertions" / "imported" / "authority.yaml"
    auth_data = instructions.load_yaml(authority_file) or {}
    capabilities = auth_data.get("capability_set") or []
    out = {}

    for cap in capabilities:
        if cap.get("capability_kind") != "SKILL":
            continue
        slug = cap.get("id", "").rsplit("/", 1)[-1]
        desc = cap.get("description", "").strip()

        lines = [
            "---",
            f"name: {slug}",
            "description: >-",
            *["  " + line for line in textwrap.wrap(desc.splitlines()[0], 76)],
            "---",
            "",
            BANNER.format(src="assertions/imported/authority.yaml").strip(),
            "",
            f"# /{slug}",
            "",
            desc,
            "",
        ]
        out[f".apm/skills/{slug}/SKILL.md"] = "\n".join(lines).strip() + "\n"

    try:
        import render
        skill_gens = {
            "wikisplain": render.wikisplain_skill,
            "search": render.search_skill,
            "technical-writing": render.technical_writing_skill,
        }
        for name, gen_fn in skill_gens.items():
            rel_path = f".apm/skills/{name}/SKILL.md"
            if rel_path not in out:
                content = gen_fn()
                if content:
                    out[rel_path] = content
    except Exception:  # noqa: BLE001  # reason: best effort — the three generators read Artifacts and templates a specialization can leave absent, and a clone missing one gets the other primitives rather than an aborted compile
        pass

    claude_skills = meta_dir.parent / ".claude" / "skills"
    if claude_skills.is_dir():
        for skill_dir in sorted(claude_skills.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if skill_md.is_file():
                rel_path = f".apm/skills/{skill_dir.name}/SKILL.md"
                if rel_path not in out:
                    out[rel_path] = skill_md.read_text(encoding="utf-8")

    return out


def hook_primitives() -> dict[str, str]:
    """Compiles the gate into a Stop hook primitive."""
    gate_hook = {
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "$CLAUDE_PROJECT_DIR/.meta/gate",
                    }
                ]
            }
        ]
    }

    return {
        ".apm/hooks/gate.json": json.dumps(gate_hook, indent=2) + "\n",
    }
