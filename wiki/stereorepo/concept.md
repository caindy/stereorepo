# Concept

**Concept** is the atomic unit of domain meaning in a Bounded Context's
[[ubiquitous-language]] (stereorepo's DR-184, stereorepo's DR-190,
stereorepo's DR-195).

In Domain-Driven Design and agentic repository maintenance, domain knowledge must
be parsed into clear, bounded units of thought. While external tools and common
software parlance often speak of "wiki entries", "wiki pages", or "topics",
stereorepo recognizes *Concept* as the foundational semantic unit, deliberately
decoupling the unit of meaning from any specific storage container.

## Contrast with Colloquial Terminology

Maintainers and external queries frequently refer to domain knowledge using
storage-oriented terminology:
- **Wiki page** or **wiki entry:** Identifies the file format (`.md`) or wiki
  system rather than the unit of domain meaning.
- **Topic:** A colloquial term from document management without ontological
  boundaries.
- **Wiki article:** Strongly avoided in stereorepo (`avoid: [wiki article]`). The
  term *Article* is strictly reserved for the empirical clauses of the
  Charter (stereorepo's Article 1, stereorepo's Article 15). Conflating wiki
  expositions with Charter Articles creates dangerous ambiguity between
  explanatory documentation and checkable working agreements.

## Diátaxis Subordination: Hierarchy and Placement

Where a Concept lands in the physical artifact hierarchy is subordinate to the
authoring agent's structural judgement under the Diátaxis Compass:

1. **Schema Gloss:** A minimal machine-checkable definition in
   `vocabulary.yaml`, providing canonical labels, alternative search labels, and
   avoid-lists.
2. **Section or Subsection:** When a concept is tightly coupled to a broader
   aggregate or subsystem, it may be authored as a distinct section (`##`) or
   subsection (`###`) within an existing document.
3. **Dedicated Wiki Page:** When a concept possesses substantial architectural depth,
   independent invariants, or wide cross-cutting relevance, it earns a standalone
   page under `wiki/<bounded-context>/<concept>.md` adhering to MOS:LEAD and
   closed-world wikilinks.
4. **Subdirectory:** Highly complex domain aggregates may expand into a dedicated
   subfolder grouping related concepts.

The agent selects the appropriate depth and container based on the reader's
posture (Learning vs. Work, Action vs. Understanding) rather than forcing every
idea into a one-file-per-thought straightjacket.

---

**See also:** [[ubiquitous-language]], [[knowledge-management]], [[bounded-context]], stereorepo's Article 1, stereorepo's DR-184, stereorepo's DR-185, stereorepo's DR-190, stereorepo's DR-195.
