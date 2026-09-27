"""The small acts around a call a probe makes: an attribute or an environment variable stood in for the length of a block, a verb run with GitHub stood in, and what a call exited with, read as text rather than allowed to end the step.
"""
import collections
import contextlib
import io
import os
import pathlib
import tempfile
from collections.abc import Callable, Iterator
from typing import Any

Outcome = collections.namedtuple("Outcome", "code out err")
"""What a call came to: `code`, the text it exited with or `None` when it returned; `out` and `err`, what it printed."""


_ABSENT = object()


def unanswered(args: object, fake: str = "the fake") -> AssertionError:
    """The refusal a fake raises for a call it does not model.

    Args:
        args: The arguments the fake was called with.
        fake: What to call the fake in the message, which a module standing in
            for more than one command needs so that an unmodelled `git` call
            and an unmodelled `gh` call read apart.

    Returns:
        AssertionError: Naming the call, so the probe report says what the fake
        was asked rather than only that it declined.
    """
    return AssertionError(f"{fake} was asked something it has no answer for: {args}")


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
def environment(**variables: str | None) -> Iterator[None]:
    """The named environment variables set for the block, `None` unsetting one, and put back after it."""
    held = {name: os.environ.get(name) for name in variables}

    def apply(values: dict[str, str | None]) -> None:
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


@contextlib.contextmanager
def workspace(**variables: str | None) -> Iterator[pathlib.Path]:
    """A temporary directory a door runs in, holding the two files it writes and no ambient toggle.

    The working directory is the temporary one for the block and is put back
    after it. `GITHUB_OUTPUT` and `GITHUB_ENV` name the `output` and `env`
    files, as a run has them, and both fallback toggles are stood down: the
    routing policy's `toggled()` reads `os.environ` where no caller passes an
    environment, so a container carrying `GEMINI_FALLBACK=true` lengthens every
    chain a door resolves and answers `tiers=2` where a case expects one rung.
    The gate runs in a loop's container and on a laptop alike, and a case that
    reads the ambient environment is a different case in each
    (solorepo's #1000). What a toggle does when it is on is
    `probes/channel/routing.py`'s subject, whose cases pass an `environ` of
    their own.

    Args:
        **variables: Further environment variables the caller stands in, `None`
            unsetting one; a name already held above is a repeated keyword
            argument.

    Yields:
        pathlib.Path: The directory, holding an empty `output` and `env`.
    """
    held = pathlib.Path.cwd()
    with tempfile.TemporaryDirectory() as where:
        root = pathlib.Path(where)
        (root / "output").touch()
        (root / "env").touch()
        os.chdir(root)
        try:
            with environment(GITHUB_OUTPUT=str(root / "output"), GITHUB_ENV=str(root / "env"),
                             GEMINI_FALLBACK=None, JULES_FALLBACK=None, COPILOT_FALLBACK=None,
                             CLAUDE_COOLDOWN_UNTIL=None, AGY_COOLDOWN_UNTIL=None,
                             ANTIGRAVITY_COOLDOWN_UNTIL=None, **variables):
                yield root
        finally:
            os.chdir(held)


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


def exit_of(call: Callable[[], object]) -> str | None:
    """What `call` exited with, as text, or `None` when it returned; see `outcome`."""
    code: str | None = outcome(call).code
    return code


def run_verb(channel: Any, fake: Any, call: Callable[[], object]) -> str | None:
    """`call` with the channel's `gh` stood in by `fake`, and what it exited with."""
    with stood_in(channel, gh=fake):
        return exit_of(call)


@contextlib.contextmanager
def written(suffix: str, text: str) -> Iterator[pathlib.Path]:
    """A file holding `text` under a temporary name ending in `suffix`, closed before the block and deleted after it, whatever the block did."""
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False) as handle:
        handle.write(text)
        path = pathlib.Path(handle.name)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def answered(call: Callable[[], Any]) -> tuple[Any, str | None, bool]:
    """`call`'s return value beside how it ended, as `(value, code, exited)`; see `outcome`.

    `outcome` reads a call's exit as text and drops what it returned, and once
    an exit and a crash are both text nothing in the text tells them apart.
    Three probes need both halves: `probes/channel/parser.py`, where a parser
    answers a namespace or exits with its usage; `probes/channel/actor.py`,
    where `channel.actor()` answers a session or refuses; and
    `probes/channel/signing_key.py`, where `role_signing_key()` answers a path
    or refuses. `value` is what the call returned, `None` where it did not
    return; `code` is `outcome(call).code`;
    `exited` is whether the call ended in `sys.exit`, read off the exception's
    class before `outcome` renders it, so that a case expecting a refusal is
    not satisfied by a crash. The `say:` prefix the channel puts on its
    refusals is not tested, since an exit carrying a number or nothing is as
    much a refusal as one carrying a sentence.
    """
    held: list[Any] = []
    exits: list[bool] = []

    def attempt() -> None:
        """`call`, its value kept in `held` and an exit noted in `exits` on its way out to `outcome`."""
        try:
            held.append(call())
        except SystemExit:
            exits.append(True)
            raise

    code = outcome(attempt).code
    return (held[0] if held else None), code, bool(exits)
