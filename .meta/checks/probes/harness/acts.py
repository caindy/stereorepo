"""The small acts around a call a probe makes: an attribute or an environment variable stood in for the length of a block, a verb run with GitHub stood in, and what a call exited with, read as text rather than allowed to end the step.
"""
import collections
import contextlib
import io
import os
from collections.abc import Iterator

Outcome = collections.namedtuple("Outcome", "code out err")
"""What a call came to: `code`, the text it exited with or `None` when it returned; `out` and `err`, what it printed."""


_ABSENT = object()


@contextlib.contextmanager
def stood_in(target: object, **attributes: object) -> Iterator[None]:
    """The named attributes of `target` replaced for the block, and put back after it, whatever the block did.

    An attribute the target did not have is removed again on the way out
    rather than left holding the stand-in.

    Args:
        target: The module or object whose attributes are replaced.
        **attributes: The attribute names, each bound to the stand-in it takes.

    Yields:
        None: The block runs with the stand-ins in place.
    """
    held = {name: getattr(target, name, _ABSENT) for name in attributes}
    for name, value in attributes.items():
        setattr(target, name, value)
    try:
        yield
    finally:
        for name, value in held.items():
            if value is _ABSENT:
                delattr(target, name)
            else:
                setattr(target, name, value)


@contextlib.contextmanager
def environment(**variables):
    """The named environment variables set for the block, `None` unsetting one, and put back after it."""
    held = {name: os.environ.get(name) for name in variables}

    def apply(values):
        for name, value in values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    apply(variables)
    try:
        yield
    finally:
        apply(held)


def outcome(call):
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
    except Exception as exc:
        code = f"{type(exc).__name__}: {exc}"
    return Outcome(code, out.getvalue(), err.getvalue())


def exit_of(call):
    """What `call` exited with, as text, or `None` when it returned; see `outcome`."""
    return outcome(call).code


def run_verb(channel, fake, call):
    """`call` with the channel's `gh` stood in by `fake`, and what it exited with."""
    with stood_in(channel, gh=fake):
        return exit_of(call)
