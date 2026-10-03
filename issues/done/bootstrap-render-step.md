---
difficulty: easy
waits_on: [bootstrap-audit]
---

# Make the bootstraps' `render` step real, or stop naming it

Both bootstraps in `.meta/assertions/bootstraps.yaml` (`work:bootstrap/python`
and `work:bootstrap/rust`) say Seeded Artifacts is held by a gate step called
`render`. Neither seed's gate has one: python-seed's `STEPS` in
`bootstraps/python/seed/gate/src/gate/__init__.py` run `lints` through
`mutants`, and the Rust seed's xtask (`bootstraps/rust/seed/xtask/src/lib.rs`)
has no `render` either. So the reference names a step its own seeds don't
report, and `just audit` flags it against both of them.

## How to reproduce

`just audit python-seed python` and `just audit rust-seed rust` each print a
gap for the missing `render` step (as a would-be
`issues/backlog/python-seed-gate-render.md`, and the Rust equivalent) and exit
non-zero.

## Wanted

A Bootstrap describes what a Project built from it inherits. Seeded Artifacts
asks that a seed (a template) be gated by rendering it and gating the
result. A Project instantiated from either seed holds no template of its own,
so there is nothing for a `render` step in its gate to render; adding an
empty step would be the "suite nothing runs" the Discipline itself warns of.

So, in both bootstraps, the Seeded Artifacts entry becomes `status: exempt`,
drops `held_by`, keeps its `exposition`, and gains an `exemption_reason`
saying that a Project built from the seed holds no seed, and naming what gates
the seed in stereorepo.

Grooming found what that is today. The "Rendered, then gated" section of
`bootstraps/python/seeded-artifacts.md` and `bootstraps/rust/seeded-artifacts.md`
(and the header comments of `bootstraps/python/render` and
`bootstraps/rust/render`) credit a `python seed` / `rust seed` job in
`.github/workflows/gate.yml` that renders the seed as `acme` and gates it. That
workflow no longer exists (no `.github/workflows/` in the tree), and nothing
else renders a seed and gates the copy: `.meta/test_specialization.py` stages
`bootstraps/<lang>` but does not gate a rendered seed. What does exist is each
seed's gate run in place, as the gates of `work:project/python-seed` and
`work:project/rust-seed` in `.meta/assertions/structure.yaml`. The
`exemption_reason` names that, and does not claim a rendered copy is gated.

Write a Decision Record settling the rule beyond these two entries: a
Bootstrap exempts a Discipline whose subject its Projects do not hold, and
says where in the portfolio that subject is held instead. Cite it from both
`exemption_reason`s.

## Out of scope

- Adding a `render` step to either seed's gate.
- Restoring a rendered-then-gated run of the seeds, or correcting the stale
  `gate.yml` prose in the two `seeded-artifacts.md` pages and the two `render`
  scripts: that is `issues/backlog/seed-rendered-gate-lost.md`.
- Any other gap `just audit` reports.

## Done when

- `just audit python-seed python` and `just audit rust-seed rust` no longer
  report a `render` gap (other gaps may remain).
- Both Seeded Artifacts entries are `exempt` with no `held_by`, and each
  `exemption_reason` names the seed Project's in-place gate and the new
  Decision Record, both of which exist in the tree.
- The rendered outputs agree with the change: the discipline tables in
  `bootstraps/python/README.md` and `bootstraps/rust/README.md` (built by
  `bootstrap_table` in `.meta/lib/render/bootstraps.py`) give Seeded
  Artifacts the same fixed exempt cell Written Decisions has ("nothing here —
  the portfolio's gate, and it says why"; the table does not print the
  reason), and `.meta/decisions.md` lists the new Decision Record.

## The plan

Data and prose only; no code changes.

1. **Decision Record.** Add `.meta/assertions/decisions/DR-356.yaml` (DR-355
   is the highest today; recheck before writing), shaped like DR-355:
   `status: ADOPTED`, `enacted_in` the two rendered pages that show the
   choice (`work:artifact/bootstraps-python-readme`,
   `work:artifact/bootstraps-rust-readme`; `bootstraps.yaml` has no artifact
   of its own). Decision: a Bootstrap exempts a project-binding Discipline
   whose subject a Project built from it does not hold, and its
   `exemption_reason` says where in the portfolio that subject is held
   instead. Alternatives: an empty `render` step (a step that checks nothing);
   `status: portfolio_scoped` (refused for project-binding Disciplines by
   `bootstrap_discipline_coverage` in `.meta/checks/graph/structure.py`).
   Context names the audit gap and the removed `gate.yml` job; consequences
   point at `seed-rendered-gate-lost` for the rendered-copy gap.
2. **`.meta/assertions/bootstraps.yaml`.** In both `work:bootstrap/python`
   and `work:bootstrap/rust`, change the `work:discipline/seeded-artifacts`
   entry to `status: exempt`, remove `held_by`, keep `exposition`, and add an
   `exemption_reason` modelled on the Written Decisions one: a Project built
   from the seed holds no seed; the seed itself is gated in place by the gate
   of `work:project/python-seed` (`work:project/rust-seed`) in stereorepo;
   cite the new DR. Do not say a rendered copy is gated.
3. **Render.** Run `just render` and commit what it changes. Expected: the
   Seeded Artifacts rows of `bootstraps/python/README.md` and
   `bootstraps/rust/README.md`, and `.meta/decisions.md`. Anything else it
   rewrites is a surprise to look at, not to commit blindly.

**Tests.** Run `just audit python-seed python` and `just audit rust-seed rust`
once each after the change, and check no `render` gap is printed. Each runs
that seed's full gate, so expect minutes. The structure check accepts an
exempt entry with a reason as it stands, and its probe
(`.meta/checks/probes/structure.py`) builds its own fixture with
`held_by: [render]`, so it needs no change. No new test: the audit run is
the behaviour, and `held` in `.meta/audit.py` already skips every Discipline
whose status is not `implemented`, which the Written Decisions entries
exercise on every audit.

**Risk.** Small. The exemption's text must not repeat the stale `gate.yml`
claim that `seeded-artifacts.md` still makes; that page is left as it is for
`seed-rendered-gate-lost`.

## What was done

The plan held as written. `DR-356` records the rule; both Seeded Artifacts
entries in `.meta/assertions/bootstraps.yaml` are `exempt`, each reason naming
`work:project/<lang>-seed`'s in-place gate and citing DR-356; `just render`
rewrote only the two bootstrap READMEs and `.meta/decisions.md`.

After the change, `just audit python-seed python` exits 0 with no gap, and
`just audit rust-seed rust` prints no `render` gap. Its one remaining gap is
that the Rust seed's gate lets `cargo test` output onto standard output, now
`issues/backlog/rust-seed-gate-stdout.md`.

Running the Rust audit inside a seat's sandbox needs `RUSTC_WRAPPER=` set
empty: the configured `sccache` wrapper is refused there ("Operation not
permitted"), the seed's gate then exits 2 silently, and the audit misreports
that as a gate reporting nothing. That misreport is
`issues/backlog/audit-gate-crash-misreported.md`.

The exempt cell in both bootstrap READMEs says the exposition page "says
why", so each `seeded-artifacts.md` now opens by saying why Seeded Artifacts
is exempt, citing DR-356. Its stale "Rendered, then gated" section is left
for `seed-rendered-gate-lost`, which now also names the stale `render` job in
each `nothing-unconsumed.md`. The opening says the seed's gate runs on the
seed where it sits, and no longer "in two ways", so it does not credit that
gate with the rendered run the section below describes.

## Pair notes

> **primary, backlog turn 1**
>
> I groomed `issues/underway/bootstrap-render-step.md` and left it at `difficulty: easy`. Its approach was already sound; I made it definite.
>
> **What I found:** the Issue asked whoever picks it up to "find what gates the seed itself." I searched, and the answer changes what the exemption can say:
> - Both `seeded-artifacts.md` pages and both `render` scripts say a seed is rendered as `acme` and gated by a CI workflow, `.github/workflows/gate.yml`. Decision Records DR-091 and DR-094 say the same. That workflow was deleted along with the pull-request flow.
> - Nothing else renders a seed and gates the copy. `test_specialization.py` copies the bootstrap directory into a fresh clone but never gates a rendered seed.
> - What does run is each seed's own gate, on the seed where it sits: the gates of `work:project/python-seed` and `work:project/rust-seed` in `.meta/assertions/structure.yaml`.
>
> **How the Issue reads now:**
> - **Wanted:** in both bootstraps, Seeded Artifacts becomes `status: exempt` with no `held_by`. Each `exemption_reason` names the seed's own gate and must not claim a rendered copy is gated. A new Decision Record states the general rule, that a Bootstrap exempts a Discipline whose subject its Projects don't hold, and both reasons cite it. Before, that Decision Record was optional.
> - **Out of scope:** adding a `render` step; restoring a rendered-then-gated run or fixing the stale text about the deleted workflow; any other gap `just audit` reports.
> - **Done when:** `just audit python-seed python` and `just audit rust-seed rust` no longer report a `render` gap, and both entries are exempt with reasons that name things that exist in the tree. I ran the Python audit once, and it still reports the `render` gap today.
>
> **New backlog Issue:** `issues/backlog/seed-rendered-gate-lost.md`. Since that workflow went, a fault that only shows in a rendered copy goes unseen, such as a missed rename or a lockfile that no longer matches. The fix is either a new run that renders the seeds and gates the copies somewhere the pair loop reaches, or correcting the text and those Decision Records.
>
> Both files are committed.

> **secondary, backlog turn 2**
>
> My partner's grooming holds up, and `difficulty: easy` is the right level. I made one addition and committed it.
>
> **What I checked:**
> - **An exempt entry passes the structure check.** The coverage check (`bootstrap_discipline_coverage` in `.meta/checks/graph/structure.py`) accepts `status: exempt` for any Discipline as long as it has an `exemption_reason`.
> - **There's a model to copy.** Both bootstraps already exempt Written Decisions the same way, by saying where the portfolio holds the subject instead.
> - **A new Decision Record is justified.** No existing one states the general rule that a Bootstrap exempts a Discipline its Projects don't hold.
> - **The work it waits on has landed.** `bootstrap-audit` is in `issues/done/`, and `.github/workflows/` really is gone, as my partner found.
>
> **What I added:** The discipline tables in `bootstraps/python/README.md` and `bootstraps/rust/README.md` are generated from these entries by `bootstrap_table` in `.meta/lib/render/bootstraps.py`. `.meta/decisions.md` is generated from the Decision Records. So "Done when" now also requires both tables to show Seeded Artifacts as exempt with its reason, and the decisions index to list the new record.

> **primary, backlog turn 3**
>
> I kept my partner's addition and fixed one wrong claim in it. Their new "Done when" item said the generated discipline tables would show Seeded Artifacts "as exempt with its reason."
>
> `bootstrap_table` in `.meta/lib/render/bootstraps.py` doesn't print the reason. For any exempt Discipline it writes the same fixed text: "nothing here — the portfolio's gate, and it says why". You can see this today on the Written Decisions rows of `bootstraps/python/README.md` and `bootstraps/rust/README.md`. I reworded that item so it expects that fixed text instead of the reason, and committed it.
>
> The rest of the Issue is unchanged, and `difficulty: easy` stays.

> **secondary, backlog turn 4**
>
> I'm changing nothing this turn. My partner's correction is right: for any exempt Discipline, `bootstrap_table` in `.meta/lib/render/bootstraps.py` prints the same fixed cell, "nothing here — the portfolio's gate, and it says why", and never the reason itself. The Written Decisions row of `bootstraps/python/README.md` shows that today. My earlier "Done when" item was wrong, and their wording fixes it.
>
> The Issue is ready to plan, at `difficulty: easy`.

> **primary, todo turn 1**
>
> I wrote the plan under `## The plan` in `issues/todo/bootstrap-render-step.md` and committed it. Nothing I read stops the Issue being done as written. The change is data and prose only, with no code changes.
>
> **The steps, in order:**
> 1. **Decision Record:** add `DR-356` (DR-355 is the highest today). It states the rule: a Bootstrap exempts a Discipline whose subject a Project built from it doesn't hold, and its `exemption_reason` says where in the portfolio that subject is held instead. Two alternatives are recorded as rejected:
>    - an empty `render` step, which would check nothing;
>    - `status: portfolio_scoped`, which the coverage check (`bootstrap_discipline_coverage` in `.meta/checks/graph/structure.py`) refuses for this kind of Discipline.
>
>    It names the two bootstrap README pages in `enacted_in`, because `bootstraps.yaml` has no artifact entry of its own to name.
> 2. **`.meta/assertions/bootstraps.yaml`:** in both bootstraps, the Seeded Artifacts entry becomes `status: exempt`, loses `held_by` and keeps its `exposition`. Its `exemption_reason` names the seed's own gate (the gate of `work:project/python-seed` or `work:project/rust-seed`) and cites the new record. It must not say a rendered copy is gated.
> 3. **Render:** run `just render`. I expect it to change only the two bootstrap README tables and `.meta/decisions.md`. Anything else it rewrites gets looked at before it is committed.
>
> **How we'll know it works:** run `just audit python-seed python` and `just audit rust-seed rust` once each, and confirm neither prints a `render` gap. Each one runs that seed's full gate, so expect minutes.
>
> No new test or check change is needed:
> - The coverage check already accepts an exempt entry that has a reason.
> - The probe for that check, `.meta/checks/probes/structure.py`, builds its own sample data, so this change doesn't touch it.
> - The audit's `held` function in `.meta/audit.py` already skips any Discipline that isn't `implemented`, and the Written Decisions entries exercise that on every audit.
>
> I had first written that the audit's probe file covers the exempt case; it doesn't, so I corrected that sentence before committing.
>
> **Risk:** small. The one trap is repeating, in the new reason, the stale claim in `seeded-artifacts.md` that a deleted CI workflow gates the rendered seed. That page stays as it is and is left to `seed-rendered-gate-lost`.

> **secondary, todo turn 2**
>
> I'm changing nothing this turn. I checked the plan's claims against the tree, and each one holds:
>
> - **DR number:** DR-355 is the highest Decision Record today, so DR-356 is the next number.
> - **`enacted_in` targets:** `work:artifact/bootstraps-python-readme` and `work:artifact/bootstraps-rust-readme` both exist in `.meta/assertions/structure.yaml`.
> - **Recipes:** `just render` and `just audit <project> <bootstrap>` both exist.
> - **Audit behaviour:** `held` in `.meta/audit.py` collects steps only from implemented Disciplines and skips exempt ones. That is why the exemption will clear the `render` gap.
> - **Record shape:** DR-355 is a fair model for the new record: `status`, `enacted_in`, `context`, and `alternatives` with a `chosen` flag and a reason for each.
>
> The plan is ready to implement.

> **primary, in-progress turn 1**
>
> Both bootstraps no longer name the missing `render` step, and neither audit reports a `render` gap now. Implemented as planned and committed.
>
> **What changed:**
> - **New Decision Record, `.meta/assertions/decisions/DR-356.yaml`:** a Bootstrap exempts a Discipline whose subject the Projects built from it don't hold, and the exemption says where that subject is held instead. It records two rejected alternatives: an empty `render` step, and `portfolio_scoped`, which the coverage check refuses for this kind of Discipline.
> - **`.meta/assertions/bootstraps.yaml`:** Seeded Artifacts is now `exempt` in both bootstraps, with no `held_by`. Each reason says a Project built from the seed holds no seed. It names the seed's own gate, run in place (`work:project/python-seed` or `work:project/rust-seed`), and cites DR-356. It does not claim a rendered copy is gated.
> - **`just render`** rewrote exactly the three files the plan expected: the Seeded Artifacts rows in both bootstrap READMEs and `.meta/decisions.md`.
>
> **Results:**
> - `just audit python-seed python` exits 0 with no gaps.
> - `just audit rust-seed rust` still exits 1, but for one gap this Issue doesn't cover: the Rust seed's gate lets `cargo test` output onto standard output. That is the Rust counterpart of the `python-seed-gate-stdout` Issue that just landed. I filed it as `issues/backlog/rust-seed-gate-stdout.md`.
> - `just gate meta` passes. The change touches no seed's directory, so no other Project's gate applied.
>
> **A trap for the next reader:** in a seat's sandbox, the Rust audit only runs with `RUSTC_WRAPPER=` set empty. Otherwise the `sccache` compiler wrapper is refused ("Operation not permitted"), the seed's gate exits 2 without printing anything, and the audit misreports that as a gate that reports nothing. This is written in the Issue's new `## What was done` section.

> **secondary, in-progress turn 2**
>
> My partner's implementation was correct, and I filled in what it left out. `just gate meta` passes, the render pass changed nothing further, and it's all committed.
>
> My partner's results stand: neither audit reports a `render` gap now. The Rust audit still exits 1 for an output-shape gap, which they filed as `rust-seed-gate-stdout`.
>
> **What I fixed:**
> - **The exemption's explanation was missing.** In both bootstrap READMEs, the Seeded Artifacts row now says "nothing here — the portfolio's gate, and it says why" and links to `seeded-artifacts.md`. That page didn't say why. Each `seeded-artifacts.md` now opens with the reason: a Project built from the seed holds no seed, and the seed is gated in place by `work:project/<lang>-seed` (DR-356). I left the stale "Rendered, then gated" section alone, since it's out of scope.
> - **The stale-prose list was incomplete.** Both `nothing-unconsumed.md` pages also credit the deleted `gate.yml` seed jobs. I added them to `issues/backlog/seed-rendered-gate-lost.md`.
>
> **New backlog Issue:** `issues/backlog/audit-gate-crash-misreported.md`. My partner noted that the Rust seed's gate dies silently in the sandbox unless `RUSTC_WRAPPER=` is set empty. The underlying fault is that `audit` in `.meta/audit.py` doesn't read the gate's exit code. A gate that crashes before printing anything is therefore reported as "reports nothing", and the audit asks for steps the gate already has. The new Issue asks the audit to say the gate failed, with its exit code, and to have its probe test that.

> **primary, in-progress turn 3**
>
> I kept my partner's additions and fixed one phrase in them. `just gate meta` passes and the change is committed.
>
> My partner's other additions hold:
> - **Opening paragraph:** each `seeded-artifacts.md` now opens by explaining the exemption, which the README's "it says why" cell points to.
> - **Stale-prose list:** both `nothing-unconsumed.md` pages were added to `seed-rendered-gate-lost`.
> - **New backlog Issue:** `audit-gate-crash-misreported` identifies the real fault behind the sandbox trap: `.meta/audit.py` ignores the gate's exit code.
>
> **The fix:** that new opening said the seed is held to the Discipline by the gate of `work:project/<lang>-seed` "in two ways". The first of those two ways is the "Rendered, then gated" section, which describes the deleted CI workflow, not that gate. So the sentence credited the seed's own gate with rendering a copy, which it never does.
>
> In both pages the opening now says that gate runs "on the seed where it sits (DR-356)" and drops "in two ways". The stale section itself is still left to `seed-rendered-gate-lost`. I added a line about this to the Issue's `## What was done` section.

> **secondary, in-progress turn 4**
>
> I'm changing nothing this turn. My partner's fix is right. "In two ways" credited the seed's own gate with the rendered run in "Rendered, then gated", but that run belonged to the deleted CI workflow, not to this gate. Saying instead that the gate runs "on the seed where it sits" is accurate, and the stale section stays left for `seed-rendered-gate-lost`.
>
> Every "Done when" item is met:
> - Neither audit reports a `render` gap now.
> - Both Seeded Artifacts entries are exempt, with no `held_by`.
> - Each reason names the seed's own gate and DR-356, both of which exist.
> - The README tables and `.meta/decisions.md` are re-rendered to match.
>
> `just gate meta` passed on my last turn. Since then my partner has changed only prose and the Issue file, and they report that it still passes.
