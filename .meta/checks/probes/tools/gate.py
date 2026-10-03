"""`.meta/gate`'s runner, loaded under the interpreter that runs it (stereorepo's DR-092, stereorepo's DR-342).
"""

import io
import threading

from checks.collect import META, check
from checks.probes.harness import load_module

SELECTIONS = (
    ((), ("meta", "rust-seed", "python-seed", "pair", "app")),
    (("app",), ("app",)),
    (("pair", "rust-standard"), ("rust-seed", "pair")),
    (("scaffold", "pair"), ("meta", "pair")),
    (("python-seed", "meta"), ("meta", "python-seed")),
)
"""Words put to `select_all`, and the Projects it must choose, once each, in declared order
(stereorepo's DR-303): none is every Project, a Product brings its Projects, and an overlap or
an order other than the declared one changes nothing, and a Project at the repository root
(`name: .`) is chosen by its id like any other."""


@check("gate runner probes", pre=True)
def gate_runner_probes() -> list[str]:
    """`.meta/gate` loads under the running interpreter, and `_emit` writes through the lock it is given.

    Loading is the case: a function signature is evaluated at `def` time, so an
    annotation naming a runtime object rather than a type raises there and
    takes every step of every Project's gate with it. `threading.Lock` is a
    factory function before Python 3.13 and a class from 3.13 on, so
    `lock: threading.Lock | None` loads on one interpreter and raises
    `TypeError: unsupported operand type(s) for |` on the other. Loaded, the
    runner's `_emit` is asked for its two paths — with a lock and without —
    and both must reach the file handed to them. Then `select_all` is put each
    of `SELECTIONS`.
    """
    problems = []
    try:
        gate = load_module(META / "gate", "gate-runner", register=False)
    except Exception as exc:  # noqa: BLE001  # reason: loading the runner evaluates its module body and every signature in it, and the probe names what failed rather than taking the gate down with the traceback this step exists to catch
        return [f"gate runner: .meta/gate did not load — {type(exc).__name__}: {exc}"]

    for name, lock in (("without a lock", None), ("under a lock", threading.Lock())):
        said = io.StringIO()
        gate._emit("ok meta/step", file=said, lock=lock)
        if said.getvalue() != "ok meta/step\n":
            problems.append(f"gate runner: _emit {name} wrote {said.getvalue()!r}, not 'ok meta/step\\n'")

    projects = {f"work:project/{name}": {"id": f"work:project/{name}"}
                for name in ("meta", "rust-seed", "python-seed", "pair")}
    projects["work:project/app"] = {"id": "work:project/app", "name": "."}
    products = {
        "work:product/scaffold": {"built_from": ["work:project/meta", "work:project/pair"]},
        "work:product/rust-standard": {"built_from": ["work:project/rust-seed"]},
    }
    for words, expected in SELECTIONS:
        got = [gate.short(p["id"]) for p in gate.select_all(list(words), projects, products)]
        if got != list(expected):
            problems.append(f"gate runner: select_all{words} chose {got}, not {list(expected)}")
    return problems

