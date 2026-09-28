# Knowledge Base (Wiki)

The repository's home for maintainer-facing exposition, structured under the
[[stereorepo/knowledge-management|Knowledge Management]] discipline (stereorepo's DR-184, stereorepo's DR-185).

Where Decision Records capture *why a choice was made* (stereorepo's DR-065) and
LinkML vocabularies capture *machine definitions and glosses*, the wiki captures
**narrative explanations**: how architectures work, how subsystems interact,
and how domain concepts behave in practice.

## Bounded Context Partitioning

In accordance with Domain-Driven Design, meaning is never global; it is always
scoped to a **Bounded Context** (`ddd:context/<name>`). The wiki directory is
partitioned accordingly:

- **[`stereorepo/`](stereorepo/README.md)** — **Hermetic.** The operating manual,
  engineering concepts, loop disciplines, and harness mechanisms of the
  `stereorepo` Bounded Context (`ddd:context/stereorepo`). When a new portfolio
  specializes from this scaffold, `wiki/stereorepo/` is inherited intact so the
  portfolio retains the documentation for its tooling and workflows.
- **`<bounded-context>/`** — **Domain-specific.** When a portfolio specializes,
  it adds subdirectories for its own declared Bounded Contexts (for example,
  `wiki/billing/`, `wiki/inventory/`). The business concepts of the product live
  there, completely separated from stereorepo's scaffold concepts.

## Editorial Conventions

Pages in this wiki adhere to Wikipedia-style conventions (stereorepo's DR-185):

1. **The Lead Sentence (MOS:LEAD):** Every page opens with a bolded subject
   followed by a copular definition stating what the concept is:
   > **`Concept`** is a ...
   The lead sentence concurs with the concept's definition in the vocabulary
   schema and serves as a standalone digest.
2. **Closed-World Wikilinks:** Internal concept references use wikilinks
   (`[[concept]]` or scoped `[[context/concept]]`). Every link must resolve to a
   recognized concept page or vocabulary item.
3. **Encyclopedic Register:** Written in third-person, present tense, neutral
   exposition. Narrative histories of specific past runs belong in
   `<module>.history.md`, not in the wiki.
4. **Dereferenced Citations:** Citations to Articles and Decision Records
   point directly to their identifiers (e.g. `A8`, `DR-184`, `DR-185`) rather than
   re-litigating rationale inline.

