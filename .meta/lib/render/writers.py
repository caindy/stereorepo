"""The files a render writes that are not prose: the justfile (stereorepo's DR-329) and the APM primitives (stereorepo's DR-172, stereorepo's DR-333).
"""

from typing import Any, NamedTuple

from lib.render import META, record


class ConditionalRecipe(NamedTuple):
    """A recipe the justfile holds only where `structure.yaml` asserts the Artifact it invokes."""

    artifact: str
    """The id of the Artifact whose tool the recipe invokes, such as `work:artifact/pair`."""
    name: str
    """The recipe's name, as its header declares it."""
    lines: tuple[str, ...]
    """The doc comment, header and body, as rendered."""


PAIR = "work:artifact/pair"
"""The pair loop, which a portfolio does not carry."""

CONDITIONAL_RECIPES: tuple[ConditionalRecipe, ...] = (
    ConditionalRecipe(PAIR, "pair", (
        "# the pair loop: carry issues to main"
        " (--once, --push, --flight SLUG, --single-seat, --model, --STAGE-model)",
        "pair *args:",
        "    uv run --quiet --script pair/pair.py run {{args}}",
    )),
    ConditionalRecipe(PAIR, "groom", (
        "# groom the backlog issues with no difficulty, and place them in ORDER (--rerank)",
        "groom *args:",
        "    uv run --quiet --script pair/pair.py groom {{args}}",
    )),
    ConditionalRecipe(PAIR, "pair-status", (
        "# what waits on you, what is underway, the running order, and the counts (--json)",
        "pair-status *args:",
        "    uv run --quiet --script pair/pair.py status {{args}}",
    )),
    ConditionalRecipe(PAIR, "pair-accept", (
        "# pass the desk check and land it (with a Flight's slug: move it to done/)",
        "pair-accept *args:",
        "    uv run --quiet --script pair/pair.py accept {{args}}",
    )),
    ConditionalRecipe(PAIR, "pair-resume", (
        "# fail the desk check: the pair picks up your notes (a Flight's slug: to backlog/)",
        "pair-resume *args:",
        "    uv run --quiet --script pair/pair.py resume {{args}}",
    )),
    ConditionalRecipe(PAIR, "pair-watch", (
        "# print the loop's events until --until landed, developer, or flight SLUG",
        "pair-watch *args:",
        "    uv run --quiet --script pair/pair.py watch {{args}}",
    )),
    ConditionalRecipe(PAIR, "pair-replay", (
        "# run a landed Issue again in a scratch clone: SLUG --mode single|pair (--force)",
        "pair-replay *args:",
        "    uv run --quiet --script pair/pair.py replay {{args}}",
    )),
    ConditionalRecipe("work:artifact/meta-test-specialization", "test-specialization", (
        "# Specialization, end to end, in a scratch repository (stereorepo's DR-347, DR-244)",
        "test-specialization *args:",
        "    uvx --python 3.13 --with pyyaml python .meta/test_specialization.py {{args}}",
    )),
    ConditionalRecipe("work:artifact/meta-release", "release", (
        "# tag a release of the APM package and publish it (--dry-run) (stereorepo's DR-320)",
        "release *args:",
        "    uvx --python 3.13 --with pyyaml python .meta/release.py {{args}}",
    )),
    ConditionalRecipe("work:artifact/meta-audit", "audit", (
        "# audit a Project's gate against a language Bootstrap, printing each gap as an Issue"
        " (--repository PATH) (stereorepo's DR-353, DR-358)",
        "audit project bootstrap *args:",
        "    .meta/audit.py {{project}} {{bootstrap}} {{args}}",
    )),
    ConditionalRecipe("work:artifact/meta-adapt", "adapt", (
        "# plan brownfield adoption for an existing Product repository",
        "adapt *args:",
        "    .meta/adapt.py {{args}}",
    )),
)
"""The recipes rendered only under an Artifact, in the order the justfile holds them. A recipe
whose tool a portfolio may lack is added here rather than written into `justfile()`, so the render
omits it where the Artifact is absent and `justfile_recipe_shape` does not demand it of a
portfolio."""


def justfile(structure: dict[str, Any] | None = None,
             conditional: tuple[ConditionalRecipe, ...] = CONDITIONAL_RECIPES) -> str:
    """The root's verb surface, rendered so that the one line in it that names
    anything comes from the assertions rather than a list kept beside them
    (stereorepo's DR-329).

    Every recipe invokes a tool under `.meta/` and implements nothing; `just
    --list` is the index. The doc comment on `gate` names what the runner
    takes, read from the Projects and Products asserted, which is the line
    that would otherwise drift when a Project is added. Never copied into a
    seed: a verb in every Project is what stereorepo's DR-092 rejected. Each of
    `conditional` follows the unconditional ones where its Artifact is asserted.

    Args:
        structure: The structure to render from; `None` loads the asserted one.
        conditional: The conditional recipes, `CONDITIONAL_RECIPES` unless a probe extends them.

    Returns:
        str: The justfile's text.
    """
    if structure is None:
        structure = record.load("assertions/structure.yaml") or {}

    def tail(p: dict[str, Any]) -> str:
        return str(p["id"]).rsplit("/", 1)[-1]

    projects = ", ".join(tail(p) for p in structure.get("projects") or [])
    products = ", ".join(tail(p) for p in structure.get("products") or [])
    takes = (f"any of the Projects: {projects}" if projects else "no Project is asserted yet")
    if products:
        takes += f" — and the Products: {products}"
    lines = [
        "# Generated by .meta/render.py from assertions/structure.yaml. Do not edit by hand:",
        "# edit the assertions and re-render.",
        "#",
        "# The verbs, typed. Every recipe invokes a tool under .meta/ and implements",
        "# nothing; `just --list` is the index (stereorepo's DR-329). Not installed? `uvx --from rust-just just`.",
        "",
        "# every recipe, and what it does",
        "default:",
        "    @just --list --unsorted",
        "",
        f"# every Project's gate — or {takes}",
        "gate *targets:",
        "    .meta/gate {{targets}}",
        "",
        "# every generated page, from the assertions",
        "render:",
        "    uvx --python 3.13 --with pyyaml python .meta/render.py",
        "",
        "# the citations this branch wrote, read against what they name; not a gate",
        'dereference *args:',
        "    uvx --python 3.13 --with linkml --with pyyaml python .meta/dereference.py {{args}}",
        "",
        "# surface unminted candidate terms by keyness and dispersion (stereorepo's DR-234)",
        "terms *args:",
        "    uvx --python 3.13 --with wordfreq python .meta/terms.py {{args}}",
        "",
        "# validate, pack, or compile the APM package (stereorepo's DR-201)",
        "apm *args:",
        "    python3 .meta/apm_compile.py {{args}}",
        "",
        "# instantiate a Project from a language Bootstrap on demand (stereorepo's DR-206)",
        "bootstrap *args:",
        "    uvx --python 3.13 --with pyyaml python .meta/bootstrap.py {{args}}",
        "",
        "# copy a stereorepo checkout's managed items here and remove what it dropped"
        " (stereorepo's DR-315)",
        "sync *args:",
        "    .meta/bundle.py sync {{args}}",
    ]

    artifacts = {art["id"] for art in structure.get("artifacts") or [] if "id" in art}
    for recipe in conditional:
        if recipe.artifact in artifacts:
            lines += ["", *recipe.lines]

    return "\n".join(lines) + "\n"


def apm_primitives() -> dict[str, str | bytes]:
    """Compiles .meta/assertions/ into .meta/.apm/ primitives and .meta/apm.yml (stereorepo's DR-172, stereorepo's DR-333)."""
    import apm_compile
    return apm_compile.rendered_primitives(META)
