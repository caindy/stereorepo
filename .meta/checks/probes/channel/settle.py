"""`act`, `shown` and `settled` over a GitHub that shows a write late, or never (solorepo's DR-264).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import functools
from typing import Any

from checks.collect import check
from checks.probes.harness import FakeIssue, answered, environment, load_channel, run_verb, stood_in

BOUND = (2, 0)
"""Two reads after the first and no seconds between them: the shape of the wait, not its length."""


@check("settle probes", pre=True)
def settle_probes() -> list[str]:
    """Every write through the channel returns settled or says it did not (solorepo's DR-264).

    `act`, over a read that answers stale once and fresh after: one write,
    two reads, the fresh answer handed back beside the write's, and no exit.
    Over a read that never shows the write: the write made once, the reads
    spent to the bound, and the process ended with what `refused` says of the
    answer GitHub still holds. `settled` with an answer already in hand reads
    nothing where that answer shows the act, which is what `mergeability`
    pays nothing for. `shown` over a read that shows the act at once costs one
    read.

    The verbs, through `act`, against an Issue whose views answer the state
    before the edit once: `claim` assigns and is refused by nothing, `release`
    the same, and `relabel` answers the labels GitHub shows once it shows the
    edit. Against one whose views stay stale past the bound, `claim` is refused
    naming who GitHub shows assigned, which is nobody.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    with stood_in(channel, SETTLES=BOUND):
        return _act_cases(channel) + _verb_cases(channel, move)


class _Late:
    """A write and a read, both counted: the read answers `stale` `late` times and `fresh` after."""

    def __init__(self, late: int) -> None:
        self.late, self.reads, self.writes = late, 0, 0

    def write(self) -> str:
        self.writes += 1
        return "written"

    def read(self) -> str:
        self.reads += 1
        return "fresh" if self.reads > self.late else "stale"


def _fresh(answer: str) -> bool:
    """Whether a read shows the write."""
    return answer == "fresh"


def _still(answer: str) -> str:
    """What the exit says of an answer that never showed the write."""
    return f"still {answer}"


def _act_cases(channel: Any) -> list[str]:
    """`act`, `settled` and `shown` over reads showing the write late, never, at once, or before."""
    problems = []
    late = _Late(1)
    value, code, _ = answered(functools.partial(channel.act, late.write, late.read, _fresh, _still))
    if code is not None or value != ("written", "fresh"):
        problems.append(f"act: a read stale once answered {value!r} with exit {code!r}, not the "
                        "write's answer beside the fresh read")
    if (late.writes, late.reads) != (1, 2):
        problems.append(f"act: a read stale once cost {late.writes} write(s) and {late.reads} "
                        "read(s), not one and two")

    never = _Late(99)
    _, code, exited = answered(functools.partial(channel.act, never.write, never.read, _fresh,
                                                 _still))
    if not exited or code != "still stale":
        problems.append(f"act: a read that never shows the write ended with {code!r}, not with "
                        "what refused says of the stale answer")
    if (never.writes, never.reads) != (1, 1 + BOUND[0]):
        problems.append(f"act: a read that never shows the write cost {never.writes} write(s) "
                        f"and {never.reads} read(s), not one and the bound")

    held = _Late(99)
    value, code, _ = answered(functools.partial(channel.settled, held.read, _fresh, None, "fresh"))
    if code is not None or value != "fresh" or held.reads != 0:
        problems.append(f"settled: an answer already in hand that shows the act was read "
                        f"{held.reads} time(s) and answered {value!r}, not held as it was")

    at_once = _Late(0)
    value, code, _ = answered(functools.partial(channel.shown, at_once.read, _fresh, _still))
    if code is not None or value != "fresh" or at_once.reads != 1:
        problems.append(f"shown: a read that shows the act at once cost {at_once.reads} read(s) "
                        f"and answered {value!r}, not one and the answer")
    return problems


def _verb_cases(channel: Any, move: Any) -> list[str]:
    """`claim`, `release` and `relabel` through `act`, over an Issue shown late and one never."""
    problems = []
    with environment(GITHUB_RUN_ID=None, ACTOR_SESSION=None):
        late = FakeIssue(["challenge", "human"], stale=1)
        said = run_verb(channel, late, lambda: move.claim("7"))
        if said is not None or late.assignees != ["o-r-coder"]:
            problems.append(f"claim: an Issue GitHub shows late was refused with {said!r} and "
                            f"left assigned to {late.assignees}, where a settle should have "
                            "waited the one stale read out")

        never = FakeIssue(["challenge", "human"], stale=99)
        said = run_verb(channel, never, lambda: move.claim("7"))
        if said is None or "assigned to nobody" not in said:
            problems.append(f"claim: an Issue GitHub never shows assigned was refused with "
                            f"{said!r}, which does not name who GitHub shows assigned")

    held = FakeIssue(["challenge", "human"], assignees=["o-r-coder"], stale=1)
    said = run_verb(channel, held, lambda: move.release("7"))
    if said is not None or held.assignees:
        problems.append(f"release: an Issue GitHub shows late was refused with {said!r} and "
                        f"left assigned to {held.assignees}")

    relabelled = FakeIssue(["challenge"], stale=1)
    value, code, _ = answered(lambda: _relabelled(channel, move, relabelled))
    if code is not None or value != ["challenge", "hard"]:
        problems.append(f"relabel: an Issue GitHub shows late answered {value!r} with exit "
                        f"{code!r}, not the labels GitHub shows once it shows the edit")
    return problems


def _relabelled(channel: Any, move: Any, fake: FakeIssue) -> list[str]:
    """`relabel` of Issue 7 adding `hard`, with `gh` stood in by `fake`."""
    with stood_in(channel, gh=fake):
        labels: list[str] = move.relabel("7", add=["hard"])
    return labels
