---
difficulty: medium
parent: onboard-fitch-mvp
---

# The Adoption probe passes in a portfolio

In fitch-mvp, after a sync, the `meta` gate's `rendered artifact probes` step
fails with "assertions/disciplines.yaml holds no Adoption Discipline".
`_probe_adopt` in `.meta/checks/probes/files/rendered.py` reads
`assertions/disciplines.yaml`, which only stereorepo has: a portfolio's
Disciplines are under `assertions/imported/`, which holds no Adoption. The
probe therefore fails in every portfolio, specialized or adopted. Its own
docstring says that in a portfolio `pages.adopt()` must render no `ADOPT.md`,
which is what it should check there instead.

`just test-specialization` runs a specialized portfolio's whole gate (step 8,
`step_8_run_gate` in `.meta/test_specialization.py`) and should have caught
this. Grooming found that nothing runs it before landing: no gate step, and
no step of the pair loop, calls `.meta/test_specialization.py`. Only the unit
probes in `.meta/checks/probes/tools/test_specialization.py` run. A probe
whose behaviour differs between stereorepo and a portfolio is therefore
tested only on the stereorepo side. `_probe_fallbacks_without_specialize` in
`rendered.py` shows how this has been handled before: it runs the check over
a view shaped like a portfolio, from inside stereorepo's own gate.

## Wanted

- `_probe_adopt` splits on what `assertions/disciplines.yaml` holds:
  - If the file is absent or holds no Adoption Discipline (a portfolio),
    the probe reports no problem when `pages.adopt()` returns `None`. It
    reports a problem when `pages.adopt()` answers a page.
  - If the file holds Adoption (stereorepo), the probe keeps its current
    checks: every step's name is on the page, and `adopt()` returns `None`
    over the two views shaped like a portfolio.
- Stereorepo's own `meta` gate exercises the portfolio branch. Run
  `_probe_adopt` with `record.load` answering a portfolio's
  `assertions/disciplines.yaml`, once absent and once without Adoption, using
  the approach `_adopt_over` already takes. Assert that it returns no
  problems. If the old "holds no Adoption Discipline" early return comes
  back, this check fails in stereorepo before it lands.
- Before writing the fix, the implementer confirms the finding above: that
  nothing runs `just test-specialization` before landing. If that turns out
  to be wrong, record the real reason here instead.

## Out of scope

- Fixing fitch-mvp itself. It picks up the change at its next `just sync`.
- Adding `just test-specialization` to the gate or to the pair loop. It
  builds and gates a whole portfolio, which is too slow for every landing.
  If that should change, write it as a new Issue.
- Auditing the other probes for the same split between stereorepo and a
  portfolio. Write any found as new Issues.

## Done when

- Running `rendered_artifact_probes()` with `record.load` answering an absent
  `assertions/disciplines.yaml`, or one with no Adoption, returns no Adoption
  problems. Over stereorepo's real assertions it still names any missing step.
- Restoring the early return `["assertions/disciplines.yaml holds no Adoption
  Discipline"]` makes the new check in stereorepo fail.
- `just test-specialization` step 8 reports no `rendered artifact probes`
  problem about Adoption. A failure there from another probe goes in a new
  Issue, per Out of scope, and does not hold this one back.

## The plan

Everything happens in `.meta/checks/probes/files/rendered.py`. `pages.adopt()`
(`.meta/lib/render/pages.py:199`) already answers `None` where
`assertions/disciplines.yaml` holds no Adoption, so it does not change.

1. **Confirm the finding.** Search `.meta/gate`, `.meta/checks/`, `pair/`
   and `justfile` for anything that calls `test_specialization.py` outside
   its unit probes. If something does run it, replace the second paragraph
   of this file with the real reason.
2. **Generalize `_adopt_over` into `_disciplines_as(held, fn)`.** It swaps
   `record.load` so that `assertions/disciplines.yaml` reads as `held`,
   calls `fn()`, and puts the original back in a `finally`. `_probe_adopt`
   and `pages._procedure` both look up `record.load` on the module each time
   they call it, so one swap reaches both. The two places that now call
   `_adopt_over` call `_disciplines_as(held, pages.adopt)` instead.
3. **Split `_probe_adopt` on what it reads.** If `adoption is None`, return
   `[]` when `pages.adopt() is None`, and otherwise return
   `["adopt() answers a page though assertions/disciplines.yaml holds no Adoption"]`.
   When Adoption is present, keep the current step-name and two-view checks
   unchanged. Rewrite the docstring to describe both branches.
4. **Add `_probe_adopt_in_a_portfolio()`.** For each of the two portfolio
   views, absent (`None`) and `without` (the real Disciplines minus
   Adoption), it runs `_disciplines_as(held, _probe_adopt)` and prefixes
   each problem with its label, following the pattern of
   `_probe_fallbacks_without_specialize`. Build `without` from
   `record.load(...) or {}` so the probe also runs in a portfolio. Call it
   from `rendered_artifact_probes()` after `_probe_adopt()`.

**Tests.** To call the check directly, run
`rendered_artifact_probes()` from `.meta/` (for example
`uvx --python 3.13 --with linkml --with pyyaml python -c "from checks.probes.files.rendered import rendered_artifact_probes as r; print(r())"`).
It prints `[]` today. `checks.collect` imports `linkml_runtime`, so
`--with linkml` is needed. Then check that each guard can fail:
- Put back the old early return
  `return ["assertions/disciplines.yaml holds no Adoption Discipline"]`.
  The new probe must report it under both labels. Revert.
- Make `pages.adopt()` return a page unconditionally. Both the portfolio
  branch and the existing two-view checks must report it. Revert.

Then run `just test-specialization` once, and record in this file that
step 8 shows no Adoption problem.

**Risk.** `record.load` is a global that the probe replaces while it runs.
If an exception escapes without the `finally`, later checks in the same run
would read the swapped value, which is why every swap goes through
`_disciplines_as`. Also, `just test-specialization` is slow and may fail at
step 8 on some other probe. Per Out of scope, such a failure goes in a new
Issue.

## Notes from the work

- **The finding is confirmed.** Outside its own unit probes, the only
  references to `test_specialization.py` are the `justfile` recipe and the
  writer that renders it (`.meta/lib/render/writers.py`). No gate step and
  nothing under `pair/` runs it.
- **The change, as planned.** In `.meta/checks/probes/files/rendered.py`:
  - `_adopt_over` became `_disciplines_as(held, fn)`.
  - The two portfolio views moved into `_portfolio_views(real)`, which
    `_probe_adopt` and the new `_probe_adopt_in_a_portfolio` both use.
  - `_probe_adopt` now returns `[]` where there is no Adoption and
    `adopt()` answers `None`.
- **Watched failing.** Run from `.meta/`, `rendered_artifact_probes()`
  prints `[]`. With the old early return put back,
  `_probe_adopt_in_a_portfolio()` reports "holds no Adoption Discipline"
  under both labels. With `pages.adopt` replaced by `lambda: "page"`, the
  stereorepo branch reports every missing step and both views, and the
  portfolio branch reports "answers a page though … holds no Adoption"
  under both labels.
- **`just test-specialization`**, run once after the change, passed all
  nine steps. Step 8 showed no Adoption problem. It was not run against
  the old code to watch step 8 fail there.
