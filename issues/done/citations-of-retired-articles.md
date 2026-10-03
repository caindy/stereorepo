---
difficulty: easy
---

# Stop citing retired Articles as though they were in force

Article 15, Article 16, Article 18 and Article 19 are retired (`.meta/charter.md`
shows each as "Retired."), but live prose still cites two of them for a rule:

- Article 15, for avoiding the word "Article" to protect "the Charter's
  empirical clauses (stereorepo's Article 1, stereorepo's Article 15)":
  - `.meta/assertions/imported/vocabulary.yaml`, the Concept's `scope_note`
    (rendered into `.meta/vocabulary.md`);
  - `wiki/stereorepo/concept.md`;
  - `wiki/stereorepo/knowledge-management.md`.
- Article 19, for "a commit that does not name its Actor is unattributable":
  - `bootstraps/python/skills/py-quality-setup/SKILL.md`, twice: the
    "Never grant `Bash(git commit *)`" paragraph under "Three things this
    skill must not do", and the paragraph after the permissions block in
    step 6, "Configure Claude Code permissions", of "Setup Workflow". This is the source; `.meta/lib/apm_compile/bootstrap.py` reads
    `bootstraps/python/skills/` and `just render` writes the copy under
    `bootstraps/python/.apm/skills/`. Both passages also send commits through
    `.meta/say/commit` and its Actor Trailer, and send `gh`'s writing verbs
    through `.meta/say/post` and `.meta/say/move`, and that permissions block
    allows `Bash(.meta/say/commit *)`. `.meta/say/` and the
    Actor class are gone too, and `.claude/settings.json` denies no `gh`
    verb today, so each of those sentences describes a tree that no longer
    exists.
  - `bootstraps/python/PROVENANCE.md`, the `py-quality-setup` row.

Found while trimming DR-179 to DR-217 (`trim-decision-records-179-217`).

## Wanted

- Each citation of a retired Article either names a current Article or
  Decision that carries the rule, or goes, with the sentence restated so it
  does not lean on it. For the Article 15 passages, Article 1 does not carry
  the reason either: A1 is "Green, then commit". The reason "Article" is
  avoided is that it is already a term, `work:concept/article` in
  `.meta/assertions/imported/vocabulary.yaml`, one clause of the Charter;
  say that and cite no Article.
- The `py-quality-setup` skill no longer mentions `.meta/say/` (`commit`,
  `post` or `move`), the Actor Trailer or the Actor, and its permissions
  block no longer allows `Bash(.meta/say/commit *)`. Seats and the developer
  commit with `git commit` today, so unless the tree gives another reason to
  withhold it, the "Never grant `Bash(git commit *)`" paragraph and the
  paragraph after the step-6 permissions block go, and the block is
  upstream's again: `Bash(git commit *)` in place of
  `Bash(.meta/say/commit *)`. With that paragraph gone, the heading "Three
  things this skill must not do" counts what is left. The claim that `.claude/settings.json` denies `gh`'s writing verbs
  goes unless that file says so.
- The `py-quality-setup` row of `bootstraps/python/PROVENANCE.md` records
  what the skill now does about `Bash(git commit *)`, without A19.
- Re-render, so `.meta/vocabulary.md` and the skill copy follow their sources.

## Out of scope

- The probe case in `.meta/checks/probes/tools/comments.py` that quotes A19
  and Article 19: it is a test string for comment shapes and stays.
- The decision log, the Issues and the history logs.
- `.meta/say/` in `excluded_paths` of
  `template/.meta/assertions/structure.yaml`, which is
  `template-excludes-retired-say-path`.

## Done when

Outside `.meta/assertions/decisions/`, `.meta/decisions.md`, `issues/`, the
history logs and the probe's test string, a grep that includes hidden
directories (`rg --hidden`; a plain `rg` skips `.meta/`) for
`Article 1[5689]` and `\bA1[5689]\b` finds only the four "Retired." headings
in `.meta/charter.md`, and a grep for `.meta/say` or `Actor` finds nothing
under `bootstraps/`. `just render` run afterwards changes no file.

## The plan

Prose only; no code or test changes. Edit the sources, then render once.

1. **The "Article" sentence, three places.** Restate it on the term, citing
   no Article: "Article" names one clause of the Charter (the Article term,
   `work:concept/article`), so a wiki page is not called one.
   - `.meta/assertions/imported/vocabulary.yaml`, the `scope_note` of
     `work:concept/concept`: replace "to protect the Charter's empirical
     clauses (stereorepo's Article 1, stereorepo's Article 15)".
   - `wiki/stereorepo/concept.md`, the "Wiki article" bullet: drop the
     parenthesis; the rest of the bullet already says why.
   - `wiki/stereorepo/knowledge-management.md`, the paragraph after the
     Subdirectory bullet: drop the parenthesis likewise.
   The "**See also:**" lines of both pages also list Article 1, which is in
   force; they stay, since the issue covers retired Articles only.
2. **`bootstraps/python/skills/py-quality-setup/SKILL.md`** (the source,
   not the `.apm/` copy):
   - Under "Three things this skill must not do", delete the "Never grant
     `Bash(git commit *)`" paragraph and rename the heading "Two things this
     skill must not do".
   - In step 6, "Configure Claude Code permissions", replace
     `"Bash(.meta/say/commit *)"` with `"Bash(git commit *)"`, and delete the
     paragraph after the JSON block that begins "`Bash(git commit *)` is
     upstream's entry". The "**Merge logic**" paragraph stays.
   - In the "Verification Checklist", the "Both targets" item that said
     `.claude/settings.local.json` grants **not** `Bash(git commit *)` or any
     `gh` writing verb now says it grants the quality tools in the step-6
     list; otherwise the checklist would contradict step 6.
3. **`bootstraps/python/PROVENANCE.md`**, `py-quality-setup` row: drop the
   sentence "The permissions it writes no longer grant `Bash(git commit *)`,
   since A19…". The skill now writes upstream's entry, so the row has no
   divergence to record about it.
4. **`just render`**, then look at the diff: it should regenerate
   `.meta/vocabulary.md` (the Concept entry) and
   `bootstraps/python/.apm/skills/py-quality-setup/SKILL.md`, and nothing
   else that this issue did not touch.

**Checks.** Run the two greps from "Done when" with `rg --hidden`. Then
run `just render` a second time and confirm `git status` shows no change.

**Risk.** Low. The only behaviour that changes is the permissions a
portfolio's `py-quality-setup` run writes, and it now grants `git commit`
the way upstream does. If something checks that the `.apm/` copy matches
its source, step 4 keeps the two in step.

## Pair notes

> **primary, backlog turn 1**
>
> I checked `issues/underway/citations-of-retired-articles.md` against the tree. It was already close to plannable: the list of places that cite retired Articles matches what the repository holds, and `.meta/say/` really is gone. I left `difficulty: easy` as it was and committed three corrections:
>
> - **Wrong hint about Article 1.** The issue suggested Article 1 alone might justify avoiding the word "Article". It can't: A1 is "Green, then commit", which has nothing to do with that word. The issue now gives the real reason to state, with no Article cited: "Article" is already a term in `.meta/assertions/imported/vocabulary.yaml` (`work:concept/article`, one clause of the Charter).
> - **Line-number citations.** The issue pointed into `bootstraps/python/skills/py-quality-setup/SKILL.md` by line numbers, which the repository's rule against line-number citations (DR-355) forbids. They now name the section and step instead. The one it called the "step-5 paragraph" is actually in step 6, "Configure Claude Code permissions". The issue now also says that `Bash(git commit *)` takes the place of `Bash(.meta/say/commit *)` in the permissions block.
> - **A grep that missed files.** The "Done when" grep, run with plain `rg`, skips `.meta/` because hidden directories are left out by default. So it would never have found the citations in `vocabulary.yaml` or `vocabulary.md`. It now says `rg --hidden`. It also requires that no "Actor" remains under `bootstraps/`, and that running `just render` afterwards changes no file.

> **secondary, backlog turn 2**
>
> I checked my partner's grooming of the issue against the files, and it holds up. Every file it lists does cite Article 15 or Article 19, which are both retired. The `.meta/say/` and Actor passages in `bootstraps/python/skills/py-quality-setup/SKILL.md` and its rendered copy are where the issue says. `.claude/settings.json` really doesn't block `gh`'s writing commands or `git commit`. The `rg --hidden` check in "Done when" also gives the expected result today.
>
> I made one change and committed it. Once the "Never grant `Bash(git commit *)`" paragraph is removed, the skill's heading "Three things this skill must not do" will only have two items under it. The issue now says the heading should count what's left.
>
> I left `difficulty: easy` as it was.

> **primary, backlog turn 3**
>
> I'm keeping my partner's change and changing nothing else. Under the heading "Three things this skill must not do" in `bootstraps/python/skills/py-quality-setup/SKILL.md`, there are three bold "Never" paragraphs, and the third is the "Never grant `Bash(git commit *)`" paragraph that the issue removes. With it gone the heading would say three over two items, so the issue is right to say the heading should count what is left. The rest of the issue still matches the tree, and `difficulty: easy` stands.

> **primary, todo turn 1**
>
> I wrote the plan into the issue under `## The plan` and committed it. Nothing in the issue as written blocks it, so there is no `# Needs elaboration` section.
>
> The change is prose only, with no code or tests, in four steps:
>
> 1. **The sentence about the word "Article"** is restated in three places, citing no Article. It now says "Article" names one clause of the Charter, so a wiki page is not called one. The three places:
>    - the Concept's `scope_note` in `.meta/assertions/imported/vocabulary.yaml`;
>    - the "Wiki article" bullet in `wiki/stereorepo/concept.md`;
>    - the paragraph after the Subdirectory bullet in `wiki/stereorepo/knowledge-management.md`.
>
>    The "See also" lines on both wiki pages also list Article 1. Article 1 is still in force, so those lines stay.
> 2. **`bootstraps/python/skills/py-quality-setup/SKILL.md`** (the source, not the rendered copy):
>    - delete the "Never grant `Bash(git commit *)`" paragraph and retitle its heading "Two things this skill must not do";
>    - in step 6's permissions block, put back `Bash(git commit *)` in place of `Bash(.meta/say/commit *)`;
>    - delete the paragraph that follows that block.
> 3. **`bootstraps/python/PROVENANCE.md`:** drop the A19 sentence from the `py-quality-setup` row.
> 4. **Re-render** with `just render`. Only `.meta/vocabulary.md` and the rendered copy of the skill under `bootstraps/python/.apm/` should change.
>
> **Checks:** the two "Done when" greps, run with `rg --hidden`, and a second `just render` that leaves `git status` unchanged.
>
> **Risk:** low. The only behaviour that changes is that the skill again grants `git commit` the way the upstream version does.

> **secondary, todo turn 2**
>
> I'd change nothing; the plan holds up against the tree.
>
> - **The "Article" sentence:** the three passages are where the plan says. Each wiki page still explains the rule once its parenthesis goes, since both keep "reserved for" or "confusion with" "the empirical clauses of the Charter". The "See also" lines cite only Article 1 and Article 17, both still in force, so leaving them is right.
> - **Other copies:** no file outside `issues/` repeats any of the sentences the plan edits except the ones it lists. The only rendered copies are `.meta/vocabulary.md` and the skill's copy under `bootstraps/python/.apm/`. Step 4 expects exactly those two to change on re-render.
> - **The `py-quality-setup` row** in `bootstraps/python/PROVENANCE.md`: the A19 sentence is its only mention of `git commit`. Dropping it, as the plan says, leaves a row with nothing out of date in it.

> **primary, in-progress turn 1**
>
> I implemented the plan as written, and nothing in it needed changing.
>
> - The Concept's `scope_note` now reads: "Article" is strictly avoided because it already names one clause of the Charter. The two wiki pages just drop the parenthesis.
> - `py-quality-setup` now has two "Never" rules, under a heading retitled "Two things this skill must not do". Its step-6 permissions block allows `Bash(git commit *)`, and the paragraph after that block is gone.
> - The `py-quality-setup` row of `bootstraps/python/PROVENANCE.md` loses its A19 sentence.
> - `just render` wrote two files: `.meta/vocabulary.md` and the skill copy under `bootstraps/python/.apm/`. A second run wrote none.
> - Both "Done when" greps, run with `rg --hidden`, give the expected result. The first finds only the four "Retired." headings and the probe's test string. The second finds nothing under `bootstraps/`.

> **primary, in-progress turn 1**
>
> I made the change as planned and committed it. `just gate meta` passes (94 steps). No other Project gate applies, because nothing under `bootstraps/python/seed/`, `bootstraps/rust/seed/` or `pair/` changed.
>
> - **The "Article" sentence:** the Concept's `scope_note` in `.meta/assertions/imported/vocabulary.yaml` now says the word "Article" is avoided because it already names one clause of the Charter. In `wiki/stereorepo/concept.md` and `wiki/stereorepo/knowledge-management.md` I only removed the bracketed Article 1 and Article 15 citations, since the rest of each sentence already gives the reason.
> - **`py-quality-setup` skill:** I removed the paragraphs about A19, `.meta/say/` and the Actor. The heading is now "Two things this skill must not do", and the permissions block in step 6 allows `Bash(git commit *)` again.
> - **`bootstraps/python/PROVENANCE.md`:** the `py-quality-setup` row no longer has its A19 sentence.
> - **Re-render:** `just render` rewrote only `.meta/vocabulary.md` and the skill's rendered copy under `bootstraps/python/.apm/`; a second run wrote nothing.
> - **Checks:** both "Done when" greps, run with `rg --hidden`, give what the issue expects. The first finds only the charter's four "Retired." headings and the probe's test string, and the second finds nothing under `bootstraps/`.
>
> The plan needed no changes, and I found no work for a new backlog Issue. My note on what changed is in the issue's Pair notes.

> **partner, in-progress turn 1**
>
> The plan left one contradiction in the skill: the "Verification Checklist" still required that `.claude/settings.local.json` **not** grant `Bash(git commit *)` or any `gh` writing verb, while step 6 now grants `git commit`. That item now says the file grants the quality tools in the step-6 list, and I added this to step 2 of the plan. I also dropped the full stop the `py-quality-setup` row of `bootstraps/python/PROVENANCE.md` had gained, since no other row in that table ends with one, and re-wrapped the "Wiki article" bullet in `wiki/stereorepo/concept.md`. `just render` rewrote the skill copy under `bootstraps/python/.apm/`.

> **secondary, in-progress turn 2**
>
> My partner's change missed one thing: the `py-quality-setup` skill now contradicted itself. Step 6 grants `Bash(git commit *)` again, but the "Verification Checklist" still required that `.claude/settings.local.json` **not** grant it, or any `gh` command that writes to GitHub.
>
> I fixed that and two small things, then committed:
>
> - **The contradiction:** that checklist item in `bootstraps/python/skills/py-quality-setup/SKILL.md` now says the settings file grants the quality tools listed in step 6. I added this to step 2 of the plan in the issue.
> - **`bootstraps/python/PROVENANCE.md`:** the `py-quality-setup` row had gained a full stop that no other row in that table has, so I removed it.
> - **`wiki/stereorepo/concept.md`:** I re-wrapped the "Wiki article" bullet, which was left with a short line where the citation was removed.
>
> `just render` updated the skill's rendered copy under `bootstraps/python/.apm/`. A second run wrote nothing. `just gate meta` passes (94 steps). No other Project gate applies, because the change touches nothing under `bootstraps/python/seed/`, `bootstraps/rust/seed/` or `pair/`.
>
> My note on these fixes is in the issue's Pair notes. I found no new work for the backlog.

> **primary, in-progress turn 3**
>
> I'm changing nothing; my partner's fixes are right and I'm keeping them.
>
> - **The contradiction they caught was real.** Step 6 of the `py-quality-setup` skill now grants `Bash(git commit *)`, but the Verification Checklist still said the settings file must not grant it. The checklist now agrees with step 6, and the plan records the fix.
> - **The other two fixes are right too:** dropping the stray full stop in `bootstraps/python/PROVENANCE.md` and re-wrapping the "Wiki article" bullet in `wiki/stereorepo/concept.md`.
> - **Nothing old is left in the skill.** A search of its source for `gh`, `git commit`, "Actor" and `say/` finds only the step-6 permission entry and ordinary words like "through".
> - **Checks:** `just gate meta` passes (94 steps). No other Project gate applies, because nothing under `bootstraps/python/seed/`, `bootstraps/rust/seed/` or `pair/` changed.
