---
difficulty: easy
parent: write-why-fork-into-records
waits_on:
  - why-fork-delivery-records
  - why-fork-board-wiki-pages
  - why-fork-harness-survey
  - why-fork-inherited-terms
---

# Delete WHY_FORK.md once its content has a home

The last part of `write-why-fork-into-records`. All four parts it waits on
are in `issues/done/`, so every claim in `WHY_FORK.md` should now be in a
Decision Record or a wiki page that the citation check reads.

## Wanted

- Audit the file section by section, and add a `## Audit` section to this
  Issue file naming, for each numbered section, the Decision Records or
  wiki pages that now carry it. The expected homes:
  - Sections 1 to 5 and 10: the records of `why-fork-delivery-records` and
    the pages of `why-fork-board-wiki-pages`.
  - Sections 6 and 7: the pages of `why-fork-harness-survey`
    (`wiki/stereorepo/meta-harness.md`, `wiki/stereorepo/cockpit.md`).
  - Section 8: the "Open questions" lists on `wiki/stereorepo/seat.md` and
    `wiki/stereorepo/supervisor.md`, which already carry all six questions.
  - Section 9: a plan the bootstrap carried out; it needs no home, and the
    audit says so. Its step 4 is `issues/backlog/release-apm-package.md`.
- A claim found with no home is added to the record or page where it
  belongs, and the audit names where.
- Delete `WHY_FORK.md`.
- In `.meta/checks/citations/loaders.py`, remove the `WHY_FORK.md` skip in
  `durable()` and the sentence of its docstring that explains the skip.
- In `issues/backlog/pair-loop-spike-evidence.md`, reword the parenthesis
  that names section 8 of `WHY_FORK.md` so it points at the open-question
  lists on the Seat and Supervisor pages instead.

## Out of scope

- Rewriting what the other parts wrote, beyond adding a missing claim.
- Answering the section 8 questions; that is
  `pair-loop-spike-evidence`.
- `apm_modules/`, which is ignored by git and regenerated.

## Done when

- `WHY_FORK.md` no longer exists.
- `git grep -l WHY_FORK -- ':!issues/done/'` lists only this Issue file,
  which moves to `issues/done/` when it lands.
- `durable()` in `loaders.py` names no file by path to skip; it still
  skips symlinks, non-files and `.git`, as before.
- This file has an `## Audit` section with an entry for each of sections 1
  to 10.

## The plan

Files touched: `WHY_FORK.md` (deleted), `.meta/checks/citations/loaders.py`,
`issues/backlog/pair-loop-spike-evidence.md`, this Issue file, and any record
or page the audit finds short of a claim.

1. **Audit.** Read `WHY_FORK.md` one section at a time against its expected
   homes, and write `## Audit` here with one entry per section 1 to 10. The
   starting map, from the `## Records` table of
   `issues/done/why-fork-delivery-records.md` and the plan of
   `issues/done/why-fork-harness-survey.md`:
   - 1 and 2 (why fork, why PR First goes): the contexts of DR-306 and
     DR-307; the taxonomy of work in DR-312 and DR-313.
   - 3 (what survives): DR-312.
   - 4 (the new delivery paradigm): DR-306 to DR-311, and the wiki pages
     `board`, `stage`, `seat`, `supervisor`, `quiet-turn`, `desk-check`.
   - 5 (alternatives rejected): the `chosen: false` alternatives of DR-306
     to DR-311; its last alternative is moot, as that Issue's Notes say.
   - 6: `wiki/stereorepo/meta-harness.md` and DR-309. 7:
     `wiki/stereorepo/cockpit.md`.
   - 8: the open-question lists of `seat.md` (four) and `supervisor.md`
     (two).
   - 9: no home; step 4 is `issues/backlog/release-apm-package.md`.
   - 10: DR-313, the wiki page of each board term, and DR-319, where
     `why-fork-inherited-terms` applied DR-313's rule to the inherited
     terms.
   A claim with no home is added to the record or page it fits, and the
   entry says so. Check against the record text, not against this map.
2. **Delete** `WHY_FORK.md` with `git rm`.
3. **`loaders.py`:** in `durable()`, drop the `if path == ROOT /
   "WHY_FORK.md": continue` pair and the docstring sentence "Not
   `WHY_FORK.md`, which is kept as written until its content is worked up
   into records."
4. **`pair-loop-spike-evidence.md`:** delete the parenthesis "(once
   section 8 of `WHY_FORK.md`, which `why-fork-remove-file` deletes)",
   which spans lines 10 and 11, and rewrap the paragraph. The sentence
   around it already says the Seat and Supervisor pages list the questions
   as open questions, so removing it is the pointer the Wanted list asks
   for.

Tests that show it works:

- `test ! -e WHY_FORK.md`.
- `git grep -l WHY_FORK -- ':!issues/done/'` lists only this Issue file.
- `grep -n WHY_FORK .meta/checks/citations/loaders.py` finds nothing.

Risks:

- **Citations of the deleted file.** `path_and_line_claims()` in
  `claims.py` fails on a `path:line` that names no file, and `durable()`
  reads `issues/done/`. `git grep -nE "WHY_FORK\.md:[0-9]"` finds no such
  citation today, and the plain mentions in `issues/done/` are not checked
  for existence, so they can stay.
- **A record that grows a claim** is `PROPOSED` and awaiting the
  developer's desk check (DR-306 to DR-313); add to it, but do not change
  its decision or status.

## Audit

Each numbered section of `WHY_FORK.md`, and where its claims now live. No
claim needed adding to a record or page. The claims listed as having no home
are about the discipline this repository forked away from, or are plans that
have been carried out. Section 1 said the fork keeps no account of that
discipline, so leaving them out is deliberate.

1. **Why fork.** DR-312 records what the fork kept, and the context of
   DR-306 records why the old discipline went. "Solorepo stays as the
   historical record" describes the other repository, not this one, and has
   no home.
2. **Why PR First has to die.** The context of DR-306 covers the
   choreography, state kept in GitHub, agents driving it, the cold start, the
   round-trips and polling, the reviewer writing English, the stall when an
   agent ignored an instruction, and the records written to patch each stall.
   The context of DR-309 covers the cold start per turn and rebases run
   separately. DR-313 covers the taxonomy of work (Actor, Agency, Job). Not
   carried: the table of seven workflows, the signed-channel hook that
   blocked `gh` reads, and the list of solorepo's DR-112 to DR-296. These are
   the old discipline's mechanics.
3. **What survives.** DR-312: the knowledge and writing disciplines, the gate
   contract's one shape, the bootstraps, APM distribution, and a bootstrap as
   a reference and an audit for a brownfield product.
4. **The new delivery paradigm.** DR-311 (a repository is the unit of
   parallelism), DR-306 (a supervisor deciding from what it observes, no
   agent at the top, the developer may edit any file), DR-307 (quiet turns,
   `Needs elaboration`), DR-308 (directories, `git mv`, front matter),
   DR-309 (vendor harness CLIs, subscription, one session for each Issue, one
   worktree), and DR-310 (local squash-merge, no pull request). The pages
   `seat`, `supervisor`, `quiet-turn`, `board`, `stage` and `desk-check`
   explain them. Gemini CLI's exclusion is DR-309's rule that a harness not
   drawing on subscription tokens is no candidate. Not carried: Antigravity
   as a later target, which is a plan, and the answer to solorepo's DR-214,
   a record this repository does not hold. The answer's two points are
   DR-306's consequence that the queue is files the developer can edit, and
   DR-309's seat started fresh when a stage names another model.
5. **Alternatives considered and rejected.** The `chosen: false`
   alternatives: the hand-off command and the `verdict:` field in DR-307,
   OKF and redundant front matter in DR-308, the agent SDK in DR-309.
   Deleting the choreography before the spike was made moot by the fork,
   as the Notes of `why-fork-delivery-records` say.
6. **The meta-harness survey.** `wiki/stereorepo/meta-harness.md`, with the
   choice of harness in DR-309.
7. **What the cockpit must do.** `wiki/stereorepo/cockpit.md`. The status
   convention it names is also `issues/backlog/cockpit-status-convention.md`.
8. **What the spike must answer.** The "Open questions" lists on
   `wiki/stereorepo/seat.md` (questions 1, 2, 4 and 6) and
   `wiki/stereorepo/supervisor.md` (3 and 5). Their answers are
   `issues/backlog/pair-loop-spike-evidence.md`.
9. **What happens next.** The bootstrap carried out the plan, so this section
   has no home. Step 4 is `issues/backlog/release-apm-package.md`.
10. **Ubiquitous Language: the board.** The board, its stages, the
    authoritative board on `main`, and what a board is not: `board.md`,
    `stage.md` and DR-308. Who moves Issues: `stage.md`, `supervisor.md` and
    `issues/README.md`. *Issue* for *Challenge*, what an Issue is not, *Epic*
    dropped, and the rule for choosing terms: DR-313 and `issue.md`. The
    re-test of inherited terms: DR-319. The words to avoid are on `board.md`
    (column, status field), `stage.md` (column, status field, and the
    backlog as the queue rather than the whole board) and `issue.md`
    (ticket, story). Not carried: `work/`, the directory's name only during
    the spike.

## Notes

- `durable()` in `.meta/checks/citations/loaders.py` now skips no file by
  name, so every Markdown file in the tree is read by the citation steps.
- The mentions of `WHY_FORK.md` in `issues/done/` stay. They are plain
  mentions, not `path:line` citations, so `path_and_line_claims()` does not
  check them.
