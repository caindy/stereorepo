# Keep rust-seed's tools off its gate's standard output

`just audit rust-seed rust` reports that rust-seed's gate prints 44 lines on
standard output in none of Article 21's shapes (stereorepo's DR-092): the
`cargo test` harness's `running N tests`, `test … ok` and `test result:` lines.
`cargo` in `bootstraps/rust/seed/xtask/src/lib.rs` lets the child's standard
output through, so `.meta/gate` cannot read the step report cleanly. This is
the Rust counterpart of `python-seed-gate-stdout`, which sent python-seed's
tools to standard error.

Send the tools' standard output to standard error, so only the `ok` / `x` /
`?` lines reach standard output. Done when `just audit rust-seed rust` reports
no gap about the gate's output shape.

Found while implementing `bootstrap-render-step`.
