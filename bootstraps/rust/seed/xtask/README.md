The gate for this workspace, as a cargo alias: `cargo xtask gate` runs every
step, and `cargo xtask <step>` runs one. It is a crate rather than a script so
that a Rust Project needs nothing but its own toolchain to be held to its
standard.

Every step answers to four rules, and they are the whole contract:

- **A5 — no gate step rewrites the tree.** Every cargo invocation here is a
  `--check`, a build or a test. Fixing is `cargo fmt` and `cargo clippy --fix`,
  run by a person, never from here.
- **A6 — every step has three outcomes.** [`Outcome::CouldNotRun`] is loud,
  unmarked and exits zero, so a missing tool is reported rather than passed.
  [`Outcome::Passed`] is marked. [`Outcome::Found`] is non-zero.
- **A7 — a check-mark is a claim about scope.** A passing step prints what it
  covered beside its mark, so `ok orphans` says how many files it looked at and
  under how many packages.
- **A21 — a gate reports each step in the one shape every gate here prints.**
  `ok`, `x` or `?`, the step, then what it covered, found, or could not do. The
  Portfolio's own gate prints the same lines, and a runner above the Projects
  reads both without knowing which language either is in.

The steps, in the order they run:

| Step | What it holds | Discipline |
|---|---|---|
| `fmt` | `cargo fmt --check` | Ratchet |
| `lints` | no lint switched off in a manifest or a cargo config | Ratchet |
| `clippy` | `cargo clippy` with every warning an error | Ratchet |
| `doc` | `cargo doc` with every rustdoc warning an error; no public item undocumented | Literate Programming |
| `test` | `cargo test`, doctests included | Literate Programming |
| `orphans` | every markdown file under a package is included by a source file | Nothing Unconsumed |
| `receipts` | every history entry names a test that exists | Nothing Unconsumed |
| `mutants` | `cargo mutants`, the signal behind the tests | Observed Failure |

The pure steps — `orphans`, `receipts`, `lints` — are functions over a path, so
`tests/probes.rs` can watch each of them fail against a tree built to fail it.
A guardrail never observed to fail is not evidence of anything.
