"""A concept page scaffolded from its definition, and a page verified against the conventions it was scaffolded to (solorepo's DR-187).
"""
from __future__ import annotations

import datetime
import pathlib

from lib.wikisplain import lead, links


def generate_page(
    title: str,
    context: str = "solorepo",
    definition: str = "",
    synonyms: list[str] | None = None,
    body: str = "",
    see_also: list[str] | None = None,
    date_str: str | None = None,
    root: pathlib.Path | None = None,
) -> str:
    """Generate canonical MOS:LEAD markdown content for a wiki concept page (solorepo's DR-187)."""
    slug = lead.slugify(title)
    syn_list = synonyms or []
    minted = date_str or datetime.date.today().isoformat()
    lead_sentence = lead.format_lead_sentence(title, definition)

    frontmatter_lines = [
        "---",
        f"slug: {slug}",
        f"context: {context}",
    ]
    if syn_list:
        frontmatter_lines.append("synonyms:")
        for s in syn_list:
            frontmatter_lines.append(f"  - {s}")
    frontmatter_lines.append(f"minted: {minted}")
    frontmatter_lines.append("---")
    frontmatter = "\n".join(frontmatter_lines)

    overview_text = body.strip() if body else (
        f"Maintainer exposition explaining the structure, lifecycle, and "
        f"operational role of {title} within the {context} bounded context."
    )

    overview_linked = links.embed_wikilinks(overview_text, context=context, root=root)

    see_also_items = list(see_also or [])
    if not see_also_items:
        default_links = ["knowledge-management", "ubiquitous-language", "pr-first"]
        see_also_items = [link for link in default_links if link != slug]

    see_also_str = ", ".join(f"[[{item}]]" for item in see_also_items)

    sections = [
        frontmatter,
        "",
        f"# {title}",
        "",
        lead_sentence,
        "",
        "## Overview",
        "",
        overview_linked,
        "",
        "## Invariants",
        "",
        f"1. **Bounded Context Scope:** Scoped hermetically to `wiki/{context}/`.",
        "2. **Concordance:** The lead definition concurs with vocabulary assertions.",
        "3. **Closed-World References:** Internal references resolve deterministically via closed-world wikilinks.",
        "",
        "---",
        "",
        f"**See also:** {see_also_str}",
        "",
    ]

    return "\n".join(sections)


def verify_page(
    content: str, rel_path: str, root: pathlib.Path | None = None
) -> list[str]:
    """Verify generated page content against MOS:LEAD and closed-world wikilink rules (solorepo's DR-187)."""
    problems: list[str] = []
    lines = content.splitlines()

    idx = 0
    if idx < len(lines) and lines[idx].strip() == "---":
        idx += 1
        while idx < len(lines) and lines[idx].strip() != "---":
            idx += 1
        if idx < len(lines) and lines[idx].strip() == "---":
            idx += 1

    while idx < len(lines) and not lines[idx].strip():
        idx += 1

    if idx >= len(lines) or not lines[idx].strip().startswith("# "):
        problems.append(f"{rel_path}: must begin with a top-level heading (# <Title>)")
        return problems

    title = lines[idx].strip()[2:].strip()
    title_clean = title.strip("`").strip()
    self_slug = lead.slugify(title_clean)
    idx += 1

    while idx < len(lines) and not lines[idx].strip():
        idx += 1

    if idx >= len(lines):
        problems.append(f"{rel_path}: empty wiki page after title")
        return problems

    lead_line = lines[idx].strip()
    match = lead.LEAD_COPULA.match(lead_line)
    if not match:
        problems.append(
            f"{rel_path}: first paragraph must open with bold copular definition "
            f"(MOS:LEAD: '**Subject** is ...')"
        )
    else:
        subject = (match.group("backticked") or match.group("plain") or "").strip()
        subject_clean = subject.strip("`").strip()
        if subject_clean.lower() != title_clean.lower():
            problems.append(
                f"{rel_path}: lead bold subject '{subject}' does not match title '{title}'"
            )

    known = links.extract_known_concepts(root)
    unfenced = links.FENCED_RE.sub("", content)
    for w_match in links.WIKILINK_RE.finditer(unfenced):
        raw = w_match.group(1).strip()
        if not raw:
            continue
        target = raw.split("|", 1)[0].split("#", 1)[0].strip()
        target_slug = target.rsplit("/", 1)[-1].lower()
        if target_slug == self_slug or target.lower() == self_slug:
            continue
        if target_slug not in known and target.lower() not in known and not target.startswith("DR-"):
            problems.append(
                f"{rel_path}: wikilink [[{raw}]] resolves to neither wiki page nor minted concept"
            )

    return problems
