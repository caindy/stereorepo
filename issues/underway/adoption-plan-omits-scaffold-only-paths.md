---
difficulty: easy
parent: onboard-fitch-mvp
---

# Leave scaffold-only paths out of a brownfield adoption plan

`.meta/lib/adapt/plan.py` plans each `dir` item of `.meta/bundle.yaml` as a
whole (`_classify_dir` never looks inside). `.meta/lib/` and `.meta/checks/`
are such items, so a repository adopted from the plan gets `.meta/lib/adapt/`
and `.meta/checks/probes/tools/test_brownfield.py`. Neither has a subject
there: its `brownfield adoption probes` step reports `?` for good, which
fails the run wherever `CI` is set (DR-261).

`portfolio-steps-without-subject` makes these nested paths entries of
`SCAFFOLD_ONLY` and leaves them out of a specialized portfolio. The adoption
plan should leave out the same paths, and the `test_brownfield.py`
could-not-run branch can then go.
