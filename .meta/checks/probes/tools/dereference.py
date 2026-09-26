"""`dereference.py`'s scopes and its report (solorepo's DR-134, solorepo's DR-192)."""

from typing import Any, cast

from checks.collect import META, check
from checks.probes.harness import load_module, outcome


@check("dereference probes", pre=True)
def dereference_probes() -> list[str]:
    """`dereference.py` scopes and reports its citation readings (solorepo's DR-134, DR-192).

    The sample scope, asked for four pairs of the durable set, answers four,
    each carrying its path, citation, sentence and body; asked twice for
    three, it answers the same sentences both times, because the rotation is
    keyed to the commit count and not to a clock. The report, handed one pair
    marked as ground moved, heads itself with what this branch wrote or
    affected; handed the same pair as a sample, with a rotating sample. The
    report's printing is captured, and what it exited with, if it did, is
    reported beside the case. An `x` closes by saying its marks are a model's
    reading to be answered and not asked again, which is what keeps a
    provisional red from teaching the re-run (solorepo's DR-134).
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
            problems.append(
                f"dereference: the report of {case} expected {header!r}, got {shown.out!r}{exited}"
            )

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

    pairs = [
        {
            "path": "foo.md",
            "cite": "solorepo's DR-001",
            "sentence": "Testing claim.",
            "context": "Span",
            "body": "Body",
            "ground_moved": True,
        }
    ]
    heading(
        "a ground-moved pair",
        lambda: deref.report([("ok", "claim")], pairs, "origin/main", False),
        "what this branch wrote or affected",
    )
    heading(
        "a sampled pair",
        lambda: deref.report([("ok", "claim")], pairs, "origin/main", False, sample=True),
        "a rotating sample",
    )
    heading(
        "a failed pair",
        lambda: deref.report([("x", "claim")], pairs, "origin/main", False),
        "not by asking again",
    )

    routed = deref.providers(environ={"GEMINI_FALLBACK": "true"})
    if [tier.harness for tier in routed] != ["claude", "gemini"]:
        problems.append(f"dereference: expected the reviewer reading chain, got {routed!r}")

    problems.extend(_provider_problems(deref, pairs[0], routed))
    return problems


def _provider_problems(deref: Any, pair: dict[str, Any], routed: tuple[Any, ...]) -> list[str]:
    """Return failures in the routed provider fallback contract."""
    calls: list[str] = []
    original_invoke = deref.ask.__globals__["invoke"]

    def invoke_primary_failure(
        pair: dict[str, Any], tier: Any, seconds: int
    ) -> tuple[str, str, bool]:
        calls.append(tier.harness)
        return (
            ("?", "claude unavailable", True)
            if tier.harness == "claude"
            else ("ok", "supported", False)
        )

    answer = _ask_with(deref, pair, routed, invoke_primary_failure, original_invoke)
    problems = []
    if answer != ("ok", "supported") or calls != ["claude", "gemini"]:
        problems.append(f"dereference: primary failure did not reach Gemini fallback: {calls!r}")

    calls.clear()

    def invoke_undecided(pair: dict[str, Any], tier: Any, seconds: int) -> tuple[str, str, bool]:
        calls.append(tier.harness)
        return "?", "the citation needs more context", False

    answer = _ask_with(
        deref,
        pair,
        routed,
        invoke_undecided,
        original_invoke,
    )
    if answer[0] != "?" or calls != ["claude"]:
        problems.append(f"dereference: a valid undecided answer failed over: {calls!r}")

    answer = _ask_with(
        deref,
        pair,
        routed,
        lambda pair, tier, seconds: ("?", f"{tier.harness} unavailable", True),
        original_invoke,
    )
    if answer != ("?", "claude unavailable; gemini unavailable"):
        problems.append(f"dereference: total fallback failure was {answer!r}")
    return problems


def _ask_with(
    deref: Any, pair: dict[str, Any], routed: tuple[Any, ...], invoke: Any, original: Any
) -> tuple[str, str]:
    """Ask after replacing the provider invocation, then restore it."""
    try:
        deref.ask.__globals__["invoke"] = invoke
        return cast(tuple[str, str], deref.ask(pair, routed))
    finally:
        deref.ask.__globals__["invoke"] = original
