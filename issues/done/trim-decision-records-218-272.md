---
difficulty: medium
parent: trim-kept-decision-records
---

# Trim PR First residue from DR-218 to DR-272

One part of `trim-kept-decision-records`: these kept Decision Records still
carry some of PR First, its GitHub choreography or the taxonomy of work in
their prose: DR-218, DR-222, DR-229, DR-239, DR-241, DR-259, DR-262, DR-268,
DR-270 and DR-272.

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

Mark a record the way the earlier parts did: `status: SUPERSEDED` with
`superseded_by: work:decision/<n>`, or `status: WITHDRAWN` with a
`withdrawn_because:` sentence naming what is gone.

DR-259 and DR-272 are cited by `CLAUDE.md` (`AGENTS.md`) and
`template/AGENTS.md`; where one is superseded, those citations move to its
successor.

## Out of scope

Records outside this part, including DR-244, which sits beside DR-239 in
the Specialization files, and DR-329, which sits beside DR-259 in
`justfile.py`. Changing any rule's substance: a successor restates a rule
from current ground, and does not widen or narrow it.

## Done when

- None of the ten records is still `ADOPTED` unless it is listed under
  `## Left as is` with a reason.
- Each superseded record names a successor that exists, and each successor
  carries no Actor, Job, Remit, Goal, Personality, Securable, coder,
  reviewer, workflow, pull request, GitHub Actions runner, channel
  (`.meta/say/`) or `check_pr` as part of its rule or its argument.
- Outside `.meta/assertions/decisions/` and `issues/done/`, no source file
  cites a superseded or withdrawn record where its successor is meant. The
  one exception is the `/search` skill's text in
  `.meta/assertions/imported/structure.yaml` and its rendered copies (see
  `## The plan`).
- The generated files (`.meta/decisions.md`, `SPECIALIZE.md`, the compiled
  skills) are re-rendered, not hand-edited, and list the new records.

## The plan

Read against the tree as it is. Gone: `.github/workflows/` (all of it,
including `coder.yml`, `gate.yml`, `dogfood.yml`, `test-specialization.yml`
and `release.yml`), `.meta/arc/` and the ARC runner image, `.meta/say/` and
the channel, `check_pr.py` and `evaluate_pr`, `.meta/checks/probes/loops/`,
`.meta/dogfood.py`, DR-147, DR-221, DR-240 and DR-252 (and with DR-252 its
three planes), and the Written Decisions steps that DR-222 added (the
Discipline now says only "Status carries the rest: recommended, or in
force"). Still there: Article 23 and Observed Failure's *Watch refusals
stand aside* step; `.meta/test_specialization.py`, its fixtures and `just
test-specialization`; the `inline python` check (`no_inline_python`), which
scans the `justfile` and the shell scripts under the tree; the root
`justfile`, whose recipes take flags, subcommands and identifiers, and the
`/wikisplain` and `/search` skills; `MUTMUT_MAX_CHILDREN` and
`CARGO_MUTANTS_JOBS` capped at eight in the seed gates; the Python 3.13
guard in `.meta/check.py`, `meta interpreter`, and the prerequisite in
`README.md`; and packages in place of modules under `.meta/checks/`
(`probes/tools/`, `probes/files/`, `citations/`, `graph/`, `files/`).

| Record | Verdict | Why |
|---|---|---|
| DR-218 | Successor S1 | The rule stands: an imported module under `.meta/` becomes a package of its own name in place, whose `__init__` imports its modules. Its one example, `probes/loops.py`, is gone, and its consequences name `check_pr.history.md` and `say/move.history.md`. Use a current package (`checks/citations/` or `checks/probes/tools/`) as the example; carry all twenty-one `enacted_in` artifacts forward. |
| DR-222 | Withdraw | It decided that only the developer adopts a decision and that a pull request carrying one waits for it. The Discipline steps it enacted are gone, the pull request is gone, and in the pair loop a seat writes a settled question as `ADOPTED` and commits it with the change (`AGENTS.md`, Conventions); a desk check (`developer` difficulty) is how the developer holds a change back now. Nothing in the tree still follows it. |
| DR-229 | Successor S2 | Article 23 and the widening of Observed Failure stand. Argue them from what a seat does in its turn, not from five Claims a coder made about pull requests, `gh pr view`, `evaluate_pr` and `channel.gh`; restate the rejected "reviewer as control" alternative as the second seat, and drop "a gate sees a pull request". The falsifier's refusal clause becomes any refusal probe, not one under `.meta/say/`; A22's "unprivileged Job" becomes what A22 says now. |
| DR-239 | Successor S3 | The rule stands: `.meta/test_specialization.py` runs Specialization end to end into a scratch repository with the fixtures under `.meta/fixtures/specialization/`, exposed as `just test-specialization`. Drop `.meta/dogfood.py`, `just dogfood` and the three workflow consequences; there is no CI. (Corrected in implementation: the runner is the gate of the Project `specialization` in `.meta/assertions/structure.yaml`, so the successor says so.) |
| DR-241 | Successor S4 | The ban on inline Python stands for what `no_inline_python` scans today: the `justfile` and shell scripts. Drop the GitHub Actions workflows, composite actions under `.meta/actions/` (gone), `coder.yml`, `.meta/say/on` and `check_pr.py --unresolved-count`. The rationale's "fleet of agents" becomes the pair. |
| DR-259 | Successor S5 | The contract stands: root recipes take only flags, subcommands and atomic identifiers, and authoring that takes prose goes to a skill (`/wikisplain`). Argue it from the operator surface `just --list` shows (DR-329), not from DR-252's three planes, the Attested Mutation Plane, the GitHub Inspection Plane, or the `pr` and `merge-manager` recipes. |
| DR-272 | Successor S5 | Same contract, applied to search (`/search`). One successor covers DR-259 and DR-272, since `AGENTS.md` cites them together and DR-272 exists only to finish what DR-259 miscounted. Carry both records' `enacted_in`, the `/search` skill's invocation and `build.py`'s warning forward; drop "Option A adopted by solo (@caindy) on the Challenge". |
| DR-262 | Successor S6 | The cap stands: both seed gates default to at most eight mutation workers, with `MUTMUT_MAX_CHILDREN` and `CARGO_MUTANTS_JOBS` to override. Argue it from gates running beside the pair loop on one machine, not from ARC runner pods on a 24-vCPU host, DR-147, coder/reviewer loop sessions or `gate.yml`. Drop the "beyond 120 seconds" half of the falsifier unless something still measures it. |
| DR-268 | Successor S7 | The rule stands: tooling keeps `#!/usr/bin/env python3`, and Python 3.13 is a prerequisite asserted at the front door (`check.py`'s guard, `meta interpreter`, `README.md`). Drop the runner image half (`.meta/arc/Dockerfile`), the channel verbs and `check_pr.py` from the shebang list (count today's shebangs), and the image clause of the falsifier. (Corrected in implementation: `SPECIALIZE.md` states no Python version, so the successor drops that consequence and `work:artifact/specialize` from `enacted_in`; see `issues/backlog/specialize-python-prerequisite.md`.) |
| DR-270 | Left as is | `PR First's eighth step` is the context's account of how citations drifted before steps had names, which is history and still true, and `work:discipline-step/pr-first/request-review` illustrates a rejected alternative whose reason (a raw CURIE in prose is jarring) holds whatever the step. The rule (named steps, slug CURIEs, ordinals refused by `claims.py`) stands as written, as DR-179 did in the last part. |

S1 to S7 become the next free numbers in the order of this table. Whoever
implements re-reads each record before writing its successor; a verdict that
turns out wrong moves in this table, with the reason.

### Steps

1. Write S1 to S7, each `status: ADOPTED`, with `supersedes:`, the
   predecessors' `applies` and `enacted_in` carried forward, a `context:`
   saying what it replaces, and a rationale argued from the current tree.
   Apply `/technical-writing`. Where a predecessor leans on a record that
   the earlier parts superseded, the successor cites the record in force:
   S1 cites DR-342 (for DR-209) and DR-344 (for DR-217); S5 drops DR-272's
   `applies: work:decision/259`, since it supersedes both, and cites DR-337
   (for DR-194) and DR-329 in place of DR-106 and DR-252; S2 cites DR-335
   (for DR-190); S3 cites DR-341 (for DR-204) and DR-329 (for DR-106). A
   successor cites no record that is gone (DR-147, DR-221, DR-240, DR-252).
2. On each superseded record change only `status: SUPERSEDED` and add
   `superseded_by:`; on DR-222 change only `status: WITHDRAWN` and add
   `withdrawn_because:`.
3. Move citations, editing sources only (not `apm_modules/`, `.agents/`,
   `.claude/` or other compiled copies), and keeping the possessive
   (`stereorepo's DR-nnn`) in files a portfolio copies:
   - S1 (DR-218): `.meta/checks/probes/tools/__init__.py`,
     `.meta/checks/probes/files/__init__.py`, `.meta/checks/graph/__init__.py`,
     `.meta/checks/files/__init__.py`, `.meta/checks/citations/__init__.py`
     and `slots.py`, `.meta/lib/dereference/reading.py`.
   - S2 (DR-229): no hand-written source cites it. `.meta/charter.md`
     lists it under "Where this came from", but that line is rendered from
     `enacted_in` (`record.accounted_by`), so carrying `meta-charter` forward
     and re-rendering is the whole move.
   - S3 (DR-239): `justfile` (through `.meta/lib/render/writers.py`, which
     writes it), `.meta/test_specialization.py`,
     `.meta/checks/probes/tools/test_specialization.py`,
     `.meta/fixtures/specialization/README.md`.
   - S4 (DR-241): `.meta/checks/files/inline_python.py`,
     `.meta/checks/files.history.md` only if the line is not history.
   - S5 (DR-259, DR-272): `AGENTS.md`, `template/AGENTS.md`,
     `.meta/checks/files/justfile.py`, `.meta/checks/probes/surface.py`,
     `.meta/lib/render/skills.py`, and the backlog Issue
     `issues/backlog/bootstrap-audit.md`, which gives both as the reason a
     recipe takes atomic identifiers only.
   - S7 (DR-268): `.meta/check.py`, `.meta/checks/files/python.py`,
     `README.md`.
   - **Not moved:** the `/search` skill's text in
     `imported/structure.yaml`, which cites DR-272. `just render` writes it
     to tracked files under `.claude/skills/`, which the seats' sandbox
     denies, as the last part found. Add this citation to
     `issues/backlog/technical-writing-skill-successor-citations.md`.
   - Then grep each superseded or withdrawn number again for anything this
     list missed.
4. Run `just render`, then check that `git status .claude/` is clean.
5. Fill in `## Left as is`.

### Tests

- `decision supersession` passes: each `superseded_by` names a later record
  that lists the old one under `supersedes:`.
- `enacting citations` passes, which is why each successor carries its
  predecessors' `enacted_in` whole.
- `cited decisions` passes, so every new citation resolves and copied files
  keep the possessive.
- `rendered prose` passes, and `just render` leaves the tree unchanged.
- A grep of each successor for the words in Done when finds them only in a
  `context:` that says what was dropped.

### Risks

- **The sandbox.** Nothing in this change may alter a `.claude/skills/`
  page. Step 4 is the guard.
- **`stated relations` reads this file.** Name each successor beside its own
  predecessor, never as a range, and never quote a wrong pairing. The
  S-labels are why this plan names no new number.
- **Probe literals.** `justfile.py` prints DR-259 in a finding message,
  and no probe asserts that text (a grep of `.meta/checks/probes/` finds
  DR-259 only in `surface.py`'s docstrings), so the message can move to S5.
  Grep the probes again for each other number before changing a message.
- **`path:line` claims.** The gate checks a `path:line` against the file, so
  this file uses paths only.

## Left as is

- **DR-270:** see the table.

## What landed

S1 to S7 are DR-345 (for DR-218), DR-346 (for DR-229), DR-347 (for
DR-239), DR-348 (for DR-241), DR-349 (for DR-259 and for DR-272), DR-350
(for DR-262) and DR-351 (for DR-268). DR-222 is withdrawn. Every citation
in the step 3 list moved; what still cites an old number is the `/search`
skill text (DR-272, now on
`issues/backlog/technical-writing-skill-successor-citations.md`) and
`.meta/checks/files.history.md` (DR-241), which is history. `just render`
left `.claude/` unchanged.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/trim-decision-records-218-272.md` and committed it. I left `difficulty: medium` as it was.
>
> **Changes to the issue:**
> - **Done when** no longer names `just gate`. Done now means:
>   - none of the ten records is still `ADOPTED` unless it is listed under "Left as is" with a reason;
>   - no successor rests on anything that has been removed;
>   - citations point to the successors;
>   - the generated files are re-rendered, not edited by hand.
> - **Out of scope** now also names DR-244 and DR-329, which sit beside records in this part, and rules out changing what any rule says.
> - **The plan** lists what is gone from the tree and what is still there, then gives a verdict for each record:
>   - **New records replace seven of the old ones.** DR-218, DR-229, DR-239, DR-241, DR-262 and DR-268 each get their own new record. DR-259 and DR-272 share one, since `AGENTS.md` cites them together and DR-272 only finishes a job DR-259 miscounted.
>   - **DR-222 is withdrawn.** It said only the developer can adopt a decision and that a pull request carrying one must wait. The Discipline steps it added are gone, and in the pair loop a seat writes a decision as `ADOPTED` itself. This is the one verdict that goes beyond tidying, so it's worth a second look.
>   - **DR-270 is left as is.** Its mention of PR First is a past example of the problem it fixed, and the reason it rejected the alternative still holds. The last part treated DR-179 the same way.
> - **Steps, tests and risks** follow the pattern the last part used. For each new record they list the files whose citations should move to it. The DR-272 citation in the `/search` skill text stays where it is and goes to the existing developer Issue instead, because the seats' sandbox can't write the rendered copies under `.claude/skills/`. The tests are named checks and greps, not a gate run.
>
> The file changed on disk while I was editing it. I took that version as current and didn't check what had changed.

> **secondary, backlog turn 2**
>
> I kept my partner's groom and left `difficulty: medium` as it was. The previous part did about as much work in one piece. To check the plan, I grepped the tree for every citation of the ten records. It had missed two, and I've added both to the plan and committed the change:
>
> - **DR-229:** The plan said nothing outside the records cites it, but `.meta/charter.md` lists it under "Where this came from". That line is generated from each record's `enacted_in` list (the files that carry the decision out). So the new record that replaces DR-229 only has to carry the charter forward in that list, and re-rendering moves the citation. No one edits the charter by hand.
> - **DR-259 and DR-272:** `issues/backlog/bootstrap-audit.md` cites both, so it now sits on the list of files whose citations move to the record that replaces them.
>
> Every other citation the grep found is either already in the plan's lists or in a generated file that re-rendering updates. That includes the copy of the `/search` skill under `.meta/.apm/skills/`, which the plan already leaves for the separate backlog Issue on skill citations.

> **primary, backlog turn 3**
>
> I checked both of my partner's additions against the tree and changed nothing.
>
> - **DR-229:** `.meta/charter.md` does cite it, in the "Where this came from" line, and that line is generated from each record's `enacted_in` list. So the record that replaces DR-229 only has to carry the charter forward in that list, and re-rendering adds it. One detail: the line still lists DR-190 and DR-216 next to the records that replaced them (DR-335 and DR-343). So DR-229 will stay on that line beside its successor rather than drop off it. That matches what the last part left behind, so nothing needs to change.
> - **DR-259 and DR-272:** `issues/backlog/bootstrap-audit.md` cites both, so it belongs on the list of files whose citations move to the record that replaces them.
>
> `difficulty: medium` stays.

> **primary, todo turn 1**
>
> The issue already had a full plan from grooming (verdicts, steps, tests and risks), and reading the code held it up. I added two things and committed them:
>
> - **Which records the new ones cite (step 1).** Some old records rely on records that earlier parts have since replaced, so the new records should cite the replacements:
>   - The new record for DR-218 cites DR-342 instead of DR-209, and DR-344 instead of DR-217.
>   - The one record replacing DR-259 and DR-272 cites:
>     - DR-337 instead of DR-194;
>     - DR-329 instead of DR-106 (I confirmed DR-106 has been replaced) and the deleted DR-252.
>
>     It also drops DR-272's link to DR-259, since it replaces both.
>   - No new record cites a record that has been deleted: DR-147, DR-221, DR-240 or DR-252.
> - **The DR-259 citation in a check's error message (risks).** `.meta/checks/files/justfile.py` prints DR-259 in a message the check reports. I grepped the tests for that check: DR-259 appears only in the docstrings of `surface.py`, and no test compares that message. So it can safely change to the new record.
>
> I also confirmed two things the plan depends on. Withdrawing a record with a stated reason is a supported field that DR-084 already uses. And DR-344 is the highest record number, so the seven new records start at DR-345.

> **secondary, todo turn 2**
>
> I kept my partner's plan and added the citations step 1 had missed, then committed.
>
> Step 1 of the plan lists, for each new record, which current records it should cite in place of ones that earlier parts have replaced. I checked every record that DR-218 through DR-272 cites against the list of replaced and withdrawn records. My partner's list was right as far as it went, but two of the new records were missing:
>
> - **S2, which replaces DR-229:** DR-229 cites DR-190, which DR-335 has replaced, so S2 cites DR-335.
> - **S3, which replaces DR-239:** DR-239 cites DR-204, which DR-341 has replaced, and DR-106, which DR-329 has replaced. S3 cites DR-341 and DR-329.
>
> None of the other records these ten cite (DR-026, DR-101, DR-144, DR-177, DR-187 and DR-210) has been replaced, so nothing else needs to move. I also confirmed that DR-344 is the highest number, so the seven new records start at DR-345.

> **primary, todo turn 3**
>
> I checked my partner's additions and changed nothing.
>
> - **The two new citations are right.** DR-190 and DR-204 are both marked superseded, and DR-335 and DR-341 each list them as the record they replace. So the record replacing DR-229 should cite DR-335, and the one replacing DR-239 should cite DR-341.
> - **The other six records really are still in force:** DR-026, DR-101, DR-144, DR-177, DR-187 and DR-210 are all still `ADOPTED`.
>
> One oddity, outside this issue: DR-259 claims to supersede DR-187, but DR-187 is still marked `ADOPTED`. The new record replacing DR-259 and DR-272 doesn't need to settle that, so I've left the plan as it is.

> **primary, in-progress turn 1**
>
> I've implemented the plan and committed it. `just gate meta` passes, including the checks on supersession, withdrawn records, cited decisions, rendered prose and the issue file itself. No other Project's directory was touched, so no other gate applied.
>
> **The records:**
> - **New records DR-345 to DR-351 replace eight old ones:**
>   - DR-345 replaces DR-218 (an imported module becomes a package in place). Its example is now `checks/citations/`.
>   - DR-346 replaces DR-229 (Article 23).
>   - DR-347 replaces DR-239 (the end-to-end Specialization test).
>   - DR-348 replaces DR-241 (no inline Python), limited to what the check scans now: the `justfile` and shell scripts.
>   - DR-349 replaces both DR-259 and DR-272 (recipes take only flags, subcommands and identifiers; tools that take prose go through skills).
>   - DR-350 replaces DR-262 (at most eight mutation-testing workers). It argues from gates running beside the pair loop on one machine.
>   - DR-351 replaces DR-268 (keep `python3` shebangs; check for Python 3.13 when a run starts).
>
>   Each old record changed only in its status and the link to its replacement. Each new record keeps its predecessor's list of files that carry it out. Where a new record names something removed (the channel, `check_pr`, GitHub, coder and reviewer), it is only in the opening paragraph, saying what was dropped.
> - **DR-222 is withdrawn**, with a reason: the steps it added and the pull request are gone, and in the pair loop a seat records a decision as `ADOPTED` itself.
> - **DR-270 is left as is**, and the issue file says why.
>
> **Citations:** every file on the plan's list now cites the new records, including `AGENTS.md`, `template/AGENTS.md` and `issues/backlog/bootstrap-audit.md`. `just render` regenerated `.meta/decisions.md`, `.meta/charter.md` and `justfile`, and left `.claude/` unchanged. Two files still cite an old number:
> - The `/search` skill's text still cites DR-272, because the seats' sandbox can't write the copies under `.claude/skills/` that rendering it would change. I added it to the existing developer Issue `technical-writing-skill-successor-citations.md`.
> - `.meta/checks/files.history.md` still cites DR-241, because that line is history.
>
> **Where the plan was wrong (corrected in the issue file):**
> - **DR-239:** the plan said nothing runs the Specialization test except by hand. In fact `.meta/test_specialization.py` is the gate of the Project `specialization`, and DR-347 says so.
> - **DR-268:** it claimed `SPECIALIZE.md` states the Python 3.13 requirement. It doesn't, so DR-351 drops that claim and no longer lists `SPECIALIZE.md` among the files that carry it out. Adding the requirement is new work, so I wrote it up as `issues/backlog/specialize-python-prerequisite.md` rather than doing it here.
>
> The issue file has a new "What landed" section that pairs each new record with the record it replaces.

> **secondary, in-progress turn 2**
>
> I checked my partner's implementation against the tree, and it holds up. I made one small edit and committed it, and `just gate meta` passes afterwards.
>
> **The edit:** DR-349 is the new record that replaces DR-259 and DR-272. The plan said it should cite DR-337 in place of DR-194, which DR-337 replaced, but the record never mentioned DR-337. It now names DR-337 as the search method the `/search` skill runs. Re-rendering after the edit changed no other file.
>
> **What I checked and left alone:**
> - **Removed things are mentioned only as history.** I searched the seven new records (DR-345 to DR-351) for the words the issue rules out, such as the channel, `check_pr`, coder, reviewer, pull request, GitHub and workflow. Each hit is in a record's opening paragraph, saying what was dropped. "Runner" in DR-347 means the test script, in its ordinary sense.
> - **Facts the new records state are true:**
>   - Observed Failure has both steps DR-346 names: *Check claims before asserting* and *Watch refusals stand aside*.
>   - Exactly eight scripts under `.meta/` carry a `python3` shebang, as DR-351 says.
>   - `SPECIALIZE.md` states no Python version. That confirms my partner was right to remove it from the files DR-351 says carry it out, and to file adding the requirement as a separate backlog Issue.
> - **Nothing in the old DR-272 was lost.** Every point it made is in DR-349 except its claim to partly replace DR-194, which belongs to DR-337 now.

> **primary, in-progress turn 3**
>
> I kept my partner's edit, which makes DR-349 cite DR-337 as the plan asked. I only re-wrapped the sentence they added: it ran past the record's line width and had an awkward comma before "directly". Re-rendering changed no other file, `just gate meta` passes, and I've committed it.

> **secondary, in-progress turn 4**
>
> My partner's only change since my last turn re-wraps the sentence I added to DR-349, and it reads correctly. I'm changing nothing more: the issue is implemented, and `just gate meta` passed on my last turn. I didn't run it again, because the change only re-wraps a line.
