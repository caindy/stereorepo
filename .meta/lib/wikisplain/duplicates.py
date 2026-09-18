"""The search for a concept already on a page, by title, alias and lead, before a second page is scaffolded.
"""
from __future__ import annotations

import pathlib
from typing import Any

import yaml

from lib.wikisplain import lead


def loaded(path: pathlib.Path) -> dict[str, Any]:
    """The YAML at `path` as a dict, or an empty one where the file is absent or will not parse."""
    if not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def page_title(path: pathlib.Path) -> str | None:
    """The first top-level heading of the page at `path`, backticks stripped, or None where there is none or the file will not read."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in raw.splitlines():
        line_s = line.strip()
        if line_s.startswith("# "):
            return line_s[2:].strip().strip("`")
    return None


def wiki_duplicates(root_path: pathlib.Path, target_slug: str, target_norm: str) -> list[dict[str, Any]]:
    """Every wiki page whose slug is `target_slug` or whose title is `target_norm`."""
    found: list[dict[str, Any]] = []
    wiki_dir = root_path / "wiki"
    if not wiki_dir.is_dir():
        return found
    for path in wiki_dir.glob("*/*.md"):
        if path.name == "README.md":
            continue
        ctx = path.parent.name
        stem = path.stem.lower()
        title = page_title(path)
        if stem == target_slug:
            label, details = path.stem, f"Existing wiki page in context '{ctx}' with matching slug '{stem}'"
        elif title is not None and title.lower() == target_norm:
            label, details = title, f"Existing wiki page in context '{ctx}' with matching title '{title}'"
        else:
            continue
        found.append({"source": "wiki", "id": f"wiki/{ctx}/{path.name}", "label": label,
                      "path": str(path.relative_to(root_path)), "details": details})
    return found


def vocabulary_duplicates(root_path: pathlib.Path, target_slug: str, target_norm: str) -> list[dict[str, Any]]:
    """Every vocabulary concept whose slug is `target_slug`, or whose preferred or alternative label is `target_norm`."""
    found: list[dict[str, Any]] = []
    for v_path in (root_path / ".meta" / "assertions" / "imported" / "vocabulary.yaml",
                   root_path / ".meta" / "assertions" / "vocabulary.yaml",
                   root_path / ".meta" / "assertions" / "domain_vocabulary.yaml"):
        for item in loaded(v_path).get("concept_set") or []:
            item_id = str(item.get("id") or "")
            item_slug = item_id.rsplit("/", 1)[-1].lower()
            pref_label = str(item.get("pref_label") or "")
            alt_labels = [str(a) for a in item.get("alt_labels") or []]
            if item_slug == target_slug or pref_label.strip().lower() == target_norm:
                details = f"Concept in vocabulary schema: {item.get('definition', '')}"
            elif any(alt.strip().lower() == target_norm for alt in alt_labels):
                details = f"Concept synonym in vocabulary schema ({alt_labels})"
            else:
                continue
            found.append({"source": "vocabulary", "id": item_id, "label": pref_label or item_slug,
                          "path": str(v_path.relative_to(root_path)), "details": details})
    return found


def discipline_duplicates(root_path: pathlib.Path, target_slug: str, target_norm: str) -> list[dict[str, Any]]:
    """Every Discipline whose slug is `target_slug` or whose name is `target_norm`."""
    found: list[dict[str, Any]] = []
    for d_path in (root_path / ".meta" / "assertions" / "imported" / "disciplines.yaml",
                   root_path / ".meta" / "assertions" / "disciplines.yaml"):
        for d in loaded(d_path).get("disciplines") or []:
            d_id = str(d.get("id") or "")
            d_slug = d_id.rsplit("/", 1)[-1].lower()
            d_name = str(d.get("name") or "")
            if d_slug == target_slug or d_name.strip().lower() == target_norm:
                found.append({"source": "discipline", "id": d_id, "label": d_name,
                              "path": str(d_path.relative_to(root_path)),
                              "details": f"Discipline in assertions: {d.get('description', '')[:80]}..."})
    return found


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
    return (wiki_duplicates(root_path, target_slug, target_norm)
            + vocabulary_duplicates(root_path, target_slug, target_norm)
            + discipline_duplicates(root_path, target_slug, target_norm))
