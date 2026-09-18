# History

### HTML numeric entities parsed as issue citations

Scanning text for Issue citations without word boundaries caused HTML numeric
entities (such as `&#39;`) to be parsed as citations of issue solorepo's #39 (solorepo's #132).
Established: `issue_citation()` reads its regular expression patterns directly
from `check_pr.py`, synchronizing parsing boundaries across gates.

Evidence: `.meta/checks/citations/loaders.py::issue_citation`

### Article falsifier slot omitted from entry text resolution

`entry_text()` enumerated an Article's slots explicitly and omitted `falsifier`,
causing verbatim quotations from an Article's falsifier to be flagged as missing
from the entry under `quoted_claims` (solorepo's #147). Established: `entry_text()` extracts
and normalizes all string scalars across the entire article structure.

Evidence: `.meta/checks/citations/prose.py::entry_text`

### Unwritten Decision numbers cited in repository prose

Prose cited Decision numbers that had not been written down (e.g. `DR-058` in
`roadmap.md`), leaving unrecorded gaps in the decision index (solorepo's DR-121).
Established: `cited_decisions()` verifies that every DR cited in durable prose
or YAML scalars resolves to an existing Decision record.

Evidence: `.meta/checks/citations/record.py::cited_decisions`

### Bare Decision citations leaked into inherited portfolio material

Files inherited by portfolios contained bare `DR-nnn` citations, which become
ambiguous or collide with the portfolio's own decision index upon specialization
(solorepo's #114). Established: `cited_decisions()` enforces that inherited files qualify
citations of solorepo's records with the possessive prefix `solorepo's DR-nnn`.

Evidence: `.meta/checks/citations/record.py::cited_decisions`

### Quoting from memory introduced untracked prose discrepancies

Prose attributing verbatim quotations to Articles or Decisions diverged from
the actual record texts, causing silent drift (solorepo's #138, solorepo's #140, solorepo's #142).
Established: `quoted_claims()` matches attributed quotations against normalized
scalar contents of cited records, accommodating elisions.

Evidence: `.meta/checks/citations/claims.py::quoted_claims`

### Unrecorded supersession and departure relationships in prose

Prose asserted relationship links (such as `supersedes` or `departs_from`)
between Decisions and Articles without setting corresponding schema slots
(solorepo's #142). Established: `stated_relations()` verifies that relational verbs in
indicative sentences match explicit relation slots in Decision assertions.

Evidence: `.meta/checks/citations/claims.py::stated_relations`

### Stale line numbers in cited file paths

Prose citing specific source lines (`path:line`) beside code snippets decayed
when file edits shifted line offsets (solorepo's #142, solorepo's #147). Established:
`path_and_line_claims()` verifies that cited lines exist and contain the
neighboring code tokens referenced in prose.

Evidence: `.meta/checks/citations/claims.py::path_and_line_claims`

### Disagreement between file citations and record enactment slots

Files named in Decision `enacted_in` assertions cited disparate Decisions,
creating inconsistencies between the index and file prose (solorepo's #152). Established:
`enacting_citations()` validates that a file named by the record cites at least
one Decision asserting enactment in that file (solorepo's DR-131).

Evidence: `.meta/checks/citations/record.py::enacting_citations`

### Bare Issue numbers in inherited files

Files inherited by portfolios cited bare Issue numbers (e.g. `#114`), which
collide with the portfolio's issue tracker upon specialization (solorepo's #114).
Established: `inherited_citations()` requires all Issue citations in inherited
files to be prefixed with `solorepo's #nnn` (solorepo's DR-132).

Evidence: `.meta/checks/citations/record.py::inherited_citations`
