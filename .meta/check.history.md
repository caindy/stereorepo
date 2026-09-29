# History

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Evidence: `<path>::<symbol>`
-->

### Hand-maintained step tables drifted from check definitions

Before self-registering checks, adding or removing a gate check required
updating separate dispatch tables and manual step counts in `main()`,
allowing steps to be registered without running or step counts to drift from
reality. Established: checks register themselves at definition via `@check`
(DR-150) and reports reflect the live registry.

Evidence: `.meta/checks/files/history.py::meta_history_evidence`

### Template seed instructions drifted from root agent conventions

When operational conventions evolved at the root (`CLAUDE.md` and `GEMINI.md` symlinks,
`move mint`, `just --list` operator surface, PR First semaphores, `just next`, and
the ban on harness memory files), `template/AGENTS.md` and `template/.meta/README.md`
lagged behind. Established: `template conventions agree` verifies that root and
template files both declare the core operational conventions (DR-183).

Evidence: `.meta/checks/files/templates.py::template_conventions_agree`

### Step or schema load exceptions halted gate without diagnostic reporting

When unexpected errors occurred during schema loading or individual check step
execution, the gate runner crashed with raw Python tracebacks, preventing
downstream checks from running or obscuring remaining step status. Established:
`main()` isolates precheck and step executions, catches unhandled exceptions, and
reports structured failure summaries without exiting early (Article 6).

Evidence: `.meta/checks/files/history.py::meta_history_evidence`

### Block-buffered standard output delayed gate streaming in subprocess pipelines

When `check.py` executed within a subprocess pipeline or under `gate`, standard
output defaulted to block buffering instead of flushing line by line, delaying
real-time step reporting and violating the streaming contract asserted in
DR-104. Established: `main()` configures line buffering on `sys.stdout`
when backed by a text stream wrapper.

Evidence: `.meta/check.py::main`

### A required status check reported green on a step that never ran

`report()` printed `?` for a `CouldNotRun` outcome and left `failed` alone, so
the gate exited zero however many steps had not executed. Under CI that read a
provisioning hole as a note: `apm package` returned `CouldNotRun` on every run
because `.github/workflows/gate.yml` installed `linkml`, `pyyaml`, `ruff`,
`mypy` and `types-pyyaml` and no `apm`, and the `files` job was a required
status check on `main` the whole time. The same file also held two answers to
one question, failing the run for a schema container that accepted nothing
while passing it for a step that said the same thing through `CouldNotRun`.
Established: every unrunnable step and every skipped container is collected
into one closing block, and `closing_block()` fails the run where `CI` holds a
non-empty value (Article 6, DR-261).

Evidence: `.meta/check.py::closing_block`

