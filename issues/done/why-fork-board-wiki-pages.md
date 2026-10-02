---
difficulty: medium
parent: write-why-fork-into-records
waits_on:
  - why-fork-delivery-records
---

# Write wiki pages for the pair loop's concepts

One part of `write-why-fork-into-records`. The ontology added eight concepts
for the pair loop, and every concept in the Ubiquitous Language carries a
wiki entry (A17, DR-190). `wiki/stereorepo/stage.md` already exists; the other
seven have no page, though `stage.md` and `flight.md` already link to
`[[issue]]`, `[[board]]`, `[[developer]]` and `[[desk-check]]`.

## Wanted

A page in `wiki/stereorepo/` for each of Issue, Board, Developer, Seat,
Supervisor, Quiet turn and Desk check, at the slugs `issue`, `board`,
`developer`, `seat`, `supervisor`, `quiet-turn` and `desk-check`, scaffolded
with the `/wikisplain` skill and shaped like `stage.md` and `flight.md`: front
matter, a bold lead, sections on what the concept does, and a "What X is not"
section where the vocabulary's scope note says what the word excludes.

- Each lead restates the concept's `definition` in
  `.meta/assertions/imported/vocabulary.yaml`, and the body draws on its scope
  note without contradicting it.
- Each page cites the Decision Records `why-fork-delivery-records` wrote that
  bear on it, at least: Issue DR-308, DR-310, DR-313; Board DR-308, DR-311;
  Developer DR-311; Seat DR-309, DR-307; Supervisor DR-306; Quiet turn DR-307;
  Desk check DR-306 and DR-298. `stage.md` gains a citation of DR-308.
- Issue says what an Issue is not (section 10 of `WHY_FORK.md`): no number,
  no status, labels or assignee, no comment thread.
- Board says it is one per repository, that the board on `main` is
  authoritative, and that a view of it holds no state.
- Seat and Supervisor list the open questions of `WHY_FORK.md` section 8 that
  concern them, as questions, without inventing answers: at least headless
  seats behaving like interactive sessions, cache reads per turn, take-over
  and hand-back for Seat; end-of-turn detection and whether quiet-turn
  agreement settles for Supervisor (Quiet turn may repeat the latter).
- No page links to or names `WHY_FORK.md`: `why-fork-remove-file` deletes it
  once this lands, so each page states what it takes from the file in its
  own words.

## Out of scope

- Changing any concept's definition, or pages for concepts other than these.
- The booktutor spike's answers (`docs/PAIR_LOOP_SPIKE.md` in
  `caindy/booktutor`). Grooming found the file unreachable: the local clone at
  `~/code/booktutor` and its bundle hold no `docs/` directory at any commit.
  Bringing them in is `pair-loop-spike-evidence`.

## Done when

- The seven new pages exist at those slugs, and `stage.md` cites DR-308.
- `/wikisplain --check-duplicate`, run before scaffolding, finds for each
  concept only its own vocabulary entry (every minted concept collides with
  itself), and each page's lead names its concept in bold followed by a
  defining verb.
- Every `[[...]]` link in the eight pages, and in `flight.md`, resolves to a
  page or an ontology entry.
- Reading each lead beside its vocabulary `definition` shows the same claim.
- `grep WHY_FORK wiki/` finds nothing.

## The plan

Prose only: no code, assertion or generated file changes. The seams the
pages must satisfy are the four wiki checks in `.meta/checks/files/wiki.py`:
`wikilinks` (every `[[...]]` resolves to a page or an ontology entry),
`wiki lead paragraphs` (first line `# <Title>`, first paragraph
`**<Title>** is ...`, and the bold subject equals the vocabulary
`pref_label`), `ubiquitous language wiki parity` (a page in
`wiki/stereorepo/` must be minted as `work:concept/<slug>`, which all seven
are) and `wiki synonyms` (no front-matter synonym on the concept's `avoid`
list).

1. For each concept, run `python3 .meta/wikisplain.py "<Pref label>"
   --check-duplicate` and confirm the only collision is its own
   `work:concept/<slug>` entry; then scaffold with
   `--slug <slug> --definition "<vocabulary definition>" --force`. `--force`
   is needed because the tool counts the concept's own vocabulary entry as a
   collision. Titles must be the exact `pref_label`: `Issue`, `Board`,
   `Developer`, `Seat`, `Supervisor`, `Quiet turn`, `Desk check` (sentence
   case, so the lead check's case-insensitive match holds and the title reads
   like `stage.md`'s).
2. Replace each scaffold's boilerplate `## Overview` and `## Invariants` with
   hand-written sections in the shape of `stage.md` and `flight.md`: what the
   concept does, how it meets its neighbours, and a `## What X is not`
   section drawn from the scope note and `avoid` list (Issue: no number,
   status, labels, assignee or comment thread, not a ticket or story; Board:
   one per repository, `main` authoritative, not a kanban or tracker, a view
   holds no state; Developer: one person, never a seat or an agent; Seat: not
   driver/navigator, not a reviewer; Supervisor: a program, not a model or an
   orchestrator; Quiet turn: not an approval or verdict; Desk check: not a
   review). Cite Decision Records as `stereorepo's DR-nnn`, the form every
   page in this context uses, with the minimum set the Wanted list gives. Do
   not list avoided words in `synonyms:`; Flight's `parent Issue` is the
   model for a synonym, and none of the seven needs one.
3. Seat and Supervisor each gain a `## Open questions` section stating the
   spike questions the Wanted list names, in the page's own words, with no
   answers and no mention of `WHY_FORK.md` or the spike document's path.
   Quiet turn may repeat whether agreement settles or rubber-stamps.
4. Link the pages to one another where the prose names a concept
   (`[[seat]]`, `[[supervisor]]`, `[[quiet-turn|quiet turn]]`,
   `[[desk-check|desk check]]`, `[[board]]`, `[[stage]]`, `[[flight]]`),
   and end each with a `**See also:**` line.
5. Add `(stereorepo's DR-308)` to `stage.md`'s lead or "What a stage is
   not" section.
6. Add the eight pages (seven new, and Stage, which was never listed) to
   "Pages in this Context" in `wiki/stereorepo/README.md`, one line each.

### Tests

- After step 2 rewrites each page, run `verify_page` from
  `.meta/lib/wikisplain/pages.py` on the finished file, not just on the
  scaffold: it runs the lead and wikilink checks the scaffold step ran. An
  empty result for all eight pages is the test. The "Verification warnings"
  printed at scaffold time check only the boilerplate that step 2 replaces.
- `grep -rn WHY_FORK wiki/` finds nothing; `grep -n "DR-308" wiki/stereorepo/stage.md` finds the citation.
- Each new page's lead read beside its `definition` in
  `.meta/assertions/imported/vocabulary.yaml` makes the same claim.
- No new test: no behaviour changes, and the four existing wiki checks
  already cover what a page must satisfy.

### Risks

- The lead check compares the bold subject to `pref_label` exactly, apart
  from case; `**Quiet turns** are` or `**A seat** is` fails.
- A "What X is not" section naturally names the avoided words. No check
  forbids them in prose, only in `synonyms:`, so naming them there is safe
  and intended.
- `wiki/stereorepo/` is inherited intact by portfolios (its README's
  Specialization Invariant), so the pages must describe the pair loop
  without naming scaffold-only paths. This plan first said `pair/` was
  allowed; it is not: the `scaffold-only paths` check refuses any page that
  names `pair/`, since a portfolio has none. `issues/` is fine.
- A vocabulary `definition` opens with a capital ("A repository's set ...").
  Passing it verbatim to `--definition` gives "**Board** is A repository's
  ...". Pass it with the article lower-cased, or fix the lead in step 2.

## Notes from implementation

- The seven pages were scaffolded with `--force`, then rewritten whole; none
  keeps the scaffold's `Overview` and `Invariants` boilerplate. Each lead is
  the vocabulary `definition` with its first article lower-cased, and
  `verify_page` returns nothing for all eight pages.
- Supervisor does not name `pair/loop.py`: the `scaffold-only paths` check in
  `just gate meta` refuses `pair/` on a wiki page, because portfolios inherit
  `wiki/stereorepo/` and have no `pair/`. It says what the vocabulary's
  scope note says instead: the scaffold holds the program, and `just pair`
  runs it.
- Seat and Supervisor carry `## Open questions` without answers, and Quiet
  turn repeats whether agreement settles. `pair-loop-spike-evidence` fills
  them in once the developer supplies the spike's findings. The pages call the
  spike "the first run of the loop in another repository" and name no file.
- `wiki/stereorepo/README.md` now lists all eight pages, Stage included,
  which it had not listed before.
- The pages' claims about the loop were checked against `pair/loop.py`.
  `just pair-accept` and `just pair-resume` take a slug only for a Flight
  (`Loop.accept`, `Loop.resume`), and Desk check now says so. A developer's
  edit between turns resets the seats' approvals (`Loop.absorb_developer`).
  Seat's "is not" list now covers `agent`, the last word on its `avoid` list.
