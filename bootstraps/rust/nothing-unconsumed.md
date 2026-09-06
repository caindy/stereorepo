# Nothing Unconsumed, in Rust

An artifact prevents drift only if something consumes it, and the question after
"what reads this?" is "what is it checked against?"

## Code

The compiler holds it. `dead_code`, `unused_imports` and the rest are warnings,
and every warning is an error under the gate.

## Prose

**`cargo xtask orphans`** — every markdown file under a package is named in an
`include_str!` in one of that package's source files, resolved the way rustc
resolves it. The consumer is rustdoc; what it is checked against is the source
tree, because a file the source does not include is one rustdoc will not
render, however carefully it was written.

**`cargo xtask receipts`** — every history entry names a test, and the test is
one `cargo test -- --list` reports. The entry is consumed by a reader; what it
is checked against is the test suite. An entry whose test is gone is the
Discipline's "delete what nothing consumes", made mechanical.

## The gate itself

Every step is in `STEPS`, and `cargo xtask gate` runs `STEPS`. A step that
exists in the crate but not in that table cannot be written, since the table is
the only thing the binary reads. There is no orphan-script check because there
is nowhere for an orphan script to be.

The Bootstrap's own [`render`](render) is consumed by the `rust seed` job of the
workflow, which runs it and then runs the gate on what it produced.
