"""The command line of `.meta/dereference.py`.

It parses scope flags, the model, and the `--pairs` half that asks nothing.
"""

import argparse
import concurrent.futures

from lib.dereference import asking, reading, report


def main(argv: list[str] | None = None) -> int:
    """Parses arguments and checks cited sentences against the entries they cite.

    Answers `could not run` in both of the ways that happens here — too much to
    ask, and nothing to ask through — loudly, unmarked, and exiting zero, which
    is what Article 6 asks of that outcome; a step that blocks nothing must not
    be able to fail the run that holds it either. There is no third way:
    `credential` always returns something to ask with, and says on stderr which.

    The default cap of 60 pairs guards a bill nobody meant to run up. `--all`
    is nobody's accident — it is the word for asking the whole record — so it
    is not capped by a number chosen for a branch, and the usage block says
    what that costs.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--all",
        action="store_true",
        help="every citation in the durable set, not only this branch's",
    )
    ap.add_argument(
        "--sample",
        nargs="?",
        const=20,
        type=int,
        default=None,
        help="a rotating sample of N citations from the durable set (default 20)",
    )
    ap.add_argument(
        "--base",
        default="origin/main",
        help="what this branch is read against (default origin/main)",
    )
    ap.add_argument(
        "--model", default=asking.MODEL, help=f"the model asked (default {asking.MODEL})"
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="the most pairs to ask about; above it the step does not run "
        "(default 60 over a branch, and no cap under --all)",
    )
    ap.add_argument("--workers", type=int, default=6, help="questions asked at once")
    ap.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="seconds one question may take before it answers `?`",
    )
    ap.add_argument(
        "--pairs",
        action="store_true",
        help="print the pairs and ask nothing: the deterministic half alone",
    )
    args = ap.parse_args(argv)

    chk = reading.citations()
    base = reading.git("merge-base", "HEAD", args.base, default="").strip() or args.base
    pairs = reading.scope(chk, base, args.all, sample=args.sample)
    if args.pairs:
        for pair in pairs:
            print(f"{pair['path']}: {pair['cite']} — {pair['sentence'][:160]}")
        print(f"{len(pairs)} pair(s)")
        return 0
    if not pairs:
        print(
            "ok dereference — no citation written or affected on this branch"
            if not args.sample
            else "ok dereference — no citations in durable set"
        )
        return 0
    limit = args.limit if args.limit is not None else (None if (args.all or args.sample) else 60)
    if limit is not None and len(pairs) > limit:
        print(
            f"?  dereference: {len(pairs)} pairs in scope, above the limit of {limit}; "
            "narrow the scope with --base, raise --limit, or ask the record with --all"
        )
        return 0
    tiers = asking.providers(args.model)
    if not asking.available(tiers):
        print("?  dereference: no eligible reading provider is on PATH")
        return 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        answers = list(pool.map(lambda pair: asking.ask(pair, tiers, args.timeout), pairs))
    return report.report(answers, pairs, base, args.all, sample=bool(args.sample))
