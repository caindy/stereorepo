---
difficulty: easy
---

# State the Python 3.13 prerequisite in SPECIALIZE.md

DR-268 said `README.md` and `SPECIALIZE.md` both state Python 3.13 or later
as a prerequisite for a fresh clone. Only `README.md` does. `SPECIALIZE.md`
names no Python version, so someone working from it alone finds out about
the floor only when `check.py` refuses their interpreter. DR-351, which
supersedes DR-268, lists what the tree holds and leaves `SPECIALIZE.md` out.
`SPECIALIZE.md`'s "Where this came from" footer still lists DR-268, because
DR-268's `enacted_in` still names `work:artifact/specialize`.

## Wanted

- The Specialization Discipline (`work:discipline/specialization` in
  `.meta/assertions/disciplines.yaml`, which `SPECIALIZE.md` is rendered
  from) states Python 3.13 or later as a prerequisite and cites DR-351. Put
  it where a reader meets it before the first step, either in the
  `description` or in the step *Start a new empty repo*.
- DR-351 adds `work:artifact/specialize` to its `enacted_in`, and adds a
  consequence saying `SPECIALIZE.md` states the floor. Amend DR-351 rather
  than write a new record: the decision is the same, and DR-351 already
  intends the prerequisite to be "written where a fresh clone reads first".
- `SPECIALIZE.md` is re-rendered and committed with the change.

## Out of scope

- `README.md`, which already states the floor.
- `ADOPT.md` and the Adoption Discipline. If they need the floor too, write
  that as a separate Issue in the backlog.
- DR-268 itself. It is superseded and stays as it was recorded.

## Done when

- `SPECIALIZE.md` says Python 3.13 or later is required, cites DR-351 in
  that sentence, and lists DR-351 in its "Where this came from" footer.
- `.meta/assertions/decisions/DR-351.yaml` lists `work:artifact/specialize`
  under `enacted_in` and has a consequence that names `SPECIALIZE.md`.
- Re-rendering leaves the tree unchanged.

## The plan

1. **The discipline.** In `.meta/assertions/disciplines.yaml`, open the
   `statement` of `work:discipline-step/specialization/start-a-new-empty-repo`
   with one sentence giving the floor, for example: "The tooling this
   portfolio inherits needs Python 3.13 or later (DR-351); `check.py`
   refuses an older interpreter." Use the step rather than the
   `description`. The description is the discipline's summary, and the
   first step is where a reader starts acting. Cite DR-351 without the
   "stereorepo's" prefix, as the other citations in that file do:
   `disciplines.yaml` is scaffold-only, so a portfolio never inherits it.
2. **The record.** In `.meta/assertions/decisions/DR-351.yaml`, add
   `work:artifact/specialize` to `enacted_in`. That id is defined in
   `.meta/assertions/structure.yaml` with `path: SPECIALIZE.md`. Then add a
   consequence after the `README.md` one: "`SPECIALIZE.md` states Python
   3.13 or later as a prerequisite in its first step." Change nothing else
   in DR-351, and leave DR-268 alone.
3. **Render.** Run `just render`. It is expected to change `SPECIALIZE.md`
   (the step text, and DR-351 added to the footer through
   `accounted_by` in `.meta/lib/render/record.py`), `.meta/disciplines.md`
   (which renders the same step) and possibly `.meta/decisions.md`. Commit
   all of them with the YAML.

**Tests.** No code changes, so no new unit test.

- `grep -n "3.13" SPECIALIZE.md` finds the sentence in step 1, with DR-351
  in it.
- DR-351 appears in the footer.
- Running `just render` a second time leaves `git status` clean.
- `enacting citations` in `.meta/checks/citations/record.py` still holds:
  `SPECIALIZE.md` now cites DR-351, and DR-351 names it.

**Risks.** Small. The step is folded YAML (`>-`), so keep the indentation
when adding the sentence. Another check could limit DR citations in a
discipline step, or could require a consequence to match an
`enacted_in` entry. The loop's gate run will show it if so.

## What was done

The plan held as written. The step *Start a new empty repo* now opens with
"The tooling this portfolio inherits needs Python 3.13 or later (DR-351),
and `check.py` refuses an older interpreter." DR-351 names
`work:artifact/specialize` in `enacted_in` and has a fourth consequence.
`just render` wrote `SPECIALIZE.md`, `.meta/disciplines.md` and
`.meta/decisions.md`, and running it a second time wrote 0 files.
`SPECIALIZE.md`'s footer now lists DR-351 next to DR-268. `just gate meta`
passes.

`ADOPT.md` has the same gap, so it is written up as
`issues/backlog/adopt-python-prerequisite.md` rather than fixed here.

## Pair notes

> **primary, backlog turn 1**
>
> I groomed `issues/underway/specialize-python-prerequisite.md` and left `difficulty: easy`. It is a small, contained change that the developer doesn't need to check by hand.
>
> - **Done criteria:** The old test, "`enacting citations` passes", proved nothing. That check passes today, because `SPECIALIZE.md` already cites other records that name it. The new criteria can be checked directly:
>   - `SPECIALIZE.md` states the Python 3.13 floor and cites DR-351 in that sentence.
>   - DR-351 appears in the file's "Where this came from" footer.
>   - DR-351 lists `work:artifact/specialize` and has a consequence naming `SPECIALIZE.md`.
>   - Re-rendering leaves the tree unchanged.
> - **Open question settled:** The issue said deciding between a new record and a change to DR-351 was part of the work. It now says to amend DR-351. The decision hasn't changed, and DR-351 already says the prerequisite should be written "where a fresh clone reads first".
> - **Placement:** The floor goes in the Specialization Discipline's `description` or in the step *Start a new empty repo*, so a reader sees it before the first step.
> - **New out-of-scope section:** It excludes `README.md` (which already states the floor), `ADOPT.md` (if it needs the floor, that becomes a separate backlog Issue) and DR-268. DR-268 is superseded and stays as recorded, so `SPECIALIZE.md` will keep listing it in its footer.

> **secondary, backlog turn 2**
>
> I'm leaving `issues/underway/specialize-python-prerequisite.md` as my partner left it, with `difficulty: easy`. I checked what it says against the tree, and all of it is accurate:
>
> - **The gap:** `SPECIALIZE.md` names no Python version. `README.md` already says "Python >= 3.13 (DR-351)".
> - **DR-351:** its `enacted_in` lists only `meta-check`, `meta-checks-files-python` and `readme`. It already intends the prerequisite to be "written where a fresh clone reads first", so changing DR-351 instead of writing a new record is the right call.
> - **Placement:** the discipline's `description` and the step *Start a new empty repo* both render into `SPECIALIZE.md` before the first step, so the floor can go in either.
> - **The footer:** "Where this came from" lists DR-268 but not DR-351. Adding `work:artifact/specialize` to DR-351's `enacted_in` should add DR-351 to that list.
> - **The checks:** each "Done when" criterion can be checked directly, none of them names a gate, and "re-rendering leaves the tree unchanged" covers any other generated file that uses the discipline's text.
>
> The scope is right for an easy Issue, so I made no edits.

> **primary, todo turn 1**
>
> I added a `## The plan` section to `issues/todo/specialize-python-prerequisite.md`; nothing is implemented yet. The steps, in order:
>
> 1. **The discipline.** The Python 3.13 floor becomes the first sentence of the step *Start a new empty repo* in `.meta/assertions/disciplines.yaml`, citing DR-351. I chose the step over the discipline's `description` because the step is where a reader starts acting.
> 2. **The record.** DR-351 gets `work:artifact/specialize` added to its `enacted_in`, plus a consequence saying `SPECIALIZE.md` states the floor. DR-268 stays as it is.
> 3. **Render.** `just render` should then change:
>    - `SPECIALIZE.md`, both the step text and the "Where this came from" footer, which `accounted_by` in `.meta/lib/render/record.py` builds from `enacted_in`;
>    - `.meta/disciplines.md`, which renders the same step;
>    - possibly `.meta/decisions.md`.
>
>    All of them get committed with the YAML.
>
> **Tests:** there is no code change, so no new unit test. The plan checks four things:
> - step 1 of `SPECIALIZE.md` contains the 3.13 sentence with DR-351;
> - DR-351 is in the footer;
> - a second `just render` leaves `git status` clean;
> - `enacting citations` still holds.
>
> **Risks:** small. The step's text is folded YAML, so the new sentence has to keep its indentation. Another check might limit DR citations in a step or tie consequences to `enacted_in`; if so, the loop's gate run will show it.

> **secondary, todo turn 2**
>
> I'm leaving my partner's plan as written. I checked the code it relies on, and it holds up:
>
> - **The footer:** `accounted_by` in `.meta/lib/render/record.py` lists every record whose `enacted_in` names the page. Adding `work:artifact/specialize` to DR-351 will therefore put DR-351 in `SPECIALIZE.md`'s "Where this came from" footer.
> - **The plain citation:** `disciplines.yaml` and `.meta/disciplines.md` are not in what a portfolio copies, so the rule requiring "stereorepo's DR-nnn" in copied files doesn't apply. Plain "DR-351" is correct.
> - **The `enacting citations` check:** this check in `.meta/checks/citations/record.py` only fails when a file the record names cites no record that names it back. After the change, `SPECIALIZE.md` cites DR-351 and DR-351 names `SPECIALIZE.md`, so it passes.
> - **Other places the step appears:** the step text appears only in `disciplines.yaml`, `.meta/disciplines.md`, `SPECIALIZE.md`, and the copy under `apm_modules/`. That copy is ignored by git, so the plan already lists every file that will change.

> **primary, in-progress turn 1**
>
> `SPECIALIZE.md` now states the Python 3.13 floor. I did it the way the plan said, and `just gate meta` passes.
>
> - **The discipline:** step 1, *Start a new empty repo*, now opens with: "The tooling this portfolio inherits needs Python 3.13 or later (DR-351), and `check.py` refuses an older interpreter."
> - **DR-351:** it now lists `work:artifact/specialize` under `enacted_in` and has a consequence naming `SPECIALIZE.md`.
> - **Render:** `just render` rewrote three files: `SPECIALIZE.md`, `.meta/disciplines.md` and `.meta/decisions.md`. The footer of `SPECIALIZE.md` now lists DR-351 next to DR-268. Running the render a second time wrote no files.
> - **Follow-up Issue:** `ADOPT.md` doesn't state the floor either, even though adoption copies the same `.meta/` tooling. I wrote that up as `issues/backlog/adopt-python-prerequisite.md` instead of fixing it here.
>
> I recorded what was done in the issue file and committed everything as `3b37fde1`.

> **secondary, in-progress turn 1**
>
> I checked the change against the "Done when" criteria, and it meets all of them. I made one edit: I reflowed the YAML lines of the step *Start a new empty repo*, which the insertion had left uneven. The text is a folded scalar, so the rendered output is the same, and `just render` wrote 0 files afterwards. `just gate meta` passes. The follow-up Issue, `issues/backlog/adopt-python-prerequisite.md`, names `work:artifact/adopt`, which exists in `.meta/assertions/structure.yaml`.

> **secondary, in-progress turn 2**
>
> My partner's implementation was already correct, so my only change was tidying the line wrapping in the YAML.
>
> **What my partner did:** `SPECIALIZE.md` now opens step 1 with "The tooling this portfolio inherits needs Python 3.13 or later (DR-351), and `check.py` refuses an older interpreter." DR-351 now names `SPECIALIZE.md` in its `enacted_in` and has a consequence saying `SPECIALIZE.md` states the floor. As a result, DR-351 now appears in the file's "Where this came from" footer.
>
> **What I changed:** inserting the new sentence had left the lines of that step uneven in `.meta/assertions/disciplines.yaml`, so I re-wrapped them. YAML joins those lines into one paragraph, so the output is identical. Re-rendering wrote no files, and `just gate meta` passes.
>
> My partner wrote the same gap in `ADOPT.md` up as a new backlog Issue, `issues/backlog/adopt-python-prerequisite.md`. I checked that the Issue names a real artifact, `work:artifact/adopt`. I added a note to the issue file and committed it as `c8d3264b`.

> **primary, in-progress turn 3**
>
> I changed nothing this turn. My partner's only edit re-wrapped the lines of the step *Start a new empty repo* in `.meta/assertions/disciplines.yaml`. That step is a single YAML paragraph, so the line breaks don't reach `SPECIALIZE.md`, and the change is correct.
>
> The issue's "Done when" criteria are all met:
> - `SPECIALIZE.md` states the Python 3.13 floor in step 1 and cites DR-351 there.
> - DR-351 lists `SPECIALIZE.md` among the files that put it into practice, and has a consequence saying so.
> - DR-351 now appears in the "Where this came from" footer of `SPECIALIZE.md`.
> - After the re-wrap, my partner ran `just render` and it wrote no files, and `just gate meta` passed. I didn't run either again because nothing has changed since.
