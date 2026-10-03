---
difficulty: medium
parent: trim-kept-decision-records
---

# Trim PR First residue from DR-179 to DR-217

One part of `trim-kept-decision-records`: these kept Decision Records still
carry some of PR First, its GitHub choreography or the taxonomy of work in
their prose: DR-179, DR-185, DR-190, DR-192, DR-194, DR-195, DR-198, DR-200,
DR-204, DR-207, DR-209, DR-216 and DR-217.

## Wanted

For each record, read it and decide which of these holds, then act on it:

- **Only an example or an aside is stale**, and the rule stands on its own:
  write a successor that states the rule with a current example, and mark
  the old record superseded by it. One successor may cover several records
  in this part.
- **The rule stands, but its argument leans on what was removed** (a class
  the ontology no longer has, such as Actor, Job, Remit, Goal, Personality or
  Securable; a coder and a reviewer; a workflow or a pull request): write the
  successor that argues it from what the repository has now, and mark the
  old one superseded.
- **The record no longer decides anything:** withdraw it.
- **The mention is still true** (a word used in its ordinary sense, say):
  leave the record, and list it under a `## Left as is` heading in this file
  with the reason.

A Decision Record is never rewritten (Journaling): the only change to an old
record is its status and the link to its successor. Each new record takes
the highest number the record holds plus one, and is re-rendered.

Several of these records are cited by `CLAUDE.md` (`AGENTS.md`) and by
skills (DR-190, DR-194, DR-198, DR-207); where one is superseded, those
citations move to its successor.

Mark a record the way the earlier parts did (DR-175, DR-084): `status:
SUPERSEDED` with `superseded_by: work:decision/<n>`, or `status: WITHDRAWN`
with a `withdrawn_because:` sentence naming what is gone.

## Out of scope

Records outside this part, including DR-334, which already supersedes DR-175
and sits beside DR-207 in `AGENTS.md`. Changing any rule's substance: a
successor restates a rule from current ground, and does not widen or narrow
it.

## Done when

- None of the thirteen records is still `ADOPTED` unless it is listed under
  `## Left as is` with a reason.
- Each superseded record names a successor that exists, and each successor
  carries no Actor, Job, Remit, Goal, Personality, Securable, coder,
  reviewer, workflow or pull request as part of its rule or its argument.
- Outside `.meta/assertions/decisions/` and `issues/done/`, no file cites a
  superseded or withdrawn record where its successor is meant: `AGENTS.md`,
  `template/AGENTS.md`, the imported assertions, the sources under
  `.meta/.apm/` and `bootstraps/` (not their compiled copies), the wiki, and
  the docstrings under `.meta/` that cite these records (about 80 files
  today) cite the successor instead. A citation that names the old record as
  history may stay. The one exception is the text of the `/technical-writing`
  and `/search` skills in `.meta/assertions/imported/structure.yaml` and
  their rendered copies, which the seats cannot re-render (see `## The plan`).
- The generated files (`.meta/decisions.md`, `SPECIALIZE.md`, the compiled
  skills) are re-rendered, not hand-edited, and list the new records.

## The plan

Read against the tree as it is. Gone: Article 15, Article 16 and Article 18,
DR-058, DR-064 and DR-176, the `noticed-and-not-done` concept and its wiki
page, `check_pr.py`, `.github/workflows/` (`coder.yml`, `review.yml`),
`.meta/say/` and the channel, `FakeGitHub` and the `merge-manager` loop, the
Actor, Personality and Remit classes, and `.meta/work/actors.yaml`. Still
there: `work:role/technical-writer` (a Role with a `communication_style`,
in `imported/authority.yaml`), Persona and its compiled agent
(`.meta/lib/apm_compile/agents.py`), `just dereference --sample` and
ground-moved scoping, `.meta/search.py` and its benchmark, the `meta doc`
check, Article 22 with four checked instances (A11, A14, A17, A20), and the
probes package (`harness/`, `files/`, `tools/` and subject modules).

| Record | Verdict | Why |
|---|---|---|
| DR-179 | Left as is | "Code review" sits in a rejected alternative whose reason still holds, and `say/*` is a list of what `.meta/` held then. The rule (every public item under `.meta/` has a docstring; public means no leading underscore; `meta doc` checks it) stands as written. |
| DR-185 | Left as is | A case-insensitive search of the record for pull, PR, GitHub, Actor, Remit, Personality, Securable, coder, review, workflow, Job, Goal, merge and Challenge finds nothing, so the parent listed it in error. Closed-world wikilinks and the MOS:LEAD check are current. |
| DR-207 | Left as is | "Leave inline commentary to reviewer judgement" is a rejected alternative, and the reason (a rubric that stops at the docstring gives a pass nothing to check a body against) holds for a seat. "Pre-handoff workflow wiring" is one consequence among five, an aside. The four exceptions stand, and superseding it would move citations the seats cannot render (the skill). |
| DR-190 | Successor S1 | The two-part regime stands: the `ubiquitous language wiki parity` check, plus judgement on unlinked domain nouns. Restate the judgement as the second seat's, in its turn, before the Issue lands, not "the reviewer role" "before merge" "in a pull request", and drop "PR First reviewer role judgement". |
| DR-192 | Successor S2 | Ground-moved scoping and `--sample` stand, and so does giving whole-corpus citation upkeep to `work:role/technical-writer` with `/search`. Drop the "coder loop during standard PRs" alternative's framing and "remit"; argue it from keeping an Issue's diff to what the Issue asks. |
| DR-194 | Successor S3 | The `/technical-writing` skill and the BM25F search stand. Drop "enforced during PR review (DR-176)", `work:personality/technical-writer`, "coder agents", "PR threads" and the falsifier's "reviewer litigation"; the benchmark figures it gives may be restated from a fresh run. |
| DR-195 | Successor S4 | What stands is the Concept as the atomic unit of domain meaning and search indexing a concept's `pref_label`, `alt_labels` and definition. The `noticed-and-not-done` concept, Article 15, DR-064 and the PR prose are gone, so the successor drops them and its falsifier keeps only the search half. |
| DR-198 | Successor S5 | The two regimes stand. Argue them from the Role's `communication_style` and the seats' turns (a seat speaks in the register in pair notes and in conversation, and applies `/technical-writing` before its turn ends), not from the Coder personality, an Actor, `coder.yml` or PR review threads. |
| DR-200 | Successor S6 | The rule stands: a Persona compiles to an agent that answers as the Persona, reads and never writes, for design interrogation. Restate it without Actor, Personality, Remit or the Stakeholder Surrogate Role: an agent session takes the Persona's context, goals and frustrations as its prompt. |
| DR-204 | Successor S7 | The rule stands: inherited probes and the search benchmark generalise over what a portfolio holds on disk, so a fresh clone passes. Drop the Challenge that occasioned it, `check_pr.py` in the Step 2 prefix list, and Article 18. |
| DR-209 | Successor S8 | The rule stands: probes are a package under `.meta/checks/probes/`, one module per subject under test, with the harness apart. Restate it with today's layout (`harness/` holding loaders, fakes and acts; `files/`, `tools/`, `citations.py`, `knowledge.py` and the rest), dropping the channel, the loops' verbs, `FakeGitHub` and the pull request that was refused. |
| DR-216 | Successor S9 | Article 22 stands. Argue it from its four checked instances (A11, A14, A17, A20) and the board (a stage is the directory an Issue file sits in, which the charter's own example gives), not from seven Articles, `coder.yml`, a Job or a reviewer. The second seat holds it, as `checked_by` already says. |
| DR-217 | Successor S10 | The rule stands: the script keeps its path, its body lives in `.meta/lib/<script>/`, modules import sibling modules, not names. Use `render` (`from lib.render import record`) or `apm_compile` as the example, not `check_pr`; drop `review.yml`, the control-plane restore and "one pull request each". Carry all forty `enacted_in` artifacts forward. |

S1 to S10 become DR-335 onward in the order of this table. Whoever
implements re-reads each record before writing its successor; a verdict that
turns out wrong moves in this table, with the reason. None is withdrawn: each
still decides something the tree holds to.

### Steps

1. Run the search benchmark (the `/search` skill's `--benchmark` mode) and
   record hit@5 and MRR under `## Benchmark`.
2. Write S1 to S10, each `status: ADOPTED`, with `supersedes:`, the
   predecessor's `applies` and `enacted_in` carried forward, a `context:`
   saying what it replaces, and a rationale argued from the current tree.
   Apply `/technical-writing`.
3. On each superseded record change only `status: SUPERSEDED` and add
   `superseded_by:`.
4. Move citations, editing sources only, and keeping the possessive
   (`stereorepo's DR-nnn`) in files a portfolio copies:
   - S1 (DR-190): `AGENTS.md`, `template/AGENTS.md`, `imported/charter.yaml`
     (A17), `imported/disciplines.yaml`, `imported/vocabulary.yaml`,
     `.meta/.apm/instructions/knowledge-management.instructions.md` and
     `ubiquitous-language.instructions.md`, `.meta/checks/files/templates.py`
     and `wiki.py`, `.meta/checks/probes/knowledge.py` and `wiki.py`,
     `wiki/stereorepo/claim.md`, `concept.md`, `evidence.md`,
     `knowledge-management.md`.
   - S2 (DR-192): `.meta/dereference.py`, `.meta/lib/dereference/reading.py`,
     `.meta/checks/probes/tools/__init__.py` and `dereference.py`,
     `.meta/search.py`.
   - S3 (DR-194): `AGENTS.md`, `template/AGENTS.md`,
     `.meta/assertions/disciplines.yaml`, `imported/disciplines.yaml`,
     `knowledge-management.instructions.md`, `.meta/checks/comments.py`,
     `.meta/checks/probes/tools/search.py`, `.meta/lib/render/skills.py`,
     `.meta/lib/search/` (`__init__`, `benchmark`, `cli`), `.meta/search.py`,
     `wiki/stereorepo/knowledge-management.md`.
   - S4 (DR-195): `imported/vocabulary.yaml`, `.meta/checks/probes/tools/search.py`,
     `.meta/lib/search/cli.py`, `.meta/search.py`, `wiki/stereorepo/concept.md`
     and `knowledge-management.md`.
   - S5 (DR-198): `AGENTS.md`, `template/AGENTS.md`,
     `.meta/lib/apm_compile/agents.py` (which writes
     `.meta/.apm/agents/technical-writer.agent.md`).
   - S6 (DR-200): `.meta/.apm/README.md`, `.meta/apm_compile.py`,
     `.meta/lib/apm_compile/agents.py` (which writes
     `the-developer.agent.md`), `imported/vocabulary.yaml`,
     `.meta/work/personas.yaml`.
   - S7 (DR-204): `.meta/test_specialization.py`.
   - S8 (DR-209): `.meta/check.py`, `.meta/checks/probes/` (`__init__`,
     `citations`, `files/__init__`, `harness/__init__`, `knowledge`,
     `structure`, `surface`, `tools/__init__`, `tools/gate`, `wiki`),
     `.meta/lib/render/record.py`, and the Python bootstrap's
     `py-quality-setup` and `py-test-quality` skills (source under
     `bootstraps/python/skills/`, which `.meta/lib/apm_compile/bootstrap.py`
     compiles to the copies under `bootstraps/python/.apm/skills/` when
     rendering).
   - S9 (DR-216): `imported/charter.yaml` (A22 `checked_by`),
     `imported/vocabulary.yaml`, `wiki/stereorepo/externalized-memory.md`.
   - S10 (DR-217): `.meta/README.md`, `.meta/adapt.py`, `.meta/apm_compile.py`,
     `.meta/bundle.py`, `.meta/render.py`, `.meta/assertions/disciplines.yaml`,
     `.meta/checks/file_sizes.baseline.yaml` (a comment),
     `.meta/checks/files/python.py`, `.meta/checks/probes/files/__init__.py`
     and `sizes.py`, `.meta/checks/probes/tools/test_brownfield.py`,
     `.meta/lib/__init__.py`, `.meta/lib/adapt/` (`__init__`, `plan`,
     `tracked`), `.meta/lib/bundle/__init__.py`.
   - **Not moved:** the skill text in `imported/structure.yaml`. It cites
     DR-190, DR-192, DR-194, DR-195, DR-198 and DR-209 in the
     `/technical-writing` skill and DR-194 in the `/search` skill, and
     `just render` writes both to tracked files under `.claude/skills/`,
     which the seats' sandbox denies. Changing that text leaves `rendered
     prose` red as `x`, and the loop would hand it back to the round cap,
     as it did on `trim-decision-records-065-177`. Instead, add these seven
     citations to `issues/backlog/technical-writing-skill-successor-citations.md`
     (a `developer` Issue already), naming the `/search` skill beside it.
   - Then grep each superseded number again for anything this list missed.
5. Run `just render`, then check that `git status .claude/` is clean: a
   change that reaches either `.claude/skills/` page means some source
   outside the skill text feeds it, and that citation goes back.
6. Re-run the benchmark and record the figures. Fill in `## Left as is`.

### Tests

- `decision supersession` passes: each `superseded_by` names a later record
  that lists the old one under `supersedes:`.
- `enacting citations` passes. Each file in an `enacted_in` must cite an
  entry naming it, which is why each successor carries its predecessor's
  `enacted_in` whole. The check asks only that a named file cite at least
  one entry naming it, and no check rejects a citation of a superseded
  record, so `skill-technical-writing` and `skill-search`, which keep
  citing the old records, stay green.
- `cited decisions` passes, so every new citation resolves and copied files
  keep the possessive.
- `rendered prose` passes, and `just render` leaves the tree unchanged.
- The Done-when greps, and the benchmark's hit@5 and MRR no lower after than
  before, both recorded here.

### Risks

- **The sandbox.** As above: nothing in this change may alter either
  `.claude/skills/` page. Step 5 is the guard.
- **`stated relations` reads this file.** Name each successor beside its own
  predecessor, never as two ranges, and never quote a wrong pairing, even to
  explain a fix. The S-labels in this plan are why it names no new number.
- **Probe literals.** A probe or a finding message may print a record number
  (`file_sizes.baseline.yaml` and `sizes.py` for DR-217, the probes'
  docstrings for DR-209). Search the probes for each number before changing
  a message.
- **`path:line` claims.** The gate checks a `path:line` against the file, so
  this file uses paths only.
- **Size.** Ten successors and about eighty files is more than the last part.
  The citation moves are mechanical, and each successor is independent, so
  if the turn runs long, land S1 to S10 with their citation moves record by
  record and check each with `cited decisions` before the next.

## Benchmark

`.meta/search.py --benchmark`, 18 queries:

- Before the first record changed: hit@5 0.94 (17/18), MRR 0.55.
- After: hit@5 0.94 (17/18), MRR 0.55.

## Left as is

- **DR-179:** "code review" sits in a rejected alternative whose reason
  still holds, and `say/*` lists what `.meta/` held then; the `meta doc`
  rule stands as written.
- **DR-185:** names no removed class, verb or workflow; closed-world
  wikilinks and the MOS:LEAD check are current.
- **DR-207:** "reviewer judgement" is a rejected alternative whose reason
  holds for a seat, and "pre-handoff workflow wiring" is an aside among its
  consequences; the four comment exceptions stand.

## What was done

- Ten successors, each beside its predecessor: DR-335 supersedes DR-190,
  DR-336 supersedes DR-192, DR-337 supersedes DR-194, DR-338 supersedes
  DR-195, DR-339 supersedes DR-198, DR-340 supersedes DR-200, DR-341
  supersedes DR-204, DR-342 supersedes DR-209, DR-343 supersedes DR-216, and
  DR-344 supersedes DR-217. Each carries its predecessor's `applies` and
  `enacted_in` whole, and names what it no longer depends on only in its
  `context:`.
- Citations moved in 55 source files. A grep for the ten old numbers outside
  the decision log, the Issues and the history logs finds them only in the
  skill text below and in generated pages: `.meta/decisions.md`, and the
  "Where this came from" lists of `.meta/charter.md`, `.meta/disciplines.md`
  and `SPECIALIZE.md`, which list superseded records too.
- **The skills' citations are not moved,** as planned: `structure.yaml`'s
  `/technical-writing` and `/search` text still cites DR-190, DR-192,
  DR-194, DR-195, DR-198 and DR-209. They are added to the `developer`
  Issue `issues/backlog/technical-writing-skill-successor-citations.md`,
  which now covers both skills and every record either part left there.
  `just render` left `.claude/` untouched.
- The benchmark first came back at MRR 0.54: DR-338's context repeated the
  phrase of the query "where do things noticed but not done go" and pushed
  its target from rank 2 to 3. Its context now names that concept without
  the phrase. That query's top hit is DR-195, a superseded record, which is
  the benchmark's business, not this Issue's.
- Beyond the plan: the Python bootstrap's `py-test-quality` skill listed the
  probes' subjects as the hooks, the channel and the loops' verbs, none of
  which exist; it now names today's subjects, and says the states "they were
  found wrong in" rather than "reviewers found them wrong in".
- `just gate meta` passes. The change touches no seed and nothing under
  `pair/`, so no other Project's gate applies.

## Pair notes

> **primary, backlog turn 1**
>
> I groomed `issues/underway/trim-decision-records-179-217.md` and committed it. Difficulty stays **medium**: it's 13 records, and the previous part (DR-065 to DR-177, which needed six successor records) was done in one piece, so there's no need to split this one.
>
> What changed:
> - **How to mark a record:** the issue now says to follow what the earlier parts did. A replaced record gets `status: SUPERSEDED` and a `superseded_by:` link (as DR-175 did); a dropped one gets `status: WITHDRAWN` and a `withdrawn_because:` sentence (as DR-084 did).
> - **Out of scope:** now also excludes DR-334, which already replaced DR-175 and is cited next to DR-207 in `AGENTS.md`. It also excludes changing what any rule says: a successor only restates the rule from what the repository has now.
> - **Done when:** the `just gate` line is gone. In its place are checks you can see in the files:
>   - None of the 13 records is still `ADOPTED` unless it is listed under `## Left as is` with a reason.
>   - Every successor named exists, and none relies on Actor, Job, Remit, Goal, Personality, Securable, coder, reviewer, workflow or pull request.
>   - Citations point to the successor everywhere outside `.meta/assertions/` and `issues/done/`. These records are cited in about 80 files today, including code docstrings, `template/AGENTS.md` and `bootstraps/`, not just `AGENTS.md` and the skills. A citation that names the old record as history can stay.
>   - Generated files are re-rendered, not edited by hand.
>
> All 13 records are still adopted, so none of the work has started yet.

> **secondary, backlog turn 2**
>
> I'm leaving the issue file as my partner wrote it. I checked what it says against the records, and it holds up:
>
> - All thirteen records (DR-179 to DR-217) are still `ADOPTED`, so none of the work has started.
> - The way it says to mark a record matches what the earlier parts actually did: DR-175 is marked `SUPERSEDED` with `superseded_by: work:decision/334`, and DR-084 is marked `WITHDRAWN` with a `withdrawn_because:` sentence.
> - The highest record is DR-334, so the first new successor will be DR-335.
> - The check that no successor mentions a "workflow" doesn't catch anything legitimate: the repository has no `.github/workflows` directory.
>
> The scope is clear, and every "Done when" item can be checked in the files without naming a gate. **medium** is the right difficulty: the previous part was about the same size and was done in one piece.

> **primary, todo turn 1**
>
> I wrote the plan under `## The plan` in `issues/todo/trim-decision-records-179-217.md` and committed it as a9a4c0af. Nothing is implemented yet.
>
> **What happens to each of the 13 records:**
> - **Left as is (3):**
>   - DR-179: the stale words are history, and its docstring rule still holds.
>   - DR-185: I found no removed class or workflow in it.
>   - DR-207: the reviewer it mentions is in a rejected option whose reason still holds, and "pre-handoff workflow wiring" is a side remark.
> - **Replaced by a new record (10):** DR-190, DR-192, DR-194, DR-195, DR-198, DR-200, DR-204, DR-209, DR-216 and DR-217. Each rule still holds, but its example or reasoning relies on something that's gone: a coder, a reviewer, an Actor or Personality, `coder.yml`, `check_pr.py`, Article 15, the "noticed and not done" concept, or the seven-Article argument (three of those Articles are gone). The plan calls the new records S1 to S10 instead of numbering them, so the gate check that reads the Issue's own wording can't trip on them. They become DR-335 onward.
> - **Withdrawn:** none. Each record still decides something the code holds to.
>
> **The main risk:** the `/technical-writing` and `/search` skills cite DR-190, DR-192, DR-194, DR-195, DR-198 and DR-209. Changing those citations means rewriting files under `.claude/skills/`, which the seats' sandbox can't do. That stalled the previous part until its round limit. So the plan leaves those skill citations alone and adds them to the existing developer Issue `technical-writing-skill-successor-citations`, for you to re-render outside the sandbox. After re-rendering, the implementer checks that nothing under `.claude/` changed. I changed "Done when" to match: it now allows that one exception, and it now also covers the shared assertion files under `.meta/assertions/imported/`, which the earlier wording had left out.
>
> **The rest of the plan:**
> - **Order:** take a search benchmark score first, write the ten new records, change only the status line on each old one, move the citations, re-render, then re-run the benchmark.
> - **Citations:** each new record has a list of the files whose citations move to it.
> - **Tests:** the existing gate checks for superseded records, cited records and enacted files must pass, the rendered pages must be up to date, and the benchmark score must not drop.
>
> **Size:** this is about 80 files and ten new records, more than the previous part. I kept it at medium because the citation moves are mechanical and each new record can be done and checked on its own.

> **secondary, todo turn 2**
>
> The plan holds up, and I made two small fixes to it (commit fb36dfc9):
>
> - **DR-185:** the plan left this verdict open until someone re-read the record. I searched the record, ignoring case, for pull, PR, GitHub, Actor, Remit, Personality, Securable, coder, review, workflow, Job, Goal, merge and Challenge, and none of them appear. So the parent Issue listed it in error, and the verdict is now plainly "Left as is".
> - **Tests:** I read the checks behind the plan's main risk, leaving the skill citations unmoved. The `enacting citations` check only asks that a file cite at least one record that names it, and no check rejects citing a superseded record. So leaving the old citations in the `/technical-writing` and `/search` skills does not fail anything, and the plan now says why.
>
> The rest I checked and left alone:
>
> - The developer Issue that the left-over skill citations go to exists, with `difficulty: developer`.
> - The supersession check matches what step 3 does.
> - Step 5's check that nothing under `.claude/` changed is the right guard against the sandbox problem that stalled the last part.

> **primary, todo turn 3**
>
> I'm leaving the plan as it is. Both of my partner's fixes hold up against the records and the checks:
>
> - **DR-185 is "Left as is".** Their search matches what I found when I read the record: it names no pull request, coder, reviewer, workflow, or removed class such as Actor or Remit. Closed-world wikilinks and the check that each wiki page opens with a bold one-sentence definition are both still in use.
> - **The tests now say why leaving the skill citations is safe.** The check that every file named in a record's `enacted_in` list cites that record only needs each file to cite at least one record that names it. No check rejects a citation of a superseded record. So the `/technical-writing` and `/search` skills can go on citing the old records without anything failing.

> **primary, in-progress turn 1**
>
> I implemented the plan and committed it as 7fc69187 and b32f494d. `just gate meta` passes with all 93 steps. The change touches no seed and nothing under `pair/`, so no other Project's gate applies.
>
> **What changed:**
> - **Ten new records, DR-335 to DR-344, each replacing one old record:** DR-335 replaces DR-190, DR-336 replaces DR-192, DR-337 replaces DR-194, DR-338 replaces DR-195, DR-339 replaces DR-198, DR-340 replaces DR-200, DR-341 replaces DR-204, DR-342 replaces DR-209, DR-343 replaces DR-216, and DR-344 replaces DR-217.
>   - Each new record keeps its old record's `applies` and `enacted_in` lists unchanged, and argues its rule from what the repository has now: the two seats, the board, the technical writer Role and today's probe and `.meta/lib/` layout.
>   - Removed things (coder, reviewer, pull request, Actor, Remit, Personality, `check_pr.py`) appear only in each record's `context:`, where it says what it replaced.
>   - On the old records, only the status and the link to the new record changed.
> - **Citations moved in 55 source files,** including `AGENTS.md`, `template/AGENTS.md`, the shared assertion files, the wiki, the checks and probes under `.meta/`, and the Python bootstrap's skills. Generated pages were re-rendered, not edited.
>   - The old numbers now appear only where expected: the decision records, Issues and history logs, the generated `.meta/decisions.md`, and the "Where this came from" lists on three generated pages. Those lists name superseded records too.
> - **Left as is:** DR-179, DR-185 and DR-207, each with its reason in the Issue file.
> - **Search benchmark:** hit@5 0.94 (17/18) and MRR 0.55, the same before and after.
>   - The first run after the change came back at MRR 0.54. DR-338's wording repeated the query "where do things noticed but not done go" and pushed the right answer from rank 2 to 3. I reworded that sentence, and the score went back to 0.55.
>
> **For you:**
> - **One task needs you.** As planned, the `/technical-writing` and `/search` skills still cite DR-190, DR-192, DR-194, DR-195, DR-198 and DR-209. Changing them means re-rendering files under `.claude/skills/`, which the seats' sandbox blocks.
>   - I widened the existing developer Issue `issues/backlog/technical-writing-skill-successor-citations.md` into one table covering both skills and both parts' leftovers.
>   - To clear it: edit `.meta/assertions/imported/structure.yaml` as that Issue says, run `just render` outside the sandbox, and commit the four `SKILL.md` copies.
> - **New backlog Issue:** `issues/backlog/citations-of-retired-articles.md`. Two live files still cite Articles that have been retired as though they were in force:
>   - `imported/vocabulary.yaml` cites Article 15.
>   - The Python bootstrap's `py-quality-setup` skill cites A19 and an Actor.
> - **One fix beyond the plan:** the Python bootstrap's `py-test-quality` skill described probe subjects that no longer exist (the hooks, the channel, the loops' verbs). It now names the current ones.

> **secondary, in-progress turn 2**
>
> My partner's implementation is correct, so I left the code and records alone. I fixed two backlog Issue files (commit 9c447c1c), and `just gate meta` passes all 93 steps.
>
> **What I checked and found correct:**
> - **The ten new records:** DR-335 to DR-344 each replace one old record (DR-190, DR-192, DR-194, DR-195, DR-198, DR-200, DR-204, DR-209, DR-216 and DR-217, in that order).
>   - Pull requests, coders, reviewers, Actors, Remit, Personality, `check_pr.py` and GitHub workflows appear only in each record's `context:`, where it says what it replaces. The rules and their reasoning don't depend on any of them.
>   - The facts they state about the code hold: the probe helpers named in DR-342 exist, the 500- and 350-line limits in DR-344 match `.meta/checks/files/python.py`, and the benchmark's 80% pass mark in DR-341 matches `.meta/lib/search/benchmark.py`.
> - **Citations:** a search for the ten old numbers finds them only where the plan allows:
>   - the decision records, the Issues and the history logs;
>   - the generated "Where this came from" lists;
>   - the `/technical-writing` and `/search` skill text and its rendered copies, which the seats' sandbox can't re-render.
> - **The citation moves:** each changed line swaps one number for its replacement, and the `stereorepo's` prefix stays in files a new portfolio copies.
>
> **What I fixed:**
> - **`issues/backlog/citations-of-retired-articles.md`** had the Python bootstrap skill's paths the wrong way round. The source is `bootstraps/python/.apm/skills/py-quality-setup/SKILL.md`, and rendering compiles it to `bootstraps/python/skills/`. The Issue now also says that the same passages send commits through `.meta/say/commit` and its Actor Trailer, both of which are gone.
> - **`issues/backlog/technical-writing-skill-successor-citations.md`** (your hands-on Issue) now also asks you to remove `(work:personality/technical-writer)` from the `/technical-writing` skill. The Personality class is gone, and you'll be re-rendering that skill anyway. Its "Done when" now checks for this too.
>
> I left one thing unchanged: Article 17's `checked_by` still starts with "Review checking…", while DR-335 now gives that judgement to the second seat. Changing an Article's wording is outside this Issue.

> **primary, in-progress turn 3**
>
> I kept almost all of my partner's changes and reversed one, committed as 38e90248. `just gate meta` passes all 93 steps. No other Project's gate applies, because nothing under `pair/` or either seed directory changed.
>
> **The one I reversed:** my partner had flipped which copy of the Python bootstrap's skills is the source. It isn't the other way round. `.meta/lib/apm_compile/bootstrap.py` reads `bootstraps/python/skills/` and writes the copy under `bootstraps/python/.apm/skills/`. It also matches what happened last turn: I edited `skills/py-test-quality`, and `just render` then updated the `.apm/` copy. In `issues/backlog/citations-of-retired-articles.md`, the source is named as `bootstraps/python/skills/py-quality-setup/SKILL.md` again, with a pointer to the compiler. My partner's addition there stays: the same passages still route commits through `.meta/say/commit` and its Actor trailer, both of which are gone.
>
> **What I kept:**
> - **The `/technical-writing` skill fix in your developer Issue** (`technical-writing-skill-successor-citations`): when you re-render that skill, also drop `(work:personality/technical-writer)`. The Personality class is gone, so this belongs in the same edit.
> - **Leaving Article 17's wording alone:** its `checked_by` still says "Review checking…", while DR-335 gives that judgement to the second seat. Rewording an Article is outside this Issue.

> **secondary, in-progress turn 4**
>
> My partner was right to reverse my change, and I've corrected the plan as well (commit ff0df6d5). `just gate meta` passes all 93 steps.
>
> `.meta/lib/apm_compile/bootstrap.py` reads the Python bootstrap's skills from `bootstraps/python/skills/` and writes the copies under `bootstraps/python/.apm/skills/`. So `bootstraps/python/skills/` is the source, which is what my partner said. I had taken the opposite direction from the plan, and the plan was wrong.
>
> The plan's list of files to update for DR-342 now gives the right direction and names the compiler, so the next reader isn't misled the same way. I changed nothing else.

> **primary, in-progress turn 5**
>
> I'm changing nothing this turn. My partner's fix is correct: the plan I wrote had the Python bootstrap's skills compiling the wrong way round. The plan now gives the right direction: `.meta/lib/apm_compile/bootstrap.py` reads the skills from `bootstraps/python/skills/` and writes the copies under `bootstraps/python/.apm/skills/`.
>
> The work itself is complete:
> - DR-335 to DR-344 replace ten of the thirteen records.
> - DR-179, DR-185 and DR-207 are kept as they are, each with its reason in the Issue file.
> - Citations moved in 55 source files.
> - The search benchmark is unchanged: hit@5 0.94 (17/18) and MRR 0.55.
>
> `just gate meta` passed all 93 steps on my last turn, and my partner reports the same after their fix. No other Project's gate applies, because nothing under `pair/` or either seed changed.
>
> One task still needs you: in the `/technical-writing` and `/search` skills, moving six old citations (DR-190, DR-192, DR-194, DR-195, DR-198 and DR-209) to their new records, and dropping `work:personality/technical-writer`. A seat can't do this, because it needs `just render` run outside the sandbox. The steps are in `issues/backlog/technical-writing-skill-successor-citations.md`.
