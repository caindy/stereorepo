# Ubiquitous Language

**Ubiquitous Language** is the discipline that ensures every concept within a
Bounded Context carries exactly one unambiguous name shared by human and agents
alike (stereorepo's DR-184, DR-185).

In an agentic development environment where autonomous loops author and review
code at high velocity, semantic drift is an acute failure mode. When different
agents invent ad-hoc synonyms for the same concept (for example, referring to
an Issue alternately as a "ticket", "story", or "task"), the mental model
fractures. The Ubiquitous Language discipline eliminates floating signifiers by
forcing every domain concept through an explicit vocabulary contract.

## Two Halves: The Gloss and the Exposition

The Ubiquitous Language operates across two complementary substrates:

1. **The Machine Schema (`vocabulary.yaml`):** The formal LinkML assertion
   defining the term's identifier, preferred label, alternative labels,
   avoid list, and a concise single-sentence definition (the gloss). This
   substrate is consumed by linters, checkers, and gate verification.
2. **The Knowledge Base (`wiki/<context>/`):** The encyclopedic narrative
   exposition explaining the concept's mechanics, edge cases, and design
   trade-offs in human-readable prose.

The lead sentence of the wiki page concurs with the machine gloss in the schema
(stereorepo's DR-185), guaranteeing that human exposition and machine
verification never diverge.

## Bounded Contexts

Meaning is never global. A term defined in the `stereorepo` Bounded Context
belongs to the engineering and loop harness. Specialized portfolios introduce
their own Bounded Contexts where business concepts are defined independently,
preventing cross-domain collisions.

## The Minting Ceremony

Agents do not casually invent new terminology in freeform text. When a new
concept is required, it must undergo the minting ceremony with the human:
establishing its preferred label, scope note, and avoid-list in the assertions.
Writing explains; deciding decides.

---

**See also:** [[knowledge-management]], stereorepo's DR-041, DR-184, DR-185.

