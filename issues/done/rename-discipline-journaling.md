---
difficulty: developer
---

# Rename the Journaling Discipline to a word that is guessed right

`why-fork-inherited-terms` re-tested *Journaling* against the rule for
choosing terms (DR-313) and found it fails: the common word means keeping a
journal or log, but the Discipline means routing narrative to the artifact
that owns it, and the residue to the Issue file, never to a commit message.
A reader who guesses from the word alone would write a log. The rename was
deferred because the name is more than a label.

## Wanted

The Discipline and its concept are renamed to *Routing*, the word
`AGENTS.md` already uses ("Route prose before writing") and that the
Discipline's own step ids use (`route-as-you-write`,
`route-findings-in-same-change`). If DR-313's test shows *Routing* collides
with an existing term, choose another and say why here. Then rename
throughout:

- `work:discipline/journaling` and its step ids in
  `.meta/assertions/imported/disciplines.yaml`;
- `work:concept/journaling` in `.meta/assertions/imported/vocabulary.yaml`,
  with *Journaling* on its `avoid` list;
- `enforces: work:discipline/journaling` in
  `.meta/assertions/imported/charter.yaml`;
- the compiled `.meta/.apm/instructions/journaling.instructions.md` and its
  line in `.gitattributes`;
- prose in `.meta/assertions/structure.yaml` and the generated
  `bootstraps/python/README.md` and `bootstraps/rust/README.md`;
- the search benchmark's expected ids in `.meta/lib/search/benchmark.py` and
  the probe in `.meta/checks/probes/tools/search.py`, which expects the
  Discipline or Concept in the top 5 for "leftover work". If the new name
  moves it out of the top 5, say so here rather than weakening the probe.

Record the rename in a new Decision Record and re-render, which regenerates
`.meta/charter.md`, `.meta/disciplines.md` and `.meta/vocabulary.md`; those
three are not edited by hand.

## Out of scope

- Existing Decision Records, which keep the old word, and so the generated
  `.meta/decisions.md` that indexes them.
- Issue files in `issues/`.

## Done when

- The developer has read the new name and its Decision Record and accepts
  them. A Discipline's name is the developer's word, and *Routing* sits
  close to the routing that the Knowledge Management Discipline already
  describes ("the pre-writing routing decision tree"), so the choice is
  checked by hand before it lands.
- `git grep -il journaling -- ':!issues/' ':!.meta/assertions/decisions/'
  ':!.meta/decisions.md'` lists only `.meta/assertions/imported/vocabulary.yaml`,
  where the word is on the `avoid` list, and the generated
  `.meta/vocabulary.md`, which renders that list in its Avoid column.
- The renamed Discipline renders into `.meta/disciplines.md` under its new
  name, and `.meta/.apm/instructions/` holds its instructions file under
  the new name and no `journaling.instructions.md`.
- The search probe still finds the Discipline or Concept in the top 5 for
  "leftover work".

## The plan

*Routing* passes DR-313's collision test: no `pref_label`, `alt_labels` or
`avoid` entry in `.meta/assertions/imported/vocabulary.yaml` uses it, and no
other Discipline or Concept id contains it. Its only other uses are as a
plain verb in the Knowledge Management Discipline and in the Journaling
Concept's own definition, which stop being a clash once the Concept is the
word.

1. **Discipline.** In `.meta/assertions/imported/disciplines.yaml` (from
   line 453): id `work:discipline/journaling` → `work:discipline/routing`,
   `name: Routing`, the six step ids `work:discipline-step/journaling/…` →
   `work:discipline-step/routing/…`, and the sentence "Journaling is that
   routing, and then the residue" is reworded so it doesn't say "Routing is
   that routing" (for example, "Routing is that, and then the residue").
2. **Concept.** In `.meta/assertions/imported/vocabulary.yaml` (line 421):
   id → `work:concept/routing`, `pref_label: Routing`, and
   `avoid: [Journaling]` added, the way other entries carry it. Keep the
   `leftover work` alt label, because the search probe depends on it.
3. **Charter.** In `.meta/assertions/imported/charter.yaml` (line 207):
   `enforces: work:discipline/routing`.
4. **Prose.** In `.meta/assertions/structure.yaml` (lines 145, 195 and 244):
   "Journaling" → "Routing". These are the sources of the two Bootstrap
   READMEs, which are regenerated rather than edited.
5. **Search.** In `.meta/lib/search/benchmark.py` (lines 34, 62 and 78),
   replace the expected ids. In `.meta/checks/probes/tools/search.py`
   (lines 32 and 53–54), replace the id set and the docstring and
   message wording.
6. **Decision Record.** Add `.meta/assertions/decisions/DR-352.yaml`
   (DR-351 is the highest). It supersedes nothing, cites DR-313 and
   `why-fork-inherited-terms` as context, rejects keeping *Journaling* and
   names one other candidate, and enacts the renamed Discipline and Concept
   artifacts. Copy the shape of DR-351.
7. **Re-render.** `just render` regenerates `.meta/disciplines.md`,
   `.meta/charter.md`, `.meta/vocabulary.md`, `.meta/decisions.md`, the
   Bootstrap READMEs, the APM primitives (writing `routing.instructions.md`,
   whose filename comes from the Discipline's id slug in
   `.meta/lib/apm_compile/instructions.py`) and `.gitattributes`.
8. **Remove the stale file.** The compile writes primitives but never
   deletes them, so `git rm .meta/.apm/instructions/journaling.instructions.md`.
   No second render is needed: `.gitattributes` is built from what the
   targets in `.meta/lib/render/targets.py` produce, not from what is on
   disk, so step 7 already drops the old line. If the file stays, the
   render's check lists it as `unrendered:` and the gate fails.

**Tests.** Run the `git grep` from *Done when* and check its output.
Run `just apm --check`, which should report nothing stale. No recipe wraps
search. Run it the way the search skill documents it
(`.meta/.apm/skills/search/SKILL.md`):
`uvx --python 3.13 --with linkml --with pyyaml python .meta/search.py "leftover work"`
should list `work:discipline/routing` or `work:concept/routing` in the top
5, and the same command with `--benchmark` should still score
hit@5 ≥ 15/18. Check `.meta/disciplines.md` for a "Routing" heading.

**Risks.**
- Any other reference to the step ids would break silently. A search found
  none outside the Discipline itself and the existing DRs, which are out
  of scope and keep the old id as history.
- The search ranking can move, because the Discipline's name and id now
  share a term with Knowledge Management's "routing" prose. If the probe
  falls out of the top 5, record it here and don't weaken the probe.
- `imported/` is marked "do not edit in a portfolio". This repository is
  the scaffold that owns those files, so editing them here is correct.

## Pair notes

> **primary, backlog turn 1**
>
> The Issue was already groomed well enough to plan, so I changed only one thing.
>
> I checked it against the repository first. Searching for "journaling" outside the excluded paths (the Issue files, the existing Decision Records and `.meta/decisions.md`) finds the 10 source files the Issue lists. It also finds three generated files the Issue didn't mention: `.meta/charter.md`, `.meta/disciplines.md` and `.meta/vocabulary.md`.
>
> **My one change:** I added a sentence to `issues/underway/rename-discipline-journaling.md` saying that re-rendering regenerates those three files, so nobody edits them by hand.
>
> **Left as it was:**
> - **What's wanted:** rename the Discipline to *Routing*, with the list of every place to rename it.
> - **Out of scope:** existing Decision Records and Issue files keep the old word.
> - **Done when:** a search finds "journaling" only on the vocabulary's `avoid` list and the page generated from it. The renamed Discipline appears under its new name in the disciplines page, with its instructions file renamed. The search probe still finds it in the top 5 results for "leftover work".
> - **Difficulty:** stays at `developer`, because the developer should read the new name and its Decision Record and accept them before it lands.

> **secondary, backlog turn 2**
>
> I'm leaving the Issue as it is. I checked it against the repository and found nothing to fix.
>
> - **Rename list:** searching for "journaling" outside the Issue files and the existing Decision Records finds 13 files. Ten are the source files the Issue lists. The other three are the generated `.meta/charter.md`, `.meta/disciplines.md` and `.meta/vocabulary.md`, which your note already says get regenerated rather than edited by hand.
> - **Search tool:** the benchmark (`.meta/lib/search/benchmark.py`) uses the Journaling ids in three places, and the probe (`.meta/checks/probes/tools/search.py`) checks them in one. Both files are on the Issue's list.
> - **Wiki:** there's no `wiki/` page for Journaling, so none needs renaming.
> - **"Routing":** the word is already used in the Knowledge Management Discipline's text. The Issue already flags this overlap and has the developer accept the name by hand.
> - **Difficulty:** `developer` is right, because the developer should read and accept the new name before it lands.

> **primary, todo turn 1**
>
> I've written the plan into `issues/todo/rename-discipline-journaling.md` under `## The plan`. Nothing is implemented yet, and the Issue doesn't need a `# Needs elaboration` section.
>
> **Checking the name:** *Routing* doesn't collide with any existing term in the vocabulary, so it passes the rule for choosing terms (DR-313). The word does already appear as a plain verb in the Knowledge Management Discipline's text, but that's the overlap the developer is already set to check by hand.
>
> **Order of the steps:**
> 1. Rename the Discipline, its id and its six step ids in `disciplines.yaml`. One sentence has to be reworded so it doesn't come out as "Routing is that routing".
> 2. Rename the Concept in `vocabulary.yaml` and put *Journaling* on its avoid list.
> 3. Update the one line in `charter.yaml` that points to the Discipline.
> 4. Change the three prose mentions in `structure.yaml`.
> 5. Update the expected results in the search benchmark and the search check.
> 6. Add a new Decision Record, `DR-352` (DR-351 is the highest so far).
> 7. Run `just render`. It regenerates the pages and writes the new instructions file, `routing.instructions.md`.
> 8. Delete the old `journaling.instructions.md` by hand, because the compile writes these files but never removes old ones. Then render again.
>
> **Tests:**
> - Run the search from *Done when*: "journaling" should appear only in the vocabulary's avoid list and the page generated from it.
> - `just apm --check` should report nothing stale.
> - The search for "leftover work" should still return the renamed Discipline or Concept in the top 5.
> - `.meta/disciplines.md` should list the Discipline as "Routing".
>
> **Risks:**
> - **Search ranking:** the Discipline now shares the word "routing" with Knowledge Management, so "leftover work" could drop out of the top 5. If it does, the Issue gets a note saying so and the check is not weakened.
> - **Step ids:** no other file uses them apart from the existing Decision Records, which keep the old word by design.
> - **Do-not-edit warning:** `imported/` says not to edit it in a portfolio. This repository is the scaffold those files come from, so editing them here is correct.

> **secondary, todo turn 2**
>
> I made two corrections to the plan in `issues/todo/rename-discipline-journaling.md`. The rest checked out against the code, so I left it as written: DR-351 is the highest record, `just render` and `just apm --check` exist, and the instructions file is named after the Discipline's id.
>
> - **Tests:** the plan said to run the search probe and benchmark "through their recipe", but no recipe runs search. I replaced that with the commands the search skill documents (`.meta/.apm/skills/search/SKILL.md`). Searching for "leftover work" should list `work:discipline/routing` or `work:concept/routing` in the top 5. The `--benchmark` run should still score at least 15 of 18 queries with the right answer in the top 5.
> - **Step 8:** the plan rendered a second time in case `.gitattributes` lists files that exist on disk. It doesn't: it's built from the files the render itself produces, so one render already drops the old line. I replaced the second render with a note that if the old `journaling.instructions.md` is left in place, the render's check lists it as `unrendered:` and the gate fails.
>
> The Issue doesn't need a `# Needs elaboration` section.

> **primary, todo turn 3**
>
> I checked my partner's two corrections against the code and both are right, so I've left the plan as it stands.
>
> - **Search commands:** no recipe runs search. The commands in the plan are the ones the search skill documents in `.meta/.apm/skills/search/SKILL.md`. The pass mark of 15 out of 18 queries matches the floor set by `min_hits` in `run_benchmark` in `.meta/lib/search/benchmark.py`.
> - **Step 8:** the render builds `.gitattributes` from the files it produces, not from what is on disk, so one render is enough. If the old `journaling.instructions.md` is left in place, `unrendered` in `.meta/lib/render/targets.py` lists it as unrendered.

## What was done

The plan held as written. Two pieces of wording were changed beyond the
ids, because a literal rename read as a tautology:

- In the Discipline's description, "Journaling is that routing, and then
  the residue" became "Routing is that, and then the residue".
- In the Concept's definition, "Routing narrative to the artifact that owns
  it" became "Sending narrative…". In `structure.yaml` (and so the Python
  Bootstrap README), "its journal is what Journaling routes" became "its
  journal is what Routing sends to the Issue file".

DR-352 records the rename. It names *Residue* as the rejected alternative,
because that word covers only the second half of the practice.

Its `enacted_in` names the files the rename edited: the three
`imported/` assertion files (charter, disciplines, vocabulary), the search
benchmark and the search probe. It does not name the root
`.meta/assertions/disciplines.yaml` and `vocabulary.yaml`, which the rename
does not touch. The Concept's scope note, which opened "The routing
practice", now opens "A practice, not a place", so it does not read
"Routing. The routing practice".

Measured after the change: "leftover work" ranks `work:concept/routing`
first (score 9.27), and DR-352 is fifth. The benchmark scores hit@5 17/18,
hit@10 18/18 and MRR 0.54. The Discipline itself is not in the top 5, but
the probe accepts the Discipline or the Concept, as it did before.
`just apm --check` reports the primitives up to date, and the *Done when*
`git grep` lists only `.meta/assertions/imported/vocabulary.yaml` and
`.meta/vocabulary.md`.

## Pair notes

> **primary, in-progress turn 1**
>
> The Journaling Discipline is now Routing, and `just gate meta` passes. It's committed as `bd85e091`.
>
> **What changed:**
> - The Discipline, its six step ids and the Concept are renamed in the assertion files. The Concept has *Journaling* on its avoid list, and the Charter now points to the new id.
> - Two sentences were reworded instead of just swapping the word, because a straight swap would have read "Routing is that routing". The Concept's definition now opens "Sending narrative…", and a sentence about the Python seed now says its journal is "what Routing sends to the Issue file".
> - The new Decision Record, `DR-352`, records the rename. Its context cites the rule for choosing terms (DR-313). It also records *Residue* as the name considered and rejected, because it covers only the second half of the practice.
> - I updated the expected results in the search benchmark and the search check.
> - I deleted the old `journaling.instructions.md` and re-rendered. That produced `routing.instructions.md` and refreshed the generated pages, the two Bootstrap READMEs and `.gitattributes`.
>
> **Checks:**
> - Searching for "journaling" outside the excluded paths now finds only the vocabulary file and its generated page.
> - `just apm --check` reports nothing stale, and `.meta/disciplines.md` has a "Routing" heading.
> - A search for "leftover work" puts the Routing Concept first. The Discipline itself isn't in the top 5, but the check accepts either one, as it did before.
> - The search benchmark scores 17 of 18 queries with the right answer in the top 5; the pass mark is 15.
>
> The first gate run failed because two line-number citations in the Issue file sat next to file names that weren't on those lines. I replaced them with function names, and the second run passed. The README changes are outside the seed directories, so no other targeted gate applied.
>
> The notes for the next reader are in the Issue's "What was done" section. Before this lands, the developer still needs to read the name *Routing* and DR-352 and accept them.

> **secondary, in-progress turn 2**
>
> My partner's rename was correct, but I fixed two things in it.
>
> - **The new Decision Record pointed at the wrong files.** DR-352 listed the files it changed as `.meta/assertions/disciplines.yaml` and `vocabulary.yaml`, but the rename didn't touch those. The files it actually edited are under `.meta/assertions/imported/`. As a result, the generated index `.meta/decisions.md` linked DR-352 to the wrong two files. DR-352 now names the files the rename edited: the three under `imported/` (charter, disciplines, vocabulary), the search benchmark and the search check. I re-rendered, so the index now links it to the right files.
> - **The Concept's note repeated itself.** The generated vocabulary page read "**Routing.** The routing practice, not a place." It now opens "A practice, not a place."
>
> I recorded both fixes in the Issue's "What was done" section.
>
> **Checks:**
> - Searching for "journaling" outside the excluded paths still finds only the vocabulary file and its generated page.
> - A search for "leftover work" still puts the Routing Concept first.
> - `just gate meta` passes.
>
> No other targeted gate applied, because the change doesn't touch either seed or `pair/`. It's committed as `d16d9d49`.
>
> Before this lands, the developer still needs to read the name *Routing* and DR-352 and accept them.

> **primary, in-progress turn 3**
>
> I'm leaving the work as it stands, because both of my partner's fixes are right.
>
> - **Files named in DR-352:** I had listed `.meta/assertions/disciplines.yaml` and `vocabulary.yaml`, which the rename never touched. That made the generated index link DR-352 to the wrong two files. DR-352 now names the files the rename actually edited: the three under `.meta/assertions/imported/` (charter, disciplines and vocabulary), the search benchmark and the search check.
> - **Concept note:** "A practice, not a place" avoids the generated vocabulary page reading "**Routing.** The routing practice".
>
> My partner reports that `just gate meta` passes after these changes, and I didn't run it again since I changed nothing. Before this lands, the developer still needs to read the name *Routing* and DR-352 and accept them.
