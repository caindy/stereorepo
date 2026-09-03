# The Rust standard

What a Rust project in a portfolio inherits, and the gates that hold it there.

| Discipline | Implemented in | State |
|---|---|---|
| Literate Programming | [`literate-programming.md`](literate-programming.md) | designed, not built |
| Observed Failure | — | not started |
| Ratchet | — | not started |
| Gates Do Not Fix | — | not started |
| Nothing Unconsumed | — | not started |
| Seeded Artifacts | — | not started |
| Written Decisions | — | not started |

The Disciplines are in `.meta/assertions/imported/disciplines.yaml`. This
directory only ever says **how** — a Bootstrap that restated a Discipline would
be a second copy of it, and the second copy is the one that drifts.

Nothing here is executable yet. There is no Rust in the repository, and
asserting a Project whose gate does not run would violate Gates Do Not Fix
before it was implemented.
