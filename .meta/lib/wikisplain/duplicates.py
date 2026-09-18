"""The search for a concept already on a page, by title, alias and lead, before a second page is scaffolded.
"""
from __future__ import annotations

import pathlib
from typing import Any

import yaml

from lib.wikisplain import lead


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
    target_slug = lead.slugify(query)
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
