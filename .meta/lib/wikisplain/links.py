"""Closed-world wikilinks: the concepts the wiki and the ontology already know, and the links a body of prose gains to them.
"""
from __future__ import annotations

import pathlib
import re

import yaml

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
