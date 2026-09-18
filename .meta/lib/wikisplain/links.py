"""Closed-world wikilinks: the concepts the wiki and the ontology already know, and the links a body of prose gains to them.
"""
from __future__ import annotations

import pathlib
import re

from lib.wikisplain import duplicates

WIKILINK_RE = re.compile(r"\[\[(.*?)\]\]")
FENCED_RE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)


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
            if path.name != "README.md":
                known[path.stem.lower()] = path.stem.lower()
    for v_path in (root_path / ".meta" / "assertions" / "imported" / "vocabulary.yaml",
                   root_path / ".meta" / "assertions" / "vocabulary.yaml",
                   root_path / ".meta" / "assertions" / "domain_vocabulary.yaml"):
        for item in duplicates.loaded(v_path).get("concept_set") or []:
            item_slug = str(item.get("id") or "").rsplit("/", 1)[-1].lower()
            known[item_slug] = item_slug
            if item.get("pref_label"):
                known[str(item["pref_label"]).lower()] = item_slug
    for d_path in (root_path / ".meta" / "assertions" / "imported" / "disciplines.yaml",
                   root_path / ".meta" / "assertions" / "disciplines.yaml"):
        for d in duplicates.loaded(d_path).get("disciplines") or []:
            d_slug = str(d.get("id") or "").rsplit("/", 1)[-1].lower()
            known[d_slug] = d_slug
            if d.get("name"):
                known[str(d["name"]).lower()] = d_slug
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
