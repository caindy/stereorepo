"""`dereference.py`'s scopes and its report (stereorepo's DR-134, stereorepo's DR-192)."""

from typing import Any, cast

from checks.collect import META, check
from checks.probes.harness import load_module, outcome


@check("dereference probes", pre=True)
def dereference_probes() -> list[str]:
    """`dereference.py` scopes and reports its citation readings (stereorepo's DR-134, DR-192).

    The sample scope, asked for four pairs of the durable set, answers four,
    each carrying its path, citation, sentence and body; asked twice for
    three, it answers the same sentences both times, because the rotation is
    keyed to the commit count and not to a clock. Over a record holding fewer
    pairs than that, as a portfolio's does, it answers each pair once. The report, handed one pair
    marked as ground moved, heads itself with what this branch wrote or
    affected; handed the same pair as a sample, with a rotating sample. The
    report's printing is captured, and what it exited with, if it did, is
    reported beside the case. An `x` closes by saying its marks are a model's
    reading to be answered and not asked again, which is what keeps a
    provisional red from teaching the re-run (stereorepo's DR-134).
    """
    deref = load_module(META / "dereference.py", "dereference", register=False)
    citations_mod = deref.citations()
    decisions = META / "assertions" / "decisions"
    sample_durable = {path for i in range(1, 10)
                      if (path := decisions / f"DR-00{i}.yaml").is_file()}
    problems = _sample_problems(deref, citations_mod, sample_durable)
    problems += _sample_problems(deref, citations_mod, {decisions / "DR-001.yaml"})

    def heading(case: str, call: Any, header: str) -> None:
        """One problem naming `case` unless the report `call` prints carries `header`."""
        shown = outcome(call)
        if header not in shown.out:
            exited = f" (exited {shown.code})" if shown.code is not None else ""
            problems.append(
                f"dereference: the report of {case} expected {header!r}, got {shown.out!r}{exited}"
            )

    pairs = [
        {
            "path": "foo.md",
            "cite": "stereorepo's DR-001",
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

    problems.extend(_ask_problems(deref, pairs[0]))
    return problems


def _sample_problems(deref: Any, citations_mod: Any, durable: set[Any]) -> list[str]:
    """Return failures in the sample scope over `durable`, which may hold fewer pairs than asked.

    Asked for four pairs, the scope answers four, or every pair the record
    holds where it holds fewer, each once and each carrying its path,
    citation, sentence and body. Asked twice for three, it answers the same
    sentences both times.
    """
    names = ", ".join(sorted(path.name for path in durable))
    available = len(deref.scope(citations_mod, "origin/main", True, durable=durable))
    if not available:
        return [f"dereference: {names} holds no pair to sample"]
    problems = []
    four = deref.scope(citations_mod, "origin/main", False, sample=4, durable=durable)
    if len(four) != min(4, available):
        held = f"{available} pair{'s' if available != 1 else ''}"
        problems.append(f"dereference: sample=4 over {names}, which holds {held}, "
                        f"expected {min(4, available)}, got {len(four)}")
    if len({(p["cite"], p["sentence"]) for p in four}) != len(four):
        problems.append(f"dereference: sample=4 over {names} answered a pair twice")
    for pair in four:
        if not ("path" in pair and "cite" in pair and "sentence" in pair and "body" in pair):
            problems.append(f"dereference: sample pair missing required keys: {pair}")
    first = deref.scope(citations_mod, "origin/main", False, sample=3, durable=durable)
    again = deref.scope(citations_mod, "origin/main", False, sample=3, durable=durable)
    if [p["sentence"] for p in first] != [p["sentence"] for p in again]:
        problems.append(f"dereference: identical sample queries over {names} "
                        "produced different results")
    return problems


def _ask_problems(deref: Any, pair: dict[str, Any]) -> list[str]:
    """Return failures in how `ask` reads the model's one-line answer."""
    problems = []
    original = deref.ask.__globals__["subprocess"]

    class Done:
        """A stand-in for a finished `claude -p` process."""

        def __init__(self, stdout: str, returncode: int = 0) -> None:
            self.stdout, self.stderr, self.returncode = stdout, "", returncode

    for stdout, code, want in (
        ("ok the words\n", 0, ("ok", "the words")),
        ("x it says otherwise\n", 0, ("x", "it says otherwise")),
        ("maybe\n", 0, "?"),
        ("", 1, "?"),
    ):

        class Fake:
            """Replaces `subprocess` inside `ask` for one answer."""

            TimeoutExpired = original.TimeoutExpired
            result = Done(stdout, code)

            @classmethod
            def run(cls, *_args: Any, **_kwargs: Any) -> Done:
                return cls.result

        try:
            deref.ask.__globals__["subprocess"] = Fake
            answer = cast(tuple[str, str], deref.ask(pair))
        finally:
            deref.ask.__globals__["subprocess"] = original
        got = answer if isinstance(want, tuple) else answer[0]
        if got != want:
            problems.append(f"dereference: {stdout!r} (exit {code}) read as {answer!r}")
    return problems
