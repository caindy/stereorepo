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

### Reviewer tool confinement duplication across review and triage workflows

Reviewer tool confinement under Antigravity CLI (`agy`) was configured solely
via an embedded heredoc in `.github/workflows/review.yml` and absent from
`.github/workflows/triage.yml`, risking tool divergence and unconfined execution
during triage fallback (solorepo's #699). Established: reviewer tool confinement
is unified in `.meta/detect_fallback.py` under `REVIEWER_CORE_TOOLS` and
`REVIEWER_BEFORE_TOOL_MATCHER` and applied by `.meta/actions/agy`, with
`gemini_allowlist_matches_claude` and `gemini_core_matches_hook_matcher`
verifying tool parity against dangerous tools and hook matcher alignment
across `review.yml` and `triage.yml`.

Evidence: `.meta/checks/files/workflows.py::gemini_allowlist_matches_claude`

### Embedded inline Python invocation in coder workflow promotion

The promotion step in `.github/workflows/coder.yml` embedded an inline Python
invocation (`python3 -c '...'`), bypassing static analysis tools (`ruff`,
`mypy`), syntax checkers, and gate checks (solorepo's DR-241,
solorepo's #666). Established: `no_inline_python` scans workflow YAML files,
composite actions, shell scripts, and recipes, rejecting embedded Python
invocations and requiring dedicated `.meta/` scripts or CLI flags.

Evidence: `.meta/checks/files/workflows.py::no_inline_python`

### A wiki page declaring the words its own concept forbids

A page's frontmatter `synonyms` and its concept's `avoid` list were both
machine-readable and nothing compared them:
`ubiquitous_language_wiki_parity` reads slugs against minted identifiers in
both directions and reads neither list. Both pages minted in
caindy/solorepo#581 declared as synonyms words their concept forbids —
`wiki/solorepo/claim.md` carried `work:concept/claim`'s whole `avoid` list,
word for word and in order — and the gate stayed green while the reviewer
caught them (solorepo's DR-231, solorepo's #594). The cost is retrieval:
`.meta/lib/search/build.py` folds a frontmatter list item into the title field
of the BM25 index, which is the highest weight it carries, so the search
answered with the page for the forbidden word. Established:
`wiki_synonyms_are_not_avoided` reads every page's `synonyms` against the
`avoid` list of the concept, discipline or domain concept minted at its slug,
matched on the slugified word.

Evidence: `.meta/checks/files/wiki.py::wiki_synonyms_are_not_avoided`

### Reviewer workflow lacked symlink containment gate

An unvetted pull request could check out outbound symlinks allowing pattern-based
tools to traverse into host runner directories and access credentials (solorepo's DR-251,
solorepo's #458). Established: `reviewer_symlinks_verified` verifies that
`.github/workflows/review.yml` invokes `python3 .meta/hooks/worktree_only.py --audit-symlinks`
prior to credential provisioning, and validates that the repository worktree contains no
outbound symlinks.

Evidence: `.meta/checks/files/workflows.py::reviewer_symlinks_verified`

### Reviewer tool confinement bypassed under Antigravity CLI without fine-grained permission denials

The reviewer workflow configured `tools.core` to restrict Gemini capability bounds,
but containerized Antigravity CLI (`agy`) enforces capability bounds strictly via
`permissions.deny` rather than `tools.core`, leaving write and network capabilities
unconfined if `permissions.deny` is omitted (solorepo's DR-110, solorepo's DR-245,
solorepo's #636). Established: `configure_reviewer_settings` and `merge_settings` in
`.meta/detect_fallback.py` configure explicit `permissions.deny: ["write_file(*)", "read_url(*)", "execute_url(*)"]`
directly in `~/.gemini/antigravity-cli/settings.json` while preserving credentials,
audited by `gemini_allowlist_matches_claude` in `.meta/checks/files/workflows.py` and probed by
`fallback_probes`.

Evidence: `.meta/checks/files/workflows.py::gemini_allowlist_matches_claude`

### Concept set silent overwrites on duplicate concept identifiers

PyYAML parses sequence items independently, and LinkML index collection keyed by identifier silently overwrites earlier definitions with later occurrences when an `id` is declared twice in a `concept_set` list, masking duplicate concept definitions with divergent attributes and avoid lists (solorepo's DR-190, solorepo's #549). Established: `duplicate_concept_ids` scans all YAML assertion and template files declaring a `concept_set`, reporting duplicate concept IDs with their line numbers.

Evidence: `.meta/checks/files/templates.py::duplicate_concept_ids`

### Reviewer prompt lacked working path to pr-first-reviewer and permitted premature subagent exits

The Gemini CLI reviewer prompt instructed the session to "Read /pr-first-reviewer first"
and delegated review passes across Claude-specific plugin and foreground subagent commands,
providing no working file path to `/pr-first-reviewer` under Antigravity CLI and causing
headless batch runs (`agy -p`) to exit prematurely upon asynchronous subagent invocation
before posting review verdicts (solorepo's DR-107, solorepo's DR-254, solorepo's #637).
Established: `.github/workflows/review.yml` provides the concrete path
`.agents/skills/pr-first-reviewer/SKILL.md` for direct single-session evaluation under
"review the pull request (agy)", while `detect_fallback.py` adds `invoke_subagent(*)` to
`REVIEWER_DENIED_PERMISSIONS`, audited by `gemini_allowlist_matches_claude`.

Evidence: `.meta/checks/files/workflows.py::gemini_allowlist_matches_claude`



### Unbounded line length under `.meta/`

`.meta/ruff.toml` selected no line-length family, so nothing bounded a line and
the tree grew one of 488 characters (solorepo's DR-177, solorepo's #751). The
debt a 100-character bound found was diffuse — 1179 lines spread over the tree,
the largest single file holding under a tenth of them — so no flat step could
admit it in a diff anyone would read. Established: `meta_lines` ratchets `E501`
alone against `.meta/checks/lines.baseline.yaml`, and `meta_ruff` passes the
rule over on the command line so the declared ruleset still runs whole.

Evidence: `.meta/checks/files/python.py::meta_lines`

### A coder pass bounded by caps its own prompt never named

`coder_depth` emitted a turn cap and a minute cap for every coder pass and
`.github/workflows/coder.yml` spent them on `--max-turns` and `timeout-minutes`,
but no prompt said either number, so a session learned its budget only by
running out of it and a run cut off mid-thread left the branch where it stood
(solorepo's #844). The first mechanization made both numbers mandatory in all
eight prompts, which told the four Antigravity CLI passes a turn cap the harness
does not take: `.meta/run_agy.py` passes `--print-timeout` alone. Established:
each prompt names the minute cap, and names the turn cap exactly where its own
step passes `--max-turns`, over the prompt-bearing steps read out of the `coder`
job rather than a hand-written list.

Evidence: `.meta/checks/files/workflows.py::coder_prompts_name_turn_budget`

### Tracked and unignored text files contaminated by merge conflict markers

Rebasing a branch current is routine (PR First step 14), but conflicts in
documentation, YAML, or defect history files can append conflict markers to
the tail of files, bypassing language syntax checkers and merging into `main`
silently (solorepo's #772, solorepo's #742). Established: `conflict_markers`
scans the tree as git sees it (tracked files and untracked files git does not
ignore, excluding symlinks) via `sources.tree()`, reporting any line matching
git's conflict marker patterns (`<<<<<<<`, `=======`, `>>>>>>>`).

Evidence: `.meta/checks/files/conflicts.py::conflict_markers`
