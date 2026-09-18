"""`search.py`'s index and its benchmark (solorepo's DR-103).
"""
import contextlib
import io

from checks.collect import META, ROOT, check
from checks.probes.harness import load_module


@check("search probes", pre=True)
def search_probes():
    """`search.py` indexes the assertions and the wiki, ranks by Okapi BM25F over three fields, and meets the retrieval benchmark (solorepo's DR-103, solorepo's DR-194, solorepo's DR-195).

    The index built over `.meta/assertions/` and `wiki/` holds at least a
    hundred documents. Asked who is allowed to push to trunk, the top five
    hold Article 18, solorepo's DR-100 or solorepo's DR-072; asked for
    leftover work, they hold the Concept noticed-and-not-done or
    solorepo's DR-195, the Decision that minted that ingress alias. The
    eighteen-query benchmark passes at hit@5 of fifteen or better; its
    printing is silenced, because its return value is the verdict. And a
    result's dictionary carries `id`, `score` and `source_file`.
    """
    search = load_module(META / "search.py", "search", register=False)
    problems = []
    index = search.build_index(META, ROOT)
    if len(index.docs) < 100:
        problems.append(f"search: index populated too few documents ({len(index.docs)})")

    results = index.search("who is allowed to push to trunk", top_k=5)
    ranked = [res.identifier for res in results]
    if not any(ident in ranked for ident in ("work:article/18", "work:decision/100", "work:decision/072")):
        problems.append("search: 'who is allowed to push to trunk' expected solorepo's Article 18, "
                        f"solorepo's DR-100, or solorepo's DR-072 in top 5, got {ranked}")
    leftover = [res.identifier for res in index.search("leftover work", top_k=5)]
    if "work:concept/noticed-and-not-done" not in leftover and "work:decision/195" not in leftover:
        problems.append(f"search: 'leftover work' expected noticed-and-not-done in top 5, got {leftover}")

    with contextlib.redirect_stdout(io.StringIO()):
        failed = search.run_benchmark(index)
    if failed != 0:
        problems.append(f"search: solorepo's DR-103 benchmark failed {failed} queries "
                        "below threshold (hit@5 >= 15/18)")

    if results:
        shown = results[0].to_dict()
        if not ("id" in shown and "score" in shown and "source_file" in shown):
            problems.append(f"search: SearchResult dictionary missing expected fields: {shown}")
    return problems
