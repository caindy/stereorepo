"""The command line of `.meta/search.py`: a query with its limit and format, or `--benchmark`.
"""
import argparse
import json
import sys

from lib.search import META, ROOT, benchmark, build


def main() -> None:
    """CLI entrypoint for search and benchmark evaluation."""
    parser = argparse.ArgumentParser(
        description="Search repository assertions, decisions, and wiki by meaning (BM25, stereorepo's DR-103, stereorepo's DR-337, stereorepo's DR-338)."
    )
    parser.add_argument("query", nargs="*", help="Query terms to search for")
    parser.add_argument("--limit", type=int, default=5, help="Number of results to return (default 5)")
    parser.add_argument("--detail", action="store_true", help="Print full snippet context")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--benchmark", action="store_true", help="Run the 18 evaluation benchmark queries (stereorepo's DR-103)")

    args = parser.parse_args()

    index = build.build_index(META, ROOT)

    if args.benchmark:
        sys.exit(benchmark.run_benchmark(index))

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
