"""The report: one mark per pair in the shape A21 reads, and the summary a reader takes from it.
"""



from typing import Any


def report(
    answers: list[tuple[str, str]],
    pairs: list[dict[str, Any]],
    where: str,
    everything: bool,
    sample: bool = False,
) -> int:
    """A21's three lines, from a step that is not a gate.

    One step, one mark. `x` where any pair failed, and the undecided are listed
    under it too, because a run that found one false citation and left four
    unanswered has said two things and a reader needs both. `?` where none
    failed and some could not be decided, which exits zero: the outcome A6
    leaves unmarked is what a step says when it could not answer, and a step
    that answered none of its pairs has found nothing.
    """
    has_ground_moved = any(p.get("ground_moved") for p in pairs)
    if sample:
        scoped = f"a rotating sample of {len(pairs)} citation(s) from the durable set"
    elif everything:
        scoped = "the durable set"
    elif has_ground_moved:
        scoped = f"what this branch wrote or affected over {where}"
    else:
        scoped = f"what this branch wrote over {where}"
    bad = [(p, why) for (mark, why), p in zip(answers, pairs, strict=True) if mark == "x"]
    held = [(p, why) for (mark, why), p in zip(answers, pairs, strict=True) if mark == "?"]

    def lines(items: list[tuple[dict[str, Any], str]], mark: str) -> None:
        for pair, why in items:
            print(f"     {mark} {pair['path']}: {pair['cite']} — {why}")
            print(f"       “{pair['sentence'][:160]}”")

    if bad:
        print(f"x  dereference ({len(bad)})")
        lines(bad, "x")
        lines(held, "?")
        return 1
    if held:
        print(f"?  dereference: {len(held)} of {len(pairs)} citation(s) undecided in {scoped}")
        lines(held, "?")
        return 0
    print(f"ok dereference — {len(pairs)} citation(s) in {scoped}, "
          "each supported by what it names")
    return 0
