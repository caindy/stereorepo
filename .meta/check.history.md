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

### Template seed instructions drifted from root agent conventions

When operational conventions evolved at the root (`CLAUDE.md` and `GEMINI.md` symlinks,
`move mint`, `just --list` operator surface, PR First semaphores, `just next`, and
the ban on harness memory files), `template/AGENTS.md` and `template/.meta/README.md`
lagged behind. Established: `template conventions agree` verifies that root and
template files both declare the core operational conventions (solorepo's DR-183).

Receipt: `.meta/checks/files.py::template_conventions_agree`
