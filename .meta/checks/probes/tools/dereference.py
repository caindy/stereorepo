"""`dereference.py`'s scopes and its report (solorepo's DR-134, solorepo's DR-192).
"""

from typing import Any

from checks.collect import META, check
from checks.probes.harness import load_module, outcome


@check("dereference probes", pre=True)
def dereference_probes() -> list[str]:
    """`dereference.py` extracts citation pairs across the diff, sample and ground-moved scopes, and heads its report by the scope it read (solorepo's DR-134, solorepo's DR-192).

    The sample scope, asked for four pairs of the durable set, answers four,
    each carrying its path, citation, sentence and body; asked twice for
    three, it answers the same sentences both times, because the rotation is
    keyed to the commit count and not to a clock. The report, handed one pair
    marked as ground moved, heads itself with what this branch wrote or
    affected; handed the same pair as a sample, with a rotating sample. The
    report's printing is captured, and what it exited with, if it did, is
    reported beside the case.
    """
    deref = load_module(META / "dereference.py", "dereference", register=False)
    citations_mod = deref.citations()
    sample_durable = {META / "assertions" / "decisions" / f"DR-00{i}.yaml" for i in range(1, 10)}
    problems = []

    def heading(case: str, call: Any, header: str) -> None:
        """One problem naming `case` unless the report `call` prints carries `header`."""
        shown = outcome(call)
        if header not in shown.out:
            exited = f" (exited {shown.code})" if shown.code is not None else ""
            problems.append(f"dereference: the report of {case} expected {header!r}, "
                            f"got {shown.out!r}{exited}")

    four = deref.scope(citations_mod, "origin/main", False, sample=4, durable=sample_durable)
    if len(four) != 4:
        problems.append(f"dereference: sample=4 expected 4 pairs, got {len(four)}")
    for pair in four:
        if not ("path" in pair and "cite" in pair and "sentence" in pair and "body" in pair):
            problems.append(f"dereference: sample pair missing required keys: {pair}")
    first = deref.scope(citations_mod, "origin/main", False, sample=3, durable=sample_durable)
    again = deref.scope(citations_mod, "origin/main", False, sample=3, durable=sample_durable)
    if [p["sentence"] for p in first] != [p["sentence"] for p in again]:
        problems.append("dereference: identical sample queries produced different results")

    pairs = [{"path": "foo.md", "cite": "solorepo's DR-001", "sentence": "Testing claim.",
              "context": "Span", "body": "Body", "ground_moved": True}]
    heading("a ground-moved pair",
            lambda: deref.report([("ok", "claim")], pairs, "origin/main", False),
            "what this branch wrote or affected")
    heading("a sampled pair",
            lambda: deref.report([("ok", "claim")], pairs, "origin/main", False, sample=True),
            "a rotating sample")
    return problems
