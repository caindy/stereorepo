"""The index built over every identified object under `.meta/assertions/` and every concept under `wiki/`, through the gate's own collector when it can be imported.
"""
import re
import sys
import types
from pathlib import Path

from lib.search import bm25

collect: types.ModuleType | None = None
try:
    from checks import collect as _collect
except ImportError:
    pass
else:
    collect = _collect


def build_index(meta_dir: Path, root_dir: Path) -> bm25.SearchIndex:
    """Build a BM25F search index from .meta/assertions/*.yaml and wiki/**/*.md.

    The assertions are indexed through `collect`, and are skipped with a warning
    on stderr where LinkML is not installed, so a search still answers over the
    wiki alone. The wiki is indexed from its Markdown, `README.md` aside.
    """
    index = bm25.SearchIndex()

    if collect is not None:
        try:
            assertion_files = {
                p.name: p.relative_to(root_dir).as_posix()
                for p in (meta_dir / "assertions").rglob("*.yaml")
            }
            views = collect.views()
            entities, _, _ = collect.collect(views)
            for entity_id, (cls, obj, file_path) in entities.items():
                pref_label = obj.get("pref_label", "")
                alt_labels_list = obj.get("alt_labels", [])
                alt_labels_str = " ".join(str(a) for a in alt_labels_list) if isinstance(alt_labels_list, list) else str(alt_labels_list)
                definition = obj.get("definition", "")

                name = obj.get("name", "") or obj.get("title", "") or pref_label
                title_text = f"{name} {alt_labels_str} {entity_id} {file_path}".strip()
                summary_text = str(
                    obj.get(
                        "context",
                        obj.get(
                            "description",
                            obj.get("rationale", definition),
                        ),
                    )
                )
                other_text = " ".join(
                    bm25.extract_strings(
                        {
                            k: v
                            for k, v in obj.items()
                            if k
                            not in (
                                "name",
                                "title",
                                "pref_label",
                                "alt_labels",
                                "context",
                                "description",
                                "rationale",
                                "definition",
                            )
                        }
                    )
                )

                field_tokens = {
                    "title": bm25.tokenize(title_text),
                    "summary": bm25.tokenize(summary_text),
                    "body": bm25.tokenize(other_text),
                }
                rel_source = assertion_files.get(file_path, f".meta/assertions/{file_path}")
                index.add_document(
                    identifier=entity_id,
                    kind=cls,
                    payload=obj,
                    source_file=rel_source,
                    field_tokens=field_tokens,
                )
        except Exception as err:
            print(f"Warning: collect could not load LinkML schemas: {err}", file=sys.stderr)

    wiki_dir = root_dir / "wiki"
    if wiki_dir.is_dir():
        for path in sorted(wiki_dir.rglob("*.md")):
            if path.name == "README.md":
                continue
            text = path.read_text(encoding="utf-8")
            title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else path.stem
            rel_path = path.relative_to(root_dir).as_posix()

            content_text = text
            synonyms_text = ""
            if content_text.startswith("---"):
                parts = content_text.split("---", 2)
                if len(parts) >= 3:
                    fm = parts[1]
                    content_text = parts[2]
                    syn_match = re.findall(r"^\s*-\s+(.+)$", fm, re.MULTILINE)
                    if syn_match:
                        synonyms_text = " ".join(syn_match)

            paragraphs = [p.strip() for p in content_text.split("\n\n") if p.strip()]
            summary = paragraphs[0] if paragraphs else ""
            body = "\n\n".join(paragraphs[1:]) if len(paragraphs) > 1 else ""

            field_tokens = {
                "title": bm25.tokenize(f"{title} {synonyms_text} {path.stem}"),
                "summary": bm25.tokenize(summary),
                "body": bm25.tokenize(body),
            }
            index.add_document(
                identifier=f"wiki:{path.stem}",
                kind="wiki_concept",
                payload={"name": title, "description": summary[:300]},
                source_file=rel_path,
                field_tokens=field_tokens,
            )

    index.finalize()
    return index
