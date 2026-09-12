# History

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Receipt: `<path>::<symbol>`
-->

### Required contexts drifted from workflow job names

A comment previously advised "rename in both places or in neither", but
renaming a workflow job left branch rulesets waiting on a context nothing
produced, blocking merges without explanation. Established: required status
checks are read directly from branch rulesets and verified against workflow
job definitions.

Receipt: `.meta/checks/files.py::gate_workflows_agree`
