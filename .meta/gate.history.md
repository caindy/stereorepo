# History

### Iterating subprocess pipe read ahead in blocks delaying live gate streaming

When streaming gate execution output using loop iteration over `proc.stdout`,
the Python runtime buffered standard input in blocks rather than lines, causing
initial `ok` reports from slow-building compilers (such as Cargo) to stall in
buffers until execution completed. Established: `run()` uses `iter(proc.stdout.readline, "")`
to guarantee unbuffered line-by-line streaming of Article 21 check reports.

Evidence: `.meta/checks/files/history.py::meta_history_evidence`

### Empty project selection reported passing gate over zero checks

When a portfolio lacked project assertions during specialization setup or when a
product asserted no constituent projects, executing the gate runner evaluated zero
steps and returned exit code 0. Established: `main()` verifies non-empty project
selection and fails closed with an informative error when no gates exist to run.

Evidence: `.meta/checks/files/history.py::meta_history_evidence`

### Serial project gate execution compounded top-level verification duration

Executing independent project gates sequentially serialized compile and test
workloads, accumulating wall-clock latency across all declared projects.
Established: `main()` executes multi-project gate suites concurrently using a
thread pool executor with thread-safe output streaming while preserving
deterministic per-project step aggregation.

Evidence: `.meta/checks/files/history.py::meta_history_evidence`

### Runtime-evaluated threading.Lock annotation aborting the gate runner at load

When the concurrent runner annotated its print lock as `threading.Lock | None`,
the interpreter evaluated that union at `def` time. `threading.Lock` is a
factory function before Python 3.13 and a class from 3.13 on, so the runner
loaded on 3.13 and raised `TypeError: unsupported operand type(s) for |:
'builtin_function_or_method' and 'NoneType'` on 3.12, taking every step of
every Project's gate with it. Established: `_emit()` and `run()` quote the
annotation, deferring it to the type checker, which reads `threading.Lock`
as the class typeshed declares.

Evidence: `.meta/checks/probes/tools/gate.py::gate_runner_probes`
