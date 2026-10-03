---
difficulty: medium
parent: trim-kept-decision-records
---

# Trim PR First residue from DR-002 to DR-048

One part of `trim-kept-decision-records`: these kept Decision Records still
carry some of PR First, its GitHub choreography or the taxonomy of work in
their prose: DR-002, DR-003, DR-006, DR-007, DR-008, DR-015, DR-019, DR-020,
DR-021, DR-023, DR-031, DR-039 and DR-048.

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

A Decision Record is never rewritten (Journaling). The only change to an old
record is the one `.meta/work/decisions.yaml` allows: a superseded record
gets `status: SUPERSEDED` and `superseded_by:` naming its successor, which
lists it under `supersedes:`; a withdrawn record gets `status: WITHDRAWN` and
`withdrawn_because:` (as DR-036 does). Each new record takes the highest
number the record holds plus one, and `.meta/decisions.md` is re-rendered.

Where a superseded or withdrawn record is cited by something that is not a
Decision Record (today: `.meta/assertions/imported/charter.yaml`,
`disciplines.yaml`, `domain_vocabulary.yaml`, `.meta/work/purpose.yaml`,
`.meta/work/personas.yaml`, `.meta/.apm/instructions/nothing-unconsumed.instructions.md`,
`.meta/lib/search/benchmark.py`, `.meta/apm_compile.py`, `.meta/schemas.md`),
the citation moves to the successor, or is dropped if the record was
withdrawn; generated files (`.meta/charter.md`, `.meta/disciplines.md`,
`.meta/decisions.md`, `.agents/rules/`, the copies under `apm_modules/`) are
re-rendered rather than edited. In `benchmark.py` the citation is a gold
label (`work:decision/015` in a query's expected results): it moves to the
successor that now carries that content, and the search benchmark must still
score as well as it did before.

## Out of scope

- Records outside the thirteen listed, including later records that cite
  them (DR-017, DR-087, DR-205 and others): they are journal entries and
  stay as written.
- The parts covering DR-065 onwards (sibling Issues in `issues/backlog/`).
- Changing the ontology, the schema of a Decision Record, or the checks.

## Done when

- Each of the thirteen records has `status: SUPERSEDED` with a
  `superseded_by:`, or `status: WITHDRAWN` with a `withdrawn_because:`, or
  appears under `## Left as is` in this file with a one-line reason.
- Every successor lists what it supersedes under `supersedes:`, and its
  statement and rationale name no Actor, Job, Remit, Goal, Personality,
  Securable, coder, reviewer, pull request or PR First, except to say what
  it replaced.
- No file outside `.meta/assertions/decisions/` and `issues/` cites a
  superseded or withdrawn record from this list.
- `.meta/decisions.md` shows the new records and the changed statuses.
- The search benchmark (the `/search` skill's `--benchmark` mode, scoring
  `.meta/lib/search/benchmark.py`) reports a hit@5 count and an MRR no lower
  than it reported before the first record changed. Record both pairs of
  figures in this file.

## The plan

The current ontology (`.meta/work/*.yaml`) has Capability, Role (with
`communication_style`), Persona, PersonaGoal (END, EXPERIENCE, LIFE),
JobToBeDone (`persona` and `serves` required), Article (with `example` and
`falsifier`, but no `origin`), Discipline, Issue and WorkEntity. It has no
Goal, Agency, Challenge, Deadline, Definition of Done, Personality, Actor,
Remit, Securable, Permission, AuditRecord or BOM. Reading the thirteen records
against that list gives these verdicts:

| Record | Verdict | Why |
|---|---|---|
| DR-002 | Left as is | "Ontology of work" is still what the repository calls `.meta/work/`, and DR-023 already records that `work_ontology.md` was dropped. |
| DR-023 | Left as is | It names no removed class. The ontology is still seven modules. |
| DR-003 | Successor S1 | LinkML still holds. Its examples (a SMART Goal, a Definition of Done) are gone; use `JobToBeDone.serves` being required, and a Capability shared by many Roles. |
| DR-006, DR-008 | Successor S2 | A skill composes tools, a tool is atomic (`composed_of` and its rule, `.meta/work/authority.yaml`), and nothing more is reified until a consumer needs it. The BOM and audit arguments go. S2 must carry DR-008's sentence, "a coordinate system invented ahead of its consumer is one that will be wrong", because Nothing Unconsumed quotes it. |
| DR-007 | Successor S3 | APM is still the packaging target (`.meta/.apm/`, `apm_compile.py`). Argue it from what APM carries now (skills, Discipline instructions, rules compiled per harness), not from Securable or Remit. |
| DR-015 | Successor S4 | Only the example list is stale (Challenge, Goal, Job). Restate it with the current vocabulary: Persona, Capability, Role, Discipline, Article, Issue, Specialization. |
| DR-019, DR-020, DR-021, DR-031, DR-039 | Successor S5 | One chain: a Persona is Cooper's user archetype (six PersonaKinds); its goals are tiered and an END goal is identified; a Job to be Done names its Persona, not a Role, and `serves` at least one of that Persona's END goals. Drop Personality, Actor, Agency, Goal, Challenge and the Permission and AuditRecord analogy. The dialogue register is now `Role.communication_style`. |
| DR-048 | Successor S6 | The names Article and Charter stand. Argue them from `example` and `falsifier` instead of `origin`, and leave the two writing styles to DR-198 and `Role.communication_style` instead of two Personalities. Keep `applies:` on Articles 1 and 12, both of which are still live. |

No record is withdrawn. Whoever implements re-reads each record before
writing its successor; a verdict that turns out wrong moves in this table,
and the reason is written here.

### Steps

1. Run the `/search` skill's benchmark (`uvx --python 3.13 --with linkml --with pyyaml python .meta/search.py --benchmark`) and
   write the hit@5 and MRR figures below.
2. Write S1 to S6 as `.meta/assertions/decisions/DR-nnn.yaml`, numbered from
   the highest number on the branch plus one (DR-323 to DR-328 today). Each
   has `status: ADOPTED`, `supersedes:` listing its predecessors, the
   predecessors' `enacted_in` and `applies` carried forward, a `context:`
   saying which removed class it routes around, and a rationale argued from
   the current schema. Use `/technical-writing` for the prose.
3. On each superseded record change only `status: SUPERSEDED` and add
   `superseded_by:`. Leave the rest of the file untouched.
4. Move each citation to its successor:
   - `.meta/schemas.md` (DR-003) → S1
   - `.meta/assertions/imported/charter.yaml` and `disciplines.yaml`
     (DR-008) → S2
   - `.meta/apm_compile.py` docstring (DR-007) → S3
   - `.meta/assertions/domain_vocabulary.yaml` comment and the
     `work:decision/015` gold label in `.meta/lib/search/benchmark.py` → S4
   - `.meta/work/purpose.yaml` (DR-021, DR-039) and `.meta/work/personas.yaml`
     (DR-021) → S5
   - before editing, grep for `DR-0nn` and `decision/0nn` across the tree
     (excluding `issues/`, the record itself and generated output) to catch
     any citation this list missed.
5. Run `just render`. It regenerates `.meta/decisions.md`,
   `.meta/charter.md`, `.meta/disciplines.md` and, through its
   `apm_primitives` writer, `.meta/.apm/instructions/nothing-unconsumed.instructions.md`
   (whose DR-008 citations come from `disciplines.yaml`, so that file is
   never edited by hand). `.agents/` and `apm_modules/` are git-ignored and
   are not part of the change.
6. Re-run the benchmark, write the figures below, and fill in
   `## Left as is` for DR-002 and DR-023.

### Tests

- The graph check `decision supersession` (`.meta/checks/graph/record.py`)
  passes: every `superseded_by` names a later record, and every `supersedes`
  names an earlier one.
- No check compares the two slots, so read them by hand: every
  `superseded_by: work:decision/nnn` on an old record is listed in that
  successor's `supersedes:`, and the reverse. (`supersedes:` is in use, as in
  DR-059's `- work:decision/049`; no record uses `superseded_by:` yet, and its
  value is a single id in the same form, `work:decision/019`. These would
  be the first records with `status: SUPERSEDED`.)
- The `stated relations` check (`.meta/checks/citations/claims.py`) passes:
  any prose naming one record as superseding another is backed by the slot. Name
  predecessors in prose only where the slot already holds them.
- `git grep -nP 'DR-0(02|03|06|07|08|15|19|20|21|23|31|39|48)\b|decision/0(02|03|06|07|08|15|19|20|21|23|31|39|48)\b' -- ':!.meta/assertions/decisions' ':!issues'`
  (`-P`, because POSIX ERE has no `\b` and `-E` silently matches nothing)
  finds only DR-002 and DR-023, plus rows that `just render` derives from
  the predecessors' own `enacted_in` and `applies`: the index and the
  artifact table in `.meta/decisions.md`, and Articles 1 and 12's "Where
  this came from" in `.meta/charter.md`, which list DR-048 beside DR-328.
- A grep of S1 to S6 for Actor, Agency, Remit, Securable, Personality,
  Challenge, coder, reviewer, pull request and PR First finds them only in
  `context:`, where they say what was replaced.
- The benchmark's hit@5 and MRR are no lower than in step 1.

### Risks

- **Numbering:** a sibling part that lands first takes DR-323 onwards.
  Renumber at implementation time from the record on the branch, and do not
  hard-code numbers in citations until the files exist.
- **Words that are still current:** "Goal" and "Job" are banned as removed
  classes, but PersonaGoal, "END goal" and Job to be Done are current. The
  word-check grep has to tell them apart.
- **Ranking:** S4 replaces DR-015 as an expected result for "which languages
  can a new portfolio choose". The search indexes every status, so DR-015
  still competes for that query. If MRR drops, check whether S4's prose ranks
  below its predecessor's before touching anything else.
- **Partial supersession:** DR-059 notes that supersession is usually
  partial. S5 must state all five predecessors' surviving rules, or a reader
  of the record loses one.

## Left as is

- **DR-002** (Rough in an ontology of work): "ontology of work" is still
  what the repository calls `.meta/work/` and what `AGENTS.md` asks the
  vocabulary to come from. The `work_ontology.md` it names was a file of
  its day, and DR-023 already records dropping it.
- **DR-023** (The work ontology splits into seven modules): it names no
  removed class, and `.meta/work/` still holds seven modules.

## Benchmark

| | hit@5 | MRR |
|---|---|---|
| Before the first record changed | 17/18 | 0.55 |
| After | 17/18 | 0.55 |

## What the next reader should know

- Eleven records are now `SUPERSEDED`, the first in the record: DR-003,
  DR-006, DR-007, DR-008, DR-015, DR-019, DR-020, DR-021, DR-031, DR-039 and
  DR-048. Their successors are DR-323 to DR-328, mapped in the plan's table.
  The old files changed only in `status` and the added `superseded_by`.
- The first draft of DR-328 also restated that a retired Article number is
  a hole. That pushed DR-328 above DR-085 for the benchmark query "an old
  rule no longer applies, how is it retired" and dropped MRR to 0.54. The
  sentence was not DR-048's decision (the Charter's own header holds it), so
  it was cut, and MRR returned to 0.55. A successor that restates
  neighbouring rules competes with them in search.
- Article 8's example in `charter.yaml` said reification "was reverted in
  DR-008". A renumber would have made it false, since DR-324 reverted
  nothing, so it now says the revert happened and DR-324 keeps it out.
- The plan said Article 1 was a hole. It is live (the Ratchet), so DR-328
  keeps `applies` on Articles 1 and 12, as DR-048 did.
- Personality residue outside this part's records is filed as
  `issues/backlog/remove-personality-residue.md`.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/trim-decision-records-002-048.md` and committed it. I left `difficulty: medium` unchanged: it covers thirteen records, each needing a judgment call and a small change. That fits in one piece and doesn't need the developer to check it by hand.
>
> What I changed:
>
> - **How a change to an old record is written:** I looked up the format in `.meta/work/decisions.yaml` and the supersession check in `.meta/checks/graph/record.py`. A superseded record gets `status: SUPERSEDED` and `superseded_by:`, and its successor lists it under `supersedes:`. A withdrawn record gets `status: WITHDRAWN` and `withdrawn_because:`, as DR-036 does. No record in the repository is marked `SUPERSEDED` yet, so this part will be the first to use that status.
> - **Citations from other files:** besides other Decision Records, nine files cite records from this list, including `charter.yaml`, `disciplines.yaml`, `purpose.yaml`, `personas.yaml`, one `.apm` instruction file and `benchmark.py`. The issue now names them and says each citation moves to the successor, or is dropped if the record is withdrawn.
> - **Out of scope:** later Decision Records that cite these (DR-017, DR-087, DR-205 and others) stay as written, because records are never rewritten. Also out are the sibling parts from DR-065 onwards and any change to the schema, the ontology or the checks.
> - **Done when:** I removed `just gate` and replaced it with four things anyone can check:
>   - every listed record is superseded, withdrawn, or listed under `## Left as is` with a reason;
>   - each successor names its predecessors and never relies on a removed class or on PR First;
>   - no file outside the decision records and `issues/` cites a retired record;
>   - `.meta/decisions.md` has been re-rendered.
>
> The sibling issues (065–177, 179–217, 218–272) still name `just gate` as their test, but I didn't touch them because they're outside this turn.

> **secondary, backlog turn 2**
>
> I made one change to the issue file and committed it. Everything else my partner wrote holds up, and `difficulty: medium` stays.
>
> **What I checked against the repository:**
> - **Record format:** the superseded and withdrawn format matches `.meta/work/decisions.yaml`.
> - **Checks:** `.meta/checks/graph/record.py` checks the direction of each supersession, and it rejects a record that is both withdrawn and superseded.
> - **Citing files:** searching the repository finds the same nine files the issue lists as citing these records.
>
> **What I added** (commit `f3d6e83`):
> - **Generated copies:** the issue says generated files are re-rendered, but it didn't say which ones. I named them: `.meta/charter.md`, `.meta/disciplines.md`, `.meta/decisions.md`, `.agents/rules/` and the copies under `apm_modules/`.
> - **The benchmark citation:** `.meta/lib/search/benchmark.py` doesn't cite DR-015 in prose. It lists `work:decision/015` as one of a search query's expected results. The issue now says that result moves to the successor record that carries DR-015's content, and that the search benchmark must score no worse than before.

> **primary, backlog turn 3**
>
> I kept my partner's additions and added one line to the issue's "Done when" list. `difficulty: medium` stays.
>
> **Their additions are correct.** In `.meta/lib/search/benchmark.py` (line 70), `work:decision/015` is one of a search query's expected results. Both `.agents/rules/` and `apm_modules/` hold generated copies that cite these records, so those copies need re-rendering.
>
> **What was missing:** their rule that the search benchmark must score no worse than before was only under "Wanted", so nothing in the done conditions would catch a regression. I added it as the last "Done when" item. That's commit `4c13985`.

> **secondary, backlog turn 4**
>
> I made the benchmark condition my partner added to "Done when" measurable, and committed it as `df5d21f`. Nothing else in the issue changed, and `difficulty: medium` stays.
>
> The condition said the benchmark must score "no worse than before", without saying which figure to compare. The benchmark prints four figures: hit@1, hit@5, hit@10 and MRR (how high, on average, the expected result ranks). Only the hit@5 count decides whether it passes: at least 15 of 18 queries must find an expected result in their top five. MRR is the clearest sign of a ranking getting worse.
>
> The condition now says:
> - **How to run it:** the benchmark runs through the `/search` skill's `--benchmark` mode.
> - **What must hold:** the hit@5 count and the MRR are each no lower than before the first record changed.
> - **What to record:** both pairs of figures, before and after, go in the issue file.

> **primary, backlog turn 5**
>
> I'm leaving the issue as it stands. My partner's change is accurate and nothing else needs adding:
>
> - **How it runs:** the `/search` skill's `--benchmark` mode runs `.meta/search.py --benchmark` against the 18 queries in `.meta/lib/search/benchmark.py`.
> - **What it reports:** it prints a hit@5 count and an MRR. The run passes only when at least 15 of the 18 queries find an expected result in their top five.
>
> So "hit@5 count and MRR no lower than before, with both pairs of figures recorded in the issue" is a condition anyone can check. The issue is ready to plan, and `difficulty: medium` stays.

> **primary, todo turn 1**
>
> I wrote the plan under `## The plan` in `issues/todo/trim-decision-records-002-048.md` and committed it as `74a17d0`. Nothing is implemented yet.
>
> **What I read:** all thirteen records, the current ontology in `.meta/work/`, the citing files, and the supersession check.
>
> **What the ontology has today:** Capability, Role (which has a `communication_style`), Persona, PersonaGoal, JobToBeDone, Article (with `example` and `falsifier`, but no `origin`), Discipline and Issue. It no longer has Goal, Agency, Challenge, Personality, Actor, Remit, Securable, Permission, AuditRecord or BOM.
>
> **Verdict for each record:**
>
> | Record | Verdict | Why |
> |---|---|---|
> | DR-002 | Left as is | "Ontology of work" is still what the repository calls `.meta/work/`. |
> | DR-023 | Left as is | It names no removed class, and the ontology is still seven modules. |
> | DR-003 | One successor | The rule stands; its SMART Goal and Definition of Done examples get current ones. |
> | DR-006 and DR-008 | One shared successor | It keeps the rule on how skills and tools compose, and DR-008's "coordinate system invented ahead of its consumer" line, which the Nothing Unconsumed discipline quotes. |
> | DR-007 | One successor | APM stays the packaging target, argued without Securable or Remit. |
> | DR-015 | One successor | Only the example vocabulary list changes. |
> | DR-019, DR-020, DR-021, DR-031 and DR-039 | One shared successor | They form one chain: a Persona, its tiered goals, and the Job to be Done that names the Persona and serves one of its goals. |
> | DR-048 | One successor | The Article and Charter names stand, argued without `origin` or Personalities. |
>
> That makes six new records. None of the thirteen is withdrawn.
>
> **Order of the steps:**
> 1. Run the search benchmark and record its hit@5 and MRR.
> 2. Write the six successors.
> 3. On each old record, change only its status and add the link to its successor.
> 4. Move the citations in the nine files the issue lists, including the benchmark's expected result for DR-015.
> 5. Re-render the generated pages and recompile the APM output.
> 6. Run the benchmark again and record the figures.
>
> **Tests:** the supersession and citation checks pass. A search shows no file outside the decision records, `issues/` and generated output still cites the retired numbers. A word search of the six new records finds no removed class. The benchmark scores no lower than before.
>
> **Risks the plan names:**
> - **Numbering:** the successors would be DR-323 to DR-328 today, but a sibling part that lands first would take those numbers.
> - **Word overlap:** "Goal" and "Job" are removed classes, but "PersonaGoal", "END goal" and "Job to be Done" are current, so the word check has to tell them apart.
> - **Ranking:** the search indexes superseded records too, so DR-015 will compete with its own successor in the benchmark.
> - **Lost rules:** the five-record successor must restate every rule that still stands, or a reader of the record loses one.

> **secondary, todo turn 2**
>
> I kept my partner's six successor records and their verdict for each record, but three parts of the plan didn't match the code. I corrected them in the plan and committed it as `cb57fd2`. Nothing is implemented yet.
>
> - **The render step:** `just render` is enough on its own, because its `apm_primitives` writer regenerates `.meta/.apm/instructions/nothing-unconsumed.instructions.md` from `disciplines.yaml`. That file is generated, so it is never edited by hand. `.agents/` and `apm_modules/` are git-ignored, so they are not part of the change. The plan's extra `just apm` step is gone.
> - **The check on the two supersession fields:** the plan said the checks in `.meta/checks/citations/` confirm that `superseded_by` and `supersedes` agree from both ends. No check does that. `claims.py`'s `stated relations` check only confirms that a supersession stated in prose (one record named as superseding another) is also recorded in those fields. The plan now says:
>   - **Read both fields by hand:** every `superseded_by` on an old record must be listed in its successor's `supersedes`, and the reverse.
>   - **Value form:** a reference is written `work:decision/019`. No record uses `supersedes:` yet, so there is no example in the repository to copy.
>   - **The prose check:** it is listed as a test of its own.
> - **The leftover-citation search:** "grep outside generated output" is now an exact `git grep` command that covers both `DR-0nn` and `decision/0nn` and searches only files git tracks. It should find only DR-002, DR-023 and the old records' rows in `.meta/decisions.md`.
>
> I also gave step 1 the full benchmark command, taken from the `/search` skill.

> **primary, todo turn 3**
>
> I kept my partner's corrections and fixed one wrong statement in the plan, committed as `30109b0`.
>
> **What checks out:**
> - `just render` regenerates the Nothing Unconsumed instruction file through its `apm_primitives` writer.
> - `.agents/` and `apm_modules/` are git-ignored, so they aren't part of the change.
> - No check confirms that `superseded_by` on an old record and `supersedes` on its successor agree. `claims.py` only checks that a supersession stated in prose is also recorded in one of those fields.
> - The exact `git grep` command for leftover citations is a better test than my vaguer wording.
>
> **What I fixed:** the plan said no record uses `supersedes:` yet. That's wrong: ten records already use it, DR-059 among them. The field no record has used yet is `superseded_by:`, so these will be the first records with `status: SUPERSEDED`. I've noted that in the plan and pointed to DR-059's entry as the example to copy.

> **secondary, todo turn 4**
>
> I'm changing nothing this turn. My partner's correction is right. I wrongly said no record uses `supersedes:` because my search only matched the field at the start of a line, and in these records it is indented. DR-059 lists `- work:decision/049` under it.
>
> The field is in more records than my partner counted: 13, not 10. The plan doesn't depend on that number. No record has `superseded_by:` yet, so the plan is right that these will be the first records with `status: SUPERSEDED`. The plan stands as it is.

> **primary, in-progress turn 1**
>
> I've implemented the plan and committed it as `9e368d1` and `f7e9efa`. `just gate meta` passes, and the search benchmark is unchanged: hit@5 17/18 and MRR 0.55, both before and after.
>
> **Six new records** replace the stale reasoning:
>
> | New record | Replaces | What it keeps |
> |---|---|---|
> | DR-323 | DR-003 | The ontology is LinkML. Its examples are now a required `serves` on a Job to be Done and the tool-atomicity rule. |
> | DR-324 | DR-006, DR-008 | A skill composes tools, a tool is atomic, and nothing more is modelled until something uses it. It carries DR-008's "a coordinate system invented ahead of its consumer is one that will be wrong", which the Nothing Unconsumed discipline quotes. |
> | DR-325 | DR-007 | APM packages what an agent reads or runs. Schemas, checks and tool permissions stay out. |
> | DR-326 | DR-015 | The rule about the two languages, with a current list of the imported words. |
> | DR-327 | DR-019, DR-020, DR-021, DR-031, DR-039 | A Persona, its tiered goals, and a Job to be Done that names the Persona and serves at least one of its END goals. |
> | DR-328 | DR-048 | The Charter and Article names, argued from each Article's `example` and `falsifier`. |
>
> **The old records:** the eleven above changed only in `status: SUPERSEDED` and the added `superseded_by`. They are the first superseded records in the repository. DR-002 and DR-023 are listed under `## Left as is` with their reasons. None was withdrawn.
>
> **Citations** moved to the new records in eight source files, including the benchmark's expected result for DR-015. Then I re-rendered the generated pages.
>
> **Where the plan was wrong (corrected in the issue):**
> - **The leftover-citation search:** `git grep -E` with `\b` silently matches nothing, so the plan's command could never fail. It now uses `-P`.
> - **Article 1:** the plan called it a hole, but it is live, so DR-328 keeps `applies` on Articles 1 and 12.
> - **Generated pages:** they still list the old records beside their successors, because those rows come from the old records' own fields, which can't be edited. The test now says to expect them.
>
> **Ranking:** my first draft of DR-328 also restated that a retired Article number is a hole. That pushed it above DR-085 for the benchmark query "an old rule no longer applies, how is it retired", and MRR dropped to 0.54. The sentence wasn't DR-048's decision, so I cut it, and MRR returned to 0.55.
>
> **Other fixes:** Article 8's example said reification "was reverted in DR-008". Pointing that at DR-324 would have made it false, so I reworded it. I also reworded two example sentences in the issue file that the `stated relations` check read as real supersessions.
>
> **Left for later:** three places still name the removed Personality class: an undefined `personality` field on Persona, an id that nothing defines in `structure.yaml`, and a row in `.meta/.apm/README.md`. They're outside this issue, so I filed them as `issues/backlog/remove-personality-residue.md`.

> **secondary, in-progress turn 2**
>
> I'm leaving my partner's work as it is. It meets the issue's done conditions, and `just gate meta` passes, including the checks on supersession, references, served goals and the issue board.
>
> - **The two supersession fields agree:** the eleven old records' `superseded_by` and the `supersedes` lists on DR-323 to DR-328 match in both directions. No check compares them, so I compared them myself.
> - **Leftover citations:** the `git grep -P` search turns up the thirteen numbers only in the generated pages, `.meta/decisions.md` and `.meta/charter.md`. Those pages rebuild their lists from the old records' own fields, and the plan already says to expect them there.
> - **Removed classes:**
>   - Actor, Agency, Remit, Securable, Personality and Challenge appear in DR-323 to DR-328 only in `context:`, to say what was replaced.
>   - Goal and Job appear outside `context:` only as "END goal" and "Job to be Done", which are current terms.
>   - No new record names a coder, a reviewer, a pull request or PR First.
> - **No rule was lost:** I checked DR-327 against DR-020, DR-031 and DR-039. It keeps each rule that still stands: the six PersonaKinds, that an END goal is specific with no deadline, that `serves` is required, and that the `served goals` check rejects a goal of the wrong tier or another Persona's.
> - **The claims in the new records are true:**
>   - **DR-323:** the rule that a tool composes nothing exists in `.meta/work/authority.yaml`.
>   - **DR-325:** `.meta/.apm/` does hold `agents/` and `hooks/`.
> - **Benchmark:** my partner recorded hit@5 at 17/18 and MRR at 0.55, the same before and after. I didn't re-run it.
>
> My partner also filed `issues/backlog/remove-personality-residue.md` for three places outside this issue that still name Personality. It has no "Done when" section yet; grooming will give it one.
