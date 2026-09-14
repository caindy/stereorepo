#!/usr/bin/env python3
"""Operational authoring tool for Knowledge Management wiki concepts (solorepo's DR-187).

This tool provides a deterministic workflow for checking duplicates, scaffolding,
and verifying maintainer-facing wiki concept pages under `wiki/<context>/<slug>.md`
following Wikipedia editorial conventions (MOS:LEAD bold lead definitions,
closed-world wikilinks, and Bounded Context partitioning).
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import sys
from typing import Any

try:
    import yaml
except ImportError:
    import subprocess
    cmd = ["uvx", "--with", "pyyaml", "python", str(pathlib.Path(__file__).resolve()), *sys.argv[1:]]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

LEAD_COPULA = re.compile(
    r"^\*\*(?:`(?P<backticked>[^`]+)`|(?P<plain>[^*]+))\*\*\s+"
    r"(?P<copula>is|are|was|were|refers to|serves as|organizes|provides|names|represents)\b",
    re.IGNORECASE,
)

WIKILINK_RE = re.compile(r"\[\[(.*?)\]\]")
FENCED_RE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)


def slugify(text: str) -> str:
    """Convert a title or concept string into a canonical lowercase slug (solorepo's DR-187)."""
    cleaned = text.strip().lower()
    cleaned = re.sub(r"[_\s]+", "-", cleaned)
    cleaned = re.sub(r"[^a-z0-9-]", "", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned.strip("-")


def format_lead_sentence(title: str, definition: str) -> str:
    """Format a MOS:LEAD compliant bold copular lead sentence for a concept (solorepo's DR-187).

    The definition supplies its own copula where it opens with one — `is`,
    `are`, `refers to` and the rest — and is given `is` where it does not, so
    the lead reads as one sentence either way. An empty definition is led with
    a placeholder rather than left bare.
    """
    title_clean = title.strip()
    def_clean = definition.strip()

    if not def_clean:
        def_clean = "a concept within maintainer exposition"

    match = re.match(
        r"^(?:is|are|was|were|refers to|serves as|organizes|provides|names|represents)\b\s*",
        def_clean,
        re.IGNORECASE,
    )
    copula_body = def_clean if match else f"is {def_clean}"

    if not copula_body.endswith("."):
        copula_body = copula_body + "."

    return f"**{title_clean}** {copula_body}"


def find_duplicates(
    query: str, context: str = "solorepo", root: pathlib.Path | None = None
) -> list[dict[str, Any]]:
    """Search for colliding concepts in vocabulary, disciplines, and wiki pages (solorepo's DR-187).

    Three sources are read in turn — the wiki pages, then the vocabulary
    assertions, then the disciplines — and each is matched on slug and on
    label, so a page named for a concept and a concept named for a page collide
    whichever was written first. A source that is absent or will not parse
    contributes nothing rather than stopping the search.
    """
    root_path = root or pathlib.Path(__file__).resolve().parent.parent
    target_slug = slugify(query)
    target_norm = query.strip().lower()
    duplicates: list[dict[str, Any]] = []

    wiki_dir = root_path / "wiki"
    if wiki_dir.is_dir():
        for path in wiki_dir.glob("*/*.md"):
            if path.name == "README.md":
                continue
            ctx = path.parent.name
            stem = path.stem.lower()
            if stem == target_slug:
                duplicates.append({
                    "source": "wiki",
                    "id": f"wiki/{ctx}/{path.name}",
                    "label": path.stem,
                    "path": str(path.relative_to(root_path)),
                    "details": f"Existing wiki page in context '{ctx}' with matching slug '{stem}'",
                })
                continue

            try:
                raw = path.read_text(encoding="utf-8")
            except OSError:
                continue

            for line in raw.splitlines():
                line_s = line.strip()
                if line_s.startswith("# "):
                    heading_title = line_s[2:].strip().strip("`")
                    if heading_title.lower() == target_norm:
                        duplicates.append({
                            "source": "wiki",
                            "id": f"wiki/{ctx}/{path.name}",
                            "label": heading_title,
                            "path": str(path.relative_to(root_path)),
                            "details": f"Existing wiki page in context '{ctx}' with matching title '{heading_title}'",
                        })
                    break

    vocab_files = [
        root_path / ".meta" / "assertions" / "imported" / "vocabulary.yaml",
        root_path / ".meta" / "assertions" / "vocabulary.yaml",
        root_path / ".meta" / "assertions" / "domain_vocabulary.yaml",
    ]
    for v_path in vocab_files:
        if not v_path.is_file():
            continue
        try:
            data = yaml.safe_load(v_path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        for item in data.get("concept_set") or []:
            item_id = str(item.get("id") or "")
            item_slug = item_id.rsplit("/", 1)[-1].lower()
            pref_label = str(item.get("pref_label") or "")
            alt_labels = [str(a) for a in item.get("alt_labels") or []]

            if item_slug == target_slug or pref_label.strip().lower() == target_norm:
                duplicates.append({
                    "source": "vocabulary",
                    "id": item_id,
                    "label": pref_label or item_slug,
                    "path": str(v_path.relative_to(root_path)),
                    "details": f"Concept in vocabulary schema: {item.get('definition', '')}",
                })
            elif any(alt.strip().lower() == target_norm for alt in alt_labels):
                duplicates.append({
                    "source": "vocabulary",
                    "id": item_id,
                    "label": pref_label or item_slug,
                    "path": str(v_path.relative_to(root_path)),
                    "details": f"Concept synonym in vocabulary schema ({alt_labels})",
                })

    discipline_files = [
        root_path / ".meta" / "assertions" / "imported" / "disciplines.yaml",
        root_path / ".meta" / "assertions" / "disciplines.yaml",
    ]
    for d_path in discipline_files:
        if not d_path.is_file():
            continue
        try:
            d_data = yaml.safe_load(d_path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        for d in d_data.get("disciplines") or []:
            d_id = str(d.get("id") or "")
            d_slug = d_id.rsplit("/", 1)[-1].lower()
            d_name = str(d.get("name") or "")
            if d_slug == target_slug or d_name.strip().lower() == target_norm:
                duplicates.append({
                    "source": "discipline",
                    "id": d_id,
                    "label": d_name,
                    "path": str(d_path.relative_to(root_path)),
                    "details": f"Discipline in assertions: {d.get('description', '')[:80]}...",
                })

    return duplicates


def extract_known_concepts(root: pathlib.Path | None = None) -> dict[str, str]:
    """Extract known vocabulary and wiki concepts as a mapping of term to canonical target (solorepo's DR-187).

    Reads the same three sources as `find_duplicates` and in the same order,
    so a term a search collides against is a term this map resolves. A
    vocabulary concept contributes its slug and its preferred label, and a
    discipline its slug and its name, each pointing at the slug.
    """
    root_path = root or pathlib.Path(__file__).resolve().parent.parent
    known: dict[str, str] = {}

    wiki_dir = root_path / "wiki"
    if wiki_dir.is_dir():
        for path in wiki_dir.glob("*/*.md"):
            if path.name == "README.md":
                continue
            stem = path.stem.lower()
            known[stem] = stem

    vocab_files = [
        root_path / ".meta" / "assertions" / "imported" / "vocabulary.yaml",
        root_path / ".meta" / "assertions" / "vocabulary.yaml",
        root_path / ".meta" / "assertions" / "domain_vocabulary.yaml",
    ]
    for v_path in vocab_files:
        if not v_path.is_file():
            continue
        try:
            data = yaml.safe_load(v_path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        for item in data.get("concept_set") or []:
            item_id = str(item.get("id") or "")
            item_slug = item_id.rsplit("/", 1)[-1].lower()
            pref_label = str(item.get("pref_label") or "")
            known[item_slug] = item_slug
            if pref_label:
                known[pref_label.lower()] = item_slug

    discipline_files = [
        root_path / ".meta" / "assertions" / "imported" / "disciplines.yaml",
        root_path / ".meta" / "assertions" / "disciplines.yaml",
    ]
    for d_path in discipline_files:
        if not d_path.is_file():
            continue
        try:
            d_data = yaml.safe_load(d_path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        for d in d_data.get("disciplines") or []:
            d_id = str(d.get("id") or "")
            d_slug = d_id.rsplit("/", 1)[-1].lower()
            d_name = str(d.get("name") or "")
            known[d_slug] = d_slug
            if d_name:
                known[d_name.lower()] = d_slug

    return known


def embed_wikilinks(
    text: str, context: str = "solorepo", root: pathlib.Path | None = None
) -> str:
    """Automatically embed closed-world wikilinks for recognized concepts in prose (solorepo's DR-187)."""
    known = extract_known_concepts(root)
    sorted_terms = sorted(known.keys(), key=len, reverse=True)

    lines = text.splitlines()
    out_lines = []
    in_fence = False

    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            out_lines.append(line)
            continue
        if in_fence or line.strip().startswith("#") or not line.strip():
            out_lines.append(line)
            continue

        mod_line = line
        for term in sorted_terms:
            if len(term) < 4:
                continue
            pattern = re.compile(r"(?<!\[\[)(?<!`)\b(" + re.escape(term) + r")\b(?!`)(?!\]\])", re.IGNORECASE)
            match = pattern.search(mod_line)
            if match:
                matched_text = match.group(1)
                target_slug = known[term]
                replacement = f"[[{target_slug}|{matched_text}]]" if matched_text.lower() != target_slug else f"[[{target_slug}]]"
                mod_line = pattern.sub(replacement, mod_line, count=1)
                break
        out_lines.append(mod_line)

    return "\n".join(out_lines)


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
    slug = slugify(title)
    syn_list = synonyms or []
    minted = date_str or datetime.date.today().isoformat()
    lead_sentence = format_lead_sentence(title, definition)

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

    overview_linked = embed_wikilinks(overview_text, context=context, root=root)

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
    self_slug = slugify(title_clean)
    idx += 1

    while idx < len(lines) and not lines[idx].strip():
        idx += 1

    if idx >= len(lines):
        problems.append(f"{rel_path}: empty wiki page after title")
        return problems

    lead_line = lines[idx].strip()
    match = LEAD_COPULA.match(lead_line)
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

    known = extract_known_concepts(root)
    unfenced = FENCED_RE.sub("", content)
    for w_match in WIKILINK_RE.finditer(unfenced):
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


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for wikisplain operational authoring tool (solorepo's DR-187)."""
    parser = argparse.ArgumentParser(
        description="Scaffold, check, and explain Knowledge Management wiki concepts (solorepo's DR-187)."
    )
    parser.add_argument(
        "concept",
        help="The name or title of the concept (e.g., 'Domain Storytelling').",
    )
    parser.add_argument(
        "--context",
        default="solorepo",
        help="The Bounded Context subfolder under wiki/ (default: 'solorepo').",
    )
    parser.add_argument(
        "--definition",
        default="",
        help="Copular definition sentence body (e.g. 'a visual modeling method...').",
    )
    parser.add_argument(
        "--synonyms",
        default="",
        help="Comma-separated synonyms or alternate labels.",
    )
    parser.add_argument(
        "--slug",
        default="",
        help="Optional slug override (default: slugified title).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated page to stdout without writing to disk.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing wiki page if a duplicate exists.",
    )
    parser.add_argument(
        "--check-duplicate",
        action="store_true",
        help="Only check whether concept or slug already exists, then exit.",
    )

    args = parser.parse_args(argv)
    root = pathlib.Path(__file__).resolve().parent.parent

    dups = find_duplicates(args.concept, context=args.context, root=root)

    if args.check_duplicate:
        if dups:
            print(f"Collision: concept '{args.concept}' already exists in:")
            for d in dups:
                print(f"  - [{d['source']}] {d['label']} ({d['id']}) in {d['path']}: {d['details']}")
            return 1
        print(f"Clear: concept '{args.concept}' does not collide with vocabulary or wiki entities.")
        return 0

    if dups and not args.force:
        print(f"Error: concept '{args.concept}' collides with existing entities:")
        for d in dups:
            print(f"  - [{d['source']}] {d['label']} ({d['id']}) in {d['path']}: {d['details']}")
        print("Pass --force to proceed with scaffolding anyway.")
        return 1

    title = args.concept.strip()
    slug = args.slug.strip() if args.slug.strip() else slugify(title)
    syn_list = [s.strip() for s in args.synonyms.split(",") if s.strip()] if args.synonyms else []

    content = generate_page(
        title=title,
        context=args.context,
        definition=args.definition,
        synonyms=syn_list,
        root=root,
    )

    target_file = root / "wiki" / args.context / f"{slug}.md"
    rel_path = f"wiki/{args.context}/{slug}.md"

    problems = verify_page(content, rel_path, root=root)
    if problems:
        print(f"Verification warnings for {rel_path}:")
        for p in problems:
            print(f"  ! {p}")

    if args.dry_run:
        print(content)
        return 0

    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(content, encoding="utf-8")
    print(f"Scaffolded {rel_path} successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
