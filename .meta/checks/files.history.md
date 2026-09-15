# History

### PyYAML silent overwrites on duplicate mapping keys

PyYAML's default loader silently accepted repeated mapping keys, retaining only
the last occurrence and masking duplicate definitions such as repeated `steps:`
blocks in composite actions and workflow jobs (solorepo's DR-053, solorepo's DR-120, solorepo's #129).
Established: `duplicate_keys` checks all YAML and YML files under `.meta/` and
solorepo's `template/` using `Strict`, reporting any repeated mapping keys.

Receipt: `.meta/checks/files.py::duplicate_keys`

### Broken relative Markdown links in documentation

Relative links in Markdown pages decayed after file relocations or renamings
(e.g. `schemas.md` pointing to stale decision paths), remaining undetected by
manual inspection (solorepo's DR-036, solorepo's #45). Established: `markdown_links`
verifies that every relative link in non-template Markdown files resolves to a
tracked path or directory in the tree.

Receipt: `.meta/checks/files.py::markdown_links`

### Scaffold-only directory names in inherited portfolio files

Files copied into new portfolios by Specialization contained references to
directories that exist only in solorepo scaffolding (such as solorepo's `template/`,
solorepo's `bootstraps/`, and solorepo's `SPECIALIZE.md`), leaving broken references
in portfolio documentation and workflows (solorepo's DR-036, solorepo's #45, solorepo's #75).
Established: `scaffold_only_paths` scans inherited documentation and workflows to ensure
no unqualified references to scaffold-only paths survive Specialization.

Receipt: `.meta/checks/files.py::scaffold_only_paths`

### Shared job drift between root and template gate workflows

The root gate workflow (`.github/workflows/gate.yml`) and the seeded template
gate workflow (in solorepo's `template/.github/workflows/gate.yml`) drifted in permissions and
job steps, leaving newly cloned portfolios running outdated workflow logic
(solorepo's DR-114, solorepo's DR-115, solorepo's DR-119, solorepo's #113, solorepo's #125).
Established: `gate_workflows_agree` enforces structural and semantic equality
across shared triggers, permissions, and jobs (`pull-request`, `sweep`).

Receipt: `.meta/checks/files.py::gate_workflows_agree`

### Operational convention divergence between root and template instructions

Operational conventions updated in root repository instructions (`AGENTS.md`,
`.meta/README.md`) drifted from the seeded template copies in solorepo's `template/AGENTS.md`
and solorepo's `template/.meta/README.md`, causing clones to start with divergent conventions
(solorepo's DR-183, solorepo's #11). Established: `template_conventions_agree` verifies
that key operational conventions are mirrored in template seed files.

Receipt: `.meta/checks/files.py::template_conventions_agree`

### Type checking blind to the extension-less programs under `.meta/`

`meta_types` handed mypy the `.meta/` directory, and a directory walk collects
`*.py` and nothing else, so the eight programs that carry a Python shebang in
place of a suffix — `.meta/gate`, the channel's four verbs and the three
programs under `.meta/arc/` — were outside the step while `meta_doc`, in the
same module, saw all thirty-six (solorepo's DR-210, solorepo's #436). The
channel is where the credential is read and the `Actor:` Trailer composed, and
it is the part of the tree a test run does not cover. Established: `is_py` is
module-level and both steps ask it what Python under `.meta/` is, `meta_types`
names the suffix-less programs on the command line under
`--scripts-are-modules`, which keeps mypy from calling every script `__main__`
and aborting on the duplicate, and the baseline gained an entry for each.

Receipt: `.meta/checks/files.py::is_py`
