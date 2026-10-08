"""What the root verb surface owes its callers: a recipe signature built from
flags, subcommands and atomic identifiers, every parameter reaching the tool it
was declared for, and a doc comment for the index `just --list` prints
(stereorepo's DR-329, stereorepo's DR-349).

The surface this governs is the public one: a `just` private recipe (its name
prefixed `_`) is an internal subroutine called only from another recipe's
body, never typed by an operator and never listed by `just --list`, so it
sits outside stereorepo's DR-349's operator-facing contract and this module does
not see it.
"""

import pathlib
import re
from typing import NamedTuple

from checks.collect import ROOT, TEMPLATE, CouldNotRun, Found, Passed, StepOutcome, check
from lib.render.writers import CONDITIONAL_RECIPES, ConditionalRecipe

Contract = dict[str, tuple[tuple[str, str], ...]]
"""A recipe name against the parameters it takes, each paired with the kind of value it carries."""

JUSTFILE = ROOT / "justfile"
"""The rendered root verb surface, which is the only justfile the contract governs."""

RECIPE = re.compile(r"^@?(?P<name>[a-z][a-z0-9_-]*)(?P<params>(?:\s+[^\s:]+)*)\s*:(?!=).*$")
"""Matches a recipe header line, capturing the verb and the parameter list before the colon.
Dependencies after the colon are matched and discarded, so a recipe that has them is still read;
`(?!=)` keeps a top-level `name := value` assignment out. The name group excludes a leading `_`
by design, not oversight: a `just` private recipe is outside the operator surface this contract
governs, so this pattern is deliberately blind to it rather than admitting it
and exempting it downstream."""

ASSIGNMENT = re.compile(r"^(?:export\s+)?(?P<name>[a-z][a-z0-9_-]*)\s*:=")
"""Matches a top-level assignment, whose name a recipe body may interpolate without declaring it."""

INTERPOLATION = re.compile(r"\{\{\s*(?P<name>[A-Za-z_][A-Za-z0-9_-]*)\s*\}\}")
"""Matches a `{{name}}` interpolation in a recipe body, capturing the parameter it names. A just
function or conditional carries parentheses or braces and is not a bare name, so neither matches."""

FLAGS = "flags"
"""A variadic tail forwarding flags, subcommands and atomic identifiers to the tool."""

SUBCOMMAND = "subcommand"
"""A scalar naming one of a closed set of targets the recipe dispatches on."""

TOOL_ROOTS = (".meta/", "pair/")
"""Where a recipe's tool may live: the staging ground, or the scaffold-only pair loop."""

IDENTIFIER = "identifier"
"""A scalar carrying one atomic identifier, such as an issue slug."""

CONTRACT: Contract = {
    "default": (),
    "gate": (("targets", FLAGS),),
    "render": (),
    "dereference": (("args", FLAGS),),
    "terms": (("args", FLAGS),),
    "apm": (("args", FLAGS),),
    "bootstrap": (("args", FLAGS),),
    "audit": (("project", IDENTIFIER), ("bootstrap", IDENTIFIER), ("args", FLAGS)),
    "sync": (("args", FLAGS),),
    "test-specialization": (("args", FLAGS),),
    "release": (("args", FLAGS),),
    "adapt": (("args", FLAGS),),
    "pair": (("args", FLAGS),),
    "groom": (("args", FLAGS),),
    "pair-status": (("args", FLAGS),),
    "pair-accept": (("args", FLAGS),),
    "pair-resume": (("args", FLAGS),),
    "pair-watch": (("args", FLAGS),),
    "pair-replay": (("args", FLAGS),),
    "pair-replay-report": (("args", FLAGS),),
}
"""The declared shape of every root recipe: each parameter in signature order, paired with
the kind of value it carries. There is no prose kind to declare, so a recipe taking a bare
multi-word positional cannot be written down here and fails the step until it is redesigned
(stereorepo's DR-349)."""


def _parameters(raw: str) -> list[tuple[str, str]]:
    """Reads a recipe's raw parameter list into (name, kind) pairs.

    Tokenizes on whitespace, so a `SUBCOMMAND` default may not itself contain a
    space: `greeting="hello world"` reads as two bogus parameters rather than one.

    Args:
        raw: The text between a recipe's name and its colon.

    Returns:
        list[tuple[str, str]]: One pair per parameter, in signature order, the kind being
        `FLAGS` for a `*`- or `+`-prefixed variadic, `SUBCOMMAND` for a scalar carrying a
        default, and `IDENTIFIER` for a bare scalar.
    """
    parameters = []
    for token in raw.split():
        if token.startswith(("*", "+")):
            parameters.append((token[1:], FLAGS))
        elif "=" in token:
            parameters.append((token.split("=", 1)[0], SUBCOMMAND))
        else:
            parameters.append((token, IDENTIFIER))
    return parameters


class Recipe(NamedTuple):
    """One recipe as the justfile declares it."""

    number: int
    """The line its header sits on, as the finding names it."""
    name: str
    """Its verb, which is the key the contract declares it under."""
    parameters: tuple[tuple[str, str], ...]
    """Its parameters in signature order, each paired with the kind of value it carries."""
    body: tuple[str, ...]
    """Its indented body lines."""
    documented: bool
    """Whether a doc comment sits immediately above its header, which `just --list` prints."""


def _recipes(text: str) -> list[Recipe]:
    """Parses a justfile into its recipes.

    Args:
        text: The whole justfile.

    Returns:
        list[Recipe]: One entry per recipe header the file holds, in the order they appear.
    """
    recipes = []
    lines = text.splitlines()
    for number, line in enumerate(lines, 1):
        match = RECIPE.match(line)
        if not match:
            continue
        documented = number > 1 and lines[number - 2].lstrip().startswith("#")
        body = []
        for following in lines[number:]:
            if not following.strip():
                break
            if not following.startswith((" ", "\t")):
                break
            body.append(following)
        recipes.append(Recipe(number, match["name"], tuple(_parameters(match["params"])),
                              tuple(body), documented))
    return recipes


def _departures(where: str, recipe: Recipe, declared: tuple[tuple[str, str], ...] | None,
                assignments: frozenset[str]) -> list[str]:
    """Reads one recipe against the shape the contract declares for it.

    Args:
        where: The recipe's file and line, as the finding names it.
        recipe: The recipe as `_recipes` parsed it.
        declared: The parameters the contract declares, or None if it declares no such recipe.
        assignments: The names the justfile assigns at its top level, which a body may
            interpolate without declaring them as parameters.

    Returns:
        list[str]: One line per departure, empty where the recipe conforms.
    """
    name, parameters, body, documented = (
        recipe.name,
        recipe.parameters,
        recipe.body,
        recipe.documented,
    )
    problems = []
    if declared is None:
        problems.append(
            f"{where} is not in the argument-passing contract — declare its parameters in "
            "CONTRACT as flags, a subcommand or an atomic identifier, or route it to an "
            "agent skill if it takes prose (stereorepo's DR-349)"
        )
    elif parameters != declared:
        problems.append(f"{where} takes {parameters}, but the contract declares {declared}")

    interpolated = {match["name"] for line in body for match in INTERPOLATION.finditer(line)}
    problems += [f"{where} declares '{parameter}' and never interpolates it"
                 for parameter, _ in parameters if parameter not in interpolated]
    known = {parameter for parameter, _ in parameters} | assignments
    problems += [f"{where} interpolates '{{{{{unknown}}}}}', which it does not declare"
                 for unknown in sorted(interpolated - known)]

    if name != "default" and not any(root in line for line in body for root in TOOL_ROOTS):
        problems.append(f"{where} invokes no tool under .meta/ (stereorepo's DR-329)")
    if not documented:
        problems.append(f"{where} carries no doc comment, so `just --list` indexes it blank")
    return problems


@check("justfile recipe shape")
def justfile_recipe_shape(
    path: pathlib.Path = JUSTFILE,
    contract: Contract = CONTRACT,
    scaffold: bool | None = None,
    conditional: tuple[ConditionalRecipe, ...] = CONDITIONAL_RECIPES,
) -> StepOutcome:
    """Checks that root recipes meet the declared argument-passing contract.

    The root `justfile` interpolates `{{name}}` unquoted, so a caller's quotes
    around a multi-word value are discarded before the tool sees its argv. The
    contract answers that by admitting only flags, subcommands and atomic
    identifiers, none of which carry a space. This step holds the rendered
    surface to it: the recipes present are the recipes `CONTRACT` declares, each
    with the same parameters in the same order and of the same kind; every
    parameter is interpolated into the body at least once; every interpolation
    names a declared parameter or a name the file assigns at its top level, an
    unnamed one expanding to nothing rather than failing; every body invokes a
    tool under `.meta/`, or the pair loop under `pair/`; and every recipe
    carries the doc comment `just --list` prints as the index. A portfolio's
    surface is not held to the conditional recipes, which the render writes only
    under an Artifact a portfolio may lack.

    Args:
        path: The justfile to read.
        contract: The recipes the surface must hold, against their parameters.
        scaffold: Whether the surface is the scaffold's, which holds
            every one of `conditional`; `None` asks whether `template/` exists.
        conditional: The recipes the render writes only under an Artifact,
            which a portfolio's surface is not held to.

    Returns:
        Passed | Found | CouldNotRun: The recipes checked, or one line per departure.
    """
    if not path.is_file():
        return CouldNotRun(f"no justfile at {path}")

    text = path.read_text(encoding="utf-8")
    recipes = _recipes(text)
    if not recipes:
        return CouldNotRun(f"{path.name} holds no recipes")

    effective_contract = dict(contract)
    if scaffold is None:
        scaffold = TEMPLATE.is_dir()
    if not scaffold:
        for exempt in conditional:
            effective_contract.pop(exempt.name, None)

    assignments = frozenset(match["name"] for line in text.splitlines()
                            if (match := ASSIGNMENT.match(line)))
    problems: list[str] = []
    seen = set()
    for recipe in recipes:
        seen.add(recipe.name)
        problems += _departures(f"{path.name}:{recipe.number} {recipe.name}", recipe,
                                effective_contract.get(recipe.name), assignments)

    problems += [
        (
            f"{path.name}: the contract declares '{missing}', which the rendered surface "
            "does not hold"
        )
        for missing in sorted(set(effective_contract) - seen)
    ]

    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(recipes)} recipes, each taking flags, subcommands or atomic identifiers")
