"""The Okapi BM25 index: the tokens a text yields, the strings an assertion holds, and a result with its score.
"""
import collections
import dataclasses
import math
import re
from typing import Any

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


@dataclasses.dataclass
class SearchResult:
    """A scored document match from the search index; `full_snippet` is the whole text where `snippet` was cut short."""

    identifier: str
    title: str
    kind: str
    source_file: str
    score: float
    snippet: str
    full_snippet: str = ""

    def __post_init__(self) -> None:
        self.full_snippet = self.full_snippet or self.snippet

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
        """Rank documents against a query using the BM25F multi-field scoring algorithm.

        Each query token contributes its Robertson-Sparck Jones inverse document
        frequency, smoothed by add-one, times a saturation curve over one
        weighted term frequency. That frequency is combined across the fields
        before saturating rather than after: BM25F normalizes each field by its
        own average length and `b` parameter, then sums, so a term in a short
        title and a term in a long body saturate together rather than twice.
        """
        q_tokens = tokenize(query)
        if not q_tokens or self.total_docs == 0:
            return []

        scores: dict[str, float] = collections.defaultdict(float)
        for token in q_tokens:
            if token not in self.doc_freqs:
                continue
            df = self.doc_freqs[token]
            idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)
            for identifier in self.docs:
                tf_tilde = 0.0
                for f in self.FIELDS:
                    raw_tf = self.doc_field_tokens[identifier][f].count(token)
                    if raw_tf > 0:
                        b = self.b_params[f]
                        avg_l = self.field_avg_len[f]
                        doc_l = self.doc_field_lens[f][identifier]
                        len_norm = 1.0 - b + b * (doc_l / avg_l)
                        tf_tilde += self.weights[f] * (raw_tf / len_norm)

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
