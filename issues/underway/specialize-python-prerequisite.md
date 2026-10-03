---
difficulty: easy
---

# State the Python 3.13 prerequisite in SPECIALIZE.md

DR-268 said `README.md` and `SPECIALIZE.md` both state Python 3.13 or later
as a prerequisite for a fresh clone. Only `README.md` does; `SPECIALIZE.md`
names no Python version, so someone specializing from it alone meets the
floor only when `check.py` refuses their interpreter. DR-351, its successor,
records what the tree holds and leaves `SPECIALIZE.md` out.

## Wanted

The Specialization Discipline in `.meta/assertions/disciplines.yaml`, which
`SPECIALIZE.md` is rendered from, states Python 3.13 or later as a
prerequisite, citing DR-351, and DR-351 names `work:artifact/specialize` in
its `enacted_in` again. Whether that wants a new record or only a
consequence on DR-351 is part of the work.

## Done when

`SPECIALIZE.md`, re-rendered, states the Python 3.13 floor, and
`enacting citations` passes.
