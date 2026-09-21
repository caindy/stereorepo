"""The floor on `select`, against selectors that reach it and ones that do not (solorepo's DR-263).

`files.python.unselected` is read by the `meta lints` step rather than run
beside it, so a wrong answer shows as a wrong verdict rather than as a failure:
a floor that accepts `B` for `BLE` reports a ruleset as whole while
flake8-blind-except is switched off and a bare `except Exception:` is legal
again. The cases are the two directions that matter — a selector widening
inside its own linter, which reaches, and a shorter selector belonging to a
different linter, which does not — and a failure names the case. The step
registers here rather than beside the check it exercises, because the gate over
assertions should not take its imports from a test suite (solorepo's DR-150).
"""
import collections

from checks.collect import check
from checks.files import python

FloorCase = collections.namedtuple("FloorCase", "name lint reaches misses")
"""One `[lint]` table put to `unselected`.

Attributes:
    name: What the case is called where it fails.
    lint: The table as `tomllib` would read it.
    reaches: The floor entries the answer must not name.
    misses: The floor entries it must.
"""


FLOOR_CASES = (
    FloorCase("flake8-bugbear is not flake8-blind-except",
              {"select": ["B"]}, ("B",), ("BLE",)),
    FloorCase("flake8-bandit is not flake8-simplify",
              {"select": ["S"]}, (), ("SIM",)),
    FloorCase("flake8-pytest-style is not flake8-use-pathlib",
              {"select": ["PT"]}, (), ("PTH",)),
    FloorCase("pydocstyle is not flake8-datetimez",
              {"select": ["D"]}, (), ("DTZ",)),
    FloorCase("flake8-debugger is not tryceratops",
              {"select": ["T"]}, (), ("TRY003",)),
    FloorCase("no linter answers to `P`",
              {"select": ["P"]}, (), ("PLW1510",)),
    FloorCase("tryceratops widens its own rule",
              {"extend-select": ["TRY"]}, ("TRY003",), ("SIM",)),
    FloorCase("pycodestyle widens its own families",
              {"select": ["E"]}, ("E4", "E7", "E9"), ("W",)),
    FloorCase("`C` widens both linters that answer to it",
              {"select": ["C"]}, ("C4", "C90"), ("B",)),
    FloorCase("pylint widens its own codes",
              {"select": ["PL"]}, ("PLR0912", "PLR0915", "PLW1510"), ("RET",)),
    FloorCase("ruff's widest selector reaches everything",
              {"select": ["ALL"]}, tuple(python.SELECT_FLOOR), ()),
    FloorCase("a `select` that is not a list is no selection",
              {"select": "BLE"}, (), ("BLE",)),
    FloorCase("an empty table reaches nothing",
              {}, (), tuple(python.SELECT_FLOOR)),
)
"""Every `[lint]` table the floor is asked about, one per case."""


@check("ruleset floor probes", pre=True)
def ruleset_floor_probes() -> list[str]:
    """`files.python.unselected` reads a selector as its own linter does, in floor order.

    Two directions, because the floor is only worth the narrower one
    (solorepo's DR-263). A selector that widens inside the linter owning a
    floor entry reaches it, so `TRY` satisfies `TRY003` and `PL` satisfies
    `PLW1510`; a shorter selector belonging to a different linter does not, so
    `B` leaves `BLE` unreached however much of its text it spells. `ALL`
    reaches every entry, and a `select` that is not a list selects nothing.
    """
    problems = []
    for case in FLOOR_CASES:
        missing = python.unselected(case.lint)
        problems += [f"ruleset floor: {case.name}: {rule} is not reported as unreached"
                     for rule in case.misses if rule not in missing]
        problems += [f"ruleset floor: {case.name}: {rule} is reported as unreached"
                     for rule in case.reaches if rule in missing]
    if python.unselected({}) != list(python.SELECT_FLOOR):
        problems.append("ruleset floor: an unreached floor is not answered "
                        "in the floor's own order")
    return problems
