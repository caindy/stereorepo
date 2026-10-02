---
difficulty: hard
---

# Onboard fitch-mvp, the first existing repository

Specialization turns an empty repository into a portfolio. Nothing yet takes a
repository that already has code, history and conventions of its own, and
`just adapt plan` only plans that adoption: nothing applies the plan, no
procedure covers the judgement it leaves, and no existing Product has been
brought under a gate. This Flight onboards one real repository,
`/Users/christopher/fitch-mvp`, and fixes each gap the attempt finds in the
tool that caused it, so that the second onboarding has less to find.

fitch-mvp is a Python decision-modelling framework (LinkML schemas, a Neo4j
loader, pytest). Its tests run through `./build.py`, which starts a Neo4j
Docker container. It is colocated with Jujutsu (`.jj/`), and it keeps its own
`ROADMAP.md`, `DOGFOODING.md` and a design-decision graph in
`data/fitch_design_graph.yaml`.

## Settled by the developer

- **Jujutsu goes.** fitch-mvp stops using Jujutsu with this adoption, and
  `.jj/` is removed. Nothing is lost: both of its heads are empty, and its
  `main` is an ancestor of git's.
- **Two decision regimes, split by subject.** fitch-mvp is a decision
  management product, so it keeps dogfooding its *product* decisions in its
  own model, `data/fitch_design_graph.yaml`. Its *coding* decisions (how the
  repository is built, tested and delivered) are Decision Records under
  stereorepo's discipline, in `.meta/assertions/decisions/`. Its `AGENTS.md`
  is integrated to state the split, and `ROADMAP.md`'s work items move to the
  board.
- **The gate splits around Neo4j.** `./build.py` starts a Neo4j Docker
  container, and the seats' sandbox does not run Docker. fitch-mvp's gate
  therefore has a fast part that needs no database, which seats run while
  they work, and a full part with Neo4j, which runs before an Issue lands.

Once fitch-mvp holds its assertions, both of these become its first Decision
Records.

## How anyone will know it is delivered

The Flight is delivered in two repositories, and each is checked by whoever
can see it.

**The Flight check, in stereorepo.** The pair confirms that:

- every part of this Flight is in `done/`, and each one's change is in
  `main`;
- each finding under "Findings for the adoption procedure" names a part that
  addresses it, or says it waits for the procedure.

The Flight check writes no part for the state of fitch-mvp. That repository
is outside this tree, and the seats can neither read it nor change it. Where
the pair finds that fitch-mvp is not yet onboarded, it says so in the
desk-check brief and leaves the call to the developer.

**The desk check, in fitch-mvp.** The developer confirms that:

- fitch-mvp holds the adopted bundle and its own assertions in place of the
  scaffold's, and its `README.md`, `AGENTS.md` and `.gitignore` keep their
  own content beside the stereorepo conventions;
- a seat working in fitch-mvp runs the tests that need no database without
  Docker, and an Issue that lands there has first passed the tests that need
  Neo4j;
- one Issue in fitch-mvp's `issues/backlog/` has landed on its `main` through
  `uv run --script <stereorepo>/pair/pair.py run`.

## How parts are found

The parts are not known in advance. Each is written when the onboarding finds
it, and the developer adds the next ones as desk-check notes on this Flight.

A part changes stereorepo: its tools, bundle or disciplines. The adoption
itself changes fitch-mvp, which is outside this repository's tree, so the
developer does it with an agent session in fitch-mvp rather than through this
loop, and records what it found here.

## Findings for the adoption procedure

What the procedure written after this Flight must cover, as the onboarding
finds it:

- A repository may keep its own decision log or roadmap. The procedure asks
  which subjects each one keeps, rather than assuming Decision Records and the
  board replace them. *Covered by Adoption's* "Settle the product's own records" *step* (`ADOPT.md`).
- A repository may use another version-control layer over git. The procedure
  checks that layer holds nothing git lacks before removing it.
  *Covered by Adoption's* "Retire another version-control layer" *step* (`ADOPT.md`).
- No tool applies the plan. The first pass copied `managed_items`,
  `template_items` and `symlink_items` from `lib.bundle` as
  `test_specialization.py` does, and integrated `.gitignore`, `AGENTS.md` and
  `README.md` by hand. *Covered by Adoption's* "Plan the adoption", "Copy
  the managed items" *and* "Integrate the template items" *steps* (`ADOPT.md`):
  `just adapt plan` lists only what the target tracks and no scaffold-only
  path, `bundle.py sync` (DR-315) copies the managed items, and the
  integrate and conflict entries stay a step done by hand.
- stereorepo's `.gitignore` ignores `.agents/` as a compiled harness
  directory, and fitch-mvp tracked two hand-written skills there. Moving them
  to `.claude/skills/` merges them: render compiles that directory, with the
  inherited skills, into `.meta/.apm/skills/` and `.agents/`
  (`lib/apm_compile/skills.py`), so `.agents/` can be ignored as it is here.
  The procedure moves a product's harness skills to `.claude/skills/`.
  *Covered by Adoption's* "Move harness skills" *step* (`ADOPT.md`).
- stereorepo's inherited vocabulary and wiki have Claim, Evidence and
  Decision, and fitch-mvp's domain has its own Claim, Evidence and Decision.
  The procedure lists the domain terms that share a label with an inherited
  one, so that each is recorded as confusable in `domain_vocabulary.yaml`.
  *Covered by Adoption's* "Write the assertions" *step* (`ADOPT.md`). `cited-slots-in-portfolio-schemas` addresses the
  same clash in the gate: a citation of a slot of the product's `Decision`
  passes once its Project names its schema.
- The template's DR-001 says the portfolio was specialized from stereorepo.
  An adopted repository needs an entry that says it was adopted, and
  rejects starting a new repository. *Covered by Adoption's* "Record the adoption" *step* (`ADOPT.md`).
- An existing product needs a gate that prints Article 21 lines, and
  `just bootstrap` only creates seed projects. fitch-mvp has a hand-written
  `gate.py` that wraps its build and pytest. *Covered by Adoption's* "Write
  the product's gate" *step* (`ADOPT.md`) for writing that gate. Three parts let such a gate do its job in the loop:
  `project-at-repository-root` sends a change to a product at the root to its
  Project's gate, `landing-gate-holds-on-could-not-run` holds a landing whose
  Neo4j step could not run, and `portfolio-steps-without-subject` removes the
  two `meta` steps that would otherwise hold every landing.
- The gate in the loop's worktree has no `.venv`. A portfolio cannot declare
  the `just setup` recipe the loop runs, because the `justfile` is rendered
  (`.meta/lib/render/writers.py`). fitch-mvp avoids the need: its gate runs
  under `uv run --with-requirements`. *Covered by Adoption's* "Write the product's gate" *step* (`ADOPT.md`).
- An existing codebase fails the comment, suppression and size ratchets on
  its first gate. The checks' own remedy is a baseline under `.meta/checks/`,
  which the bundle owns as managed, so a sync could overwrite it.
  `portfolio-owns-ratchet-baselines` moved the portfolio's counts to
  `.meta/baselines/`, which no sync touches (DR-314).
  *Covered by Adoption's* "Render, baseline and check" *step* (`ADOPT.md`).
- A Product needs a primary Persona, and fitch-mvp has none yet, so its
  structure declares Projects and no Product.
  *Covered by Adoption's* "Write the assertions" *step* (`ADOPT.md`).

## Desk-check brief

**What was delivered, in stereorepo.** Five parts, each in `issues/done/`
with its change on `main`:

- `adapt-plan-reads-tracked-files`: `just adapt plan` lists only what a git
  target tracks (`.meta/lib/adapt/tracked.py`). For fitch-mvp the plan fell
  from 3,094 `RETAIN` entries to 96, with 2 `INTEGRATE` and 4 `CONFLICT`.
- `cited-slots-in-portfolio-schemas`: a Project in `structure.yaml` names its
  LinkML schemas in `schemas`, and `cited schema slots` resolves the product's
  `Decision` slots against them (DR-304).
- `landing-gate-holds-on-could-not-run`: a gate step reported `?` (Neo4j or
  Docker missing) pauses the loop instead of landing. `just pair-status` names
  the step, and `just pair` re-runs the gate once Docker is up.
- `project-at-repository-root`: a Project declared with `name: .` takes every
  path no deeper Project holds, except `issues/`, `.meta/` and what the bundle
  places, which stay with `meta` (`pair/touched.py`, DR-303).
- `portfolio-steps-without-subject`: a portfolio no longer gets `.meta/adapt.py`,
  `.meta/lib/adapt/` or the brownfield probe, and `comment probes` keeps every
  Python Project's gate in lockstep with `comments.py` (DR-305). Its `meta`
  gate reports no `?`, so it passes with `CI` set and does not hold every
  landing.

Every finding under "Findings for the adoption procedure" now says whether a
part addresses it. None is fully closed by a part: all ten wait for the
procedure.

**Where to see it.** `pair/test_pair.py` (`GateSelectionTest`, and the
`?`-gate pause tests), `.meta/checks/probes/citations.py`,
`.meta/checks/probes/tools/lockstep.py`, and `CI=1 just test-specialization`.

**Not checked: fitch-mvp itself.** The seats cannot read
`/Users/christopher/fitch-mvp`, so nothing here confirms any of the three
desk-check points there. To pick up these parts, fitch-mvp needs, at least:

- its bundle synced again, so that it carries the new `pair/touched.py`,
  `pair/loop.py` and checks, and drops `.meta/lib/adapt/` and the brownfield
  probe (no tool yet removes them from an adopted repository;
  `adoption-plan-omits-scaffold-only-paths` is in the backlog);
- its root Project declared with `name: .` and its `gate`, and its schemas
  named under that Project's `schemas`.

**Worth trying.**

- In fitch-mvp, `just gate` inside a seat's sandbox: the Neo4j tests should
  report `?` and the run should pass. Then land an Issue through
  `uv run --script <stereorepo>/pair/pair.py run` with Docker stopped: it
  should pause naming the Neo4j step, and land after you start Docker and run
  it again.
- A change touching only `tests/` there should run the product's gate, and
  one touching only `issues/` should not.
- Decide whether the ratchet-baseline finding (a managed baseline a sync could
  overwrite) needs a part before a second onboarding: no part addresses it.

## Desk-check notes

fitch-mvp is onboarded: its `main` holds the bundle and its own assertions,
its whole gate passes (90 steps across the `meta` and `fitch` Projects), and
its first Issue, `docs-cite-current-slots`, landed through the pair loop with
the Neo4j step run. These notes are what that onboarding found and the parts
have not yet fixed. The seats cannot read fitch-mvp, so each note carries what
it showed.

- **A fresh worktree fails the `meta` gate until it is rendered.** The `apm
  package` and `rendered prose` steps read `.meta/apm.yml`, which is a render
  output that git ignores, so a worktree that has never run `just render`
  fails both ("Not an APM project - no apm.yml found") whatever the branch
  changed. A seat cannot render to fix it: `render.py` writes `.claude/skills/`
  first, which the seat's sandbox forbids, and stops before it writes
  `apm.yml`. In fitch-mvp the seats got past it by copying `apm.yml` from the
  developer's checkout, which holds only while the assertions are unchanged.
  Wanted: a new worktree of an unchanged `main` passes `just gate meta`
  without anyone rendering in it, whether because the gate compiles the
  package first, the loop renders when it creates the worktree, or
  `render.py` writes `apm.yml` before the harness files. Check whether
  stereorepo's own worktrees hit this too.
- **Syncing an adopted portfolio removes what the bundle drops.** Nothing
  syncs a portfolio with stereorepo. fitch-mvp was synced twice by copying
  `lib.bundle`'s `managed_items()` over it, which never deletes. When DR-305
  made `.meta/adapt.py`, `.meta/lib/adapt/` and
  `.meta/checks/probes/tools/test_brownfield.py` scaffold-only, fitch-mvp kept
  its copies, and their probe reported `?` until they were removed by hand.
  Wanted: a recipe that syncs a portfolio from a stereorepo checkout, copying
  managed items, removing the managed paths the bundle no longer lists and
  the scaffold-only ones, and leaving template items and the portfolio's own
  files alone.
- **The ratchet baselines are the portfolio's, not the bundle's.**
  `.meta/checks/*.baseline.yaml` sit inside `.meta/checks/`, a managed
  directory, so each sync of fitch-mvp overwrote its comment baseline (418
  existing comments across 27 files) with stereorepo's, and it had to be
  restored from git each time. An adopted codebase depends on its baselines
  from its first gate. Wanted: a sync never overwrites a portfolio's
  baselines, whether they move out of the managed directory or the bundle
  marks them as the portfolio's.
- **Fold `adoption-plan-omits-scaffold-only-paths` into this Flight.** That
  backlog Issue already describes the planner's half of DR-305: it still
  plans `.meta/lib/adapt/` and the brownfield probe into an adopted
  repository. Make it a part by setting its `parent:` to this Flight, rather
  than writing a new Issue for it.
- **Write the adoption procedure.** Specialization covers an empty
  repository and nothing covers an existing one. Write Adoption as a
  Discipline beside Specialization, rendered as `SPECIALIZE.md` is, from
  what fitch-mvp needed: the ten findings above in "Findings for the adoption
  procedure", the sync recipe from the note above, and three more that the
  onboarding found after the parts landed. First, the loop keeps its worktree
  at `worktrees/pair`, inside the portfolio's tree, so a product tool that
  walks the tree must be kept out of it: fitch-mvp's pytest collected the
  worktree's copy of its tests and failed on duplicate modules until a
  `pytest.ini` set `testpaths = tests`. Second, an adopted repository may
  need its interpreter pinned for its gate: `uv` defaults to Python 3.14, on
  which one of fitch-mvp's pinned requirements does not build, so its gate
  runs under `--python 3.13`. Third, prose about a product's own schema slots
  is checked against that schema only once the Project's `schemas` names it,
  so the procedure declares the schemas before the first gate.

## Desk-check children

- `adoption-discipline`
- `fresh-worktree-passes-meta-gate`
- `portfolio-owns-ratchet-baselines`
- `sync-portfolio-recipe`

The existing backlog Issue `adoption-plan-omits-scaffold-only-paths` is a
part too: its `parent:` now names this Flight.
