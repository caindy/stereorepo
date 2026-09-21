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
