"""Credential-free base GitHub CLI runner shared across .meta/ (solorepo's #748).

Executes `gh` CLI commands as subprocesses, handles timeouts (solorepo's #738),
and parses JSON output while supporting caller-provided fallbacks via the `UNSET`
sentinel. Shared by read-only tools (`next.py`, `timing`, `check_pr`) and the
attested mutation channel (`channel.py`).
"""

import json
import subprocess
import sys
from collections.abc import Sequence
from typing import Any

GH_TIMEOUT: float = 60
"""Seconds one `gh` invocation is given before it is abandoned as hung (solorepo's #738).

The bound is the default and not the rule, and it is an `int` because callers
interpolate it into the prose a hang exits with, where `60.0s` reads as a
defect. A verb that waits on `gh` for a single API call is bounded by it, and a
minute is far longer than one of those takes. Two kinds of caller pass
`timeout=None` instead: the `gh stack` invocations in `.meta/say/move`, since
rebasing or merging every layer of a stack can take longer than a minute with
nothing wrong; and the readers whose whole purpose is to degrade rather than
exit, `.meta/next.py` and `.meta/lib/timing/github.py`, which a bound would
take the screen from rather than one line of it.
"""

TIMEOUT_RETURNCODE = 124
"""The `returncode` a tolerated timeout's `CalledProcessError` carries.

It is what `timeout(1)` reports a command it killed under, and it is not an
exit status of anything here: where failure is not tolerated a timeout leaves
through `sys.exit`, whose status is 1, so a shell tells a hang from a refusal
by the prose on standard error and not by `$?`.
"""

UNSET = object()
"""Sentinel value distinguishing an omitted default argument from None."""

_DEGRADE_SENTINEL = object()
"""Sentinel indicating empty output should degrade rather than return blank."""


class GhTimeout(SystemExit):
    """A `gh` invocation abandoned at its timeout bound (solorepo's #738)."""


GH_HUNG = "gh: `gh {cmd}` answered nothing within {timeout}s"
"""What an abandoned `gh` invocation exits with, which no fatal poll pattern matches.

`GhTimeout` is a `SystemExit`, so this prose reaches
`.meta/lib/check_pr/polling.py`, whose `is_fatal_poll_error` lowercases it and
substring-matches it against `FATAL_POLL_PATTERNS`. A match makes `just watch`
exit rather than retry under backoff, so a hang must match none of them: insert
a phrase such as "not found" here and every transient hang becomes a fatal exit
from a watch that ought to have retried it.
"""


def _degrade(
    default: Any,
    why: str,
    args: Sequence[str] | None = None,
    prefix: str | None = None,
) -> Any:
    """Answers a failed read with the caller's fallback, or exits saying what went wrong.

    Parameters:
        default: Fallback value returned if not UNSET.
        why: Description of the failure or error message.
        args: Command arguments passed to gh, used to derive prefix if omitted.
        prefix: Explicit prefix for error message. Defaults to args[:2] or 'gh'.

    Returns:
        Any: The fallback value when default is not UNSET.

    Raises:
        SystemExit: When default is UNSET.
    """
    if default is not UNSET:
        return default
    if prefix is None:
        prefix = f"gh {' '.join(args[:2])}" if args else "gh"
    sys.exit(f"{prefix}: {why}")


def _relay(args: tuple[str, ...] | Sequence[str], out: subprocess.CompletedProcess[str]) -> None:
    """Prints command execution status and captured output to standard error.

    Parameters:
        args: The arguments gh was invoked with.
        out: Completed subprocess execution result.
    """
    said = "\n".join(part for part in (out.stdout.strip(), out.stderr.strip()) if part)
    print(
        f"gh {' '.join(args)}: exit {out.returncode}"
        + (f"\n{said}" if said else " and said nothing"),
        file=sys.stderr,
    )


def gh(  # noqa: PLR0913  # reason: one call's eight behaviours, named so a typo raises TypeError
    *args: str,
    default: Any = UNSET,
    env: dict[str, str] | None = None,
    timeout: float | None = GH_TIMEOUT,
    parse: bool = True,
    tolerate_fail: bool = False,
    echo: bool = False,
    blank: Any = _DEGRADE_SENTINEL,
    prefix: str | None = None,
    subprocess_module: Any = subprocess,
) -> Any:
    """Executes a gh CLI command and parses JSON or text output.

    Parameters:
        *args: Command arguments passed to gh.
        default: Fallback value returned if command fails, prints nothing, or
            prints non-JSON output when parse is True. If omitted, exits.
        env: Environment variables for the invocation, or None to inherit.
        timeout: Seconds to wait before abandoning the invocation as hung,
            GH_TIMEOUT by default; None waits indefinitely.
        parse: Whether to read the output as JSON. False returns stripped text.
        tolerate_fail: Whether to raise CalledProcessError or JSONDecodeError
            instead of degrading or exiting.
        echo: Whether to relay exit status and both streams on standard error.
        blank: Value returned when the invocation prints nothing. Where the
            caller gives none, an empty answer degrades like a failed one.
        prefix: Command prefix used in error messages, `gh <verb> <noun>` by
            default.
        subprocess_module: Subprocess module, or the stand-in a probe puts in
            its place. `.meta/checks/probes/wrappers.py` and
            `.meta/checks/probes/channel/bound.py` monkeypatch each wrapper
            module's own `subprocess` global and rely on the wrapper passing
            the bare name through to here, so dropping the parameter would have
            every probed read shell out to the real `gh` from inside the gate.
            A stand-in carries only what those wrappers name, which is why
            `TimeoutExpired` and `CalledProcessError` are fetched from it with a
            fallback to the real classes rather than read outright.

    Returns:
        Any: Parsed JSON data, stripped raw text, or caller fallback.

    Raises:
        subprocess.CalledProcessError: When tolerate_fail is True and command
            fails or times out.
        json.JSONDecodeError: When tolerate_fail is True and output is invalid JSON.
        GhTimeout: When invocation times out and tolerate_fail is False.
        SystemExit: When invocation fails or returns invalid JSON without a fallback.
    """
    cmd = ["gh", *args]
    timeout_cls = getattr(subprocess_module, "TimeoutExpired", subprocess.TimeoutExpired)
    cpe_cls = getattr(subprocess_module, "CalledProcessError", subprocess.CalledProcessError)
    try:
        out = subprocess_module.run(
            cmd, check=False, capture_output=True, text=True, env=env, timeout=timeout
        )
    except timeout_cls as expired:
        hung = f"`gh {' '.join(args)}` answered nothing within {timeout}s"
        if tolerate_fail:
            raise cpe_cls(TIMEOUT_RETURNCODE, cmd, output="", stderr=hung) from expired
        raise GhTimeout(GH_HUNG.format(cmd=" ".join(args), timeout=timeout)) from expired
    if echo:
        _relay(args, out)
    if out.returncode:
        if tolerate_fail:
            raise cpe_cls(out.returncode, cmd, output=out.stdout, stderr=out.stderr)
        return _degrade(default, out.stderr.strip(), args=args, prefix=prefix)
    text = out.stdout.strip()
    if not text:
        if blank is not _DEGRADE_SENTINEL:
            return blank
        return _degrade(default, "answered nothing", args=args, prefix=prefix)
    if not parse:
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        if tolerate_fail:
            raise
        return _degrade(default, f"answered what is not JSON: {exc}", args=args, prefix=prefix)
