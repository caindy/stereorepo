# Knowledge Management

**Knowledge Management** is the discipline that organizes maintainer-facing
exposition into an encyclopedic wiki partitioned by Bounded Context (solorepo's DR-184, solorepo's DR-185).

It provides a durable home for explanations addressed to human or agent
maintainers who arrive cold seeking to understand a subsystem or domain concept.
Without this discipline, explanations generated in sessions or pull request
reviews are either lost to ephemeral pull request threads or dumped as unlinked
markdown files that Nothing Unconsumed flags as debris.

## Core Invariants

### 1. Bounded Context Partitioning
Documentation is never global. Meaning in Domain-Driven Design is strictly
scoped to a Bounded Context (`ddd:context/<name>`). The wiki mirrors this by
housing explanations in subdirectories named for each context:
- `wiki/solorepo/` houses the hermetic operating manual for the scaffold's own
  loop machinery, roles, and disciplines.
- Specialized portfolios add peer directories for their own business contexts
  (e.g., `wiki/<context>/`).

### 2. MOS:LEAD Concordance
Every page opens with an encyclopedic lead sentence defining the subject in
bold copular phrasing (`**Subject** is a ...`). This lead sentence concurs with
the concept's machine definition in the vocabulary schema and provides an
immediate digest suitable for hover previews and automated summarization.

### 3. Closed-World Wikilinks
Internal concept references use wikilinks (`[[concept]]` or scoped
`[[context/concept]]`, solorepo's DR-185). Every link must resolve to a valid concept page or
vocabulary term. A link to an unminted concept or missing page is red and fails
gate verification.

## Relationship to Other Disciplines

- **[[Ubiquitous Language]]:** The vocabulary schema holds the one-sentence machine
  gloss; the Knowledge Management wiki holds the encyclopedic narrative
  exposition.
- **Literate Programming:** Source code docstrings state *what to do*; Decision
  Records state *why a choice was made*; history logs record *what happened*;
  and the Knowledge Management wiki explains *how the system works*.
- **Nothing Unconsumed:** A page that nothing links to is an orphan; a link that
  resolves to nothing is broken. Both are caught by gate verification.

---

**See also:** [[ubiquitous-language]], [[pr-first]], solorepo's DR-184, solorepo's DR-185.

