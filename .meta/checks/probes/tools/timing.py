"""`timing.py`'s percentile and its degrade, one case at a time (solorepo's DR-157).
"""

from checks import citations
from checks.collect import check


@check("timing probes", pre=True)
def timing_probes():
    """`timing.pick` over the lengths where nearest-rank ties, and `timing.gh` over the one default a caller can ask for (solorepo's DR-157).

    Nearest-rank: the median of `n` values is the `ceil(n/2)`-th smallest,
    which is a value that occurred. Each case is the run `1..n`, so the value
    and its rank are the same number and the expectation reads without
    arithmetic. Three of the lengths, 5, 9 and 13, are those where `0.5 * n`
    is a half with an even integer part, which `round`, being half-to-even,
    rounds down: a `pick` written with `round` answers one rank low on each,
    and five is `--deep`'s default. The fourth, 4, is the even length on which
    the two agree. The p95 of five runs is the slowest of them, and no runs is
    no figure.

    The degrade path is asked through a `gh` subcommand that does not exist,
    so the failure is a real one and not a stand-in. A caller that gives a
    default of `None` gets `None` — the default `runs_of` gives, on the token
    with no Actions scope the program is shaped around, and the one a sentinel
    of `None` cannot tell from no default — and a caller that gives `{}` gets
    `{}`. A caller that gives no default is not asked, because what it does
    is exit. `SystemExit` is caught and reported as the case's own finding:
    uncaught, a read that exits instead of degrading would take the gate down
    with every step before this one reported ok and the gate exited 1, naming
    neither the step nor the reason, because `check.py`'s precheck guard
    catches `Exception` and `SystemExit` is not one.
    """
    timing = citations.load_timing()
    problems = []
    for n in (4, 5, 9, 13):
        want = -(-n // 2)
        got = timing.pick(list(range(1, n + 1)), 0.5)
        if got != want:
            problems.append(f"timing: the median of {n} run(s) is the {want}\u2011th, "
                            f"and `pick` answered the {got}\u2011th")
    if timing.pick([1, 2, 3, 4, 5], 0.95) != 5:
        problems.append("timing: p95 of five runs is the slowest of them, "
                        "and `pick` answered otherwise")
    if timing.pick([], 0.5) is not None:
        problems.append("timing: no runs is no figure, and `pick` answered one")
    for default, want in ((None, None), ({}, {})):
        try:
            got = timing.gh("timing-probe-no-such-subcommand", default=default)
        except SystemExit:
            problems.append(f"timing: a read that fails and was given a default of "
                            f"{default!r} exited instead of degrading to it")
            continue
        if got != want:
            problems.append(f"timing: a read that fails and was given a default of "
                            f"{default!r} answered {got!r}")
    return problems
