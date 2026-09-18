"""`terms.py`'s unminted candidate extraction, keyness, and dispersion probes (solorepo's DR-234).
"""

import subprocess

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
    3. The labelled positive fixture (pre-solorepo's #581 tree, commit `8ba43766~1` or
       in-memory equivalent) surfaces `receipt` in the candidate rankings.
    4. The labelled negative fixture (post-solorepo's #581 tree, current HEAD) excludes
       minted `evidence` from the candidate rankings.
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

    head_candidates = terms.extract_candidates(
        root_path=ROOT,
        config=terms.TermsConfig(min_zipf=3.0, min_dp=0.70, min_g2=10.83, min_uses=5, limit=50),
    )
    head_terms = {c.term for c in head_candidates}
    if "evidence" in head_terms:
        problems.append("terms: minted label 'evidence' was not excluded from post-solorepo's #581 candidates")

    has_pre_commit = False
    try:
        subprocess.check_output(
            ["git", "rev-parse", "--verify", "8ba43766~1"],
            stderr=subprocess.DEVNULL,
            cwd=str(ROOT),
        )
        has_pre_commit = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    if has_pre_commit:
        pre_candidates = terms.extract_candidates(
            root_path=ROOT,
            commit="8ba43766~1",
            config=terms.TermsConfig(min_zipf=3.0, min_dp=0.70, min_g2=10.83, min_uses=5, limit=50),
        )
        pre_terms = [c.term for c in pre_candidates]
        if "receipt" not in pre_terms:
            problems.append(f"terms: unminted term 'receipt' missing from pre-solorepo's #581 top candidates: {pre_terms[:10]}")
    else:
        synth_corpus = {
            "file1.md": "receipt receipt receipt receipt receipt receipt receipt receipt",
            "file2.md": "receipt receipt receipt receipt receipt receipt receipt receipt",
            "file3.md": "an ordinary file with normal prose and standard words",
            "file4.md": "another file discussing unrelated implementation details",
        }
        synth_candidates = terms.extract_candidates(
            corpus=synth_corpus,
            root_path=ROOT,
            config=terms.TermsConfig(min_zipf=3.0, min_dp=0.45, min_g2=1.0, min_uses=3, limit=10),
        )
        synth_terms = [c.term for c in synth_candidates]
        if "receipt" not in synth_terms:
            problems.append("terms: 'receipt' failed to surface in synthetic positive fixture")

    return problems
