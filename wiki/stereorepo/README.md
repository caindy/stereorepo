# Stereorepo Context Knowledge Base

The maintainer-facing knowledge base for the `stereorepo` Bounded Context
(`ddd:context/stereorepo`, stereorepo's DR-184, stereorepo's DR-185).

This directory holds the conceptual expositions for building software products
as a team of one with a fleet of autonomous agents. It is inherited intact by
specialized portfolios so they retain the reference documentation for their
underlying tooling and gate mechanisms.

## Pages in this Context

- **[[knowledge-management|Knowledge Management]]** — The discipline governing
  maintainer exposition, encyclopedic pages, and Bounded Context documentation.
- **[[externalized-memory|Externalized Memory]]** — Why what a session would
  remember is compiled into artifacts rather than held in the agent.
- **[[flight|Flight]]** — An Issue with children, whose delivered value the
  developer desk-checks once, after its parts have landed.
- **[[issue|Issue]]** — One unit of work, as one Markdown file on the board.
- **[[board|Board]]** — A repository's set of Issue files, whose directories
  are the stages.
- **[[stage|Stage]]** — Where an Issue is on its way to `main`, held as the
  directory its file sits in.
- **[[developer|Developer]]** — The one person a repository serves.
- **[[seat|Seat]]** — One of the two harness sessions that take an Issue to
  `main` in turns.
- **[[supervisor|Supervisor]]** — The program that runs the seats and moves an
  Issue from what it observes.
- **[[quiet-turn|Quiet turn]]** — A seat's turn that changes nothing, by which
  it accepts the state it found.
- **[[desk-check|Desk check]]** — The developer's check, by hand, of a
  `developer` Issue or a Flight.
- **[[meta-harness|Meta-harness]]** — A tool that runs coding-agent harnesses
  and passes work between them, and why none surveyed was adopted.
- **[[cockpit|Cockpit]]** — The one view, yet to be built, across every
  repository the developer runs a pair loop in.
- **[[ubiquitous-language|Ubiquitous Language]]** — How terms are defined,
  bounded, and checked to prevent semantic collision across agents and the developer.

## Specialization Invariant

When specializing this repository into an independent portfolio:
- **Do not edit or delete `wiki/stereorepo/`**. It remains the operating manual for
  the repository's inherited tooling and workflows.
- Create new peer directories for your product's Bounded Contexts (for example,
  `wiki/<context>/`).

