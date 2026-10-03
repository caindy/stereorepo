# State the Python 3.13 prerequisite in ADOPT.md

DR-351 asserts the Python 3.13 floor "where a fresh clone reads first".
`README.md` and `SPECIALIZE.md` both state it, but `ADOPT.md` does not, even
though adoption copies the same `.meta/` tooling and `check.py` refuses an
older interpreter. The fix is the same as for `SPECIALIZE.md`
(`specialize-python-prerequisite`). The Adoption Discipline in
`.meta/assertions/disciplines.yaml` states the floor in its first step,
citing DR-351. DR-351 adds `work:artifact/adopt` to its `enacted_in`, and gains a consequence that names
`ADOPT.md`. Then `ADOPT.md` is re-rendered.
