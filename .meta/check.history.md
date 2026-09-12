# History

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Receipt: `<path>::<symbol>`
-->

### Hand-maintained step tables drifted from check definitions

Before self-registering checks, adding or removing a gate check required
updating separate dispatch tables and manual step counts in `main()`,
allowing steps to be registered without running or step counts to drift from
reality. Established: checks register themselves at definition via `@check`
(solorepo's DR-150) and reports reflect the live registry.

Receipt: `.meta/checks/files.py::meta_history_receipts`
