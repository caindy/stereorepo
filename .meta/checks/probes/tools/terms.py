"""`terms.py`'s unminted candidate extraction, keyness, and dispersion probes (solorepo's DR-234).

Covers multiword candidacy and phrase-shaped exclusion under solorepo's DR-271.
"""

from checks.collect import META, ROOT, check
from checks.probes.harness import load_module


@check("terms probes", pre=True)
def terms_probes() -> list[str]:
    """`terms.py` surfaces unminted terms by keyness and dispersion (solorepo's DR-234).

    Validates that:
    1. Gries' DP dispersion equals 0.0 for a flat distribution and approaches
       1.0 for a maximally concentrated distribution.
    2. Log-likelihood keyness G² evaluates to 0.0 when observed occurrences do
       not exceed expected reference occurrences.
    3. The labelled positive fixture (pre-solorepo's #581 tree or in-memory
       equivalent) surfaces `receipt` in the candidate rankings.
    4. The labelled negative fixture (post-solorepo's #581 tree or in-memory
       equivalent) excludes minted `evidence` from the candidate rankings.
    """
    terms = load_module(META / "terms.py", "terms", register=False)
    problems: list[str] = []

    flat_occurrences = {"f1.md": 10, "f2.md": 10}
    flat_lengths = {"f1.md": 100, "f2.md": 100}
    dp_flat = terms.compute_gries_dp(flat_occurrences, flat_lengths, 200, 20)
    if abs(dp_flat) > 1e-6:
        problems.append(f"terms: expected DP == 0.0 for flat distribution, got {dp_flat}")

    conc_occurrences = {"f1.md": 20, "f2.md": 0}
    conc_lengths = {"f1.md": 20, "f2.md": 180}
    dp_conc = terms.compute_gries_dp(conc_occurrences, conc_lengths, 200, 20)
    if dp_conc < 0.85:
        problems.append(f"terms: expected DP >= 0.85 for concentrated distribution, got {dp_conc}")

    g2_under = terms.compute_log_likelihood(5, 1000000, 1e-4)
    if g2_under != 0.0:
        problems.append(f"terms: expected G² == 0.0 for underrepresented term, got {g2_under}")

    g2_over = terms.compute_log_likelihood(500, 100000, 1e-4)
    if g2_over <= 0.0:
        problems.append(f"terms: expected G² > 0.0 for overrepresented term, got {g2_over}")

    synth_neg = {
        "file1.md": "evidence evidence evidence evidence token token token token",
        "file2.md": "evidence evidence evidence evidence token token token token",
        "file3.md": "an ordinary file with normal prose and standard words",
        "file4.md": "another file discussing unrelated implementation details",
    }
    neg_candidates = terms.extract_candidates(
        corpus=synth_neg,
        root_path=ROOT,
        config=terms.TermsConfig(min_zipf=3.0, min_dp=0.45, min_g2=1.0, min_uses=3, limit=10),
    )
    neg_terms = {c.term for c in neg_candidates}
    if "evidence" in neg_terms:
        problems.append("terms: minted label 'evidence' was not excluded from post-solorepo's #581 candidates")

    synth_pos = {
        "file1.md": "receipt receipt receipt receipt receipt receipt receipt receipt",
        "file2.md": "receipt receipt receipt receipt receipt receipt receipt receipt",
        "file3.md": "an ordinary file with normal prose and standard words",
        "file4.md": "another file discussing unrelated implementation details",
    }
    synth_candidates = terms.extract_candidates(
        corpus=synth_pos,
        root_path=ROOT,
        config=terms.TermsConfig(min_zipf=3.0, min_dp=0.45, min_g2=1.0, min_uses=3, limit=10),
    )
    synth_terms = [c.term for c in synth_candidates]
    if "receipt" not in synth_terms:
        problems.append("terms: 'receipt' failed to surface in synthetic positive fixture")

    return problems


PHRASE_FILLER = (
    "an ordinary file of normal prose using standard words and nothing that any "
    "reader would take for a term of art in this repository or in another one"
)

PHRASE_CORPUS: dict[str, str] = {
    "phrase1.md": "Bounded context bounded context bounded context bounded context",
    "phrase2.md": "bounded context bounded context bounded context bounded context",
    "word1.md": "loop loop loop loop loop loop loop loop",
    "word2.md": "loop loop loop loop loop loop loop loop",
    "filler1.md": PHRASE_FILLER,
    "filler2.md": PHRASE_FILLER,
}

FLOOR_CORPUS: dict[str, str] = {
    "floor1.md": "Adaptable scaffold adaptable scaffold adaptable scaffold adaptable scaffold",
    "floor2.md": "adaptable scaffold adaptable scaffold adaptable scaffold adaptable scaffold",
    "filler1.md": PHRASE_FILLER,
    "filler2.md": PHRASE_FILLER,
}

STUB_ZIPF: dict[str, float] = {
    "adaptable": 3.12,
    "scaffold": 3.03,
    "adaptable scaffold": 2.77,
}


class StubWordfreq:
    """A reference standing in for `wordfreq` at the boundary the floor decides.

    The gate's interpreter carries no `wordfreq` — `terms.py` fetches it through
    its own `uvx` shebang — so the floor is probed against a stub holding the
    relation the library documents and solorepo's DR-271 relies on: a phrase's
    combined frequency sits below the rarest of its tokens. The three entries are
    the values `wordfreq` returns for them, so the probe refuses the same phrase
    the instrument refuses.
    """

    def zipf_frequency(self, term: str, lang: str) -> float:
        """Report the reference Zipf frequency of a word or phrase."""
        return STUB_ZIPF.get(term, 5.0)

    def word_frequency(self, term: str, lang: str) -> float:
        """Report the reference relative frequency of a word or phrase."""
        return 10 ** (self.zipf_frequency(term, lang) - 9)


@check("terms phrase probes", pre=True)
def terms_phrase_probes() -> list[str]:
    """`terms.py` proposes phrases and excludes a minted label as one (solorepo's DR-271).

    Validates that:
    1. A token keeps its internal hyphen, so `drive-by` is one candidate rather
       than the two words `drive` and `by`.
    2. A phrase is drawn only from tokens sharing a line, so two structural lines
       abutting propose nothing.
    3. A phrase whose first or last token is a closed-class function word is
       never proposed.
    4. A phrase concentrated in the files covering its subject surfaces in the
       rankings once exclusion is off, and is excluded once it is on, so the same
       term turns on the minting alone.
    5. A minted multiword label no longer excludes its component words: minting
       *Dev Loop* leaves `loop` a candidate.
    6. The Zipf floor reads the phrase's own combined reference rather than each
       component word's, against `StubWordfreq`: `adaptable scaffold`, whose
       words sit at Zipf 3.12 and 3.03 and whose combination sits at 2.77, is
       refused at a floor of 3.0 and admitted at one of 2.5.
    """
    terms = load_module(META / "terms.py", "terms", register=False)
    problems: list[str] = []

    tokens = terms.tokenize("a Drive-by commit")
    if tokens != ["a", "drive-by", "commit"]:
        problems.append(f"terms: expected a hyphenated token, got {tokens}")

    runs = terms.segment("status: ADOPTED\n    applies:")
    if runs != [["status"], ["adopted"], ["applies"]]:
        problems.append(f"terms: expected one run per line, got {runs}")

    admitted = terms.iter_terms("the pull request definition of done", max_n=3)
    fragments = ("the pull", "definition of", "of done", "the pull request")
    refused = [t for t in fragments if t in admitted]
    if refused:
        problems.append(f"terms: function-word boundary failed to refuse {refused}")
    if "pull request definition" not in admitted:
        problems.append(f"terms: expected a content-word trigram among {admitted}")

    surfaced = {
        c.term
        for c in terms.extract_candidates(
            corpus=PHRASE_CORPUS,
            root_path=ROOT,
            config=terms.TermsConfig(limit=0),
        )
    }
    if "bounded context" in surfaced:
        problems.append("terms: minted label 'bounded context' was not excluded as a phrase")
    if "loop" not in surfaced:
        problems.append("terms: minting 'Dev Loop' still hides the word 'loop' from candidacy")

    unminted = terms.extract_candidates(
        corpus=PHRASE_CORPUS,
        root_path=ROOT,
        config=terms.TermsConfig(exclude_minted=False, limit=0),
    )
    if "bounded context" not in {c.term for c in unminted}:
        problems.append("terms: 'bounded context' failed to surface as a multiword candidate")

    reference = terms.wordfreq
    terms.__dict__["wordfreq"] = StubWordfreq()
    try:
        at_floor = {
            c.term
            for c in terms.extract_candidates(
                corpus=FLOOR_CORPUS,
                root_path=ROOT,
                config=terms.TermsConfig(min_zipf=3.0, limit=0),
            )
        }
        under_floor = {
            c.term
            for c in terms.extract_candidates(
                corpus=FLOOR_CORPUS,
                root_path=ROOT,
                config=terms.TermsConfig(min_zipf=2.5, limit=0),
            )
        }
    finally:
        terms.__dict__["wordfreq"] = reference

    if "adaptable scaffold" in at_floor:
        problems.append("terms: a phrase under the Zipf floor was scored on its component words")
    if "adaptable scaffold" not in under_floor:
        problems.append("terms: 'adaptable scaffold' failed to surface with the Zipf floor lowered")

    return problems
