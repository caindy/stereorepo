# Observed Failure, in Python

A guardrail never observed to fail is not evidence of anything. Two mechanisms,
one for the tests and one for the gate.

## The gate's own steps are watched failing

The pure steps of the gate — `lints`, `doc`, `orphans`, `evidence` — are
functions over a path, and
[`seed/gate/tests/test_probes.py`](seed/gate/tests/test_probes.py) builds a
throwaway workspace under pytest's temporary directory for each, breaks it the
way the step exists to catch, sees the finding, and puts it right. The steps
that wrap a tool are watched through what they wrap: `evidence` hands its
pure half the tests pytest collected, and the runner is exercised against
steps that could not run, passed and found.

That is step one of the Discipline applied to the checker rather than to the
code. Anything added to the gate arrives with the probe that fails it.

## Mutation testing is the signal behind the tests

**`uv run gate mutants`** runs `mutmut` in each package under `packages/`. A
mutant that survives is a line the tests execute without checking, and one no
test reaches is a line they do not execute; both are findings, because
coverage cannot tell you either (A3). The step is *could not run* — loud,
unmarked, exit zero — when `mutmut` is not installed, so a missing tool is
reported and not passed. It is in the workspace's dev group, so `uv sync`
installs it, which is where the step is guaranteed to run.

`mutmut run` exits zero whatever survived, so the step reads `mutmut results`
afterwards and reports each line it prints. It has been watched failing: a
test that calls the example without asserting leaves two mutants alive, and
the step says which.

The seed's package is clean under mutation. Its one function is a loop rather
than the comprehension it could be, because `mutmut` mutates nothing in a
function that is one comprehension, and a module the step cannot bite on would
seed a green mark that claims nothing.

The gate is not mutated, which is a departure from the Rust standard, whose
xtask is. Most of the gate's surface is the text of its reports, and each of
its checks is watched failing by a probe, which is the claim mutation would
make about it. The first defect in the gate that a probe would not have caught
is what changes this.

## No coverage floor

None is set. A3 makes coverage a floor beneath the tests, and a floor is set
under something that exists; one module of one function has nothing to hold
one at. The first real module sets it, with `pytest-cov` as the likely
instrument, and the number goes beside its reason.
