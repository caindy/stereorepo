#!/usr/bin/env -S uvx --python 3.13 --with wordfreq python
"""An operator audit instrument that surfaces unminted terms by keyness and dispersion (solorepo's DR-234).

Evaluates candidate terms doing technical work across the repository's durable
prose using two complementary statistical dimensions:
1. Stefan Th. Gries' Deviation of Proportions (DP): measures document locality
   (0 = uniformly distributed, 1 = concentrated in a single file).
2. Log-likelihood keyness (G²): measures statistical overuse relative to general
   English reference frequency obtained from `wordfreq`.

Candidates are words and the multiword phrases up to `--max-n` tokens that
occur within one segment of prose, scored on the same two dimensions against the
reference frequency `wordfreq` supplies for a phrase (solorepo's DR-271). A
markdown file contributes its prose alone: its fenced code blocks and inline code
spans leave the corpus before segmentation, so a shell invocation is no candidate
(solorepo's DR-279).

Filters candidates against a Zipf frequency floor (default >= 3.0) read on that
same reference, so a phrase is measured on its combined value rather than on its
component words', isolating repurposed English vocabulary from novel coinages.
Excludes preferred and alternative labels defined in the Ubiquitous Language
vocabulary assertions before candidate ranking, each label excluding the shape it
is rather than its component words.

Usage:
    just terms                                  # top 30 unminted candidates
    python3 .meta/terms.py                      # direct execution
    python3 .meta/terms.py --dp 0.75 --limit 20 # custom dispersion threshold
    python3 .meta/terms.py --min-n 2            # multiword candidates only
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
DEFAULT_MIN_N: int = 1
DEFAULT_MAX_N: int = 3

TOKEN_PATTERN = re.compile(r"[a-zA-Z]+(?:[\x27-][a-zA-Z]+)*")

SEGMENT_GAP_PATTERN = re.compile(r"[ \t]*")

FENCE_PATTERN = re.compile(r"^[ \t]{0,3}(?P<fence>`{3,}|~{3,})")

INLINE_CODE_PATTERN = re.compile(r"(?P<ticks>`+)[^`\n]*(?P=ticks)")

BOUNDARY_FUNCTION_WORDS: frozenset[str] = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "had", "has", "have",
    "how", "if", "in", "into", "is", "it", "its", "may", "might", "must",
    "no", "nor", "not", "of", "on", "or", "should", "so", "than", "that",
    "the", "their", "them", "then", "there", "these", "they", "this", "those",
    "to", "was", "were", "what", "when", "where", "which", "while", "who",
    "whose", "will", "with", "would", "you", "your",
})

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
    ".claude/skills/search/SKILL.md",
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
    min_n: int = DEFAULT_MIN_N
    max_n: int = DEFAULT_MAX_N


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
    """Extract raw label strings from structured YAML when parser is available.

    A document that will not parse, or whose concept set is not the shape this
    reads, yields no labels, so the caller falls back to the regex parser
    rather than failing.
    """
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
    except (yaml.YAMLError, AttributeError, TypeError):
        return []
    return labels


def _parse_vocab_regex(text: str) -> list[str]:
    """Extract label strings using regex patterns when YAML parser is missing."""
    labels: list[str] = []
    labels.extend(re.findall(r"^\s*pref_label:\s*(.+)$", text, re.MULTILINE))
    for chunk in re.findall(r"^\s*alt_labels:\s*\[(.*?)\]", text, re.MULTILINE):
        labels.extend(part.strip() for part in chunk.split(","))
    labels.extend(re.findall(r"^\s*-\s*([A-Za-z0-9 _-]+)$", text, re.MULTILINE))
    return labels


class VocabExclusions(NamedTuple):
    """The minted vocabulary, separated by the shape of candidate each label excludes."""

    words: frozenset[str]
    phrases: frozenset[str]

    def excludes(self, term: str) -> bool:
        """Report whether a minted label already covers this candidate term."""
        return term in (self.phrases if " " in term else self.words)


def _inflections(word: str) -> tuple[str, str]:
    """Pair a word with its standard singular or plural counterpart."""
    return (word, word[:-1] if word.endswith("s") else word + "s")


def _label_tokens(raw_label: str) -> list[str]:
    """Reduce a vocabulary label to the token sequence a candidate would carry.

    A parenthesised qualifier disambiguates the label for a reader and is no part
    of the term, so `Skill (APM primitive)` reduces to the single word `skill`.
    """
    return [t.lower() for t in TOKEN_PATTERN.findall(re.sub(r"\(.*?\)", " ", raw_label))]


def extract_vocab_exclusions(
    root_path: pathlib.Path,
    commit: str | None = None,
) -> VocabExclusions:
    """Extract exclusions from the preferred and alternative labels of vocabulary assertions.

    Reads `.meta/assertions/imported/vocabulary.yaml` and
    `.meta/assertions/vocabulary.yaml`. A single-word label excludes that word
    and its standard inflections. A multiword label excludes the phrase it is,
    every phrase contained within it, and each of their inflections. It never
    excludes its component words, so minting *Dev Loop* leaves `loop` a candidate
    (solorepo's DR-271).
    """
    vocab_files = [
        ".meta/assertions/imported/vocabulary.yaml",
        ".meta/assertions/vocabulary.yaml",
    ]
    excluded_words: set[str] = set()
    excluded_phrases: set[str] = set()

    for rel_path in vocab_files:
        text = _read_vocab_content(root_path, rel_path, commit)
        if not text:
            continue
        labels = _parse_vocab_yaml(text) or _parse_vocab_regex(text)
        for raw_label in labels:
            tokens = _label_tokens(raw_label)
            if len(tokens) == 1:
                if len(tokens[0]) > 2:
                    excluded_words.update(_inflections(tokens[0]))
                continue
            for width in range(2, len(tokens) + 1):
                for start in range(len(tokens) - width + 1):
                    window = tokens[start : start + width]
                    for last in _inflections(window[-1]):
                        excluded_phrases.add(" ".join([*window[:-1], last]))

    return VocabExclusions(words=frozenset(excluded_words), phrases=frozenset(excluded_phrases))


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


def strip_code(text: str) -> str:
    """Remove fenced code blocks and inline code spans from markdown text.

    A fenced block opens on a line of three or more backticks or tildes indented by
    no more than three spaces or tabs, and closes on the next line carrying at least
    as many of that same character, end of file closing an unterminated one. Every
    line of the block, its fences included, becomes empty.

    An inline span becomes the single backtick that bounded it, which is the run
    boundary `segment` already reads, so dropping the span's tokens leaves the prose
    on its two sides two runs rather than one. A span is bounded by equal runs of
    backticks on one line and holds no backtick of its own, which is every span the
    corpus carries; one written to quote a backtick keeps its words.
    """
    kept: list[str] = []
    fence: str | None = None

    for line in text.split("\n"):
        match = FENCE_PATTERN.match(line)
        delimiter = match.group("fence") if match is not None else None
        if fence is None:
            if delimiter is None:
                kept.append(INLINE_CODE_PATTERN.sub("`", line))
                continue
            fence = delimiter
        elif delimiter is not None and delimiter[0] == fence[0] and len(delimiter) >= len(fence):
            fence = None
        kept.append("")

    return "\n".join(kept)


def prose(rel_path: str, content: str) -> str:
    """Reduce one corpus file to the prose its candidates may be drawn from.

    A markdown file loses its fenced code blocks and inline code spans, which
    hold shell invocations and identifiers rather than phrases a reader would
    call a phrase (solorepo's DR-279). An assertion YAML file is read whole, so
    that the structural vocabulary of the assertions keeps contributing.
    """
    return strip_code(content) if rel_path.endswith(".md") else content


def segment(text: str) -> list[list[str]]:
    """Split text into the runs of adjacent word tokens a phrase may be drawn from.

    A token carries its internal apostrophes and hyphens, so `Drive-by` is one
    token rather than two. Two tokens belong to the same run when nothing but
    spaces or tabs separates them; a line ending, a comma, a backtick, a digit or
    a bullet ends the run. A line is therefore the widest a phrase may be, which
    costs the occurrences a hard wrap splits and refuses every phrase that exists
    only as two structural lines abutting — the `status: ADOPTED` of one
    assertion line and the `applies:` of the next (solorepo's DR-271).
    """
    runs: list[list[str]] = []
    current: list[str] = []
    previous_end: int | None = None

    for match in TOKEN_PATTERN.finditer(text):
        if previous_end is not None:
            gap = text[previous_end : match.start()]
            if not SEGMENT_GAP_PATTERN.fullmatch(gap):
                runs.append(current)
                current = []
        current.append(match.group(0).lower())
        previous_end = match.end()

    if current:
        runs.append(current)
    return runs


def tokenize(text: str) -> list[str]:
    """Extract lowercase word tokens from text, in order and across segment boundaries."""
    return [token for run in segment(text) for token in run]


def iter_terms(text: str, max_n: int = DEFAULT_MAX_N) -> list[str]:
    """List every candidate term occurrence in text, words first and then phrases.

    A phrase of two or more tokens is admitted only within one segment and only
    when neither its first nor its last token is a closed-class function word,
    the linguistic filter that keeps a fragment of a longer construction — *the
    pull*, *definition of* — from being proposed as a term (solorepo's DR-271).
    """
    return _terms_in_runs(segment(text), max_n)


def _terms_in_runs(runs: list[list[str]], max_n: int) -> list[str]:
    """List candidate term occurrences across already segmented token runs."""
    terms: list[str] = []
    for run in runs:
        terms.extend(run)
        for width in range(2, max_n + 1):
            for start in range(len(run) - width + 1):
                window = run[start : start + width]
                if window[0] in BOUNDARY_FUNCTION_WORDS or window[-1] in BOUNDARY_FUNCTION_WORDS:
                    continue
                terms.append(" ".join(window))
    return terms


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


def _count_corpus(
    corpus: dict[str, str],
    max_n: int = DEFAULT_MAX_N,
) -> tuple[CorpusStats, dict[str, dict[str, int]], Counter[str]]:
    """Compute token lengths, candidate term file distribution, and global counts.

    File length and corpus total are counted in words whatever `max_n` is, so a
    phrase's dispersion and expected count are measured against the same corpus
    size a word's are. Each file is read through `prose`, so a markdown file's
    code contributes to neither its length nor its candidates (solorepo's DR-279).
    """
    file_lengths: dict[str, int] = {}
    term_file_counts: dict[str, dict[str, int]] = {}
    term_total_counts: Counter[str] = Counter()
    total_tokens = 0

    for file_path, content in corpus.items():
        runs = segment(prose(file_path, content))
        words = sum(len(run) for run in runs)
        if not words:
            continue
        file_lengths[file_path] = words
        total_tokens += words
        for term, count in Counter(_terms_in_runs(runs, max_n)).items():
            if term not in term_file_counts:
                term_file_counts[term] = {}
            term_file_counts[term][file_path] = count
            term_total_counts[term] += count

    stats = CorpusStats(file_lengths=file_lengths, total_tokens=total_tokens)
    return stats, term_file_counts, term_total_counts


def _score_candidate(
    term: str,
    total_uses: int,
    term_files: dict[str, int],
    stats: CorpusStats,
    config: TermsConfig,
) -> TermCandidate | None:
    """Evaluate candidate thresholds for a single word or phrase.

    `wordfreq` supplies the reference frequency of a multi-token string by
    combining its tokens as `1 / f = 1 / f1 + 1 / f2 + …`, returning zero where
    any token is absent from the wordlist, so a phrase built on a coinage is
    refused by the same Zipf floor that refuses the coinage (solorepo's DR-271).
    The combination sits below the rarest token's own frequency, so the floor
    asks more of a phrase than that each of its words clear `min_zipf`.
    """
    if wordfreq is not None:
        zipf = float(wordfreq.zipf_frequency(term, "en"))
        ref_freq = float(wordfreq.word_frequency(term, "en"))
    else:
        zipf = 4.0
        ref_freq = 1e-5

    if zipf < config.min_zipf or ref_freq <= 0:
        return None

    dp = compute_gries_dp(term_files, stats.file_lengths, stats.total_tokens, total_uses)
    if dp < config.min_dp:
        return None

    g2 = compute_log_likelihood(total_uses, stats.total_tokens, ref_freq)
    if g2 < config.min_g2:
        return None

    return TermCandidate(term=term, dp=dp, g2=g2, uses=total_uses, zipf=zipf)


def extract_candidates(
    corpus: dict[str, str] | None = None,
    root_path: pathlib.Path | None = None,
    commit: str | None = None,
    config: TermsConfig | None = None,
) -> list[TermCandidate]:
    """Analyze corpus files to surface unminted words and phrases by keyness and dispersion."""
    cfg = config or TermsConfig()
    target_root = root_path if root_path is not None else ROOT
    if corpus is None:
        corpus = load_corpus(target_root, commit=commit)

    minted = (
        extract_vocab_exclusions(target_root, commit=commit)
        if cfg.exclude_minted
        else VocabExclusions(words=frozenset(), phrases=frozenset())
    )

    stats, term_file_counts, term_total_counts = _count_corpus(corpus, cfg.max_n)
    candidates: list[TermCandidate] = []

    for term, total_uses in term_total_counts.items():
        if total_uses < cfg.min_uses or len(term.split()) < cfg.min_n:
            continue
        if cfg.exclude_minted and minted.excludes(term):
            continue
        candidate = _score_candidate(
            term,
            total_uses,
            term_file_counts[term],
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

    width = max(18, *(len(c.term) for c in candidates))
    lines: list[str] = [
        f"{'Rank':<5} {'Term':<{width}} {'DP':<6} {'G²':<10} {'Uses':<6} {'Zipf':<5}",
        f"{'-'*5} {'-'*width} {'-'*6} {'-'*10} {'-'*6} {'-'*5}",
    ]
    for i, c in enumerate(candidates, 1):
        lines.append(
            f"{i:<5} {c.term:<{width}} {c.dp:<6.2f} {c.g2:<10.1f} {c.uses:<6} {c.zipf:<5.2f}"
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
        "--min-n",
        type=int,
        default=DEFAULT_MIN_N,
        help=f"minimum tokens per candidate; 2 reports phrases only (default: {DEFAULT_MIN_N})",
    )
    parser.add_argument(
        "--max-n",
        type=int,
        default=DEFAULT_MAX_N,
        help=f"maximum tokens per candidate phrase (default: {DEFAULT_MAX_N})",
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
        min_n=args.min_n,
        max_n=args.max_n,
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
