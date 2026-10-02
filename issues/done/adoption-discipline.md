---
difficulty: medium
parent: onboard-fitch-mvp
waits_on:
  - sync-portfolio-recipe
  - portfolio-owns-ratchet-baselines
  - adoption-plan-omits-scaffold-only-paths
---

# Write Adoption as a Discipline beside Specialization

Specialization covers an empty repository, and nothing covers an existing
one. Write Adoption as a Discipline beside Specialization, rendered as
`SPECIALIZE.md` is, from what fitch-mvp needed.

It covers:

- the ten findings under "Findings for the adoption procedure" in the
  Flight `onboard-fitch-mvp`;
- the sync recipe of `sync-portfolio-recipe`;
- keeping product tools out of the loop's worktree. The worktree sits at
  `worktrees/pair`, inside the portfolio's tree, so a product tool that walks
  the tree finds it. fitch-mvp's pytest collected the worktree's copy of its
  tests and failed on duplicate modules until a `pytest.ini` set
  `testpaths = tests`;
- pinning the interpreter for an adopted repository's gate where it needs
  one. `uv` defaults to Python 3.14, on which one of fitch-mvp's pinned
  requirements does not build, so its gate runs under `--python 3.13`;
- declaring the product's schemas before the first gate. Prose about a
  product's own schema slots is checked against that schema only once the
  Project's `schemas` names it (DR-304).

## Wanted

- A Discipline named Adoption, with id `work:discipline/adoption`, in
  `.meta/assertions/disciplines.yaml` beside Specialization, with the same
  fields: `description`, `judgement`, ordered `steps` and `produces`. Its
  judgement is what no tool decides: which of the product's own records
  (decision log, roadmap) stay and which move to Decision Records and the
  board, which domain terms clash with inherited ones, and how the gate
  integrates `README.md`, `AGENTS.md` and `.gitignore`.
- A generated page at the root, `ADOPT.md`, rendered from it by a function
  beside `pages.specialize` in `.meta/lib/render/pages.py` and registered in
  `.meta/lib/render/targets.py`. Like `SPECIALIZE.md`, it is scaffold-only:
  listed in the scaffold-only paths of `.meta/lib/bundle/__init__.py`, absent
  from a portfolio, and the page renders nothing where the assertions hold no
  Adoption Discipline. Every place `SPECIALIZE.md` is wired in gets the
  same for `ADOPT.md`: a `work:artifact/adopt` entry with `preamble` and
  `postamble` in `.meta/assertions/structure.yaml` (not the imported one, so
  a portfolio inherits none), `RENDERED_TARGETS` in `.meta/terms.py`, and
  `SCAFFOLD_ONLY` in `.meta/checks/files/scaffold.py`.
- Steps that run the tools that now exist instead of describing hand work:
  `just adapt plan` for the plan, `just sync` for copying managed items and
  removing what the bundle drops, and the ratchet baselines a portfolio owns
  (DR-314) for an existing codebase's first gate.
- The Flight `onboard-fitch-mvp` edited so that each finding marked *Waits for
  the procedure* names the Adoption step that covers it.
- `README.md`, the directory table in `AGENTS.md` (`CLAUDE.md` is a symlink
  to it) and any other place that lists `SPECIALIZE.md` as the generated
  procedure also list `ADOPT.md`, as the entry point for a repository that
  already exists.

## Out of scope

- New tools for the findings that have none: writing a product's gate,
  declaring a `just setup` for the loop's worktree, a template for an
  adopted DR-001. The step says what to do by hand; a tool, if wanted, is a
  new Issue in `issues/backlog/`.
- Changing fitch-mvp. The seats cannot reach it.
- Changing Specialization's steps, beyond a cross-reference to Adoption if
  one reads naturally.

## Done when

- `ADOPT.md` exists at the root of this repository, generated from the
  Adoption Discipline, and re-rendering leaves it unchanged.
- Each item in the list above is a step of it, or is named as handled by a
  tool that a step runs.
- Each finding in the Flight that says *Waits for the procedure* names the
  step that covers it.
- A specialized portfolio carries no `ADOPT.md` and its render writes none.
  `step_7_verify_scaffold_paths` in `.meta/test_specialization.py` already
  walks `SCAFFOLD_ONLY_PATHS`, so the bundle entry brings `ADOPT.md` under
  it; a test asserts `pages.adopt()` answers `None` over assertions holding
  no Adoption Discipline, as `specialize()` does for a portfolio.

## The plan

### Seams

- `.meta/assertions/disciplines.yaml`: the Adoption Discipline, after
  Specialization. Only this file, not `imported/`: a portfolio adopts
  nothing, as it specializes nothing. `pages.disciplines()` already renders
  every Discipline in this file into `.meta/disciplines.md`, so that page
  picks it up with no change.
- `.meta/lib/render/pages.py`: `specialize()` and a new `adopt()` share one
  body. Pull it into a private `_procedure(name, target)` that answers
  `None` when `assertions/disciplines.yaml` holds no Discipline of that
  name, and make both public functions one-line calls with their own
  docstrings. Export `adopt` from `.meta/render.py` beside `specialize`.
- `.meta/lib/render/targets.py`: `"../ADOPT.md": pages.adopt`. A target
  that answers `None` writes nothing, so a portfolio gets no page.
- `.meta/assertions/structure.yaml`: `work:artifact/adopt` with `preamble`
  and `postamble`, after `work:artifact/specialize`. The preamble says the
  page is for an existing repository and points to `SPECIALIZE.md` for an
  empty one; the postamble routes to `.meta/README.md`, as Specialization's
  does. `prose.py`'s own-prose check skips it because the path starts with
  an entry of `SCAFFOLD_ONLY`.
- Scaffold-only lists: `"ADOPT.md"` in `SCAFFOLD_ONLY_PATHS`
  (`.meta/lib/bundle/__init__.py`) and `SCAFFOLD_ONLY`
  (`.meta/checks/files/scaffold.py`), which must stay the same set, and in
  `RENDERED_TARGETS` (`.meta/terms.py`). With the bundle entry, `just sync`
  removes the page from a portfolio and `step_7_verify_scaffold_paths`
  checks that it is absent.
- `README.md` (lines 21 and 50) and the `AGENTS.md` directory table and
  Conventions line: add `ADOPT.md` as the entry point for an existing
  repository.
- `.gitattributes` is generated from the targets that answer a page, so
  the render adds `/ADOPT.md merge=union`; commit it with the page. A
  portfolio's stays without it, because `adopt()` answers `None` there.
- `issues/backlog/onboard-fitch-mvp.md`: replace each *Waits for the
  procedure.* with *Covered by Adoption's* "<step>" *step.*

### Steps of the Discipline (draft; the wording is settled when written)

Each finding from the Flight is shown in brackets.

1. **Plan the adoption.** From a stereorepo checkout, run `just adapt plan`
   against the repository. It lists only the paths the target tracks and no
   scaffold-only path. [no tool applies the plan, first half]
2. **Settle the product's own records.** For each decision log or roadmap
   the repository keeps, decide which subjects stay there and which move to
   Decision Records or the board. [own decision log or roadmap]
3. **Retire another version-control layer.** Remove a layer over git only
   after checking that it holds nothing git lacks. [other VCS layer]
4. **Copy the managed items.** Run `<checkout>/.meta/bundle.py --root
   <repo> sync <checkout>` for the first sync, because the repository has no
   `sync` recipe yet, and the checkout's own `just sync` cannot reach it:
   `--root` is an option of `bundle.py`, not of its `sync` subcommand, and
   the recipe places its arguments after `sync`. After that, run
   `just sync <checkout>` in the repository (DR-315).
   [no tool applies the plan; the sync recipe]
5. **Integrate the template items.** Work through the plan's `INTEGRATE`
   and `CONFLICT` entries. `README.md`, `AGENTS.md` and `.gitignore` keep
   their own content beside the stereorepo conventions. Link the agent
   files to `AGENTS.md`. [no tool applies the plan, second half]
6. **Move harness skills.** Hand-written skills under `.agents/` or another
   harness directory move to `.claude/skills/`, which render compiles.
   [`.agents/` is ignored]
7. **Record the adoption.** DR-001 says the repository was adopted, and
   rejects starting a new repository. [DR-001]
8. **Write the assertions.** Declare the root Project with `name: .`
   (DR-303), with its `schemas` (DR-304) and `gate`. Declare a Product only
   once there is a primary Persona. Record each domain term that shares a
   label with an inherited term as confusable in `domain_vocabulary.yaml`.
   [Claim, Evidence and Decision clash; schemas before the first gate;
   no Persona]
9. **Write the product's gate.** A gate prints Article 21 lines and wraps
   the product's build and tests. It runs under `uv run
   --with-requirements`, because the loop's worktree has no `.venv`, and
   pins `--python` where a requirement does not build on `uv`'s default.
   It keeps the product's own tools out of `worktrees/`, for example with
   pytest's `testpaths`. A step that cannot run reports `?`. [gate;
   no `.venv`; interpreter; worktree]
10. **Render, baseline and check.** Run `just render`, then the gate. Write
    the counts the existing code already has into `.meta/baselines/`
    (DR-314), not into `.meta/checks/`. Both must pass before going on.
    [ratchets]
11. **Confirm scaffold-only paths absent**, as Specialization's step does.
12. **Commit.**

`produces`: an existing repository that holds the bundle and its own
assertions, whose Issues land through the pair loop.

### Order

1. The scaffold-only lists, the target, `_procedure` and `adopt()`, and the
   Artifact entry. Render and confirm that `ADOPT.md` is not written yet,
   because no Discipline exists.
2. The Discipline, then render: `ADOPT.md` and `.meta/disciplines.md`
   appear.
3. `README.md` and `AGENTS.md`, then the Flight's findings.

### Tests

- A probe beside `_probe_fallbacks_without_specialize` in
  `.meta/checks/probes/files/rendered.py` swaps `record.load` so that
  `assertions/disciplines.yaml` reads as absent, and then as holding only
  Specialization. In both cases `pages.adopt()` must answer `None`. Over the
  real assertions it must answer a page that holds every step's name.
  Swapping `record.load` is new to the probes, so it is restored in a
  `finally`, as `targets.TARGETS` is there.
- `CI=1 just test-specialization`: the portfolio it builds has no
  `ADOPT.md` after its render (`step_7_verify_scaffold_paths`).
- Running `just render` twice leaves the tree clean.

### Risks

- `.meta/disciplines.md` is an inherited page, and the Discipline's
  statements name `pair/` and `worktrees/pair`. That page is generated and
  is not in the inherited copy set the scaffold-only scan reads, which is
  why Specialization's "Confirm scaffold-only paths absent" step already
  passes. Confirm this on the first
  render.
- Adding a Discipline makes `adoption` a known concept for
  `lib/wikisplain/links.py`, but `just render` embeds no wikilinks (only
  `/wikisplain` does, into the page it scaffolds), so "Language adoption" in
  Specialization's "Choose languages and bootstrap" step is not touched. The only effect is that
  `[[adoption]]` now resolves, which is wanted.
- `.meta/checks/files/sources.py` `inherited()` and
  `read_inherited_paths` in `.meta/test_specialization.py` read path tokens
  from `disciplines.yaml`, but both filter on
  `work:discipline/specialization`, so backticked paths in Adoption's steps
  do not leak into the inherited set.
- A17 may ask for a wiki page for the new Discipline. Specialization has
  none in `wiki/stereorepo/`, so it probably does not, but if the gate asks,
  add the page with `/wikisplain` rather than exempting it.

## Implementation notes

- The Discipline has the twelve steps the plan drafted, under the same
  names. `ADOPT.md` and `.meta/disciplines.md` are rendered from it, and the
  render added `/ADOPT.md merge=union` to `.gitattributes`.
- `pages.specialize()` and `pages.adopt()` are now one-line calls to
  `_procedure(name, target)`. `specialize()`'s output is byte-identical.
- In the seat's sandbox, `just render` stops with `PermissionError` when it
  writes `.claude/skills/wikisplain/SKILL.md`. That happens after the root
  pages are written but before `.gitattributes`. Every other render target
  matched the disk, so `.gitattributes` was written from
  `targets.rendered(targets.snapshot())`, which is the bytes `just render`
  writes. A full `just render` outside the sandbox should leave the tree
  unchanged.
- The probe is `_probe_adopt` in `.meta/checks/probes/files/rendered.py`.
  It runs under `rendered artifact probes`. Its helper `_adopt_over` swaps
  `record.load` and restores it in a `finally`.
- `RENDERED_TARGETS` in `.meta/terms.py` holds `"SPECIALIZE.md", "ADOPT.md"`
  on one line. This keeps the file at its file-size baseline instead of
  raising it.
- In `onboard-fitch-mvp`, every *Waits for the procedure* became *Covered
  by Adoption's* "<step>" *step*. The desk-check brief's sentence "all ten
  wait for the procedure" is left as it was, because it records what that
  brief found at the time.
- Not run here: `CI=1 just test-specialization`. Its
  `step_7_verify_scaffold_paths` reads `SCAFFOLD_ONLY_PATHS`, which now
  holds `ADOPT.md`.
- Second seat's review: Specialization's "Confirm scaffold-only paths
  absent" step now names `ADOPT.md` too, since a portfolio must lack both
  pages, and `SPECIALIZE.md`'s preamble routes a repository that already
  holds a product to `ADOPT.md`. These are the only edits to
  Specialization, within the cross-reference the issue allows. The "Plan the adoption" step of Adoption
  names the target (`just adapt plan <repository>`), since the
  recipe defaults to the current directory, which is the checkout.
