# History

History of defects, incidents, and recoveries for `.meta/apm_compile.py` and
`.meta/hooks/post-checkout` (DR-171).

### Post-checkout hook silently swallowed reconciliation failures under constrained environments

A git worktree could finish checkout without `.agents/skills/` populated even when
`.meta/.apm/skills/` was present, because `.meta/hooks/post-checkout` invoked
`python3 .meta/apm_compile.py --reconcile >/dev/null 2>&1 || true`. When ambient `python3`
lacked PyYAML or PATH was constrained, `apm_compile.py` failed during top-level imports
attempting to load YAML/APM primitives and shelling out to missing `uvx`, discarding all
diagnostic output and masking failure. Established: decoupled `--reconcile` in
`.meta/apm_compile.py` and `.meta/lib/apm_compile/cli.py` from packaging dependencies, augmented
PATH and added Python candidate resolution in `post-checkout`, and ensured post-checkout failures
report diagnostics to stderr without masking them.

Evidence: `.meta/checks/probes/tools/apm_compile.py::worktree_projection_probes`

### Skill projection rewrote every file and stopped at the first one it could not write

Without the `apm` CLI, `reconcile_harnesses` projected `.meta/.apm/skills/` into
`.agents/skills/` with `shutil.copytree`, which rewrote every file on every run and raised on
the first one it could not write. Under a seat's sandbox that ended `just render`, which runs
the projection after writing its pages. Established: the projection copies only a file that is
missing or whose bytes differ, and reports a file it cannot write as an action starting with
`harness.UNWRITTEN`, which render lists with its own unwritten pages.

Evidence: `.meta/checks/probes/tools/render.py::harness_projection_probes`
