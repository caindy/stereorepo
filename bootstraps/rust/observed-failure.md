# Observed Failure, in Rust

A guardrail never observed to fail is not evidence of anything. Two mechanisms,
one for the tests and one for the gate.

## The gate's own steps are watched failing

The pure steps of the xtask — `orphans`, `evidence`, `lints` — are functions
over a path, and [`seed/xtask/tests/probes.rs`](seed/xtask/tests/probes.rs)
builds a throwaway package under the target directory for each, breaks it the
way the step exists to catch, sees the finding, and puts it right. The
cargo-driven steps are watched through what they wrap: `evidence` compiles a
probe crate and reads the tests cargo lists, and the binary is run with a word
it does not know.

That is step one of the Discipline applied to the checker rather than to the
code. Anything added to the xtask arrives with the probe that fails it.

## Mutation testing is the signal behind the tests

**`cargo xtask mutants`** runs `cargo mutants` over the workspace. A mutant that
survives is a line the tests execute without checking, which is what coverage
cannot tell you (A3). The step is a finding when any viable mutant is missed,
and it is *could not run* — loud, unmarked, exit zero — when `cargo-mutants` is
not installed, so a missing tool is reported and not passed. The workflow
installs it, which is where the step is guaranteed to run.

The seed is clean under mutation, xtask included. Every step function has a
test that exercises it against its own output, because a gate whose own tests
pass against broken checks would be the failure the Discipline names.

## No coverage floor

None is set. A3 makes coverage a floor beneath the tests, and a floor is set
under something that exists; one module of eleven lines has nothing to hold
one at. The first real module sets it, with `cargo llvm-cov` as the likely
instrument, and the number goes beside its reason.
