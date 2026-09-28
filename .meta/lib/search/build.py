"""The index built over every identified object under `.meta/assertions/` and every concept under `wiki/`, through the gate's own collector when it can be imported.

History in build.history.md (stereorepo's DR-171).
"""
import re
import sys
import types
from pathlib import Path

import yaml

from lib.search import bm25

collect: types.ModuleType | None = None
try:
    from checks import collect as _collect
except ImportError:
    pass
else:
    collect = _collect

FRONTMATTER = re.compile(r"\A---\n(?P<block>.*?)\n---(?:\n|\Z)", re.DOTALL)
"""A wiki page's opening YAML frontmatter block: the `---` fence the page starts with, and everything to the fence that closes it."""


def wiki_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """A wiki page's frontmatter as a mapping, and the page with that block removed.

    The mapping is empty where the page opens with no frontmatter, where the
    block will not parse as YAML, or where it parses to anything but a mapping.
    Only the first of those returns the page unchanged, there being no block to
    cut; the other two return it with the fence and its contents removed, so a
    block no reader of frontmatter can use is not indexed as prose either.
    """
    match = FRONTMATTER.match(text)
    if not match:
        return {}, text
    try:
        block = yaml.safe_load(match.group("block"))
    except yaml.YAMLError:
        return {}, text[match.end():]
    return (block if isinstance(block, dict) else {}), text[match.end():]


def wiki_synonyms(front: dict[str, object]) -> str:
    """The synonyms a wiki page declares, space-joined for the title field, and empty where it declares none.

    Only a list-valued `synonyms` counts, which is what `wikisplain` writes and
    what the gate reads: an item under any other key is a word nobody declared
    findable, and indexing it at title weight would put the two readers of the
    same block at odds.
    """
    synonyms = front.get("synonyms")
    if not isinstance(synonyms, list):
        return ""
    return " ".join(str(synonym) for synonym in synonyms)


def build_index(meta_dir: Path, root_dir: Path) -> bm25.SearchIndex:
    """Build a BM25F search index from .meta/assertions/*.yaml and wiki/**/*.md.

    The assertions are indexed through `collect`, and are skipped with a warning
    on stderr where LinkML is not installed, so a search still answers over the
    wiki alone. The wiki is indexed from its Markdown, `README.md` aside: the
    frontmatter is dropped first, so the heading read is the page's own and not
    a YAML comment, and the heading is cut from what remains, so the summary
    field holds the lead definition sentence a page opens with and the body the
    prose after it. The heading, the page's declared `synonyms`, and its stem
    make the title field.
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
        except Exception as err:  # noqa: BLE001  # reason: LinkML raises its own hierarchy across schema load and induction, and an index built without assertions is better than a search that will not build
            print(f"Warning: collect could not load LinkML schemas: {err}", file=sys.stderr)
    else:
        print(
            "Warning: linkml_runtime is not installed, so the assertions are not indexed "
            "and this search answers over wiki/ alone.",
            file=sys.stderr,
        )

    wiki_dir = root_dir / "wiki"
    if wiki_dir.is_dir():
        for path in sorted(wiki_dir.rglob("*.md")):
            if path.name == "README.md":
                continue
            rel_path = path.relative_to(root_dir).as_posix()

            text = path.read_text(encoding="utf-8")
            front, content_text = wiki_frontmatter(text)
            synonyms_text = wiki_synonyms(front)

            title_match = re.search(r"^#\s+(.+)$", content_text, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()
                content_text = content_text[: title_match.start()] + content_text[title_match.end() :]
            else:
                title = path.stem

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
