---
difficulty: medium
parent: flights
waits_on:
  - underway-not-in-flight
  - flight-desk-check
---

# Name the Flight in the vocabulary and the docs

One part of `flights`. The Flight's behaviour has already landed; this Issue
names the Flight where the vocabulary and the board's READMEs still say
"parent issue" or describe the desk check as `developer`-only.

## Wanted

- **Flight** becomes a concept in `.meta/assertions/imported/vocabulary.yaml`,
  in `work:scheme/stereorepo`. Its definition says that a Flight is an Issue with
  children, holding one unit of value and how the developer will know that the
  value has been delivered, and that its parts are *in flight*. Its scope note
  says what a Flight is not: not a time-box (a Sprint) and not a tracker's
  Milestone. Add `Sprint` and `Milestone` to `avoid`.
- Replace "parent issue" with Flight in the Issue concept's scope note
  (`vocabulary.yaml`) and in the `Issue` class description
  (`.meta/work/purpose.yaml`).
- Update the Desk check concept. At present it covers only a `developer` Issue
  checked before it lands. It must also say that a Flight's desk check comes
  after the Flight's parts have landed on `main`, and that the Flight's desk
  check does not hold the loop. Its scope note says "Accepting lands the
  Issue"; for a Flight, whose parts have already landed, accepting moves it to
  `done/`, so reword it to cover both.
- In the Developer concept's scope note, which says the `developer` difficulty
  names "the Issues that wait for this person's desk check", add that a Flight
  waits for it too.
- Scaffold a wiki page, `wiki/stereorepo/flight.md`, with `/wikisplain`, and
  check it with the same skill (A17, DR-190).
- In `issues/README.md` and `template/issues/README.md`, change the
  `desk-check/` row, which says only "a `developer` Issue", so that it also
  admits a Flight. Add a short paragraph on the Flight's path: it waits in
  `backlog/` while its children land, goes through the Flight check, then
  moves to `desk-check/` and `done/`. The paragraph links to
  `pair/README.md` and does not repeat it. `pair/README.md` already describes
  this path, so change it only where its wording disagrees with the new
  concept.
- Write a Decision Record that states the choice of one desk check per Flight,
  after its parts have landed, over one desk check per part.
- Re-render, so that `.meta/vocabulary.md` and `.meta/decisions.md` are
  regenerated.

## Out of scope

Any change to how the loop treats a Flight: the other parts of `flights` cover
that. The same applies to the `template/` copies beyond `issues/README.md`.

## Done when

- `grep -rni "parent issue" .meta/assertions .meta/work issues/README.md
  template/issues/README.md` finds nothing.
- The Flight concept, `wiki/stereorepo/flight.md` and the new Decision Record
  exist.
- Both board READMEs describe the Flight's path.
- The Desk check and Developer concepts both mention the Flight.
- `just gate` passes.

## The plan

Everything here is prose and assertions: no Python changes. Steps in order:

1. **Vocabulary** (`.meta/assertions/imported/vocabulary.yaml`).
   - Add `work:concept/flight` beside `work:concept/issue` (~line 238), in
     `work:scheme/stereorepo`, with `broader` matching the Issue concept.
     The slug must be `flight`, because the wiki parity check
     (`ubiquitous_language_wiki_parity` in `.meta/checks/files/wiki.py`) pairs `wiki/stereorepo/<slug>.md` with
     `work:concept/<slug>`. Set `avoid: [Sprint, Milestone, epic]`, and
     `confusable_with: [work:concept/issue]`.
   - In the Issue scope note (~line 251), replace "An Issue with children is a
     parent issue" with "An Issue with children is a Flight". Keep `epic` on
     the Issue concept's avoid list.
   - Desk check (~line 330): widen the definition to cover a Flight, and change
     the scope note to say that accepting lands a `developer` Issue, or moves a
     Flight, whose parts are already on `main`, to `done/` without holding the
     loop.
   - Developer scope note (~line 232): add the Flight to what waits for the
     desk check.
2. **`Issue` class** (in `.meta/work/purpose.yaml`): "a parent issue" becomes
   "a Flight".
3. **Wiki page.** Scaffold `wiki/stereorepo/flight.md` with `/wikisplain`. It
   needs a bold lead definition, and it explains why a Flight is not a Sprint
   or a Milestone. Its path through the board links to `pair/README.md`. It
   must not list an avoided word under `synonyms` (the `wiki synonyms` check).
   Add it to the page list in `wiki/stereorepo/README.md`, and add a
   `work:artifact/wiki-stereorepo-flight` entry in
   `.meta/assertions/structure.yaml` next to the other wiki pages (~line 682),
   so that the Decision Record can cite it.
4. **Board READMEs.** Make the same edit to `issues/README.md` and
   `template/issues/README.md`: change the `desk-check/` row to "a `developer`
   Issue whose result waits for the developer's check, or a Flight whose parts
   have landed", and add one paragraph on the Flight's path after the
   "While an Issue is underway" paragraph. The template copy uses no repository
   links (its table has none), so it names the pair loop instead of linking
   `pair/README.md`. Reread `pair/README.md` lines 30–95 against the new
   concept, and change only wording that disagrees with it.
5. **Decision Record** `.meta/assertions/decisions/DR-298.yaml`. DR-297 is the
   highest number the record holds, and its shape is the one to copy. The
   choice is one desk check per Flight, after its parts land, over one desk
   check per part. `enacted_in` lists `meta-assertions-imported-vocabulary`,
   `meta-work-purpose`, `pair-readme` and `wiki-stereorepo-flight`.
6. **Re-render and check.** Run `just render`, which regenerates
   `.meta/vocabulary.md` and `.meta/decisions.md`. Then run `just gate meta`
   while working, and `just gate` at the end.

**Tests.** No new tests are needed. The existing checks cover the change:
- The wiki parity check (`ubiquitous_language_wiki_parity`) fails if
  `wiki/stereorepo/flight.md` exists without `work:concept/flight`. It reads
  from page to concept only, so a concept with no page passes it, and the grep
  and file checks in "Done when" have to catch that case.
- The `wiki synonyms` check covers the page's frontmatter.
- The decision numbering and citation checks cover DR-298.
- The Issue front-matter check still passes, because `parent:` stays the key.
- The grep in "Done when" confirms that "parent issue" is gone.

**Risks.**
- `avoid` is read in three places, and none of them looks at existing prose:
  - the `wiki synonyms` check (`.meta/checks/files/wiki.py`, `_avoided`);
  - the refusal of `--synonyms` in `/wikisplain`
    (`avoided_synonyms` in `.meta/lib/wikisplain/duplicates.py`);
  - the rendered table in `.meta/vocabulary.md`
    (`.meta/lib/render/pages.py`).

  Adding `Sprint` and `Milestone` therefore only forbids those words in the
  new page's `synonyms`. Step 1 comes before step 3 for that reason: the
  scaffold reads the vocabulary.
- The `wikisplain` duplicate check may flag the new page as close to the Issue
  concept. If it does, sharpen the lead rather than suppress the check.

## Implementation notes

- **Plan corrections.**
  - `/wikisplain` refuses to scaffold when the concept is already minted, and
    step 1 mints it first. Its duplicate check matches the concept the page
    exists to explain, so the scaffold was run with `--force`.
  - `wiki/stereorepo/` ships to portfolios, which have no `pair/`. The
    `scaffold-only paths` check refuses a link to `pair/README.md` there. The
    page names the recipes (`just pair-accept`, `just pair-resume`) instead.
  - `path and line claims` refuses `file:line` citations whose line does not
    read as the thing cited. The plan now cites the checks by function name.
- **`pair/README.md` is unchanged.** Its wording, "An Issue that other Issues
  name in `parent:` is a Flight", already agrees with the concept.
- **Beyond the plan.**
  - The front-matter example in both board READMEs now reads
    `parent: flight-slug  # the Flight this Issue is a part of`.
  - The wiki page keeps "parent Issue" as a search synonym, so a search for
    the old phrase finds the Flight. The "Done when" grep does not cover
    `wiki/`.
- **Verification.** `just render` was re-run; `just gate` passes; the "Done
  when" grep finds nothing.
