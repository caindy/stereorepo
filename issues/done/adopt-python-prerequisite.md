---
difficulty: easy
---

# State the Python 3.13 prerequisite in ADOPT.md

DR-351 says the Python 3.13 floor is written "where a fresh clone reads
first". `README.md` and `SPECIALIZE.md` both state it, but `ADOPT.md` does
not. Adoption copies the same `.meta/` tooling, and `check.py` refuses an
older interpreter, so someone working from `ADOPT.md` alone learns of the
floor only when their interpreter is refused. The fix mirrors
`issues/done/specialize-python-prerequisite.md`.

## Wanted

- The step *Plan the adoption*
  (`work:discipline-step/adoption/plan-the-adoption` in
  `.meta/assertions/disciplines.yaml`, which `ADOPT.md` is rendered from)
  opens with one sentence saying the tooling the repository inherits needs
  Python 3.13 or later, citing DR-351 without the "stereorepo's" prefix, and
  saying that `check.py` refuses an older interpreter. Word it like the
  matching sentence in the step *Start a new empty repo* of the
  Specialization Discipline.
- DR-351 (`.meta/assertions/decisions/DR-351.yaml`) adds
  `work:artifact/adopt` to `enacted_in`, and adds a consequence after the
  `SPECIALIZE.md` one: "`ADOPT.md` states Python 3.13 or later as a
  prerequisite in its first step." Amend DR-351 rather than writing a new
  record, because the decision is the same.
- `ADOPT.md`, `.meta/disciplines.md` and `.meta/decisions.md` are
  re-rendered and committed with the change.

## Out of scope

- `README.md` and `SPECIALIZE.md`, which already state the floor.
- Any other step of the Adoption Discipline, and anything else in DR-351.
- Changing how any script picks its interpreter.

## Done when

- Step 1 of `ADOPT.md` says Python 3.13 or later is required and cites
  DR-351 in that sentence.
- `ADOPT.md` ends with a "Where this came from" footer listing DR-351. No
  record enacts `ADOPT.md` today, so the footer is new; `_procedure` in
  `.meta/lib/render/pages.py` appends it through `accounted_by` once DR-351
  names `work:artifact/adopt`.
- DR-351 lists `work:artifact/adopt` under `enacted_in` and has a
  consequence that names `ADOPT.md`.
- Re-rendering a second time leaves the tree unchanged.

## The plan

1. **The discipline.** In `.meta/assertions/disciplines.yaml`, open the
   folded (`>-`) `statement` of
   `work:discipline-step/adoption/plan-the-adoption` with: "The tooling this
   repository inherits needs Python 3.13 or later (DR-351), and `check.py`
   refuses an older interpreter." The rest of the statement, which begins
   "From the stereorepo checkout, run `just adapt plan <repository>`", stays
   as it is. Keep the step's indentation and line width. Cite without the
   "stereorepo's" prefix, as *Start a new empty repo* does, because
   `disciplines.yaml` is scaffold-only.
2. **The record.** In `.meta/assertions/decisions/DR-351.yaml`, append
   `work:artifact/adopt` to `enacted_in`, after `work:artifact/specialize`.
   Then append a consequence after the `SPECIALIZE.md` one: "`ADOPT.md`
   states Python 3.13 or later as a prerequisite in its first step."
   Change nothing else.
3. **Render.** Run `just render`. Expect it to write `ADOPT.md` (the step
   sentence, plus a new footer from `accounted_by` in
   `.meta/lib/render/record.py`, which `_procedure` in
   `.meta/lib/render/pages.py` appends), `.meta/disciplines.md` and
   `.meta/decisions.md`. Commit them with the YAML, then run `just render`
   again and confirm it writes nothing.

**Tests.** The change is to prose and records only, so it needs no new unit
test. What shows it works:

- `grep -n "3.13" ADOPT.md` finds the sentence in step 1, with DR-351 in it.
- The last line of `ADOPT.md` is the "Where this came from" footer, and it
  lists DR-351 alone.
- `enacting citations` in `.meta/checks/citations/record.py` holds:
  `ADOPT.md` is now named by DR-351, and cites it in step 1.
- `_probe_adopt` in `.meta/checks/probes/files/rendered.py` still finds
  every step name, which the change leaves alone.

**Risks.** Small. `ADOPT.md` is scaffold-only, but DR-351 cannot point a
portfolio at a missing artifact: `.meta/bundle.yaml` does not carry the
scaffold's records, and a portfolio's only inherited record is the
template's `DR-001.yaml`. So `unresolved references` in
`.meta/checks/graph/structure.py` never sees `work:artifact/adopt` outside
stereorepo. The footer sits after the "Then" postamble, as it does in
`SPECIALIZE.md`.

## What was done

The plan held as written. The step *Plan the adoption* now opens with "The
tooling this repository inherits needs Python 3.13 or later (DR-351), and
`check.py` refuses an older interpreter." DR-351 names `work:artifact/adopt`
in `enacted_in` and has a fifth consequence naming `ADOPT.md`. `just render`
wrote `ADOPT.md`, `.meta/disciplines.md` and `.meta/decisions.md`, and a
second run wrote 0 files. `ADOPT.md` now ends with a "Where this came from"
footer listing DR-351 alone. The edited `statement` is folded (`>-`), so its
source lines were rewrapped to the step's width without changing the
rendered text.

## Pair notes

> **primary, backlog turn 1**
>
> I groomed `issues/underway/adopt-python-prerequisite.md` and set `difficulty: easy`. It's a small change to one discipline step, one decision record (DR) and the files rendered from them, and the developer doesn't need to check it by hand. It's committed in two commits, `577b4201` and `98cf45f5`.
>
> The Issue now follows the same pattern as `issues/done/specialize-python-prerequisite.md`:
>
> - **What is wanted:**
>   - The first step, *Plan the adoption*, of the Adoption Discipline in `.meta/assertions/disciplines.yaml` opens with one sentence: the tooling needs Python 3.13 or later (DR-351), and `check.py` refuses an older interpreter.
>   - DR-351 is amended rather than replaced: it adds `work:artifact/adopt` to `enacted_in`, plus a consequence saying `ADOPT.md` states the requirement in its first step.
>   - `ADOPT.md`, `.meta/disciplines.md` and `.meta/decisions.md` are re-rendered and committed with the change.
> - **Out of scope:** `README.md` and `SPECIALIZE.md`, which already state the requirement; every other Adoption step and the rest of DR-351; and how any script chooses its interpreter.
> - **Done when:**
>   - Step 1 of `ADOPT.md` states the requirement and cites DR-351.
>   - DR-351 lists `work:artifact/adopt` and has a consequence naming `ADOPT.md`.
>   - `ADOPT.md` ends with a "Where this came from" footer listing DR-351.
>   - Re-rendering a second time changes nothing.
>
> One thing the original text didn't mention: `ADOPT.md` has no "Where this came from" footer today, because no DR lists it under `enacted_in`. Once DR-351 does, `_procedure` in `.meta/lib/render/pages.py` adds the footer through `accounted_by`. The Issue now says the footer is new, so whoever implements it won't be surprised by the extra change in the render.

> **secondary, backlog turn 2**
>
> I'm leaving the Issue as it is. Your grooming holds up against the code:
>
> - **The step to edit is the right one.** *Plan the adoption* (`work:discipline-step/adoption/plan-the-adoption` in `.meta/assertions/disciplines.yaml`) is the first step of the Adoption Discipline. The sentence to copy, at the start of *Start a new empty repo* in the Specialization Discipline, reads as the Issue says.
> - **DR-351 is ready for the amendment.** Its `enacted_in` lists `readme` and `specialize` but not `adopt`. Its consequences end with the `SPECIALIZE.md` one, so the new consequence goes where the Issue says. `work:artifact/adopt` already exists in `.meta/assertions/structure.yaml`.
> - **The footer claim is correct.** `ADOPT.md` has no "Where this came from" footer today. `_procedure` in `.meta/lib/render/pages.py` ends with `record.accounted_by(target)`, so the footer will appear once DR-351 names the artifact.
> - **`difficulty: easy` fits.** It's one sentence, one amendment to an existing decision record (DR), and a re-render. The "Done when" section describes behaviour and doesn't name a gate.

> **primary, todo turn 1**
>
> I added a `## The plan` section to `issues/todo/adopt-python-prerequisite.md` and committed it as `299ba987`. Nothing is implemented yet. The steps, in order:
>
> 1. **The discipline step.** In `.meta/assertions/disciplines.yaml`, the step *Plan the adoption* opens with: "The tooling this repository inherits needs Python 3.13 or later (DR-351), and `check.py` refuses an older interpreter." This copies the sentence in *Start a new empty repo*, with "portfolio" changed to "repository". The rest of the step stays as it is.
> 2. **The decision record.** In `.meta/assertions/decisions/DR-351.yaml`, add `work:artifact/adopt` to `enacted_in`, plus one consequence naming `ADOPT.md`. Nothing else in DR-351 changes.
> 3. **Render.** `just render` should rewrite `ADOPT.md` (the new sentence and a new "Where this came from" footer), `.meta/disciplines.md` and `.meta/decisions.md`. A second run should write nothing.
>
> **Tests:** this is a prose-and-record change, so it needs no new unit test. It works when:
> - `ADOPT.md` states the requirement and cites DR-351 in step 1.
> - `ADOPT.md` ends with a footer that lists DR-351 alone.
> - The `enacting citations` check still passes, since `ADOPT.md` both cites DR-351 and is named by it.
> - `_probe_adopt` still finds every step name.
>
> **Risk:** small. `ADOPT.md` exists only in stereorepo, not in a portfolio, so inside a portfolio DR-351 will name a file that isn't there. `SPECIALIZE.md` has been in the same position since its own change landed. The loop's gate run would show it if that turns out to be a problem.
>
> Reading the code turned up nothing that blocks the Issue as written, so it has no `# Needs elaboration` section.

> **secondary, todo turn 2**
>
> I made one fix to the plan and committed it as `146a1953`. The rest of your plan checks out against the code.
>
> **The fix: the risk paragraph.** It said that in a portfolio DR-351 would name an artifact that doesn't exist there, and left the gate run to find out. That can't happen. `.meta/bundle.yaml` doesn't copy stereorepo's decision records into a portfolio; the only record a portfolio inherits is the template's `DR-001.yaml`. So the `unresolved references` check in `.meta/checks/graph/structure.py` never meets `work:artifact/adopt` outside stereorepo. The paragraph now says that. It had also cited `SCAFFOLD_ONLY` in the wrong file, and that citation is gone.
>
> **Confirmed as written:**
> - **The citations check.** `enacting citations` in `.meta/checks/citations/record.py` only fails when a file that a record names cites none of the records that name it. After the change, `ADOPT.md` cites DR-351, which names it, so the check holds.
> - **The footer.** No record names `work:artifact/adopt` today, so the new footer will list DR-351 alone.
> - **The step-name probe.** `_probe_adopt` in `.meta/checks/probes/files/rendered.py` looks only for step names, and the change leaves those alone.

> **primary, todo turn 3**
>
> I'm leaving the plan as it stands. My partner's rewritten risk paragraph is correct: `.meta/bundle.yaml` copies only the template's `DR-001.yaml` into a portfolio, so a portfolio never sees DR-351's reference to `work:artifact/adopt`.
>
> One small correction to their note, which doesn't affect the plan: the `SCAFFOLD_ONLY` citation they removed was in the right file. The list that names `ADOPT.md` is `SCAFFOLD_ONLY` in `.meta/checks/files/scaffold.py`. A different list with the same name, in `.meta/checks/probes/tools/__init__.py`, covers only probes. The plan reads fine without the citation either way.

> **primary, in-progress turn 1**
>
> I implemented the plan as written and committed it as `aa0d02de`. `just gate meta` passes.
>
> - **`.meta/assertions/disciplines.yaml`:** step 1, *Plan the adoption*, now opens with "The tooling this repository inherits needs Python 3.13 or later (DR-351), and `check.py` refuses an older interpreter."
> - **`.meta/assertions/decisions/DR-351.yaml`:** `work:artifact/adopt` is added under `enacted_in`, and there is a new consequence saying `ADOPT.md` states the requirement in its first step.
> - **Rendered files:** `just render` rewrote `ADOPT.md`, `.meta/disciplines.md` and `.meta/decisions.md`, and a second run wrote 0 files. `ADOPT.md` states the requirement in step 1 and now ends with a "Where this came from" footer that lists DR-351 alone.
>
> I added a `## What was done` section to the Issue file. The change touches no other Project's directory, so no other gate applies. I found no work outside this Issue to write up in the backlog.

> **secondary, in-progress turn 2**
>
> Your implementation matches the plan. I made one fix and committed it as `be07714e`.
>
> **The fix:** the source text of the step *Plan the adoption* in `.meta/assertions/disciplines.yaml` had one line much wider than its neighbours. The plan said to keep the step's line width, so I rewrapped it. The text is a folded YAML block (`>-`), which joins its lines into one paragraph, so the rendered pages don't change: `just render` wrote 0 files. I added a sentence about this to "What was done" in the Issue file.
>
> **Checks:**
> - `just gate meta` passes, all 95 steps.
> - Your correction in the pair notes is right: the `SCAFFOLD_ONLY` that covers `ADOPT.md` is the one in `.meta/checks/files/scaffold.py`. The Issue file needed no change for it.
> - The change touches no other Project's directory, so no other gate applies.

> **primary, in-progress turn 3**
>
> I'm changing nothing this turn. My partner's rewrap keeps the step's source lines at a similar width. The `statement` is a folded YAML block (`>-`), which joins its lines into one paragraph, so the rendered `ADOPT.md` is identical. The rest of the step was already wrapped this way before this Issue. I didn't run `just gate meta` again: nothing has changed since my partner ran it, and it passed all 95 steps. The work matches the plan and the "Done when" criteria.
