"""What a call came to, read as text rather than allowed to end the step.
"""
import collections
import contextlib
import io
from collections.abc import Callable

Outcome = collections.namedtuple("Outcome", "code out err")
"""What a call came to: `code`, the text it exited with or `None` when it returned; `out` and `err`, what it printed."""


def outcome(call: Callable[[], object]) -> Outcome:
    """What `call` came to, as an `Outcome`, with its printing captured rather than shown.

    Every way out is an answer. `sys.exit(text)` is `text`; a return is `None`;
    any other exception is its type and message, as `TypeError: ...`. Raised
    instead, a fake's designed refusal — an `AssertionError` naming the call it
    has no answer for — or a number a case did not model would end the step at
    its first surprise and leave `check.py`'s precheck guard to report one line
    for the whole of it with every later case unrun (A7). Returned as text, the
    refusal still says in the report what the fake was asked.
    """
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            call()
        code = None
    except SystemExit as exc:
        code = str(exc.code)
    except Exception as exc:  # noqa: BLE001  # reason: the fake under test may raise anything, and the refusal is reported as text so later cases still run (A7)
        code = f"{type(exc).__name__}: {exc}"
    return Outcome(code, out.getvalue(), err.getvalue())
