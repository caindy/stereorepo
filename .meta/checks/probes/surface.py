"""The root verb surface's argument contract, driven against the departures it exists to refuse (solorepo's DR-259, solorepo's DR-209).
"""

import pathlib
import tempfile

from checks.collect import Found, Passed, check
from checks.files.justfile import FLAGS, IDENTIFIER, Contract, justfile_recipe_shape

CONFORMING = """# the pull request gate
pr n *args:
    python3 .meta/check_pr.py {{n}} {{args}}
"""
"""One recipe of each declared kind, documented, invoking a tool under `.meta/`, and interpolating both parameters."""

DEPARTURES: tuple[tuple[str, str, str], ...] = (
    (
        "a recipe taking a bare prose positional",
        "# scaffold a wiki concept\nwikisplain concept:\n    python3 .meta/wikisplain.py {{concept}}\n",
        "not in the argument-passing contract",
    ),
    (
        "a declared recipe re-signed under the contract's back",
        "# the pull request gate\npr n extra *args:\n    python3 .meta/check_pr.py {{n}} {{extra}} {{args}}\n",
        "but the contract declares",
    ),
    (
        "a parameter declared and never interpolated",
        "# the pull request gate\npr n *args:\n    python3 .meta/check_pr.py {{n}}\n",
        "declares 'args' and never interpolates it",
    ),
    (
        "an interpolation naming no parameter, which expands to nothing",
        "# the pull request gate\npr n *args:\n    python3 .meta/check_pr.py {{nn}} {{args}}\n",
        "which it does not declare",
    ),
    (
        "a recipe implementing its own verb rather than invoking a tool",
        "# the pull request gate\npr n *args:\n    gh pr view {{n}} {{args}}\n",
        "invokes no tool under .meta/",
    ),
    (
        "a recipe `just --list` would index blank",
        "pr n *args:\n    python3 .meta/check_pr.py {{n}} {{args}}\n",
        "carries no doc comment",
    ),
    (
        "a recipe reached behind a dependency, which sits after the colon",
        "# the pull request gate\npr concept *args: sweep\n    python3 .meta/check_pr.py {{concept}} {{args}}\n",
        "but the contract declares",
    ),
)
"""Each case: what it is, the justfile that holds it, and the substring the step's finding must carry."""

TOLERATED: tuple[tuple[str, str], ...] = (
    (
        "a name the file assigns at its top level, which is not a parameter",
        'python := "python3"\n\n# the pull request gate\npr n *args:\n    {{python}} .meta/check_pr.py {{n}} {{args}}\n',
    ),
    (
        "a recipe whose body `just` runs quietly",
        "# the pull request gate\n@pr n *args:\n    python3 .meta/check_pr.py {{n}} {{args}}\n",
    ),
    (
        "a private recipe, which sits outside the operator surface even carrying a bare prose "
        "positional the contract would otherwise refuse (solorepo's #771)",
        "# the pull request gate\npr n *args:\n    python3 .meta/check_pr.py {{n}} {{args}}\n\n"
        "_scratch note:\n    python3 .meta/check_pr.py {{note}}\n",
    ),
)
"""Each conforming surface: what it holds, and the justfile that holds it."""


@check("verb surface probes", pre=True)
def verb_surface_probes() -> list[str]:
    """`justfile_recipe_shape` passes a conforming surface and names each departure the argument-passing contract refuses (solorepo's DR-106, solorepo's DR-259).

    Driven through the step's `path` and `contract` seams against a one-recipe
    contract, a surface whose recipe is documented, signed as the contract
    declares, invoking a tool under `.meta/` and interpolating every parameter
    it takes comes to `Passed`. Each departure in `DEPARTURES` comes to `Found`
    carrying the substring named beside it: a recipe the contract does not
    declare, which is how a bare prose positional arrives (solorepo's #482); a
    declared recipe whose signature changed; a parameter never interpolated; an
    interpolation naming no parameter, which `just` expands to nothing rather
    than refusing; a recipe implementing its own verb; a recipe carrying no doc
    comment; and a recipe carrying a dependency after its colon, which is read
    rather than skipped. Each surface in `TOLERATED` comes to `Passed`: a
    body interpolating a name the file assigns at its top level, a recipe
    `just` runs quietly, and a private (`_`-prefixed) recipe, which is outside
    the operator surface the contract governs even where its own shape would
    otherwise be refused (solorepo's #771). A surface holding no recipe the
    contract declares is reported as the missing recipe rather than passing
    silently.
    """
    contract: Contract = {"pr": (("n", IDENTIFIER), ("args", FLAGS))}
    problems = []

    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "justfile"

        path.write_text(CONFORMING, encoding="utf-8")
        outcome = justfile_recipe_shape(path=path, contract=contract)
        if not isinstance(outcome, Passed):
            problems.append(f"verb surface: a conforming surface came to {outcome!r}, not Passed")

        for name, text in TOLERATED:
            path.write_text(text, encoding="utf-8")
            outcome = justfile_recipe_shape(path=path, contract=contract)
            if not isinstance(outcome, Passed):
                problems.append(f"verb surface: {name} came to {outcome!r}, not Passed")

        for name, text, expected in DEPARTURES:
            path.write_text(text, encoding="utf-8")
            outcome = justfile_recipe_shape(path=path, contract=contract)
            if not isinstance(outcome, Found):
                problems.append(f"verb surface: {name} came to {outcome!r}, not Found")
            elif not any(expected in problem for problem in outcome.problems):
                problems.append(f"verb surface: {name} was found as {list(outcome.problems)}, "
                                f"which does not say {expected!r}")

        path.write_text("# what to work on next\nnext:\n    python3 .meta/next.py\n", encoding="utf-8")
        outcome = justfile_recipe_shape(path=path, contract=contract)
        if not isinstance(outcome, Found):
            problems.append(f"verb surface: a surface missing a declared recipe came to {outcome!r}, not Found")

    return problems
