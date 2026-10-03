# History

### Article falsifier slot omitted from entry text resolution

`entry_text()` enumerated an Article's slots explicitly and omitted `falsifier`,
causing verbatim quotations from an Article's falsifier to be flagged as missing
from the entry under `quoted_claims`. Established: `entry_text()` extracts
and normalizes all string scalars across the entire article structure.

Evidence: `.meta/checks/citations/prose.py::entry_text`

### Unwritten Decision numbers cited in repository prose

Prose cited Decision numbers that had not been written down (e.g. `DR-058` in
`roadmap.md`), leaving unrecorded gaps in the decision index (stereorepo's DR-121).
Established: `cited_decisions()` verifies that every DR cited in durable prose
or YAML scalars resolves to an existing Decision record.

Evidence: `.meta/checks/citations/record.py::cited_decisions`

### Bare Decision citations leaked into inherited portfolio material

Files inherited by portfolios contained bare `DR-nnn` citations, which become
ambiguous or collide with the portfolio's own decision index upon specialization. Established: `cited_decisions()` enforces that inherited files qualify
citations of stereorepo's records with the possessive prefix `stereorepo's DR-nnn`.

Evidence: `.meta/checks/citations/record.py::cited_decisions`

### Quoting from memory introduced untracked prose discrepancies

Prose attributing verbatim quotations to Articles or Decisions diverged from
the actual record texts, causing silent drift.
Established: `quoted_claims()` matches attributed quotations against normalized
scalar contents of cited records, accommodating elisions.

Evidence: `.meta/checks/citations/claims.py::quoted_claims`

### Unrecorded supersession and departure relationships in prose

Prose asserted relationship links (such as `supersedes` or `departs_from`)
between Decisions and Articles without setting corresponding schema slots. Established: `stated_relations()` verifies that relational verbs in
indicative sentences match explicit relation slots in Decision assertions.

Evidence: `.meta/checks/citations/claims.py::stated_relations`

### Stale line numbers in cited file paths

Prose citing specific source lines (`path:line`) beside code snippets decayed
when file edits shifted line offsets. Established:
`path_and_line_claims()` verifies that cited lines exist and contain the
neighboring code tokens referenced in prose. The next entry replaced that
step.

Evidence: `.meta/checks/citations/claims.py::no_line_citations`

### Line citations refused

Verifying cited lines still failed the gate on files nobody touched: an edit
that moved lines in a source file made a citation of it elsewhere stale, so
the edit failed on prose it never changed, pair notes and done Issue files
included. Established: `no_line_citations()` refuses every `path:line` code
span in durable prose instead of resolving it, and prose cites the path and
the name of the thing in it (stereorepo's DR-355).

Evidence: `.meta/checks/citations/claims.py::no_line_citations`

### Disagreement between file citations and record enactment slots

Files named in Decision `enacted_in` assertions cited disparate Decisions,
creating inconsistencies between the index and file prose. Established:
`enacting_citations()` validates that a file named by the record cites at least
one Decision asserting enactment in that file (stereorepo's DR-131).

Evidence: `.meta/checks/citations/record.py::enacting_citations`

### A citation opening a sentence read as bare

`FOREIGN` matched only the
lowercase possessive, so a sentence-initial `Stereorepo's DR-nnn` fell through
to the bare scan and was reported as a citation missing the possessive it
already carried. Established: the pattern holds the
leading letter of `stereorepo's`/`Stereorepo's` case-insensitive and every other
character exact.

Evidence: `.meta/checks/probes/knowledge.py::citation_form_probes`

### Stale schema slot names cited in prose after schema refactoring

Prose in assertion preambles and documentation cited schema slot names in backticks
that had been removed or replaced in LinkML ontologies, leaving dangling slot
references unchecked. In stereorepo's DR-087, `Article.origin`
was removed from `.meta/work/disciplines.yaml` and replaced with `example`, but a
preamble comment in `.meta/assertions/imported/charter.yaml` retained
"`origin` is the receipt" silently until the minting change. Established:
assertion comment blocks are parsed as prose alongside scalar fields, and
`cited_schema_slots()` verifies qualified `Class.slot` citations, explicit slot phrases,
and document-scoped former slot names against LinkML schema declarations across
living durable prose (excluding historical decision records and challenges).

Evidence: `.meta/checks/probes/citations.py::cited_schema_slot_probes`

### A product's own schema slots cited in its documentation

fitch-mvp, the first repository onboarded, cites slots of its own class
`Decision` in its `README.md` and `ROADMAP.md`. `cited_schema_slots()`
resolved them against stereorepo's Decision Record, a class of the same name
with other slots, and failed each one. Established: a Project names its
LinkML schemas in its `schemas` slot, `product_views()` loads them, and a
citation passes when stereorepo's schemas or a product's declare the slot
on the class it names. A named schema that is missing, does not load or
declares no class fails the step (stereorepo's DR-304).

Evidence: `.meta/checks/probes/citations.py::_probe_product_schemas`
