"""The channel's `gh` over a call that never answers, and the retry that call is owed (solorepo's #738).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import subprocess
import types
from typing import Any

from checks.collect import check
from checks.probes.harness import (
    load_channel,
    outcome,
    stood_in,
)


def _hung_subprocess(calls: list[tuple[tuple[str, ...], float | None]]) -> Any:
    """As much of `subprocess` as `channel.gh` uses, its `run` answering a call only when the call carries no bound.

    Each invocation is recorded in `calls` as the command and the `timeout=` it
    was given. A bounded call raises `TimeoutExpired`, which is the hang the
    cases are about; an unbounded one returns successfully, so a `run` that was
    handed no bound is a passing call and not a timing-out one, and a probe
    asserting on the exit is asserting that the bound was applied.
    """
    def run(cmd: list[str], **kwargs: Any) -> Any:
        bound = kwargs.get("timeout")
        calls.append((tuple(cmd), bound))
        if bound is None:
            return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=bound)
    return types.SimpleNamespace(run=run, TimeoutExpired=subprocess.TimeoutExpired,
                                 CalledProcessError=subprocess.CalledProcessError,
                                 CompletedProcess=subprocess.CompletedProcess)


@check("gh bound probes", pre=True)
def gh_bound_probes() -> list[str]:
    """`channel.gh` and `channel.gh_with_retry` over a `gh` that answers nothing, one case at a time.

    A verb of the channel is one API call behind a CLI that refreshes its own
    auth, and an unbounded call against a rate-limited API can stop without
    stopping: no answer, no failure, and nothing for a caller to report. The
    bound is what turns that into a failure, and a failure is a shape the
    channel already has answers for.

    Five cases, each over a `run` that raises `TimeoutExpired` rather than
    waiting the seconds out, so the probe costs no wall clock. The stand-in
    answers a call that carries no `timeout=` successfully, so what the first
    four cases assert is that `GH_TIMEOUT` reached `subprocess.run`: strip the
    bound from the call and every one of them stops failing. A plain call
    exits, and the refusal names both the call and the bound it passed, because
    a timeout indistinguishable from a refusal sends its reader to the wrong
    question. A call that tolerates failure raises `CalledProcessError` under
    `TIMEOUT_RETURNCODE` rather than the `TimeoutExpired` no caller here
    catches, which is what lets `gh_with_retry` retry a hang without being
    taught a second failure shape. And `gh_with_retry` does retry it: the
    stand-in counts the invocations, so a bound that stopped the first call and
    then gave up is told from one that tried again.

    The fourth is the same hang under a fallback: a call carrying `default={}`
    answers that fallback rather than exiting, having still made all three
    attempts. `{}` is the fallback rather than `None` because a wrapper that
    ignored `default` and returned bare would answer `None` too, and the two
    would be one observation. What the whole failure contract says a fallback
    answers, over every read that goes wrong, is
    `.meta/checks/probes/wrappers.py`'s subject; what is asserted here is that
    the attempts are spent before the fallback is reached.

    The fifth is the opt-out the `gh stack` calls take: `timeout=None` reaches
    `subprocess.run` as `None` and the call waits, because a stack rebase or a
    stack merge is not the single API call the bound was sized for.

    `role_credential` is stood in as well, so the cases turn on the bound
    rather than on whether the machine running them holds a Role's key, and so
    is `_stack_extension`, whose own bounded `gh extension list` would otherwise
    be the call the fifth case's stack invocation times out on rather than the
    stack invocation itself; what that preflight does is
    `.meta/checks/probes/channel/extension.py`'s subject.
    """
    channel, _, _ = load_channel()
    problems: list[str] = []
    calls: list[tuple[tuple[str, ...], float | None]] = []

    with stood_in(channel, subprocess=_hung_subprocess(calls), role_credential=lambda: {},
                  _stack_extension=lambda: None):
        exited = outcome(lambda: channel.gh("pr", "view", "7"))
        bound = calls[0][1] if calls else "no call at all"
        try:
            channel.gh("pr", "view", "7", tolerate_fail=True)
            raised: subprocess.CalledProcessError | None = None
        except subprocess.CalledProcessError as exc:
            raised = exc
        calls.clear()
        retried = outcome(lambda: channel.gh_with_retry("pr", "view", "7", tries=3, delay=0))
        attempts = len(calls)
        calls.clear()
        answers: list[Any] = []
        fell_back = outcome(lambda: answers.append(
            channel.gh_with_retry("pr", "view", "7", tries=3, delay=0, default={})))
        degraded: Any = answers[0] if answers else f"an exit saying {fell_back.code!r}"
        degraded_attempts = len(calls)
        calls.clear()
        channel.gh("stack", "push", parse=False, timeout=None)
        opted_out = calls[0][1] if calls else "no call at all"

    said = str(exited.code)
    if bound != channel.GH_TIMEOUT:
        problems.append(f"gh: a call left to the default reached `subprocess.run` with "
                        f"timeout={bound!r} rather than {channel.GH_TIMEOUT!r}, and an "
                        "invocation carrying no bound is the hang this exists to refuse")
    if not exited.code or "answered nothing within" not in said or "pr view 7" not in said:
        problems.append(f"gh: a call that never answered exited with {exited.code!r}, "
                        "which names neither the call nor the bound it passed")
    if raised is None:
        problems.append("gh: a call that never answered and was told to tolerate failure "
                        "raised nothing a caller here catches")
    elif raised.returncode != channel.TIMEOUT_RETURNCODE:
        problems.append(f"gh: a tolerated timeout raised under {raised.returncode!r} rather than "
                        f"{channel.TIMEOUT_RETURNCODE!r}")
    if not retried.code or "answered nothing within" not in str(retried.code):
        problems.append(f"gh_with_retry: a hung call came to {retried.code!r}")
    if attempts != 3:
        problems.append(f"gh_with_retry: a hung call was invoked {attempts} time(s) of the three "
                        "it asked for, and a hang it does not retry is a hang it cannot outlast")
    if degraded != {}:
        problems.append(f"gh_with_retry: a hung call carrying a fallback of {{}} came to "
                        f"{degraded!r} rather than that fallback, and a wrapper that answers "
                        "only `None` is one that never read `default` at all")
    if degraded_attempts != 3:
        problems.append(f"gh_with_retry: a hung call carrying a fallback was invoked "
                        f"{degraded_attempts} time(s) of the three it asked for, and a fallback "
                        "reached before the attempts are spent is a hang it did not outlast")
    if opted_out is not None:
        problems.append(f"gh: a call passing `timeout=None` reached `subprocess.run` with "
                        f"timeout={opted_out!r}, and a stack rebase cut off at a minute "
                        "leaves the branches it already pushed behind it")
    return problems
