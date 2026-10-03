"""The agent primitives: Roles and Personas compiled to `agents/` (stereorepo's DR-333).
"""
from __future__ import annotations

import pathlib
from typing import Any

from lib.apm_compile import BANNER, META, instructions


def role_agent(role_id: str, r: dict[str, Any]) -> str:
    """One operational Role's agent file: its remit, its communication style, and write access only where the Role writes."""
    role_slug = role_id.rsplit("/", 1)[-1]
    comm_style = r.get("communication_style", "").strip()

    tools = ["read", "shell"]
    if role_slug == "technical-writer":
        tools.append("write")

    tools_yaml = "\n".join(f"  - {t}" for t in tools)

    lines = [
        "---",
        f"name: {role_slug}",
        "description: >-",
        f"  {r.get('description', '').strip()}",
        "model: inherit",
        "tools:",
        tools_yaml,
        "---",
        "",
        BANNER.format(src="assertions/imported/authority.yaml").strip(),
        "",
        f"# {r.get('name', role_slug).capitalize()} Agent",
        "",
        f"**Role:** {r.get('description', '').strip()}",
        "",
        "## Conversational Communication Register (stereorepo's DR-339)",
        "",
        comm_style,
        "",
        "## Authoring Invariants",
        "",
        "When authoring durable repository files (code docstrings, Decision Records, wiki pages),",
        "follow the Diátaxis quadrant being authored rather than conversational voice.",
    ]
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def persona_agent(p: dict[str, Any]) -> str:
    """One stakeholder Persona's agent file: an interrogation surrogate that reads and never writes (stereorepo's DR-340)."""
    persona_slug = p.get("id", "").rsplit("/", 1)[-1]
    name = p.get("name", persona_slug)
    desc = p.get("description", "").strip()
    context = p.get("context", "").strip()

    lines = [
        "---",
        f"name: {persona_slug}",
        "description: >-",
        f"  {desc} Interrogation surrogate for collaborative product and feature design (stereorepo's DR-340).",
        "model: inherit",
        "tools:",
        "  - read",
        "---",
        "",
        BANNER.format(src="assertions/personas.yaml").strip(),
        "",
        f"# {name} (Interrogation Surrogate)",
        "",
        f"You are assuming the Persona of **{name}** for collaborative product and feature design (stereorepo's DR-340).",
        "Your role is to evaluate design proposals, workflow ergonomics, and UX against your explicit goals and frustrations.",
        "Do NOT behave as a generic agreeable assistant: push back when proposals violate your preferences or create cognitive drag.",
        "",
        "## Worldview & Context",
        "",
        context,
        "",
    ]

    if p.get("persona_goals"):
        lines.extend(["## Goal Hierarchy", ""])
        for g in p["persona_goals"]:
            gtype = g.get("goal_type", "GOAL")
            statement = g.get("statement", "").strip()
            lines.append(f"- **{gtype}:** {statement}")
        lines.append("")

    if p.get("behaviors"):
        lines.extend(["## Characteristic Behaviors", ""])
        for b in p["behaviors"]:
            lines.append(f"- {b.strip()}")
        lines.append("")

    if p.get("frustrations"):
        lines.extend(["## Rejection Boundaries & Frustrations", ""])
        for f in p["frustrations"]:
            lines.append(f"- {f.strip()}")
        lines.append("")

    if p.get("proficiencies"):
        lines.extend(["## Proficiencies", ""])
        for prof in p["proficiencies"]:
            lines.append(f"- {prof.strip()}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def agent_primitives(meta_dir: pathlib.Path = META) -> dict[str, str]:
    """Compiles Roles and Personas into agent primitives (stereorepo's DR-340).

    Two kinds of agent, written into one directory. An operational Role, such as
    the technical writer, carries its own communication style, and is given
    write access only where the Role writes. A stakeholder Persona compiles to an interrogation
    surrogate for collaborative product and feature design (stereorepo's DR-340),
    which reads and never writes.
    """
    authority_file = meta_dir / "assertions" / "imported" / "authority.yaml"
    personas_file = meta_dir / "assertions" / "personas.yaml"

    auth_data = instructions.load_yaml(authority_file) or {}
    personas_data = instructions.load_yaml(personas_file) or {}

    roles = {r["id"]: r for r in auth_data.get("roles") or []}
    out = {}
    for role_id, r in roles.items():
        out[f".apm/agents/{role_id.rsplit('/', 1)[-1]}.agent.md"] = role_agent(role_id, r)
    for p in personas_data.get("personas") or []:
        out[f".apm/agents/{p.get('id', '').rsplit('/', 1)[-1]}.agent.md"] = persona_agent(p)
    return out
