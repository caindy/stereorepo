"""`.meta/gate`'s runner, loaded under the interpreter that runs it (solorepo's DR-092, solorepo's DR-209).
"""

import io
import threading

from checks.collect import META, check
from checks.probes.harness import load_module


@check("gate runner probes", pre=True)
def gate_runner_probes() -> list[str]:
    """`.meta/gate` loads under the running interpreter, and `_emit` writes through the lock it is given (solorepo's #746).

    Loading is the case: a function signature is evaluated at `def` time, so an
    annotation naming a runtime object rather than a type raises there and
    takes every step of every Project's gate with it. `threading.Lock` is a
    factory function before Python 3.13 and a class from 3.13 on, so
    `lock: threading.Lock | None` loads on one interpreter and raises
    `TypeError: unsupported operand type(s) for |` on the other. Loaded, the
    runner's `_emit` is asked for its two paths — with a lock and without —
    and both must reach the file handed to them.
    """
    problems = []
    try:
        gate = load_module(META / "gate", "gate-runner", register=False)
    except Exception as exc:
        return [f"gate runner: .meta/gate did not load — {type(exc).__name__}: {exc}"]

    for name, lock in (("without a lock", None), ("under a lock", threading.Lock())):
        said = io.StringIO()
        gate._emit("ok meta/step", file=said, lock=lock)
        if said.getvalue() != "ok meta/step\n":
            problems.append(f"gate runner: _emit {name} wrote {said.getvalue()!r}, not 'ok meta/step\\n'")
    return problems
