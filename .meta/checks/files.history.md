# History

### PyYAML silent overwrites on duplicate mapping keys

PyYAML's default loader silently accepted repeated mapping keys, retaining only
the last occurrence and masking duplicate definitions such as repeated `steps:`
blocks in composite actions and workflow jobs (stereorepo's DR-053).
Established: `duplicate_keys` checks all YAML and YML files under `.meta/` and
stereorepo's `template/` using `Strict`, reporting any repeated mapping keys.

Evidence: `.meta/checks/files/templates.py::duplicate_keys`

### Broken relative Markdown links in documentation

Relative links in Markdown pages decayed after file relocations or renamings
(e.g. `schemas.md` pointing to stale decision paths), remaining undetected by
manual inspection (stereorepo's DR-036). Established: `markdown_links`
verifies that every relative link in non-template Markdown files resolves to a
tracked path or directory in the tree.

Evidence: `.meta/checks/files/markdown.py::markdown_links`

### Scaffold-only directory names in inherited portfolio files

Files copied into new portfolios by Specialization contained references to
directories that exist only in stereorepo scaffolding (such as stereorepo's `template/`,
stereorepo's `bootstraps/`, and stereorepo's `SPECIALIZE.md`), leaving broken references
in portfolio documentation and workflows (stereorepo's DR-036).
Established: `scaffold_only_paths` scans inherited documentation and workflows to ensure
no unqualified references to scaffold-only paths survive Specialization.

Evidence: `.meta/checks/files/scaffold.py::scaffold_only_paths`

### Operational convention divergence between root and template instructions

Operational conventions updated in root repository instructions (`AGENTS.md`,
`.meta/README.md`) drifted from the seeded template copies in stereorepo's `template/AGENTS.md`
and stereorepo's `template/.meta/README.md`, causing clones to start with divergent conventions
(stereorepo's DR-183). Established: `template_conventions_agree` verifies
that key operational conventions are mirrored in template seed files.

Evidence: `.meta/checks/files/templates.py::template_conventions_agree`

### Type checking blind to the extension-less programs under `.meta/`

`meta_types` handed mypy the `.meta/` directory, and a directory walk collects
`*.py` and nothing else, so the eight programs that carry a Python shebang in
place of a suffix — `.meta/gate`, the channel's four verbs and the three
programs under `.meta/arc/` — were outside the step while `meta_doc`, in the
same module, saw all thirty-six (stereorepo's DR-210). The
channel is where the credential is read and the `Actor:` Trailer composed, and
it is the part of the tree a test run does not cover. Established: `is_py` is
module-level and both steps ask it what Python under `.meta/` is, `meta_types`
names the suffix-less programs on the command line under
`--scripts-are-modules`, which keeps mypy from calling every script `__main__`
and aborting on the duplicate, and the baseline gained an entry for each.

Evidence: `.meta/checks/files/sources.py::is_py`

### Embedded inline Python invocation in coder workflow promotion

The promotion step in `.github/workflows/coder.yml` embedded an inline Python
invocation (`python3 -c '...'`), bypassing static analysis tools (`ruff`,
`mypy`), syntax checkers, and gate checks (stereorepo's DR-241). Established: `no_inline_python` scans workflow YAML files,
composite actions, shell scripts, and recipes, rejecting embedded Python
invocations and requiring dedicated `.meta/` scripts or CLI flags.

Evidence: `.meta/checks/files/inline_python.py::no_inline_python`

### A wiki page declaring the words its own concept forbids

A page's frontmatter `synonyms` and its concept's `avoid` list were both
machine-readable and nothing compared them:
`ubiquitous_language_wiki_parity` reads slugs against minted identifiers in
both directions and reads neither list. Both pages minted in
one change declared as synonyms words their concept forbids —
`wiki/stereorepo/claim.md` carried `work:concept/claim`'s whole `avoid` list,
word for word and in order — and the gate stayed green while the reviewer
caught them (stereorepo's DR-231). The cost is retrieval:
`.meta/lib/search/build.py` folds a frontmatter list item into the title field
of the BM25 index, which is the highest weight it carries, so the search
answered with the page for the forbidden word. Established:
`wiki_synonyms_are_not_avoided` reads every page's `synonyms` against the
`avoid` list of the concept, discipline or domain concept minted at its slug,
matched on the slugified word.

Evidence: `.meta/checks/files/wiki.py::wiki_synonyms_are_not_avoided`

### Concept set silent overwrites on duplicate concept identifiers

PyYAML parses sequence items independently, and LinkML index collection keyed by identifier silently overwrites earlier definitions with later occurrences when an `id` is declared twice in a `concept_set` list, masking duplicate concept definitions with divergent attributes and avoid lists (stereorepo's DR-190). Established: `duplicate_concept_ids` scans all YAML assertion and template files declaring a `concept_set`, reporting duplicate concept IDs with their line numbers.

Evidence: `.meta/checks/files/templates.py::duplicate_concept_ids`

### Unbounded line length under `.meta/`

`.meta/ruff.toml` selected no line-length family, so nothing bounded a line and
the tree grew one of 488 characters (stereorepo's DR-177). The
debt a 100-character bound found was diffuse — 1179 lines spread over the tree,
the largest single file holding under a tenth of them — so no flat step could
admit it in a diff anyone would read. Established: `meta_lines` ratchets `E501`
alone against `.meta/checks/lines.baseline.yaml`, and `meta_ruff` passes the
rule over on the command line so the declared ruleset still runs whole.

Evidence: `.meta/checks/files/python.py::meta_lines`

### Tracked and unignored text files contaminated by merge conflict markers

Rebasing a branch current is routine (PR First's *Bring a branch current by rebase* step), but conflicts in
documentation, YAML, or defect history files can append conflict markers to
the tail of files, bypassing language syntax checkers and merging into `main`
silently. Established: `conflict_markers`
scans the tree as git sees it (tracked files and untracked files git does not
ignore, excluding symlinks) via `sources.tree()`, reporting any line matching
git's conflict marker patterns (`<<<<<<<`, `=======`, `>>>>>>>`).

Evidence: `.meta/checks/files/conflicts.py::conflict_markers`


### Issue front matter that the pair loop silently ignores

The pair loop reads an Issue's `difficulty`, `waits_on` and `parent` and
nothing else, so a misspelt key (`dificulty: easy`), a difficulty outside the
enum (`difficulty: trivial`) or a `waits_on` naming no Issue left the Issue
ungroomed or waiting forever, with nothing to say why. Established:
`board_front_matter` holds every `issues/<stage>/*.md` file but `README.md` to
the slots of the ontology's `Issue` class and the values of its `Difficulty`
enum, read off the schema, and resolves `waits_on` and `parent` against the
slugs on the board, leaving a `<repository>:<slug>` entry unresolved.

Evidence: `.meta/checks/files/board.py::board_front_matter`
