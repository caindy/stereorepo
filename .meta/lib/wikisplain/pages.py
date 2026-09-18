"""A concept page scaffolded from its definition, and a page verified against the conventions it was scaffolded to (solorepo's DR-187).
"""
from __future__ import annotations

import dataclasses
import datetime
import pathlib

from lib.wikisplain import lead, links


@dataclasses.dataclass
class Page:
    """What a concept page is generated from: its title, bounded context, one-sentence definition, synonyms, body, see-also links and minting date, each but the title optional."""

    title: str
    context: str = "solorepo"
    definition: str = ""
    synonyms: list[str] | None = None
    body: str = ""
    see_also: list[str] | None = None
    date_str: str | None = None


def generate_page(page: Page, root: pathlib.Path | None = None) -> str:
    """Generate canonical MOS:LEAD markdown content for the wiki concept `page` (solorepo's DR-187)."""
    title, context, body = page.title, page.context, page.body
    see_also = page.see_also
    slug = lead.slugify(title)
    syn_list = page.synonyms or []
    minted = page.date_str or datetime.date.today().isoformat()
    lead_sentence = lead.format_lead_sentence(title, page.definition)

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


def past_frontmatter(lines: list[str]) -> int:
    """The index of the first line after any YAML frontmatter block and the blank lines that follow it."""
    idx = 0
    if idx < len(lines) and lines[idx].strip() == "---":
        idx += 1
        while idx < len(lines) and lines[idx].strip() != "---":
            idx += 1
        if idx < len(lines) and lines[idx].strip() == "---":
            idx += 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    return idx


def lead_problems(lines: list[str], rel_path: str) -> tuple[list[str], str | None]:
    """The MOS:LEAD problems of a page and its title: no top-level heading, nothing after it, no bold copular lead, or a lead whose subject is not the title."""
    idx = past_frontmatter(lines)
    if idx >= len(lines) or not lines[idx].strip().startswith("# "):
        return [f"{rel_path}: must begin with a top-level heading (# <Title>)"], None
    title = lines[idx].strip()[2:].strip()
    title_clean = title.strip("`").strip()
    idx += 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx >= len(lines):
        return [f"{rel_path}: empty wiki page after title"], title_clean
    match = lead.LEAD_COPULA.match(lines[idx].strip())
    if not match:
        return [f"{rel_path}: first paragraph must open with bold copular definition "
                f"(MOS:LEAD: '**Subject** is ...')"], title_clean
    subject = (match.group("backticked") or match.group("plain") or "").strip()
    if subject.strip("`").strip().lower() != title_clean.lower():
        return [f"{rel_path}: lead bold subject '{subject}' does not match title '{title}'"], title_clean
    return [], title_clean


def wikilink_problems(content: str, rel_path: str, self_slug: str, root: pathlib.Path | None) -> list[str]:
    """Every wikilink outside a fence that names neither a known concept nor the page itself, `DR-` targets excepted."""
    known = links.extract_known_concepts(root)
    problems = []
    for w_match in links.WIKILINK_RE.finditer(links.FENCED_RE.sub("", content)):
        raw = w_match.group(1).strip()
        if not raw:
            continue
        target = raw.split("|", 1)[0].split("#", 1)[0].strip()
        target_slug = target.rsplit("/", 1)[-1].lower()
        if target_slug == self_slug or target.lower() == self_slug:
            continue
        if target_slug not in known and target.lower() not in known and not target.startswith("DR-"):
            problems.append(f"{rel_path}: wikilink [[{raw}]] resolves to neither wiki page nor minted concept")
    return problems


def verify_page(
    content: str, rel_path: str, root: pathlib.Path | None = None
) -> list[str]:
    """Verify generated page content against MOS:LEAD and closed-world wikilink rules (solorepo's DR-187)."""
    problems, title_clean = lead_problems(content.splitlines(), rel_path)
    if title_clean is None or (problems and "after title" in problems[0]):
        return problems
    return problems + wikilink_problems(content, rel_path, lead.slugify(title_clean), root)
