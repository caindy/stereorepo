"""`boundary.operator_boundary`, driven against the steps it exists to refuse and the
ones it must not (solorepo's DR-209, solorepo's DR-275).

The step is in the gate, so a wrong `Found` on this tree shows as a failure. What it
cannot show is a wrong `Passed` — a step that types the script again once solorepo's #918's call
sites are back to reading normally — or a wrong `Found` on a file the tree does not
happen to hold today, the prose of an agent workflow's `prompt:` being the one that
names these tools most often. Both are asked here, one case at a time.
"""

import pathlib
import tempfile

from checks.collect import Found, Passed, check
from checks.files.boundary import TEMPLATE_WORKFLOWS, operator_boundary

SURFACE = """# every Project's gate
gate target="":
    .meta/gate {{target}}

# the pull request gate
pr n *args:
    python3 .meta/check_pr.py {{n}} {{args}}

# every generated page, from the assertions
render:
    uvx --python 3.13 --with pyyaml python .meta/render.py

# evaluate open pull requests and merge the top candidate
merge-manager *args:
    .meta/say/move merge-manager {{args}}
"""
"""A verb surface of four recipes: one wrapping a bare tool, one an interpreted script, one
an `uvx`-run script, and one a verb of the channel, which is the Attested Mutation Plane's
and not this rule's (solorepo's DR-252)."""

WORKFLOW = "on: push\njobs:\n  one:\n    runs-on: ubuntu-latest\n    steps:\n      - run: {}\n"
"""A one-step workflow, its `run:` filled in per case."""

DEPARTURES: tuple[tuple[str, str, str], ...] = (
    (
        "a bare tool a recipe wraps",
        WORKFLOW.format(".meta/gate"),
        "`just gate`",
    ),
    (
        "an interpreted script a recipe wraps",
        WORKFLOW.format("python3 .meta/check_pr.py 5 --threads"),
        "`just pr`",
    ),
    (
        "a script a recipe wraps, run through uvx",
        WORKFLOW.format("uvx --python 3.13 --with pyyaml python .meta/render.py"),
        "`just render`",
    ),
    (
        "a wrapped tool reached behind an environment assignment",
        WORKFLOW.format("GH_TOKEN=x .meta/gate"),
        "`just gate`",
    ),
    (
        "a wrapped tool on the far side of a shell operator",
        WORKFLOW.format("|\n          git fetch origin && python3 .meta/check_pr.py --sweep"),
        "`just pr`",
    ),
    (
        "a composite action's own step",
        "runs:\n  using: composite\n  steps:\n    - run: .meta/gate\n      shell: bash\n",
        "`just gate`",
    ),
)
"""Each case: what it is, the file that holds it, and the substring the finding must carry."""

TOLERATED: tuple[tuple[str, str], ...] = (
    (
        "a verb of the channel, which a workflow addresses directly (solorepo's DR-252)",
        WORKFLOW.format(".meta/say/move merge-manager --dry-run"),
    ),
    (
        "a tool no recipe wraps",
        WORKFLOW.format("uvx --python 3.13 --with pyyaml python .meta/check.py"),
    ),
    (
        "a wrapped tool named as an argument rather than run",
        WORKFLOW.format("git checkout origin/main -- .meta/check_pr.py"),
    ),
    (
        "a wrapped tool inside a comment",
        WORKFLOW.format("|\n          # was: .meta/gate meta\n          just gate meta"),
    ),
    (
        "a wrapped tool inside an agent's prompt, which is prose and not a step",
        "on: push\njobs:\n  one:\n    steps:\n      - uses: anthropics/claude-code-action@v1\n"
        "        with:\n          prompt: |\n            Run python3 .meta/check_pr.py 5\n",
    ),
    (
        "the recipe itself",
        WORKFLOW.format("just gate meta"),
    ),
)
"""Each conforming file: what it holds, and the file that holds it."""


@check("operator boundary probes", pre=True)
def operator_boundary_probes() -> list[str]:
    """`operator_boundary` finds a step that types a wrapped tool, and no step that only names one.

    The rule is solorepo's DR-275's, as solorepo's #921 and solorepo's #940 widened it.
    Driven through the step's `justfile` and `roots` seams against a four-recipe
    surface. Each departure in `DEPARTURES` comes to `Found` naming the recipe the step
    owed: a bare tool, an interpreted script, one run through `uvx`, one behind an
    environment assignment, one on the far side of a shell operator, and one in a
    composite action's own steps rather than a workflow job's. Each file in `TOLERATED`
    comes to `Passed`: a verb of the channel, a tool no recipe wraps, a wrapped tool
    passed to `git` as an argument, one inside a shell comment, one inside an agent's
    `prompt:`, and the recipe itself. A tree holding no workflow at all comes to
    `CouldNotRun` rather than passing on an empty scan.
    """
    problems = []

    default_roots = operator_boundary.__defaults__[1] if operator_boundary.__defaults__ else ()
    if TEMPLATE_WORKFLOWS not in default_roots:
        problems.append("operator boundary: TEMPLATE_WORKFLOWS is not in default roots")

    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        justfile = root / "justfile"
        justfile.write_text(SURFACE, encoding="utf-8")
        workflows = root / "workflows"
        workflows.mkdir()
        path = workflows / "one.yml"

        for name, text in TOLERATED:
            path.write_text(text, encoding="utf-8")
            outcome = operator_boundary(justfile=justfile, roots=(workflows,))
            if not isinstance(outcome, Passed):
                problems.append(f"operator boundary: {name} came to {outcome!r}, not Passed")

        for name, text, expected in DEPARTURES:
            path.write_text(text, encoding="utf-8")
            outcome = operator_boundary(justfile=justfile, roots=(workflows,))
            if not isinstance(outcome, Found):
                problems.append(f"operator boundary: {name} came to {outcome!r}, not Found")
            elif not any(expected in problem for problem in outcome.problems):
                problems.append(f"operator boundary: {name} was found as {list(outcome.problems)}, "
                                f"which does not say {expected!r}")

        path.unlink()
        outcome = operator_boundary(justfile=justfile, roots=(workflows,))
        if isinstance(outcome, (Passed, Found)):
            problems.append(f"operator boundary: a tree with no workflow came to {outcome!r}, "
                            "not CouldNotRun")

    return problems
