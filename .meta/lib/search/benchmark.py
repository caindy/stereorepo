"""The benchmark: the queries the index must answer with a known object near the top, and the count of those it does (solorepo's DR-194).
"""

from lib.search import bm25


def run_benchmark(index: bm25.SearchIndex) -> int:
    """Run the 18 evaluation benchmark queries from Challenge 18 (solorepo's DR-194).

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

    print(f"Running BM25 evaluation over {len(active_queries)} benchmark queries (solorepo's DR-194):\n")
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
