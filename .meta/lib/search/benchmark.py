"""The benchmark: the queries the index must answer with a known object near the top, and the count of those it does (stereorepo's DR-194).
"""

from lib.search import bm25


def run_benchmark(index: bm25.SearchIndex) -> int:
    """Run the 18 evaluation benchmark queries (stereorepo's DR-194).

    Returns 0 where hit@5 reaches 15 of the 18 queries. A portfolio holds a
    different record and so a different subset of the targets, and a query whose
    targets are all absent is dropped rather than counted as a miss; the
    threshold there is 80% of what remains.
    """
    queries: list[tuple[str, list[str]]] = [
        (
            "what has been decided about naming",
            ["work:decision/078", "work:decision/065", "work:discipline/written-decisions"],
        ),
        (
            "which rules bear on generated files",
            ["work:discipline/seeded-artifacts", "work:decision/034"],
        ),
        (
            "which directory says what stage an issue is in",
            ["work:concept/stage", "work:concept/board", "work:concept/issue"],
        ),
        (
            "has anyone argued for a search index over the record before",
            ["work:decision/103", "work:decision/077"],
        ),
        (
            "why can't I put reasoning in a commit message",
            ["work:article/14", "work:discipline/journaling"],
        ),
        (
            "how does a seat agree with the other seat",
            ["work:concept/quiet-turn", "work:concept/seat"],
        ),
        (
            "why are there no dates in the decision record",
            ["work:decision/081", "work:decision/049", "work:discipline/written-decisions"],
        ),
        (
            "who moves an issue from one stage to the next",
            ["work:concept/supervisor", "work:concept/stage", "work:concept/board"],
        ),
        (
            "how does a portfolio get updates from the scaffold",
            ["work:portfolio/stereorepo", "work:discipline/specialization"],
        ),
        (
            "which issues wait for the developer to check them by hand",
            ["work:concept/desk-check", "work:concept/developer"],
        ),
        (
            "what is the difference between a seat and the developer",
            ["work:concept/seat", "work:concept/developer"],
        ),
        (
            "where do things noticed but not done go",
            ["work:discipline/journaling", "work:concept/journaling"],
        ),
        (
            "why is there a stakeholders directory",
            ["work:decision/041", "work:artifact/stakeholders-readme", "work:decision/040"],
        ),
        (
            "which languages can a new portfolio choose",
            ["work:discipline/specialization", "work:decision/046", "work:decision/014", "work:decision/326"],
        ),
        (
            "what makes the scaffold its own product",
            ["work:portfolio/stereorepo", "work:product/scaffold", "work:decision/030"],
        ),
        (
            "I finished a task and there is leftover work, what do I do with it",
            ["work:discipline/journaling", "work:concept/journaling"],
        ),
        (
            "an old rule no longer applies, how is it retired",
            ["work:decision/085", "work:decision/070"],
        ),
        (
            "why is an issue a file and not a GitHub Issue",
            ["work:concept/issue", "work:concept/board"],
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

    print(f"Running BM25 evaluation over {len(active_queries)} benchmark queries (stereorepo's DR-194):\n")
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

    min_hits = 15 if n >= 18 else int(0.8 * n)
    return 0 if hits_5 >= min_hits else 1
