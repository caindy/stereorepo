# Knowledge Management

**Knowledge Management** is the discipline governing the classification, routing,
and authoring of all maintainer-facing prose across the repository according to
the Diátaxis Compass (stereorepo's Article 17, stereorepo's DR-184,
stereorepo's DR-185, stereorepo's DR-337, stereorepo's DR-196).

It provides autonomous agents and maintainers with a deterministic decision
procedure before drafting a single word of prose, answering both *where to write*
and *how to write*. Without this discipline, explanations generated during coding
sessions drift into ephemeral conversation, accumulate as ad-hoc
markdown debris, or mix incongruous modes across artifact boundaries.

## The Diátaxis Compass: Documentation Coordinates

Knowledge is organized along two orthogonal axes reflecting reader posture:
- **Context of Activity:** **Learning** (exploring concepts, acquiring perspective)
  versus **Work** (executing intent, solving an immediate problem).
- **Mode of Thought:** **Action** (practical steps) versus **Understanding**
  (systematic facts, theoretical reflection).

Every written artifact in stereorepo maps to exactly one quadrant:

1. **Reference (Work + Understanding):** Public function and class docstrings,
   LinkML schemas (`.meta/*_ontology.yaml`), and CLI glosses. Register: dry,
   complete, lookup-oriented. Describes contracts, parameters, and invariants
   without opinions, tutorials, or historical debates (stereorepo's DR-171, stereorepo's DR-334).
2. **Explanation (Learning + Understanding):** `wiki/<context>/<concept>.md`,
   Decision Records (`DR-nnn.yaml`), and module overviews. Register: expository,
   context-rich, and rationale-driven. Answers *why* choices were made and explores
   architectural trade-offs.
3. **How-To (Work + Action):** `justfile` recipes, operational runbooks, or
   stereorepo's `SPECIALIZE.md`. Register: imperative, task-focused ("Do X to achieve Y").
   Assumes reader competence and omits theoretical digressions.
4. **Tutorial (Learning + Action):** Onboarding lessons and bootstrap quickstarts.
   Register: guided, step-by-step walkthroughs with immediate observable feedback.

## Pre-Writing Routing: Where to Write

Before drafting prose for a change, an authoring agent executes a deterministic
routing tree:

1. **Repeatable Procedure or Command?** Write a `justfile` recipe or
   stereorepo's `SPECIALIZE.md` step (**How-To**).
2. **Contract Fact, Schema, or Function?** Write an item docstring or LinkML
   slot definition (**Reference**).
3. **Settled Architectural Choice Between Alternatives?** Mint and write a
   Decision Record in `.meta/assertions/decisions/DR-nnn.yaml` (**Explanation**).
4. **Incident Narrative or Defect History?** Append to `<module>.history.md`
   with verifiable Evidence (**Explanation**).
5. **Enduring Domain Concept or Subsystem Overview?** Scaffold via `/wikisplain`
   (`.meta/wikisplain.py`) and author under `wiki/<context>/<concept>.md` (**Explanation**).
6. **Unrouted Residue?** What changed, the path taken and the approach that
   lost belong in the issue file, which lands in `issues/done/` with the change;
   work noticed and not done is a new file in `issues/backlog/`. An issue file
   is not a documentation container.

## Concept Decoupling and Container Subordination

The atomic semantic unit of domain knowledge is the [[concept]] (stereorepo's DR-338).
The physical storage container is strictly subordinate to the authoring agent's
structural judgement under Diátaxis:
- **Schema Gloss:** A brief definition in `vocabulary.yaml` when machine checks
  and search aliases suffice.
- **Section or Subsection:** Authored as `##` or `###` within an existing document
  when tightly bound to a larger aggregate.
- **Dedicated Wiki Page:** A standalone page under `wiki/<context>/<concept>.md`
  when an idea exhibits independent invariants, architectural depth, or broad relevance.
- **Subdirectory:** A folder grouping related concept pages for complex domain aggregates.

The term *Article* is strictly avoided for wiki pages (`avoid: [wiki article]`)
to prevent catastrophic confusion with the empirical clauses of the Charter.

## Core Invariants

### 1. Bounded Context Partitioning
Documentation is never global. Meaning in Domain-Driven Design is strictly
scoped to a [[bounded-context]] (`ddd:context/<name>`). The wiki mirrors this by
housing explanations in subdirectories named for each context:
- `wiki/stereorepo/` houses the hermetic operating manual for the scaffold's own
  loop machinery, roles, and disciplines.
- Specialized portfolios add peer directories for their own business contexts
  (e.g., `wiki/<context>/`).

### 2. MOS:LEAD Concordance & 1:1 Parity
Every page opens with an encyclopedic lead sentence defining the subject in
bold copular phrasing (`**Subject** is a ...`). This lead sentence concurs with
the concept's machine definition in the vocabulary schema. Every concept in the
[[ubiquitous-language]] maintains 1:1 parity with a wiki page (stereorepo's Article 17,
stereorepo's DR-335).

### 3. Closed-World Wikilinks
Internal concept references use wikilinks (`[[concept]]` or scoped
`[[context/concept]]`, stereorepo's DR-185). Every link must resolve to a valid concept page or
vocabulary term. A link to an unminted concept or missing page fails gate verification.

### 4. Google Developer Style Sentences
- Address the reader directly as "you" in the present tense.
- Use the active voice ("The gate verifies assertions", not "Assertions are verified").
- Eliminate dead filler words ("to" instead of "in order to", "use" instead of "utilize").
- Prefer concrete symbols, files, and flags over sterile generic descriptions.
- Vary rhythm by alternating short declarative statements with compound explanatory sentences.

---

**See also:** [[concept]], [[ubiquitous-language]], stereorepo's Article 1, stereorepo's Article 17, stereorepo's DR-184, stereorepo's DR-185, stereorepo's DR-187, stereorepo's DR-335, stereorepo's DR-337, stereorepo's DR-338, stereorepo's DR-196.
