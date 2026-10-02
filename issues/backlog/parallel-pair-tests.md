# Run the pair tests in parallel

`just gate pair` runs `pair/test_pair.py` in one process, one test after
another (`pair/gate.py`). On 2026-10-02 the suite held 209 tests in 17
classes and took 96 seconds in a seat's sandbox, measured with a logging
`git` shim in place. Seats run it several times in an Issue that touches
`pair/`, and the loop runs it again in the full gate before landing.

`pair-test-git-traffic` found that cutting git calls cannot halve the
suite's cost, since the loop's own writes and the tests' setup already make
up more than half of them. It named running the test classes in several
processes as the way to cut wall time, and the developer chose that.

## Wanted

- `just gate pair` runs the tests across several processes, for example one
  worker per CPU, each taking whole test classes.
- The step still prints the shape every gate prints (`ok <step> — <scope>`,
  or `x  <step> (<count>)` with one line per failure, A21), and exits
  non-zero when any test fails.
- Tests that share state across classes, such as environment variables,
  the current directory or a fixed path, are made independent, so the
  result does not depend on which worker runs them.

## Out of scope

- Reducing the git calls the loop or the tests make (`pair-test-git-traffic`).
- The other Projects' gates.

## Done when

- `just gate pair` passes with the same tests and the same assertions.
- Its wall time, measured once before and once after in a seat's sandbox,
  falls by at least half. Both times are recorded in this file.
- A failing test still shows as one line under its step, naming the test.
