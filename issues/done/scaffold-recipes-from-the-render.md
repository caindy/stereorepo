---
difficulty: medium
---

# Derive the scaffold-only recipes from the render

`SCAFFOLD_RECIPES` in `.meta/checks/files/justfile.py` lists by hand the
recipes a portfolio's `justfile` does not hold. The render decides the same
thing separately, in `justfile()` in `.meta/lib/render/writers.py`, by which
Artifacts `structure.yaml` asserts:

| Artifact | Recipes |
|---|---|
| `work:artifact/pair` | `pair`, `groom`, `pair-status`, `pair-accept`, `pair-resume`, `pair-watch` |
| `work:artifact/meta-test-specialization` | `test-specialization` |
| `work:artifact/meta-release` | `release` |
| `work:artifact/meta-audit` | `audit` |
| `work:artifact/meta-adapt` | `adapt` |

When a recipe is added under one of those conditions and not to the tuple,
every portfolio's `justfile recipe shape` step fails while stereorepo's
passes; `release` did exactly that (`release-recipe-is-scaffold-only`).

## Wanted

- The set of conditional recipes, each with the Artifact it depends on, is
  declared once, in one place that both the render and the check read (for
  example a table in `.meta/lib/render/writers.py` that `justfile()` iterates
  and `justfile.py` imports, or the reverse).
- `justfile()` renders each conditional recipe from that table, so a recipe
  added to it is both rendered under its condition and known to the check,
  and a recipe written outside it is unconditional.
- `SCAFFOLD_RECIPES` is derived from the table, or replaced by it, and the
  rendered `justfile` is byte-identical to today's.
- `justfile()` loads `structure.yaml` itself today, so it gains optional
  parameters (the structure and the table, defaulting to the asserted
  structure and the module's table), so that a probe can render a portfolio's
  surface without touching the repository's files.
- The probe in `.meta/checks/probes/surface.py` that mentions
  `SCAFFOLD_RECIPES` still describes what it tests.

## Out of scope

- Running a portfolio's gate before landing (`portfolio-gate-before-landing`).
- Changing which recipes are scaffold-only.
- How `justfile_recipe_shape` tells the scaffold from a portfolio: it keeps
  its `scaffold` argument (whether `template/` exists) and exempts every
  conditional recipe in a portfolio, without reading `structure.yaml`.

## Done when

- `SCAFFOLD_RECIPES` is no longer a hand-written list of names: a grep of
  `.meta/checks/` finds no literal list of the ten recipe names. `CONTRACT`
  still names each of them with its parameters; that is the argument
  contract, not the list of conditional recipes.
- A probe in `.meta/checks/probes/surface.py` adds an entry to the table
  under an Artifact a portfolio's `structure.yaml` lacks, and shows two
  things with no other edit: `justfile()` omits the recipe, and
  `justfile_recipe_shape(..., scaffold=False)` passes a contract that
  declares it.
- `just render` leaves the root `justfile` unchanged.

## The plan

The table lives with the render, in `.meta/lib/render/writers.py`, and the
check imports it: the render is what decides, and `.meta/checks/` already
imports `lib.render` (`.meta/checks/probes/tools/render.py`).

1. **The table.** In `writers.py`, add a `NamedTuple` `ConditionalRecipe`
   (`artifact`, `name`, `lines`) and a tuple `CONDITIONAL_RECIPES` holding the
   ten recipes in today's order: `pair`, `groom`, `pair-status`,
   `pair-accept`, `pair-resume`, `pair-watch`, `test-specialization`,
   `release`, `audit`, `adapt`. `lines` is a `tuple[str, ...]` holding the
   doc comment, header and body as rendered today, without the leading blank
   line.
2. **`justfile()`.** Signature becomes
   `justfile(structure: dict[str, Any] | None = None,
   conditional: tuple[ConditionalRecipe, ...] = CONDITIONAL_RECIPES) -> str`;
   `None` loads `assertions/structure.yaml` as now. The five `if ... in
   artifacts` blocks become one loop that appends `""` and `recipe.lines` for
   each recipe whose `artifact` is asserted. Today's pair block already
   separates its six recipes with a blank line each, so the output is
   byte-identical. `"../justfile": writers.justfile` in `TARGETS` in
   `.meta/lib/render/targets.py` and the import in `.meta/render.py` call it
   with no arguments and are unchanged. Docstring: say a conditional recipe
   is added to the table, not written inline.
3. **The check.** In `.meta/checks/files/justfile.py`, delete
   `SCAFFOLD_RECIPES` and import `CONDITIONAL_RECIPES` from
   `lib.render.writers`. Give `justfile_recipe_shape` a `conditional`
   parameter defaulting to `CONDITIONAL_RECIPES`; in a portfolio it pops the
   `name` of each of `conditional` from the effective contract. (Not
   `recipes`: the function already binds a local `recipes` to the parsed
   surface, and the first draft that used the name exempted the surface's
   own recipes instead of the table's.) Nothing
   else reads `SCAFFOLD_RECIPES` (it is not re-exported from
   `checks/files/__init__.py`), so a derived copy beside the parameter would
   be a second, unused name for the same set. The parameter lets the probe
   hand the render and the check the same extended table without editing a
   module constant. Keep `scaffold` as it is. Rewrite the docstring
   sentences that name `SCAFFOLD_RECIPES` to name the table.
4. **The probe.** In `.meta/checks/probes/surface.py`, add
   `conditional_recipe_probes`, a probe of its own beside
   `verb_surface_probes`. Folded into that function, the case took it past
   ruff's complexity and branch ceilings. An extra
   `ConditionalRecipe` under `work:artifact/absent` is appended to
   `CONDITIONAL_RECIPES`. Then:
   - `justfile(structure=portfolio, conditional=extended)`, where `portfolio` is
     `{"artifacts": []}`, holds no header for it. With no Projects, the
     `gate` doc comment reads "no Project is asserted yet", which the check
     accepts;
   - that rendered text, written to the temporary path, passes
     `justfile_recipe_shape(..., contract=CONTRACT plus the extra recipe,
     scaffold=False, conditional=extended)`;
   - with the artifact asserted, the render holds the recipe.
   Update the docstring sentence about `release` and `SCAFFOLD_RECIPES` so it
   names what the table is.
5. Run `just render` and confirm `git diff justfile` is empty.

**Risks.** Byte identity of the root `justfile`: the long doc comments for
`pair` and `audit` are written as string concatenations today, and must keep
their exact text. Step 5 catches any drift. Import order:
`checks.files.justfile` importing `lib.render.writers` pulls in
`lib.render.record` and `yaml`. Probes already do this, but if the check
module loads where `lib` is not on the path, the import fails at collection.
The new probe imports both modules, so it fails the same way if the import
does not resolve.

## Pair notes

> **primary, backlog turn 1**
>
> The issue was already groomed well, so I made one small change and left `difficulty: medium` as it was.
>
> I checked it against the code and it holds up:
> - `SCAFFOLD_RECIPES` in `.meta/checks/files/justfile.py` is a hand-written list of the ten recipes.
> - `justfile()` in `.meta/lib/render/writers.py` adds the same recipes under the five Artifacts the issue's table lists.
> - The probe in `.meta/checks/probes/surface.py` mentions `SCAFFOLD_RECIPES`.
> - Code under `.meta/checks/` already imports from `lib.render`, so the check can read a table kept with the render.
>
> **My change:** I added one point to "Out of scope". The check in `.meta/checks/files/justfile.py` (`justfile_recipe_shape`) keeps deciding scaffold versus portfolio the way it does now, by whether `template/` exists. In a portfolio it skips every recipe in the table, and it does not read `structure.yaml`. Without this, the "Done when" test could be read as asking the check to decide recipe by recipe from the Artifacts, which would be a bigger change than the issue intends.

> **secondary, backlog turn 2**
>
> The issue described the code accurately, and I left `difficulty: medium` as it was. I made three small edits so it is precise enough to plan from, and committed them.
>
> - **Rendering a portfolio's `justfile` in a probe:** `justfile()` in `.meta/lib/render/writers.py` loads `structure.yaml` itself. A probe therefore had no way to give it a portfolio's structure or a changed table. "Wanted" now asks for optional parameters for the structure and the table. They default to what is asserted today, so the root `justfile` renders the same as before.
> - **What the probe must show:** "Done when" now says the probe lives in `.meta/checks/probes/surface.py`. It must show two things with no other edit:
>   - the render leaves out a recipe added to the table under an Artifact the portfolio lacks;
>   - `justfile_recipe_shape(..., scaffold=False)` still passes when the contract declares that recipe.
> - **The grep test:** `CONTRACT` in `.meta/checks/files/justfile.py` will still name all ten recipes with their parameters. "Done when" now says this is expected, so those names don't count as the hand-written list the grep is looking for.

> **primary, backlog turn 3**
>
> I checked my partner's edits against the code and am keeping them, so I changed nothing this turn. `difficulty: medium` stays.
>
> - **Optional parameters for `justfile()`:** this is needed. `justfile()` in `.meta/lib/render/writers.py` takes no arguments and loads `assertions/structure.yaml` itself. Without the new parameters, a probe has no way to render a portfolio's `justfile`.
> - **The probe and the grep test:** the probe now has a specific job and a fixed home in `.meta/checks/probes/surface.py`. The grep test now says that `CONTRACT` still naming the ten recipes doesn't count as the hand-written list. Both changes are correct and fit with the scope note I added last turn.

> **primary, todo turn 1**
>
> I wrote the plan into the issue file under `## The plan`. I didn't find anything that blocks the issue, so there is no `# Needs elaboration` section.
>
> **Where the list lives:** in a new table, `CONDITIONAL_RECIPES` in `.meta/lib/render/writers.py`. Each entry names a recipe, the Artifact it depends on, and its rendered lines, in today's order. The check imports the table from there.
>
> **The steps:**
> 1. **Render:** `justfile()` gets two optional parameters, the structure and the table. With no arguments it loads `structure.yaml` and uses the module's table, so the two places that call it today don't change. Its five `if` blocks become one loop over the table. The six pair recipes are already separated by blank lines, so the loop gives the same output.
> 2. **Check:** `SCAFFOLD_RECIPES` in `.meta/checks/files/justfile.py` is built from the table's names instead of being typed out. `justfile_recipe_shape` gets a `recipes` parameter, so the probe can give the render and the check the same extended table without editing a module constant. The `scaffold` argument stays as it is.
> 3. **Probe:** a new case in `verb_surface_probes` in `.meta/checks/probes/surface.py` adds a recipe to the table under an Artifact that isn't asserted. It shows three things:
>    - the render leaves the recipe out;
>    - the rendered output passes the check as a portfolio's, even though the contract declares that recipe;
>    - when the Artifact is asserted, the render includes the recipe.
>
>    The probe's docstring sentence about `SCAFFOLD_RECIPES` is updated to describe what it now tests.
> 4. **Confirm:** `just render` must leave the root `justfile` unchanged.
>
> **Risks:**
> - **Exact text:** the doc comments for `pair` and `audit` are built by joining strings today, and must render exactly as they do now. Step 4 catches any difference.
> - **Import:** the check module will now import from `lib.render`, which also loads `yaml`. Probes already do this. The new probe imports both modules, so it fails if the import doesn't resolve.

> **secondary, todo turn 2**
>
> I read my partner's plan against the code and it holds up, so I kept it and made three edits to it, which are committed. Nothing blocks the issue, so there is no `# Needs elaboration` section.
>
> - **Step 3, the check:** the plan builds `SCAFFOLD_RECIPES` from the table and also gives `justfile_recipe_shape` a `recipes` parameter. Nothing would read that constant, because nothing else uses it and `checks/files/__init__.py` doesn't export it. So the same set of names would live in two places again. The step now deletes `SCAFFOLD_RECIPES` and rewrites the docstring sentences that mention it to name the table instead.
> - **Step 1, the table:** each entry's rendered lines are now an immutable tuple of strings, so the table can't be changed in place.
> - **Step 4, the probe:** the portfolio structure is now spelled out as `{"artifacts": []}`. With no Projects asserted, the doc comment on `gate` reads "no Project is asserted yet", which the check accepts. So rendering the whole `justfile` and then checking it works as the plan expects.
>
> On the plan's import risk: no module in `.meta/checks/files/` imports from `lib` yet, but `.meta/gate` runs with pyyaml and the probes already import `lib.render`, so the import should work wherever the checks run.

> **primary, todo turn 3**
>
> The plan stands, so I changed nothing this turn.
>
> I checked my partner's three edits against the code and am keeping them:
>
> - **Deleting `SCAFFOLD_RECIPES`:** this is allowed. "Wanted" says the constant may be "derived from the table, or replaced by it". The only places that use it are inside `.meta/checks/files/justfile.py`, so once `justfile_recipe_shape` takes a `recipes` parameter, a copy built from the table would have no reader.
> - **Rendered lines as a tuple:** each entry's lines are now a `tuple[str, ...]`, so the table can't be changed in place. That is safe for a module-level default that the probe extends.
> - **The probe's `{"artifacts": []}` structure:** the check needs the `gate` recipe to have a doc comment, and the render still gives it one. With no Projects asserted it reads "no Project is asserted yet". So the probe can render the whole `justfile` and then run the check on it as the plan expects.

> **primary, in-progress turn 1**
>
> The list of scaffold-only recipes now lives in one table that both the render and the check read. `just render` leaves the root `justfile` byte-for-byte unchanged, and `just gate meta` passes. I didn't run any other gate, because the change only touches `.meta/` and the issue file. It is committed.
>
> - **The table:** `CONDITIONAL_RECIPES` in `.meta/lib/render/writers.py` lists each of the ten recipes with the Artifact it depends on and its rendered lines. `justfile()` now has one loop over the table instead of five separate `if` blocks. It also takes two optional arguments, the structure and the table. Called with none, it behaves as before.
> - **The check:** `SCAFFOLD_RECIPES` is gone. `justfile_recipe_shape` in `.meta/checks/files/justfile.py` imports the table and takes it as a `conditional` argument. In a portfolio, it skips every recipe in the table.
> - **The probe:** the new `conditional_recipe_probes` in `.meta/checks/probes/surface.py` adds a recipe to the table under an Artifact that isn't asserted, and changes nothing else. It shows three things:
>   - a portfolio's render leaves the recipe out;
>   - that rendered file passes the check as a portfolio's, even though the contract declares the recipe;
>   - with the Artifact asserted, the render includes the recipe.
>
>   I broke the render on purpose, so that it ignored the Artifact condition, and the probe failed as it should. Without that break, it passes.
>
> I updated the plan in the issue file where the work didn't go as written:
>
> - **Parameter name:** the plan called the new parameter `recipes`, but the check already uses a local variable with that name for the parsed `justfile`. My first draft therefore skipped the file's own recipes instead of the table's, and the existing probes failed. I renamed it to `conditional` in both functions.
> - **Separate probe:** adding the new case inside `verb_surface_probes` made that function too complex for ruff's limits. So it is its own probe.
>
> I found nothing outside this issue that needed a new backlog file.

> **secondary, in-progress turn 2**
>
> I'm leaving the implementation as it stands and changed nothing this turn.
>
> - **Matches the plan:** the plan in the issue file already records the two places the work departed from it. The new parameter is called `conditional`, because the check already had a local variable named `recipes`. The new case is its own probe, because adding it to `verb_surface_probes` broke ruff's complexity limits.
> - **The root `justfile`:** `just render` leaves it unchanged, and the working tree was clean afterwards.
> - **The meta gate:** `just gate meta` passes, all 95 steps. Its steps include the new `conditional recipe probes`.
> - **Nothing left behind:** a search outside `issues/` finds no remaining mention of `SCAFFOLD_RECIPES`. No wiki page, Decision Record or `AGENTS.md` describes adding a scaffold-only recipe, so no document needed to change with the code.
> - **A mistyped Artifact id is still caught:** if a table entry named an Artifact that doesn't exist, the scaffold's render would leave that recipe out. The scaffold's check would then report it missing, because `CONTRACT` still declares it.
