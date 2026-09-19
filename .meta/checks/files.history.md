# History

### PyYAML silent overwrites on duplicate mapping keys

PyYAML's default loader silently accepted repeated mapping keys, retaining only
the last occurrence and masking duplicate definitions such as repeated `steps:`
blocks in composite actions and workflow jobs (solorepo's DR-053, solorepo's DR-120, solorepo's #129).
Established: `duplicate_keys` checks all YAML and YML files under `.meta/` and
solorepo's `template/` using `Strict`, reporting any repeated mapping keys.

Evidence: `.meta/checks/files/templates.py::duplicate_keys`

### Broken relative Markdown links in documentation

Relative links in Markdown pages decayed after file relocations or renamings
(e.g. `schemas.md` pointing to stale decision paths), remaining undetected by
manual inspection (solorepo's DR-036, solorepo's #45). Established: `markdown_links`
verifies that every relative link in non-template Markdown files resolves to a
tracked path or directory in the tree.

Evidence: `.meta/checks/files/markdown.py::markdown_links`

### Scaffold-only directory names in inherited portfolio files

Files copied into new portfolios by Specialization contained references to
directories that exist only in solorepo scaffolding (such as solorepo's `template/`,
solorepo's `bootstraps/`, and solorepo's `SPECIALIZE.md`), leaving broken references
in portfolio documentation and workflows (solorepo's DR-036, solorepo's #45, solorepo's #75).
Established: `scaffold_only_paths` scans inherited documentation and workflows to ensure
no unqualified references to scaffold-only paths survive Specialization.

Evidence: `.meta/checks/files/workflows.py::scaffold_only_paths`

### Shared job drift between root and template gate workflows

The root gate workflow (`.github/workflows/gate.yml`) and the seeded template
gate workflow (in solorepo's `template/.github/workflows/gate.yml`) drifted in permissions and
job steps, leaving newly cloned portfolios running outdated workflow logic
(solorepo's DR-114, solorepo's DR-115, solorepo's DR-119, solorepo's #113, solorepo's #125).
Established: `gate_workflows_agree` enforces structural and semantic equality
across shared triggers, permissions, and jobs (`pull-request`, `sweep`).

Evidence: `.meta/checks/files/workflows.py::gate_workflows_agree`

### Operational convention divergence between root and template instructions

Operational conventions updated in root repository instructions (`AGENTS.md`,
`.meta/README.md`) drifted from the seeded template copies in solorepo's `template/AGENTS.md`
and solorepo's `template/.meta/README.md`, causing clones to start with divergent conventions
(solorepo's DR-183, solorepo's #11). Established: `template_conventions_agree` verifies
that key operational conventions are mirrored in template seed files.

Evidence: `.meta/checks/files/templates.py::template_conventions_agree`

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

Evidence: `.meta/checks/files/sources.py::is_py`

### Gemini CLI reviewer holding tools the Claude path never grants

`.github/workflows/review.yml`'s Gemini CLI path named no `tools.core`, so
where the Claude path's `--allowedTools` leaves `Write`, `Edit`, `WebFetch`
and `WebSearch` simply absent, an unset `tools.core` left every one of
Gemini CLI's counterparts — `write_file`, `replace`, `web_fetch`,
`google_web_search` — reachable, the opposite default holding the boundary
open rather than shut (solorepo's #452, solorepo's #454). Established:
`gemini_allowlist_matches_claude` reads both paths' allowlists out of
`review.yml` and fails when either names either half of a `DANGEROUS_TOOLS`
pair, so the two cannot drift apart in that direction again unnoticed.

Evidence: `.meta/checks/files/workflows.py::gemini_allowlist_matches_claude`

### `tools.core` admitting a tool the `BeforeTool` matcher never guards

This pull request's own first head named `activate_skill` in the Gemini path's
`tools.core` without a place for it in the `BeforeTool` matcher `worktree_only.py`
is registered against, so the one admitted tool's calls never reached the
worktree-confinement hook — an invariant stated only in a comment, caught only
by a review thread, with every other gate green (solorepo's #454). Established:
`gemini_core_matches_hook_matcher` parses both lists out of `review.yml` and
fails on any difference between them, in either direction.

Evidence: `.meta/checks/files/workflows.py::gemini_core_matches_hook_matcher`

### Embedded inline Python invocation in coder workflow promotion

The promotion step in `.github/workflows/coder.yml` embedded an inline Python
invocation (`python3 -c '...'`), bypassing static analysis tools (`ruff`,
`mypy`), syntax checkers, and gate checks (solorepo's DR-241,
solorepo's #666). Established: `no_inline_python` scans workflow YAML files,
composite actions, shell scripts, and recipes, rejecting embedded Python
invocations and requiring dedicated `.meta/` scripts or CLI flags.

Evidence: `.meta/checks/files/workflows.py::no_inline_python`
