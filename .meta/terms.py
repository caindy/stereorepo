#!/usr/bin/env -S uvx --with wordfreq python
"""An operator audit instrument that surfaces unminted terms by keyness and dispersion (solorepo's DR-234).

Evaluates candidate terms doing technical work across the repository's durable
prose using two complementary statistical dimensions:
1. Stefan Th. Gries' Deviation of Proportions (DP): measures document locality
   (0 = uniformly distributed, 1 = concentrated in a single file).
2. Log-likelihood keyness (G²): measures statistical overuse relative to general
   English reference frequency obtained from `wordfreq`.

Filters candidates against a Zipf frequency floor (default >= 3.0) to isolate
repurposed English vocabulary from novel coinages, and excludes preferred and
alternative labels defined in the Ubiquitous Language vocabulary assertions
before candidate ranking.

Usage:
    just terms                                  # top 30 unminted candidates
    python3 .meta/terms.py                      # direct execution
    python3 .meta/terms.py --dp 0.75 --limit 20 # custom dispersion threshold
    python3 .meta/terms.py --format json        # machine-readable output
    python3 .meta/terms.py --commit 8ba43766~1  # audit an earlier git tree
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import types
from collections import Counter
from collections.abc import Sequence
from typing import NamedTuple

wordfreq: types.ModuleType | None = None
try:
    import wordfreq as _wf

    wordfreq = _wf
except ImportError:
    pass

yaml: types.ModuleType | None = None
try:
    import yaml as _yaml

    yaml = _yaml
except ImportError:
    pass


META = pathlib.Path(__file__).resolve().parent
ROOT = META.parent

DEFAULT_MIN_ZIPF: float = 3.0
DEFAULT_MIN_DP: float = 0.70
DEFAULT_MIN_G2: float = 10.83
DEFAULT_MIN_USES: int = 5
DEFAULT_LIMIT: int = 30

RENDERED_TARGETS: frozenset[str] = frozenset({
    ".meta/charter.md",
    ".meta/decisions.md",
    ".meta/disciplines.md",
    ".meta/vocabulary.md",
    "SPECIALIZE.md",
    ".meta/apm.yml",
    ".meta/templates/decision.md",
    ".claude/skills/pr-first/SKILL.md",
    ".claude/skills/pr-first-reviewer/SKILL.md",
    ".claude/skills/technical-writing/SKILL.md",
    ".claude/skills/wikisplain/SKILL.md",
})

IGNORED_DIRECTORIES: frozenset[str] = frozenset({
    ".git",
    ".venv",
    "target",
    "node_modules",
    ".review",
    ".apm",
})


class TermsConfig(NamedTuple):
    """Configuration parameters for candidate extraction."""

    min_zipf: float = DEFAULT_MIN_ZIPF
    min_dp: float = DEFAULT_MIN_DP
    min_g2: float = DEFAULT_MIN_G2
    min_uses: int = DEFAULT_MIN_USES
    exclude_minted: bool = True
    sort_by: str = "g2"
    limit: int = DEFAULT_LIMIT


class TermCandidate(NamedTuple):
    """A scored candidate term extracted from the corpus."""

    term: str
    dp: float
    g2: float
    uses: int
    zipf: float

    def to_dict(self) -> dict[str, float | int | str]:
        """Convert candidate to a JSON-serializable dictionary."""
        return {
            "term": self.term,
            "dp": round(self.dp, 4),
            "g2": round(self.g2, 2),
            "uses": self.uses,
            "zipf": round(self.zipf, 2),
        }


def _read_vocab_content(root_path: pathlib.Path, rel_path: str, commit: str | None) -> str | None:
    """Read raw vocabulary text from either git tree or working filesystem."""
    if commit is not None:
        try:
            return subprocess.check_output(
                ["git", "show", f"{commit}:{rel_path}"],
                text=True,
                stderr=subprocess.DEVNULL,
                cwd=str(root_path),
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    full_path = root_path / rel_path
    if full_path.is_file():
        return full_path.read_text(encoding="utf-8", errors="ignore")
    return None


def _parse_vocab_yaml(text: str) -> list[str]:
    """Extract raw label strings from structured YAML when parser is available."""
    if yaml is None:
        return []
    labels: list[str] = []
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict):
            for c in data.get("concept_set") or []:
                if isinstance(c, dict):
                    pref = c.get("pref_label")
                    if isinstance(pref, str):
                        labels.append(pref)
                    for alt in c.get("alt_labels") or []:
                        if isinstance(alt, str):
                            labels.append(alt)
    except Exception:
        pass
    return labels


def _parse_vocab_regex(text: str) -> list[str]:
    """Extract label strings using regex patterns when YAML parser is missing."""
    labels: list[str] = []
    labels.extend(re.findall(r"^\s*pref_label:\s*(.+)$", text, re.MULTILINE))
    for chunk in re.findall(r"^\s*alt_labels:\s*\[(.*?)\]", text, re.MULTILINE):
        labels.extend(part.strip() for part in chunk.split(","))
    labels.extend(re.findall(r"^\s*-\s*([A-Za-z0-9 _-]+)$", text, re.MULTILINE))
    return labels


def extract_vocab_labels(root_path: pathlib.Path, commit: str | None = None) -> set[str]:
    """Extract all preferred and alternative labels from vocabulary assertions.

    Reads `.meta/assertions/imported/vocabulary.yaml` and
    `.meta/assertions/vocabulary.yaml`, collecting single-word components and
    standard inflections (singular and plural) so minted terms are cleanly
    excluded from candidate generation.
    """
    vocab_files = [
        ".meta/assertions/imported/vocabulary.yaml",
        ".meta/assertions/vocabulary.yaml",
    ]
    excluded_words: set[str] = set()

    for rel_path in vocab_files:
        text = _read_vocab_content(root_path, rel_path, commit)
        if not text:
            continue
        labels = _parse_vocab_yaml(text) or _parse_vocab_regex(text)
        for raw_label in labels:
            clean = re.sub(r"\(.*?\)", "", raw_label)
            for word in re.findall(r"\b[a-zA-Z]+\b", clean.lower()):
                if len(word) > 2:
                    excluded_words.add(word)
                    if word.endswith("s"):
                        excluded_words.add(word[:-1])
                    else:
                        excluded_words.add(word + "s")

    return excluded_words


def _is_durable_path(rel_path: str) -> bool:
    """Determine whether a relative file path qualifies as durable prose."""
    if rel_path in RENDERED_TARGETS or rel_path.startswith(".meta/.apm/"):
        return False
    parts = rel_path.split("/")
    if any(ign in parts for ign in IGNORED_DIRECTORIES):
        return False
    is_md = rel_path.endswith(".md")
    is_assertion = (rel_path.endswith(".yaml") or rel_path.endswith(".yml")) and (
        rel_path.startswith(".meta/assertions/")
    )
    return is_md or is_assertion


def _load_git_corpus(root_path: pathlib.Path, commit: str) -> dict[str, str]:
    """Load corpus files from a designated git commit."""
    corpus: dict[str, str] = {}
    raw_files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", commit],
        text=True,
        cwd=str(root_path),
    ).splitlines()

    for rel_path in raw_files:
        if not _is_durable_path(rel_path):
            continue
        try:
            content = subprocess.check_output(
                ["git", "show", f"{commit}:{rel_path}"],
                text=True,
                stderr=subprocess.DEVNULL,
                cwd=str(root_path),
            )
            corpus[rel_path] = content
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return corpus


def _load_fs_corpus(root_path: pathlib.Path) -> dict[str, str]:
    """Load corpus files from the working directory filesystem."""
    corpus: dict[str, str] = {}
    for root_dir, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRECTORIES]
        for filename in filenames:
            full_path = pathlib.Path(root_dir) / filename
            try:
                rel_path = full_path.relative_to(root_path).as_posix()
            except ValueError:
                continue
            if not _is_durable_path(rel_path):
                continue
            try:
                corpus[rel_path] = full_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
    return corpus


def load_corpus(root_path: pathlib.Path, commit: str | None = None) -> dict[str, str]:
    """Load durable markdown and assertion YAML files into an in-memory corpus mapping."""
    if commit is not None:
        return _load_git_corpus(root_path, commit)
    return _load_fs_corpus(root_path)


def tokenize(text: str) -> list[str]:
    """Extract lowercase alphanumeric word tokens from text."""
    return [w.lower() for w in re.findall(r"\b[a-zA-Z]+(?:\x27[a-zA-Z]+)?\b", text)]


def compute_gries_dp(
    occurrences_by_file: dict[str, int],
    file_lengths: dict[str, int],
    total_tokens: int,
    total_occurrences: int,
) -> float:
    """Compute Stefan Th. Gries' Deviation of Proportions (DP) dispersion metric.

    Formula:
        DP = 0.5 * sum(|f_i / F - s_i / N|)
    where:
        f_i: count of word in file i
        F: total count of word in corpus
        s_i: token length of file i
        N: total token count of corpus
    """
    if total_tokens <= 0 or total_occurrences <= 0:
        return 0.0

    accumulated: float = 0.0
    for file_path, file_len in file_lengths.items():
        v_i = file_len / total_tokens
        p_i = occurrences_by_file.get(file_path, 0) / total_occurrences
        accumulated += abs(p_i - v_i)

    return 0.5 * accumulated


def compute_log_likelihood(
    observed_in_corpus: int,
    total_corpus_tokens: int,
    reference_relative_freq: float,
) -> float:
    """Compute Dunning/Rayson log-likelihood keyness (G²) against a reference distribution.

    Evaluates whether the word occurs with greater frequency in the corpus than
    expected from the reference English distribution. If observed <= expected,
    returns 0.0.
    """
    if total_corpus_tokens <= 0 or reference_relative_freq <= 0:
        return 0.0

    expected = total_corpus_tokens * reference_relative_freq
    if observed_in_corpus <= expected:
        return 0.0

    return 2.0 * (
        observed_in_corpus * math.log(observed_in_corpus / expected)
        - (observed_in_corpus - expected)
    )


class CorpusStats(NamedTuple):
    """Aggregated token statistics across the corpus."""

    file_lengths: dict[str, int]
    total_tokens: int


def _count_corpus(corpus: dict[str, str]) -> tuple[CorpusStats, dict[str, dict[str, int]], Counter[str]]:
    """Compute token lengths, word file distribution, and global counts."""
    file_lengths: dict[str, int] = {}
    word_file_counts: dict[str, dict[str, int]] = {}
    word_total_counts: Counter[str] = Counter()
    total_tokens = 0

    for file_path, content in corpus.items():
        tokens = tokenize(content)
        if not tokens:
            continue
        file_lengths[file_path] = len(tokens)
        total_tokens += len(tokens)
        counts = Counter(tokens)
        for word, count in counts.items():
            if word not in word_file_counts:
                word_file_counts[word] = {}
            word_file_counts[word][file_path] = count
            word_total_counts[word] += count

    return CorpusStats(file_lengths=file_lengths, total_tokens=total_tokens), word_file_counts, word_total_counts


def _score_candidate(
    word: str,
    total_uses: int,
    word_files: dict[str, int],
    stats: CorpusStats,
    config: TermsConfig,
) -> TermCandidate | None:
    """Evaluate candidate thresholds for a single word."""
    if wordfreq is not None:
        zipf = float(wordfreq.zipf_frequency(word, "en"))
        ref_freq = float(wordfreq.word_frequency(word, "en"))
    else:
        zipf = 4.0
        ref_freq = 1e-5

    if zipf < config.min_zipf or ref_freq <= 0:
        return None

    dp = compute_gries_dp(word_files, stats.file_lengths, stats.total_tokens, total_uses)
    if dp < config.min_dp:
        return None

    g2 = compute_log_likelihood(total_uses, stats.total_tokens, ref_freq)
    if g2 < config.min_g2:
        return None

    return TermCandidate(term=word, dp=dp, g2=g2, uses=total_uses, zipf=zipf)


def extract_candidates(
    corpus: dict[str, str] | None = None,
    root_path: pathlib.Path | None = None,
    commit: str | None = None,
    config: TermsConfig | None = None,
) -> list[TermCandidate]:
    """Analyze corpus files to surface unminted candidate terms by keyness and dispersion."""
    cfg = config or TermsConfig()
    target_root = root_path if root_path is not None else ROOT
    if corpus is None:
        corpus = load_corpus(target_root, commit=commit)

    excluded_words = (
        extract_vocab_labels(target_root, commit=commit)
        if cfg.exclude_minted
        else set()
    )

    stats, word_file_counts, word_total_counts = _count_corpus(corpus)
    candidates: list[TermCandidate] = []

    for word, total_uses in word_total_counts.items():
        if total_uses < cfg.min_uses or (cfg.exclude_minted and word in excluded_words):
            continue
        candidate = _score_candidate(
            word,
            total_uses,
            word_file_counts[word],
            stats,
            cfg,
        )
        if candidate is not None:
            candidates.append(candidate)

    if cfg.sort_by == "dp":
        candidates.sort(key=lambda c: (c.dp, c.g2, c.uses), reverse=True)
    elif cfg.sort_by == "uses":
        candidates.sort(key=lambda c: (c.uses, c.g2, c.dp), reverse=True)
    else:
        candidates.sort(key=lambda c: (c.g2, c.dp, c.uses), reverse=True)

    if cfg.limit > 0:
        candidates = candidates[: cfg.limit]

    return candidates


def format_table(candidates: Sequence[TermCandidate]) -> str:
    """Format candidate terms into a human-readable text table."""
    if not candidates:
        return "No candidate terms met the configured thresholds."

    lines: list[str] = [
        f"{'Rank':<5} {'Term':<18} {'DP':<6} {'G²':<10} {'Uses':<6} {'Zipf':<5}",
        f"{'-'*5} {'-'*18} {'-'*6} {'-'*10} {'-'*6} {'-'*5}",
    ]
    for i, c in enumerate(candidates, 1):
        lines.append(
            f"{i:<5} {c.term:<18} {c.dp:<6.2f} {c.g2:<10.1f} {c.uses:<6} {c.zipf:<5.2f}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="terms",
        description=(
            "Surface unminted candidate terms by log-likelihood keyness and Gries' DP dispersion."
        ),
    )
    parser.add_argument(
        "--dp",
        type=float,
        default=DEFAULT_MIN_DP,
        help=f"minimum Gries' DP dispersion threshold (default: {DEFAULT_MIN_DP})",
    )
    parser.add_argument(
        "--g2",
        type=float,
        default=DEFAULT_MIN_G2,
        help=f"minimum log-likelihood keyness threshold (default: {DEFAULT_MIN_G2})",
    )
    parser.add_argument(
        "--zipf",
        type=float,
        default=DEFAULT_MIN_ZIPF,
        help=f"minimum English Zipf frequency floor (default: {DEFAULT_MIN_ZIPF})",
    )
    parser.add_argument(
        "--min-uses",
        type=int,
        default=DEFAULT_MIN_USES,
        help=f"minimum occurrences in corpus (default: {DEFAULT_MIN_USES})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"maximum number of candidates to output (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--sort",
        choices=["g2", "dp", "uses"],
        default="g2",
        help="sorting metric for candidate ranking (default: g2)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="output format (default: table)",
    )
    parser.add_argument(
        "--no-exclude",
        action="store_true",
        help="do not exclude minted vocabulary labels",
    )
    parser.add_argument(
        "--commit",
        type=str,
        default=None,
        help="audit a specific git commit tree instead of working directory",
    )
    parser.add_argument(
        "--path",
        type=pathlib.Path,
        default=ROOT,
        help=f"root directory of repository (default: {ROOT})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute candidate term extraction CLI."""
    args = build_parser().parse_args(argv)

    config = TermsConfig(
        min_zipf=args.zipf,
        min_dp=args.dp,
        min_g2=args.g2,
        min_uses=args.min_uses,
        exclude_minted=not args.no_exclude,
        sort_by=args.sort,
        limit=args.limit,
    )

    candidates = extract_candidates(
        root_path=args.path,
        commit=args.commit,
        config=config,
    )

    if args.format == "json":
        print(json.dumps([c.to_dict() for c in candidates], indent=2))
    else:
        print(format_table(candidates))

    return 0


if __name__ == "__main__":
    sys.exit(main())
