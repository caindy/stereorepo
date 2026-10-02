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
`step_8_run_gate` in `.meta/test_specialization.py`) and should have failed
on this before `adoption-discipline` landed. It did not.

## Wanted

- In a portfolio, where `assertions/disciplines.yaml` is absent or holds no
  Adoption, `_probe_adopt` passes and checks that `pages.adopt()` writes
  nothing. In stereorepo it keeps checking every step's name.
- The reason `just test-specialization` missed the failure is written in this
  file, and that gap is closed, so that a probe failing only in a portfolio
  fails `just test-specialization` before it lands.

## Out of scope

- Fixing fitch-mvp itself; it picks the change up at its next `just sync`.
