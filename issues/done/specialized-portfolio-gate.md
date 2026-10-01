---
difficulty: medium
---

# Make a freshly specialized portfolio pass its own gate

`just test-specialization` specializes the scaffold into a scratch repository
and runs that portfolio's gate. The portfolio's `meta` Project fails five
steps. Every one of them also failed before the bootstrap removed PR First;
it went unnoticed because the test ran only in a weekly workflow.

## How to reproduce

Run `just test-specialization` at the root. The portfolio's gate reports `x`
on these steps:

- `rendered artifact probes`: the `rendered(None)` fallback is judged by
  whether it renders `../SPECIALIZE.md`, a target only the scaffold has
  (`.meta/checks/probes/files/rendered.py`, `_probe_fallbacks`).
- `dereference probes`: `--sample 4` finds 2 pairs, since a portfolio's
  record is smaller than the scaffold's.
- `brownfield adoption probes`: the probe reads `template/.meta/README.md`,
  which a portfolio does not have.
- `comment probes`: the probe imports the Python seed's `gate` module, which
  a portfolio has only once it bootstraps Python.
- `scaffold-only paths`: the Python bootstrap's APM skills, copied into
  `.meta/.apm/skills/`, name `bootstraps/`.

## Wanted

Each step passes in a portfolio without being weakened in the scaffold. A
probe that exercises something only the scaffold has either moves among the
scaffold-only paths, so specialization removes it, or passes over the absence
the way the specialization probe already does, reporting `?` with what it
could not check rather than `ok`. A probe whose threshold assumes the
scaffold's size (the dereference sample) scales to what the portfolio has.

## Out of scope

- Running `just test-specialization` from `just gate`. It is slow, and whether
  it belongs there is a separate question.
- Failures that a portfolio's other Projects might have once it bootstraps a
  language.
- The `cited schema slots` step, which reports `?` when `git log` times out
  in the scratch repository. That `?` is honest, and it is not one of the five.

## Done when

- `just test-specialization` exits 0, and its portfolio summary reports no
  `meta` step as `x`.
- In the scaffold, each of the five steps runs the same checks against the
  same inputs as before. The dereference sample stays at 4 when there are
  enough pairs to draw from.
- In a portfolio, a step that cannot do its check because the scaffold-only
  material it needs is missing reports `?` and names what is missing. It does
  not report `ok`. A step whose input exists only in the scaffold leaves the
  portfolio altogether, by being listed among the scaffold-only paths.
- Each probe changed to report `?` has a test that runs it against a tree
  missing the scaffold-only input, and that test asserts the `?` outcome and
  its message. The rendered artifact probe has a test that its fallback check
  passes over a set of default targets without `../SPECIALIZE.md`. The
  dereference probe has a test with fewer pairs than the default sample, and
  that test asserts the sample shrinks to fit.
- No skill copied into `.meta/.apm/skills/` by the Python bootstrap names
  `bootstraps/`. Alternatively, the scaffold-only paths check stops treating
  bootstrap-copied skills as portfolio content. Either way, the scaffold's own
  check still catches a genuine `bootstraps/` reference in portfolio content,
  and a test shows it doing so.

## The plan

Each of the five steps can be fixed on its own, so the order below is just
cheapest first. Every probe step is registered from `.meta/checks/probes/`,
and a step may take a parameter with a default as a seam for a probe to pass
a fake through (`checks.collect.check`).

1. **Scaffold-only paths.** The portfolio's `.meta/.apm/skills/py-*` are not
   inherited files. `bootstrap.py` (`install_bootstrap_apm_package`) copies
   the Python bootstrap's skills into `.claude/skills/`, and the portfolio's
   `apm_compile` (`lib/apm_compile/skills.py`, the `.claude/skills` loop)
   then brings them into `.meta/.apm/skills/`. The fault is in the eight
   skills' own text, so fix it at the source: reword the one line in each of
   `bootstraps/python/skills/*/SKILL.md` that names `bootstraps/`. Line 22 is
   the "such as `bootstraps/python/seed`" example in the Target contexts
   block, and `py-quality-setup` line 122 names the seed's `pyproject.toml`.
   Describe the Project generically ("the Project
   `just bootstrap python <path>` lays down"). Do not just qualify the line
   with "stereorepo's": `files/scaffold.py` would exempt it, but the skill
   then points a portfolio at a path it does not have. `lint-gate.py` in
   `py-git-hooks` also names `bootstraps/`, but the check scans only `.md`
   and `.yaml`, so leave it. Then run
   `just render` so `bootstraps/python/.apm/skills/` is regenerated
   (`lib/apm_compile/bootstrap.py`). Afterwards, check that
   `grep -rn 'bootstraps/' bootstraps/python/skills --include=SKILL.md`
   finds nothing.
   For the test, pull the per-line scan in `scaffold_only_paths` out into a
   module-level function: given a path, the names and the root, it returns
   the problem lines. Add a `scaffold-only path probes` step in a new
   `checks/probes/files/scaffold.py`, re-exported from
   `checks/probes/files/__init__.py`. It writes a temporary `.md` file
   holding a bare `bootstraps/python/seed` and a line saying "stereorepo's
   `bootstraps/`", then asserts that the first is reported once and the
   second is not.
2. **Rendered artifact probes** (`probes/files/rendered.py`,
   `_probe_fallbacks`). Judge `rendered(None)` by `../.gitattributes`, which
   is in `targets.TARGETS` in every repository and is never `None`, instead
   of by `../SPECIALIZE.md`. Give `_probe_fallbacks` a test case: set
   `targets.TARGETS` temporarily to a map without `../SPECIALIZE.md` (one
   mock page plus `gitattributes`), restore it in a `finally`, and assert
   that the fallback reports nothing.
3. **Dereference probes** (`probes/tools/dereference.py`). Narrow
   `sample_durable` to the `DR-00n.yaml` files that exist. Count what is
   available with `deref.scope(..., everything=True, durable=...)`, then
   expect `min(4, available)` from `sample=4` and use `min(3, available)` for
   the repeatability pair. If nothing is available, that is a problem and the
   step does not pass. The step has no seam for `durable`, so move the
   sample assertions into `_sample_problems(deref, citations_mod, durable)`,
   which the step calls with the narrowed set. For the test, call it again
   from the step over a durable set of `DR-001.yaml` alone. Before relying on that set, first confirm in
   the scaffold that it yields fewer than four pairs. If it doesn't, pick a
   file that does.
   *Corrected in the work:* the shortfall was a bug in the tool, not only a
   threshold in the probe. `sampled` (`lib/dereference/reading.py`) filled
   its window from the pool written out twice, so a `sample` wider than the
   pool answered the same pair twice. `DR-001.yaml` holds one pair, and
   `sample=4` gave 2. The window is now `min(sample, len(pool))`, with the
   offset unchanged, so a pool at least as large as the sample rotates
   exactly as before. The probe also asserts that no pair is answered twice.
4. **Brownfield adoption probes** (`probes/tools/test_brownfield.py`). The
   adoption plan sources `.meta/README.md` and the rest of the bundle's
   template entries from `template/` (`.meta/bundle.yaml`). A portfolio has
   no `template/`. Give `test_brownfield_probes` the seam
   `scaffold_dir: pathlib.Path = META.parent`. Where
   `scaffold_dir / "template"` is absent, return
   `CouldNotRun("no template/ to adopt from: brownfield adoption is planned from the scaffold")`.
   Do that before any sub-check runs, because `_check_retains_and_integrations`
   would raise on the missing README. Change the return type to
   `StepOutcome`, with `Found` or `Passed` as now otherwise. The test is a
   probe case that calls it with a temporary directory holding no
   `template/` and asserts `CouldNotRun` with that message.
5. **Comment probes** (`probes/tools/comments.py`, `_seed_gate_sync`). When
   `ROOT / "bootstraps/python/seed/gate/src"` is absent, the sync check
   cannot run, but the other sub-probes still can. Make
   `_seed_gate_sync` take the seed directory as a parameter defaulting to
   that path, and have it return `None` for "absent" rather
   than a problem. `comment_probes` then returns `Found` if any sub-probe
   found something. If not, it returns `CouldNotRun` naming the missing seed
   gate and saying the remaining comment probes passed. Only when everything
   ran does it return `Passed`. Its test calls `_seed_gate_sync` with a
   temporary empty directory and asserts the absent result. A second check
   asserts that `comment_probes` wraps that result as `CouldNotRun` with the
   message. This may need the seam on `comment_probes` itself
   (`seed: pathlib.Path = ...`).
   *As built:* the step's last move is `_verdict(problems, synced,
   seed_gate)`, and the probe asserts on `_verdict` directly rather than
   running the whole step a second time inside itself. Running it again would
   repeat the mypy and ruff sub-probes. The step keeps a `seed_gate` seam.
6. **End to end.** Run `just test-specialization`. It should exit 0 with no
   `x` in the portfolio's `meta` summary. Brownfield and comment probes
   should show as `?` in its "steps that could not run" block. All five
   steps should report as they did before in the scaffold.

**Risks.**

- `?` fails the run under CI (`check.py`, `closing_block`, DR-261). So a
  portfolio whose CI sets `CI` will fail permanently on the two `?` steps,
  and `just test-specialization` will too if it runs with `CI` set.
  `step_8_run_gate` passes the environment through. The issue chose `?` over
  `ok` deliberately, so that stays. Instead, add a backlog Issue: steps whose
  subject a portfolio never has should leave the portfolio, which would need
  a sub-path exclusion in specialization (`SCAFFOLD_ONLY_PATHS` in
  `test_specialization.py` and `files/scaffold.py` match top-level names
  only).
- Brownfield adoption, and so `.meta/adapt.py`, may be scaffold-only in
  substance. Whether `adapt.py` should ship in a portfolio at all goes in the
  same backlog note, not this Issue.
- Rewording the skills changes generated files under
  `bootstraps/python/.apm/`. `rendered prose` pins them, so commit the
  regenerated output along with the source edit.
- In a portfolio, `import gate` in `_seed_gate_sync` relies on `sys.path`
  order. With the seed absent, nothing is imported, so no other `gate`
  module can be picked up by accident.

## Notes

- **The sandbox blocked `just render`.** It writes
  `.claude/skills/*/SKILL.md`, which the seat's sandbox denies. The eight
  regenerated `bootstraps/python/.apm/skills/*/SKILL.md` files were copied
  from `bootstraps/python/skills/` instead. That is what
  `python_bootstrap_primitives` does: it copies each file verbatim. Before
  the copy, each committed `.apm` file matched its source byte for byte, and
  `rendered prose` passes on the result.
- **What a portfolio reports now.** `just test-specialization --verbose`
  shows `ok` for `rendered artifact probes`, `dereference probes` and
  `scaffold-only paths` (81 files). It shows `?` for `brownfield adoption
  probes` and `comment probes`, each naming what is missing. In the
  scaffold, all five report `ok`, alongside the new `scaffold-only path
  probes` step. `cited schema slots` reported `?` in both, because `git log`
  timed out after 30 seconds. That is the sandbox, and it predates this
  Issue.
- **The two `?` steps fail a portfolio's run wherever `CI` is set.** That
  follow-up, with whether `.meta/adapt.py` belongs in a portfolio and
  whether a portfolio's seed sync should check its own Python Project, is
  `issues/backlog/portfolio-steps-without-subject.md`.
