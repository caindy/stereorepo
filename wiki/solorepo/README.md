# Solorepo Context Knowledge Base

The maintainer-facing knowledge base for the `solorepo` Bounded Context
(`ddd:context/solorepo`, solorepo's DR-184, solorepo's DR-185).

This directory holds the conceptual expositions for building software products
as a team of one with a fleet of autonomous agents. It is inherited intact by
specialized portfolios so they retain the reference documentation for their
underlying loops, harnesses, and gate mechanisms.

## Pages in this Context

- **[[knowledge-management|Knowledge Management]]** — The discipline governing
  maintainer exposition, encyclopedic pages, and Bounded Context documentation.
- **[[pr-first|PR First]]** — The operational workflow where work begins with
  a pull request and autonomous loops advance, review, and merge it.
- **[[ubiquitous-language|Ubiquitous Language]]** — How terms are defined,
  bounded, and checked to prevent semantic collision across agents and human.

## Specialization Invariant

When specializing this repository into an independent portfolio:
- **Do not edit or delete `wiki/solorepo/`**. It remains the operating manual for
  the repository's inherited tooling and workflows.
- Create new peer directories for your product's Bounded Contexts (for example,
  `wiki/<context>/`).

