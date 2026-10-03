---
difficulty: easy
---

# Count `release` among the recipes only the scaffold renders

Every portfolio's `meta` gate fails `justfile recipe shape` with "the contract
declares 'release', which the rendered surface does not hold". `f1bb5d3`
added `release` to `CONTRACT` in `.meta/checks/files/justfile.py`, and the
render writes the recipe only where `work:artifact/meta-release` is asserted
(`.meta/lib/render/writers.py`), which is in stereorepo alone. The recipe was
not added to `SCAFFOLD_RECIPES`, the tuple of recipes a portfolio's surface
does not hold. fitch-mvp hit it on its first sync after `f1bb5d3`.

It is the third check today that is right in stereorepo and wrong in every
portfolio, after `_probe_adopt` and the wiki parity probe
(`portfolio-gate-before-landing`).

## Wanted

- `"release"` joins `SCAFFOLD_RECIPES` in `.meta/checks/files/justfile.py`.
- `justfile_recipe_shape` decides scaffold or portfolio by
  `TEMPLATE.is_dir()` inside its body, so no probe can reach the portfolio
  branch from stereorepo. Give the step a seam beside `path` and `contract`
  (for example `scaffold: bool | None = None`, falling back to
  `TEMPLATE.is_dir()`), and drive it from the probe.

## Out of scope

- Deriving `SCAFFOLD_RECIPES` from the render's `work:artifact/meta-*`
  conditions so the two cannot drift (`scaffold-recipes-from-the-render`).
- Running a portfolio's gate before landing (`portfolio-gate-before-landing`).

## How anyone will know it is done

A new case in `verb_surface_probes` (`.meta/checks/probes/surface.py`),
driven through the step's `path`, `contract` and scaffold seams with a
contract declaring `release` alongside one ordinary recipe and a surface
holding only the ordinary one:

- as a portfolio, the step comes to `Passed`;
- as the scaffold, it comes to `Found`, naming `'release'` as the declared
  recipe the surface does not hold.

stereorepo's own `justfile` still holds `release` and still passes the step
unchanged.

## The plan

1. `.meta/checks/files/justfile.py`
   - Append `"release"` to `SCAFFOLD_RECIPES`.
   - Add `scaffold: bool | None = None` to `justfile_recipe_shape` after
     `contract`. Resolve it to `TEMPLATE.is_dir()` when it is `None`, and
     drop the scaffold recipes when it resolves to `False`. A defaulted
     parameter is a probe seam that `@check` passes nothing for
     (`check` in `.meta/checks/collect.py`), so the gate keeps calling the step
     as it does now.
   - Add an `Args:` entry for each of the three seams in the docstring.
2. `.meta/checks/probes/surface.py`, in `verb_surface_probes`
   - Add a case that writes `CONFORMING` (which holds only `landed`).
   - Run the check against `{**contract, "release": (("args", FLAGS),)}`.
   - Run it once with `scaffold=False`, expecting `Passed`.
   - Run it once with `scaffold=True`, expecting `Found` with a problem
     containing `the contract declares 'release'`, the missing-recipe line,
     so that a departure elsewhere cannot satisfy it.
   - Pass `scaffold` explicitly both times. The probe also runs in
     portfolios, where `TEMPLATE` is absent.
   - Extend the docstring with one sentence describing the case.
3. Leave the existing probe calls as they are. They declare no scaffold
   recipe, so they behave the same whichever way `scaffold` resolves.

**Risk:** low. Only the step's own probe passes `scaffold`. The real
`justfile` still holds `release`, and in stereorepo `scaffold` resolves to
`True` as it did before.

## What was done

The work followed the plan. The new probe case sits at the end of
`verb_surface_probes`, after the missing-recipe case. Its failure messages
share a `without` prefix to stay under the file's line baseline in
`.meta/checks/lines.baseline.yaml`. The pair notes' citations of
`.meta/checks/collect.py` and `.meta/checks/files/justfile.py` lost their
line numbers, because `path and line claims` refused them once the code
moved.

The case was not run against the step without the fix, but its portfolio
half depends on it by construction: `scaffold=False` removes only the names in
`SCAFFOLD_RECIPES` from the contract, so without `"release"` there the
declared `release` stays, the step reports it missing, and the probe fails.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/release-recipe-is-scaffold-only.md` and set its difficulty to **easy**.
>
> - **What is wanted:** add `"release"` to `SCAFFOLD_RECIPES` in `.meta/checks/files/justfile.py`. That tuple lists the recipes only stereorepo renders, so a portfolio's check no longer expects them.
> - **One change the original issue missed:** the check decides "scaffold or portfolio?" with a hard-coded `TEMPLATE.is_dir()` call. Run from stereorepo, that always answers "scaffold", so no test can exercise the portfolio case. The issue now asks for a parameter that lets a test choose, falling back to `TEMPLATE.is_dir()` when not given.
> - **How anyone will know it is done:** a new case in the existing `verb_surface_probes` test (`.meta/checks/probes/surface.py`). It checks a `justfile` that is missing `release` against a contract that declares it:
>   - treated as a portfolio, the check passes;
>   - treated as stereorepo, it fails and names `'release'` as the missing recipe.
>
>   stereorepo's own `justfile` still contains `release` and still passes.
> - **Out of scope:**
>   - Generating `SCAFFOLD_RECIPES` from the render's own conditions so the two lists can't drift. The issue says to file this as a new backlog issue if `portfolio-gate-before-landing` doesn't already cover it.
>   - Running a portfolio's checks before landing, which is the `portfolio-gate-before-landing` issue.

> **secondary, backlog turn 2**
>
> I left my partner's grooming as it was and resolved one open point in it.
>
> **What I checked:** the issue's claims match the code.
> - `release` is in the list of recipes every `justfile` must have (`CONTRACT`), but not in the list a portfolio may leave out (`SCAFFOLD_RECIPES`).
> - The render writes the `release` recipe only when `work:artifact/meta-release` is asserted, which is only in stereorepo.
> - `justfile_recipe_shape` decides "stereorepo or portfolio?" by calling `TEMPLATE.is_dir()` inside its body (`.meta/checks/files/justfile.py`). Run from stereorepo, it always answers "stereorepo", so a test can't reach the portfolio case without the new parameter the issue asks for.
> - The test the issue names, `verb_surface_probes` in `.meta/checks/probes/surface.py`, already calls the check with `path` and `contract`, so adding the new parameter there is straightforward.
> - The difficulty, **easy**, fits.
>
> **What I changed:** the "Out of scope" section said to file a backlog issue for keeping the two recipe lists in sync, but only if `portfolio-gate-before-landing` didn't already cover it. It doesn't, so I filed it as `issues/backlog/scaffold-recipes-from-the-render.md`. I left its `difficulty` unset so `just groom` picks it up. The out-of-scope bullet now names that issue instead of the condition. Both changes are committed.

> **primary, backlog turn 3**
>
> I'm leaving the issue as it stands.
>
> My partner made two changes, and both hold up against the code:
>
> - **New backlog issue:** they filed the follow-up as `issues/backlog/scaffold-recipes-from-the-render.md`. It covers keeping the list of recipes only stereorepo has in step with what the render actually writes. Each condition it cites matches `.meta/lib/render/writers.py`: the `pair` recipes at line 73, `test-specialization` at 102, `release` at 110 and `adapt` at 118.
> - **"Out of scope" bullet:** it now names that new issue instead of saying "file one if needed".
>
> The groomed issue is still precise enough to plan, and **easy** still fits.

> **primary, todo turn 1**
>
> I've written the plan under `## The plan` in `issues/todo/release-recipe-is-scaffold-only.md`. It touches two files and nothing is implemented yet.
>
> 1. **`.meta/checks/files/justfile.py`:**
>    - Add `"release"` to `SCAFFOLD_RECIPES`, the list of recipes only stereorepo has.
>    - Give `justfile_recipe_shape` a new optional parameter, `scaffold`. When it is left out, the check decides as it does now, by looking for stereorepo's `template/` directory.
>    - The gate passes nothing for a parameter with a default (`check` in `.meta/checks/collect.py`), so the gate's own run doesn't change.
> 2. **`.meta/checks/probes/surface.py`:** add one test case. It checks a `justfile` without `release` against a contract that declares it:
>    - as a portfolio (`scaffold=False`), the check passes;
>    - as stereorepo (`scaffold=True`), it fails and names `'release'`.
>
>    Both runs set `scaffold` explicitly, because this test also runs inside portfolios, which have no `template/` directory.
> 3. **Existing test cases:** they stay as they are, since none of them involves a stereorepo-only recipe.
>
> The risk is low. Only the new test case sets `scaffold`, and stereorepo's real `justfile` still contains `release`. Planning turned up no reason the issue can't be done as written.

> **secondary, todo turn 2**
>
> My partner's plan holds up against the code. I made one small change to it and committed that.
>
> **What I checked:**
> - **The gate isn't affected.** The decorator that registers checks with the gate (`check` in `.meta/checks/collect.py`) passes nothing for a parameter that has a default. So the new `scaffold` parameter only matters when a test passes it; the gate keeps running the check as it does now.
> - **Nothing else depends on what changes.** Apart from the test file and the re-export in `.meta/checks/files/__init__.py`, nothing else uses `justfile_recipe_shape` or `SCAFFOLD_RECIPES`.
> - **The existing test cases still behave the same.** Their contract declares only `landed`, which is not a stereorepo-only recipe, so their results don't depend on how `scaffold` resolves. That includes runs inside a portfolio.
>
> **What I changed:** when the check runs as stereorepo, the new test case was only going to look for the word `'release'` in the failure. I tightened it to look for the full message `the contract declares 'release'`. That way the test passes only on the "missing recipe" failure, not on a different failure that happens to mention `release`.

> **primary, todo turn 3**
>
> I'm leaving the plan as it stands.
>
> My partner made one change: the new test case now looks for the full message `the contract declares 'release'` instead of just the word `'release'`. That matches the text the check prints for a missing recipe in `justfile_recipe_shape`. It also makes the test stricter, since a different failure that happens to mention `release` can no longer make it pass.

> **primary, in-progress turn 1**
>
> I've implemented the plan, the `meta` gate passes, and the work is committed as `bc5a496`. A portfolio's checks no longer expect a `release` recipe, while stereorepo's still do.
>
> - **`.meta/checks/files/justfile.py`:**
>   - `"release"` is now in `SCAFFOLD_RECIPES`, the list of recipes only stereorepo has.
>   - `justfile_recipe_shape` takes a new optional `scaffold` parameter. When it is left out, the check still decides by looking for stereorepo's `template/` directory, so the gate's own run is unchanged.
>   - The docstring now describes all three parameters.
> - **`.meta/checks/probes/surface.py`:** a new test case in `verb_surface_probes` checks a `justfile` without `release` against a contract that declares it. As a portfolio's it must pass. As stereorepo's it must fail with `the contract declares 'release'`.
>
> I didn't confirm that the new test case fails without the fix: the script that would have shown it needed sandbox approval, so I skipped it.
>
> Two other things changed to get the `meta` gate to pass:
>
> - **Long lines:** my first version pushed `surface.py` over its allowed number of lines longer than 100 characters, so I shortened the new failure messages.
> - **Stale line citations:** the gate's `path and line claims` check rejected the pair notes' references to lines in `.meta/checks/collect.py` and `.meta/checks/files/justfile.py`, because the code had moved. They now name the file and the symbol, without line numbers.
>
> The issue file records both under a new `## What was done` section. No other directories were touched, so `meta` was the only gate to run.

> **secondary, in-progress turn 2**
>
> My partner's code is correct and I left it unchanged. I fixed one thing in the issue file, and `just gate meta` now passes; it was failing when I started.
>
> **The gate failure:** the gate checks that line-number references in documents still point at the right code. My partner had already removed the old line numbers from earlier notes. But the loop added their own end-of-turn note afterwards, and that note quoted the stale line references into `.meta/checks/collect.py` and `.meta/checks/files/justfile.py` again. I removed the line numbers from that note, and the gate passes.
>
> **The code:**
> - `"release"` is now in `SCAFFOLD_RECIPES`, the list of recipes only stereorepo has.
> - `justfile_recipe_shape` takes the new optional `scaffold` parameter. When it's left out, the check still looks for stereorepo's `template/` directory, so the gate runs it as before.
> - The new test case runs the check both ways and looks for the exact "missing recipe" message.
>
> **Not run:** I couldn't confirm that the new test fails without the fix. The command that would have shown it was denied, just as it was for my partner. Instead I added a short explanation to `## What was done` in the issue file. With `scaffold=False`, the check drops only the recipes listed in `SCAFFOLD_RECIPES`. Without `"release"` in that list, the check would report `release` as missing and the test would fail.
>
> No other directories were touched, so `meta` was the only gate to run.

> **primary, in-progress turn 3**
>
> I left the code as it was and fixed the issue file again; `just gate meta` now passes, and the fix is committed as `97810bf`.
>
> - **The gate failure:** `just gate meta` was failing when I started this turn. My partner's note quoted the two old line numbers in `.meta/checks/collect.py` and `.meta/checks/files/justfile.py` again while describing how they had removed them. The gate checks that line numbers cited in documents still point at the right code, so it rejected them. I reworded that sentence to name only the files.
> - **One more old citation:** an earlier note pointed at a line range in `.meta/checks/files/justfile.py`. The gate doesn't check line ranges, but that code has moved too, so the note now names `justfile_recipe_shape` instead.
> - **My partner's added reasoning is correct:** as a portfolio, the check drops only the recipes listed in `SCAFFOLD_RECIPES`. If `release` weren't in that list, the check would report it missing and the new test case would fail. So the test does guard the fix, even though no one could run it without the fix.
>
> No other directories were touched, so `meta` was the only gate to run.

> **secondary, in-progress turn 4**
>
> The code is still correct and I left it unchanged. `just gate meta` was failing again when I started this turn; I fixed the cause and it now passes.
>
> **Why it failed again:** my partner's latest note explained how they had removed the two out-of-date line references, and in doing so quoted both references again. The gate checks that line numbers cited in documents still point at the right code, so it rejected them. I reworded that sentence to name only the two files.
>
> **Why it keeps happening:** the loop adds each seat's end-of-turn note to the Issue file after that seat has run the gate. So a bad reference in a note isn't caught until the other seat's turn, and that seat spends its turn fixing it. That's a pair-loop problem, not part of this issue. I filed it as `issues/backlog/pair-notes-escape-the-seats-gate.md`, which suggests the loop strip the line numbers from references when it writes a note into the file.
>
> To keep this note from causing the same failure, it cites no line numbers. Only the issue file and the new backlog file changed, so `meta` was the only gate to run. Both changes are committed.

> **primary, in-progress turn 5**
>
> I left the code as it was and made one small change to the issue file, committed as `010b619`. `just gate meta` passes.
>
> - **What I changed:** my last note still quoted the line range `.meta/checks/files/justfile.py:237-243`. The gate doesn't check line ranges, so this wasn't failing anything, but the code there has moved. The note now names only the file.
> - **My partner's change:** I agree with their new backlog issue, `issues/backlog/pair-notes-escape-the-seats-gate.md`. Each seat's end-of-turn note is added to the issue file only after that seat has run the gate, so a stale line reference in a note isn't caught until the other seat's turn. That is what happened on the last two turns here.
>
> Only the issue file changed, so `meta` was the only gate to run.

> **secondary, in-progress turn 6**
>
> I changed nothing this turn. The work is done and `just gate meta` passes.
>
> The code matches the plan: `release` is in `SCAFFOLD_RECIPES`, the check takes the new optional `scaffold` parameter, and the new test case covers both the portfolio and the stereorepo outcome. My partner's latest note quotes the old line range in `.meta/checks/files/justfile.py` while describing how they removed it, the same slip as the last two turns. The gate doesn't check line ranges, so nothing fails, and I left the note alone. The cause is already filed as `issues/backlog/pair-notes-escape-the-seats-gate.md`.
