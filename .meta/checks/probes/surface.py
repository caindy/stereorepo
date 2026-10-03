"""The root verb surface's argument contract, driven against the departures it exists to refuse (stereorepo's DR-349, stereorepo's DR-342).
"""

import pathlib
import tempfile

from checks.collect import Found, Passed, check
from checks.files.justfile import CONTRACT, FLAGS, IDENTIFIER, Contract, justfile_recipe_shape
from lib.render.writers import CONDITIONAL_RECIPES, ConditionalRecipe, justfile

ABSENT = ConditionalRecipe("work:artifact/absent", "absent", (
    "# a recipe under an Artifact no portfolio asserts",
    "absent *args:",
    "    .meta/absent.py {{args}}",
))
"""A conditional recipe added to the table and nowhere else, as a new scaffold-only verb arrives."""

CONFORMING = """# what landed
landed n *args:
    python3 .meta/show.py {{n}} {{args}}
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
        "# what landed\nlanded n extra *args:\n    python3 .meta/show.py {{n}} {{extra}} {{args}}\n",
        "but the contract declares",
    ),
    (
        "a parameter declared and never interpolated",
        "# what landed\nlanded n *args:\n    python3 .meta/show.py {{n}}\n",
        "declares 'args' and never interpolates it",
    ),
    (
        "an interpolation naming no parameter, which expands to nothing",
        "# what landed\nlanded n *args:\n    python3 .meta/show.py {{nn}} {{args}}\n",
        "which it does not declare",
    ),
    (
        "a recipe implementing its own verb rather than invoking a tool",
        "# what landed\nlanded n *args:\n    git log --grep {{n}} {{args}}\n",
        "invokes no tool under .meta/",
    ),
    (
        "a recipe `just --list` would index blank",
        "landed n *args:\n    python3 .meta/show.py {{n}} {{args}}\n",
        "carries no doc comment",
    ),
    (
        "a recipe reached behind a dependency, which sits after the colon",
        "# what landed\nlanded concept *args: render\n    python3 .meta/show.py {{concept}} {{args}}\n",
        "but the contract declares",
    ),
)
"""Each case: what it is, the justfile that holds it, and the substring the step's finding must carry."""

TOLERATED: tuple[tuple[str, str], ...] = (
    (
        "a name the file assigns at its top level, which is not a parameter",
        'python := "python3"\n\n# what landed\nlanded n *args:\n    {{python}} .meta/show.py {{n}} {{args}}\n',
    ),
    (
        "a recipe whose body `just` runs quietly",
        "# what landed\n@landed n *args:\n    python3 .meta/show.py {{n}} {{args}}\n",
    ),
    (
        "a private recipe, which sits outside the operator surface even carrying a bare prose "
        "positional the contract would otherwise refuse",
        "# what landed\nlanded n *args:\n    python3 .meta/show.py {{n}} {{args}}\n\n"
        "_scratch note:\n    python3 .meta/show.py {{note}}\n",
    ),
)
"""Each conforming surface: what it holds, and the justfile that holds it."""


@check("verb surface probes", pre=True)
def verb_surface_probes() -> list[str]:
    """`justfile_recipe_shape` passes a conforming surface and names each departure the argument-passing contract refuses (stereorepo's DR-329, stereorepo's DR-349).

    Driven through the step's `path` and `contract` seams against a one-recipe
    contract, a surface whose recipe is documented, signed as the contract
    declares, invoking a tool under `.meta/` and interpolating every parameter
    it takes comes to `Passed`. Each departure in `DEPARTURES` comes to `Found`
    carrying the substring named beside it: a recipe the contract does not
    declare, which is how a bare prose positional arrives; a
    declared recipe whose signature changed; a parameter never interpolated; an
    interpolation naming no parameter, which `just` expands to nothing rather
    than refusing; a recipe implementing its own verb; a recipe carrying no doc
    comment; and a recipe carrying a dependency after its colon, which is read
    rather than skipped. Each surface in `TOLERATED` comes to `Passed`: a
    body interpolating a name the file assigns at its top level, a recipe
    `just` runs quietly, and a private (`_`-prefixed) recipe, which is outside
    the operator surface the contract governs even where its own shape would
    otherwise be refused. A surface holding no recipe the
    contract declares is reported as the missing recipe rather than passing
    silently. A surface without `release`, one of `CONDITIONAL_RECIPES`, passes
    as a portfolio's and is reported missing as the scaffold's.
    """
    contract: Contract = {"landed": (("n", IDENTIFIER), ("args", FLAGS))}
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

        path.write_text(CONFORMING, encoding="utf-8")
        with_release: Contract = {**contract, "release": (("args", FLAGS),)}
        without = "a surface without 'release'"
        outcome = justfile_recipe_shape(path=path, contract=with_release, scaffold=False)
        if not isinstance(outcome, Passed):
            problems.append(f"verb surface: {without}, as a portfolio's, came to {outcome!r}")
        outcome = justfile_recipe_shape(path=path, contract=with_release, scaffold=True)
        missing = "the contract declares 'release'"
        if not isinstance(outcome, Found):
            problems.append(f"verb surface: {without}, as the scaffold's, came to {outcome!r}")
        elif not any(missing in problem for problem in outcome.problems):
            problems.append(f"verb surface: {without}, as the scaffold's, was found as "
                            f"{list(outcome.problems)}, which does not say {missing!r}")

    return problems


@check("conditional recipe probes", pre=True)
def conditional_recipe_probes() -> list[str]:
    """A recipe added to `CONDITIONAL_RECIPES` alone is rendered and exempted under its Artifact.

    `ABSENT`, appended to the table and declared in the contract, is the only
    edit. `justfile()` omits it from a portfolio asserting no Artifact, and
    that portfolio's rendered surface comes to `Passed` as a portfolio's,
    though the contract declares it. With its Artifact asserted, the render
    holds it.
    """
    problems = []
    extended = (*CONDITIONAL_RECIPES, ABSENT)
    header = ABSENT.lines[1]
    portfolio = justfile(structure={"artifacts": []}, conditional=extended)
    if header in portfolio.splitlines():
        problems.append(f"conditional recipe: a portfolio asserting no Artifact holds {header!r}")

    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "justfile"
        path.write_text(portfolio, encoding="utf-8")
        contract = {**CONTRACT, ABSENT.name: (("args", FLAGS),)}
        outcome = justfile_recipe_shape(path=path, contract=contract, scaffold=False,
                                        conditional=extended)
    if not isinstance(outcome, Passed):
        problems.append(f"conditional recipe: a portfolio's rendered surface came to {outcome!r}")

    asserted = justfile(structure={"artifacts": [{"id": ABSENT.artifact}]}, conditional=extended)
    if header not in asserted.splitlines():
        problems.append(f"conditional recipe: {header!r} is missing under its asserted Artifact")
    return problems
