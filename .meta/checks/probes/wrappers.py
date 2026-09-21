"""The three `gh` wrappers no other step asks anything, held to the failure contract the four were converged on (solorepo's #737).
"""
import collections
import functools
import subprocess
import types
from typing import Any

from checks.collect import META, Found, Passed, check
from checks.probes.harness import answered, load_channel, load_module, stood_in

NO_DEFAULT = object()
"""A caller that passes no `default`, as a value the table of fallbacks can hold."""

DEGRADE = object()
"""A read that answers the caller's fallback, and exits where the caller gave none."""

BLANK = object()
"""A read whose answer is the wrapper's own, which is where the contracts still differ."""

MISSING = ("wrapper-probe-no-such-subcommand",)
"""The `gh` subcommand every read is made over, which does not exist, so that a real failure needs neither network nor credential."""

Wrapper = collections.namedtuple("Wrapper", "name module blank")
"""A wrapper under probe: what a finding calls it, the module holding its `gh`, and what it answers a read that succeeded and printed nothing."""

Case = collections.namedtuple("Case", "name code out rule")
"""One read: what it did, the exit status and output `gh` is stood in to give it, and what the contract says it answers."""

CASES = (
    Case("failed", 1, "", DEGRADE),
    Case("printed what is not JSON", 0, "{ not json", DEGRADE),
    Case("printed nothing", 0, "", BLANK),
)
"""The three ways a read goes wrong, as `gh` reports them."""

FALLBACKS: tuple[Any, ...] = (None, {}, NO_DEFAULT)
"""The fallbacks a caller gives: the two `UNSET` exists to tell apart, and none at all."""

WIDTH = 120
"""How much of what a read exited with a finding carries: Article 21 gives a problem one line, and `gh`'s own refusal is its whole usage screen."""


def stand_in(code: int, out: str) -> types.SimpleNamespace:
    """`subprocess` as a wrapper reads it, answering one call.

    Parameters:
        code (int): The exit status the call is given.
        out (str): What the call is given to have printed.

    Returns:
        types.SimpleNamespace: A stand-in carrying `run` and `CalledProcessError`,
        which is all of `subprocess` these wrappers name. The exception class is
        the real one, so a wrapper that raises rather than exits raises what a
        caller catches.
    """
    done = subprocess.CompletedProcess(["gh", *MISSING], code, out, "stood in")
    return types.SimpleNamespace(run=lambda *args, **kwargs: done,
                                 CalledProcessError=subprocess.CalledProcessError)


def contract(wrapper: Wrapper, case: Case, default: Any) -> tuple[Any, bool]:
    """What the contract says one read answers.

    Parameters:
        wrapper (Wrapper): The wrapper read from.
        case (Case): What the read did.
        default (Any): The fallback given, or `NO_DEFAULT`.

    Returns:
        tuple[Any, bool]: The value the read answers, and whether it exits instead.
    """
    rule = wrapper.blank if case.rule is BLANK else case.rule
    if rule is not DEGRADE:
        return rule, False
    if default is NO_DEFAULT:
        return None, True
    return default, False


def read(wrapper: Wrapper, default: Any) -> Any:
    """Call `wrapper`'s `gh` over `MISSING`, passing `default` where one is given.

    Parameters:
        wrapper (Wrapper): The wrapper to read from.
        default (Any): The fallback to pass, or `NO_DEFAULT` to pass none.

    Returns:
        Any: What the wrapper answered.

    Raises:
        SystemExit: Where the wrapper exits rather than answering.
    """
    if default is NO_DEFAULT:
        return wrapper.module.gh(*MISSING)
    return wrapper.module.gh(*MISSING, default=default)


def named(default: Any) -> str:
    """Name the fallback a read was given, for a finding.

    Parameters:
        default (Any): The fallback given, or `NO_DEFAULT`.

    Returns:
        str: The phrase a finding puts after "was given".
    """
    return "no fallback" if default is NO_DEFAULT else f"a fallback of {default!r}"


def refusal(code: str | None) -> str:
    """What a read exited with, on one line, so a finding is one line.

    Parameters:
        code (str | None): What `answered` read the exit as.

    Returns:
        str: The text, its newlines and runs of space collapsed and cut to `WIDTH`.
    """
    said = " ".join(str(code).split())
    return said if len(said) <= WIDTH else f"{said[:WIDTH]}…"


def shown(wrapper: Wrapper, value: Any) -> str:
    """What a read answered, named rather than shown where it is the wrapper's own sentinel.

    Parameters:
        wrapper (Wrapper): The wrapper read from.
        value (Any): What it answered.

    Returns:
        str: The value, or what the sentinel is, which no `repr` says.
    """
    if value is getattr(wrapper.module, "UNSET", NO_DEFAULT):
        return "its own `UNSET` sentinel"
    return repr(value)


def held(wrapper: Wrapper, case: Case, default: Any) -> list[str]:
    """One read of one wrapper, against what the contract says it answers.

    Parameters:
        wrapper (Wrapper): The wrapper to read from.
        case (Case): What `gh` is stood in to do.
        default (Any): The fallback to pass, or `NO_DEFAULT` to pass none.

    Returns:
        list[str]: The finding, or nothing where the read answered as the contract says.
    """
    want, exits = contract(wrapper, case, default)
    with stood_in(wrapper.module, subprocess=stand_in(case.code, case.out)):
        got, code, exited = answered(functools.partial(read, wrapper, default))
    said = f"{wrapper.name}: a read that {case.name} and was given {named(default)}"
    if exits and not exited:
        return [f"{said} answered {shown(wrapper, got)} rather than exiting"]
    if exited and not exits:
        return [f"{said} exited with {refusal(code)!r} rather than answering {want!r}"]
    if not exits and got != want:
        return [f"{said} answered {shown(wrapper, got)} rather than {want!r}"]
    return []


def anchored(wrapper: Wrapper) -> list[str]:
    """One read of one wrapper through `gh` itself, with nothing stood in and `None` for the fallback.

    Parameters:
        wrapper (Wrapper): The wrapper to read from.

    Returns:
        list[str]: The finding, or nothing where the read degraded to `None`.
    """
    got, code, exited = answered(functools.partial(read, wrapper, None))
    said = f"{wrapper.name}: `gh {MISSING[0]}`, which fails for real"
    if exited:
        return [f"{said}, exited with {refusal(code)!r} rather than degrading to the fallback given"]
    if got is not None:
        return [f"{said}, answered {shown(wrapper, got)} rather than the fallback given"]
    return []


@check("gh wrapper probes", pre=True)
def gh_wrapper_probes() -> Found | Passed:
    """`next.py`, `check_pr`'s and the channel's `gh`, each over the three reads that go wrong and the three fallbacks a caller gives (solorepo's #737).

    Four wrappers under `.meta/` run the same GitHub CLI call, and each was
    written because the ones before it exited the process rather than
    degrading. `timing probes` asks the fourth, `.meta/lib/timing/github.py`,
    for its two degrades; these three are asked here, so that a fifth written
    the old way is a convention held by the gate rather than by whoever read
    the pull request that converged them.

    The contract is one sentence per limb. A read that fails, one that printed
    what is not JSON, and one that printed nothing all take the same route: the
    caller's fallback where it gave one, and `sys.exit` where it gave none,
    which is what the `UNSET` sentinel exists to tell apart — a caller wanting
    `None` back is not a caller asking to die. The channel's is the one
    departure, and it is deliberate rather than drift: its `gh` carries the
    writes as well as the reads, so a call that succeeded and printed nothing
    answers the empty string, which is what a write answers with. `blank`
    carries that per wrapper, so the departure is written down here rather
    than found by whoever changes it.

    `gh` is stood in for the three cases, because no real subcommand succeeds
    while printing nothing on demand. One read per wrapper is then made
    through `gh` itself, over a subcommand that does not exist, so the stand-in
    is anchored to a failure that is real: no network and no credential are
    needed for one, and the channel's credential is stood in so that the probe
    asks nothing of `~/.config/solorepo/`. `SystemExit` is read back as an
    answer rather than allowed to end the step, which uncaught would take the
    gate down naming neither the step nor the case.
    """
    channel, _, _ = load_channel()
    subjects = (
        Wrapper("next.gh", load_module(META / "next.py", "next_probe", register=False), DEGRADE),
        Wrapper("check_pr.github.gh",
                load_module(META / "lib" / "check_pr" / "github.py", "check_pr_github_probe",
                            register=False),
                DEGRADE),
        Wrapper("channel.gh", channel, ""),
    )
    problems: list[str] = []
    with stood_in(channel, role_credential=dict):
        for wrapper in subjects:
            for case in CASES:
                for default in FALLBACKS:
                    problems += held(wrapper, case, default)
            problems += anchored(wrapper)
    if problems:
        return Found(problems)
    return Passed(f"{len(subjects)} wrappers over {len(CASES)} failed reads "
                  f"and {len(FALLBACKS)} fallbacks, and one real `gh` failure each")
