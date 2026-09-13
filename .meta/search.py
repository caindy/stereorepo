#!/usr/bin/env python3
"""Retrieval over the repository assertions, decisions, and wiki by meaning (solorepo's DR-103, solorepo's DR-192, solorepo's DR-194, solorepo's DR-195).

Provides an in-memory Okapi BM25 search index over all identified objects
declared in .meta/assertions/*.yaml and concepts defined in wiki/**/*.md.
Enables agents and the solo to find relevant decisions, articles, disciplines,
and roles using natural language queries without relying on exact substring grep.

Usage:
    python3 .meta/search.py "<query>" [--limit N] [--detail] [--json]
    python3 .meta/search.py --benchmark
"""

import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

# Ensure .meta is importable for collect
META = Path(__file__).resolve().parent
ROOT = META.parent
if str(META) not in sys.path:
    sys.path.insert(0, str(META))

try:
    from checks import collect
except ImportError:
    collect = None


STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "of", "to", "in", "for", "with",
    "on", "at", "by", "from", "is", "it", "its", "i", "do", "does",
    "did", "there", "this", "that", "was", "were", "be", "been", "as",
})


def tokenize(text: str) -> list[str]:
    """Split text into lowercase alphanumeric tokens, filtering common syntactic stop words."""
    return [t for t in re.findall(r"[a-zA-Z0-9_\-]+", text.lower()) if t not in STOPWORDS]


def extract_strings(val: Any) -> list[str]:
    """Recursively collect all human-readable string values from nested structures."""
    if isinstance(val, str):
        return [val]
    if isinstance(val, dict):
        result = []
        for k, v in val.items():
            if k not in ("id", "applies", "enacted_in", "capabilities"):
                result.extend(extract_strings(v))
        return result
    if isinstance(val, list):
        result = []
        for item in val:
            result.extend(extract_strings(item))
        return result
    return []


class SearchResult:
    """A scored document match from the search index."""

    def __init__(
        self,
        identifier: str,
        title: str,
        kind: str,
        source_file: str,
        score: float,
        snippet: str,
        full_snippet: str = "",
    ) -> None:
        """Initialize a search result."""
        self.identifier = identifier
        self.title = title
        self.kind = kind
        self.source_file = source_file
        self.score = score
        self.snippet = snippet
        self.full_snippet = full_snippet or snippet

    def to_dict(self) -> dict[str, Any]:
        """Convert result to a dictionary for JSON output."""
        return {
            "id": self.identifier,
            "title": self.title,
            "kind": self.kind,
            "source_file": self.source_file,
            "score": round(self.score, 2),
            "snippet": self.snippet,
            "full_snippet": self.full_snippet,
        }


class SearchIndex:
    """Okapi BM25F search index over structured assertions and wiki pages."""

    FIELDS = ("title", "summary", "body")

    def __init__(
        self,
        k1: float = 1.5,
        weights: dict[str, float] | None = None,
        b_params: dict[str, float] | None = None,
    ) -> None:
        """Initialize an empty BM25F search index with per-field scoring parameters."""
        self.k1 = k1
        self.weights = weights or {"title": 3.0, "summary": 2.0, "body": 1.0}
        self.b_params = b_params or {"title": 0.4, "summary": 0.75, "body": 0.75}
        self.docs: dict[str, tuple[str, dict[str, Any], str]] = {}
        self.doc_field_tokens: dict[str, dict[str, list[str]]] = {}
        self.doc_field_lens: dict[str, dict[str, int]] = {f: {} for f in self.FIELDS}
        self.field_avg_len: dict[str, float] = dict.fromkeys(self.FIELDS, 1.0)
        self.doc_freqs: dict[str, int] = collections.defaultdict(int)
        self.total_docs: int = 0

    def add_document(
        self,
        identifier: str,
        kind: str,
        payload: dict[str, Any],
        source_file: str,
        field_tokens: dict[str, list[str]],
    ) -> None:
        """Add a multi-field document to the index."""
        self.docs[identifier] = (kind, payload, source_file)
        self.doc_field_tokens[identifier] = field_tokens
        unique_tokens: set[str] = set()
        for f in self.FIELDS:
            tokens = field_tokens.get(f, [])
            self.doc_field_lens[f][identifier] = len(tokens)
            unique_tokens.update(tokens)
        for token in unique_tokens:
            self.doc_freqs[token] += 1

    def finalize(self) -> None:
        """Compute aggregate statistics after adding all documents."""
        self.total_docs = len(self.docs)
        if self.total_docs > 0:
            for f in self.FIELDS:
                total_len = sum(self.doc_field_lens[f].values())
                self.field_avg_len[f] = total_len / self.total_docs if total_len > 0 else 1.0

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Rank documents against a query using the BM25F multi-field scoring algorithm."""
        q_tokens = tokenize(query)
        if not q_tokens or self.total_docs == 0:
            return []

        scores: dict[str, float] = collections.defaultdict(float)
        for token in q_tokens:
            if token not in self.doc_freqs:
                continue
            df = self.doc_freqs[token]
            # Robertson-Spärck Jones IDF formula with add-1 smoothing
            idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)
            for identifier in self.docs:
                # BM25F: compute length-normalized weighted term frequency across fields
                tf_tilde = 0.0
                for f in self.FIELDS:
                    raw_tf = self.doc_field_tokens[identifier][f].count(token)
                    if raw_tf > 0:
                        b = self.b_params[f]
                        avg_l = self.field_avg_len[f]
                        doc_l = self.doc_field_lens[f][identifier]
                        len_norm = 1.0 - b + b * (doc_l / avg_l)
                        tf_tilde += self.weights[f] * (raw_tf / len_norm)

                # Apply saturation curve over the combined weighted term frequency
                if tf_tilde > 0:
                    scores[identifier] += idf * ((tf_tilde * (self.k1 + 1.0)) / (tf_tilde + self.k1))

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for identifier, score in ranked:
            kind, payload, source_file = self.docs[identifier]
            title = str(payload.get("name", payload.get("title", payload.get("pref_label", identifier))))
            snippet = str(
                payload.get(
                    "context",
                    payload.get(
                        "description",
                        payload.get("rationale", payload.get("definition", "")),
                    ),
                )
            )
            raw_clean = " ".join(snippet.split())
            snippet_clean = raw_clean[:177] + "..." if len(raw_clean) > 180 else raw_clean
            results.append(
                SearchResult(
                    identifier=identifier,
                    title=title,
                    kind=kind,
                    source_file=source_file,
                    score=score,
                    snippet=snippet_clean,
                    full_snippet=raw_clean,
                )
            )
        return results


def build_index(meta_dir: Path, root_dir: Path) -> SearchIndex:
    """Build a BM25F search index from .meta/assertions/*.yaml and wiki/**/*.md."""
    index = SearchIndex()

    # 1. Index assertions via collect if LinkML is available
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
                    extract_strings(
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
                    "title": tokenize(title_text),
                    "summary": tokenize(summary_text),
                    "body": tokenize(other_text),
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

    # 2. Index wiki pages
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
                "title": tokenize(f"{title} {synonyms_text} {path.stem}"),
                "summary": tokenize(summary),
                "body": tokenize(body),
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


def run_benchmark(index: SearchIndex) -> int:
    """Run the 18 evaluation benchmark queries from Challenge 18 and solorepo's DR-103."""
    queries: list[tuple[str, list[str]]] = [
        (
            "what has been decided about naming",
            ["work:decision/078", "work:decision/065", "work:discipline/written-decisions"],
        ),
        (
            "which rules bear on generated files",
            ["work:discipline/seeded-artifacts", "work:decision/034", "work:decision/083"],
        ),
        (
            "has a ruleset check for required job names been argued before",
            ["work:challenge/4", "work:decision/061", "work:decision/057"],
        ),
        (
            "has anyone argued for a search index over the record before",
            ["work:challenge/18", "work:decision/103", "work:decision/077"],
        ),
        (
            "why can't I put reasoning in a commit message",
            ["work:article/14", "work:decision/076", "work:discipline/journaling", "work:decision/052"],
        ),
        (
            "how does a comment say which agent wrote it",
            ["work:decision/068", "work:concept/trailer", "work:discipline/pr-first"],
        ),
        (
            "why are there no dates in the decision record",
            ["work:decision/081", "work:decision/049", "work:discipline/written-decisions"],
        ),
        (
            "what happens when a review thread is resolved without an answer",
            ["work:article/16", "work:discipline/pr-first", "work:concept/review-thread"],
        ),
        (
            "how does a portfolio get updates from the scaffold",
            ["work:portfolio/solorepo", "work:discipline/specialization"],
        ),
        (
            "who is allowed to push to trunk",
            ["work:decision/072", "work:decision/100", "work:article/18", "work:discipline/pr-first"],
        ),
        (
            "what is the difference between a Role and a Remit",
            ["work:decision/066", "work:decision/073", "work:concept/remit"],
        ),
        (
            "where do things noticed but not done go",
            [
                "work:article/15",
                "work:discipline/pr-first",
                "work:decision/064",
                "work:concept/noticed-and-not-done",
            ],
        ),
        (
            "why is there a stakeholders directory",
            ["work:decision/041", "work:artifact/stakeholders-readme", "work:decision/040"],
        ),
        (
            "which languages can a new portfolio choose",
            ["work:discipline/specialization", "work:decision/046", "work:decision/014", "work:decision/015"],
        ),
        (
            "what makes the scaffold its own product",
            ["work:portfolio/solorepo", "work:product/scaffold", "work:decision/030"],
        ),
        (
            "I finished a task and there is leftover work, what do I do with it",
            [
                "work:decision/054",
                "work:discipline/journaling",
                "work:discipline/pr-first",
                "work:concept/noticed-and-not-done",
                "wiki:noticed-and-not-done",
            ],
        ),
        (
            "an old rule no longer applies, how is it retired",
            ["work:decision/085", "work:decision/070", "work:decision/057"],
        ),
        (
            "why does the tracker live in GitHub instead of a file",
            ["work:decision/088", "work:decision/061", "work:decision/028", "work:discipline/pr-first"],
        ),
    ]

    active_queries = [(q, targets) for q, targets in queries if any(t in index.docs for t in targets)]
    if not active_queries:
        print("No benchmark target documents present in index.")
        return 0

    hits_1 = 0
    hits_5 = 0
    hits_10 = 0
    reciprocal_ranks = []

    print(f"Running BM25 evaluation over {len(active_queries)} benchmark queries (solorepo's DR-103):\n")
    for q, targets in active_queries:
        results = index.search(q, top_k=10)
        target_set = set(targets)
        rank = None
        for i, res in enumerate(results, start=1):
            if res.identifier in target_set:
                rank = i
                break
        if rank == 1:
            hits_1 += 1
        if rank and rank <= 5:
            hits_5 += 1
        if rank and rank <= 10:
            hits_10 += 1
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        rank_str = f"rank={rank}" if rank else "miss"
        top_match = results[0].identifier if results else "none"
        print(f"  {q[:48]:<50} {rank_str:<9} top: {top_match}")

    mrr = sum(reciprocal_ranks) / len(active_queries)
    n = len(active_queries)
    print("\nBenchmark Summary:")
    print(f"  hit@1:  {hits_1 / n:.2f} ({hits_1}/{n})")
    print(f"  hit@5:  {hits_5 / n:.2f} ({hits_5}/{n})")
    print(f"  hit@10: {hits_10 / n:.2f} ({hits_10}/{n})")
    print(f"  MRR:    {mrr:.2f}")

    # Passes if hit@5 is at least 15 of 18 (in solorepo) or 80% of active queries (in specialized portfolio)
    min_hits = 15 if n >= 18 else int(0.8 * n)
    return 0 if hits_5 >= min_hits else 1


def main() -> None:
    """CLI entrypoint for search and benchmark evaluation."""
    parser = argparse.ArgumentParser(
        description="Search repository assertions, decisions, and wiki by meaning (BM25, solorepo's DR-103, solorepo's DR-194, solorepo's DR-195)."
    )
    parser.add_argument("query", nargs="*", help="Query terms to search for")
    parser.add_argument("--limit", type=int, default=5, help="Number of results to return (default 5)")
    parser.add_argument("--detail", action="store_true", help="Print full snippet context")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--benchmark", action="store_true", help="Run the 18 evaluation benchmark queries (solorepo's DR-103)")

    args = parser.parse_args()

    index = build_index(META, ROOT)

    if args.benchmark:
        sys.exit(run_benchmark(index))

    query_str = " ".join(args.query).strip()
    if not query_str:
        parser.print_help()
        sys.exit(1)

    results = index.search(query_str, top_k=args.limit)

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
        return

    if not results:
        print(f"No matches found for {query_str!r}.")
        return

    print(f"Search results for {query_str!r} ({len(results)} matches):\n")
    for i, res in enumerate(results, start=1):
        print(f"{i}. [{res.score:.2f}] {res.title} ({res.identifier})")
        print(f"   file: {res.source_file}")
        snippet = res.full_snippet if args.detail else res.snippet
        if snippet:
            print(f"   {snippet}")
        print()


if __name__ == "__main__":
    main()
