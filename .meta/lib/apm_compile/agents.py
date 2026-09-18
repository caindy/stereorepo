"""The agent primitives: Roles, Personalities and Personas compiled to `agents/` (solorepo's DR-173).
"""
from __future__ import annotations

import pathlib

from lib.apm_compile import BANNER, META, instructions


def role_agent(role_id: str, r: dict, personalities: dict) -> str:
    """One operational Role's agent file: its remit, the communication style of the Personality sharing its slug, and write access only where the Role writes."""
    role_slug = role_id.rsplit("/", 1)[-1]
    personality_id = f"work:personality/{role_slug}"
    personality = personalities.get(personality_id) or {}
    comm_style = personality.get("communication_style", "").strip()

    tools = ["read", "shell"]
    if role_slug in ("coder", "technical-writer"):
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
        BANNER.format(src="assertions/imported/authority.yaml and actors.yaml").strip(),
        "",
        f"# {r.get('name', role_slug).capitalize()} Agent",
        "",
        f"**Role Remit:** {r.get('description', '').strip()}",
        "",
        "## Conversational Communication Register (solorepo's DR-198, solorepo's DR-199)",
        "",
        comm_style,
        "",
        "## Authoring Invariants",
        "",
        "When authoring durable repository files (code docstrings, Decision Records, wiki pages),",
        "follow the Diátaxis quadrant being authored rather than conversational voice.",
    ]
    if role_slug == "coder":
        lines.extend([
            "Apply the /technical-writing skill before handoff (solorepo's DR-194, solorepo's DR-198, solorepo's DR-207):",
            "keep item docstrings dry Reference contracts without reviewer litigation (solorepo's DR-175),",
            "hold source comments to the four permissible exceptions, mechanize constraints before pruning,",
            "route defect narratives to <module>.history.md naming probe Evidence (solorepo's DR-171), and audit",
            "suppressions as defects.",
        ])
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def persona_agent(p: dict) -> str:
    """One stakeholder Persona's agent file: an interrogation surrogate that reads and never writes (solorepo's DR-200)."""
    persona_slug = p.get("id", "").rsplit("/", 1)[-1]
    name = p.get("name", persona_slug)
    desc = p.get("description", "").strip()
    context = p.get("context", "").strip()

    lines = [
        "---",
        f"name: {persona_slug}",
        "description: >-",
        f"  {desc} Interrogation surrogate for collaborative product and feature design (solorepo's DR-200).",
        "model: inherit",
        "tools:",
        "  - read",
        "---",
        "",
        BANNER.format(src="assertions/personas.yaml").strip(),
        "",
        f"# {name} (Interrogation Surrogate)",
        "",
        f"You are assuming the Persona of **{name}** for collaborative product and feature design (solorepo's DR-200).",
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
    """Compiles Roles, Personalities, and Personas into agent primitives (solorepo's DR-199, solorepo's DR-200).

    Two kinds of agent, written into one directory. An operational Role — the
    coder, the reviewer, the technical writer — takes the communication style
    of the Personality sharing its slug, and is given write access only where
    the Role writes. A stakeholder Persona compiles to an interrogation
    surrogate for collaborative product and feature design (solorepo's DR-200),
    which reads and never writes.
    """
    authority_file = meta_dir / "assertions" / "imported" / "authority.yaml"
    actors_file = meta_dir / "assertions" / "imported" / "actors.yaml"
    personas_file = meta_dir / "assertions" / "personas.yaml"

    auth_data = instructions.load_yaml(authority_file) or {}
    actors_data = instructions.load_yaml(actors_file) or {}
    personas_data = instructions.load_yaml(personas_file) or {}

    personalities = {p["id"]: p for p in actors_data.get("personalities") or []}
    roles = {r["id"]: r for r in auth_data.get("roles") or []}
    out = {}
    for role_id, r in roles.items():
        out[f".apm/agents/{role_id.rsplit('/', 1)[-1]}.agent.md"] = role_agent(role_id, r, personalities)
    for p in personas_data.get("personas") or []:
        out[f".apm/agents/{p.get('id', '').rsplit('/', 1)[-1]}.agent.md"] = persona_agent(p)
    return out
