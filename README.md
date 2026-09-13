# solorepo

A scaffold for building software products as a **team of one in the agentic AI
era**. Clone it, specialize it, and you have a **Portfolio**: one repository, one
Bounded Context, one Ubiquitous Language, holding however many Products and
Projects.

The premise it is built on: judge any way of working by whether it still holds
with one human and a fleet of agents. A process that assumes several people —
hand-offs, review rotas, ceremonies — is a poor fit unless an agent can hold the
other seat.

## Start here

**Point an agent at this repository and tell it to read
[`SPECIALIZE.md`](SPECIALIZE.md).** That is the whole entry point. The steps are
an instruction to follow rather than a program to run, because the work is
judgement about one specific portfolio.

## What you inherit

| | |
|---|---|
| **A vocabulary** | An ontology of work — Capability, Permission, Role, Goal, Remit, Agency, Actor, Job — reified in LinkML, alongside DDD itself. Your domain language stays your own; this is the language for talking about the work. |
| **Disciplines** | Structured ways of working that must be adhered to because they are not programs: Specialization, Literate Programming, Progressive Disclosure, Dogfooding. |
| **A gate** | `check.py` enforces six invariants the schemas state and cannot check, including reference resolution across files. |
| **A load map** | One small always-loaded file that routes to everything else, and is deliberately insufficient on its own. |

## Working on the scaffold itself

[`AGENTS.md`](AGENTS.md) — and `CLAUDE.md` and `GEMINI.md`, which are symlinks
to it — orients an agent working on solorepo rather than on a portfolio made
from it. From there, [`.meta/README.md`](.meta/README.md) is the load map.

## Provenance

The Disciplines and gates here are not invented. They are drawn from Domain-Driven
Design, from Alan Cooper's persona work, from SKOS, and from a working
`python_bootstrap` repository whose load map and template-as-data argument are
adopted almost whole. Where a rule exists, `.meta/decisions.md` records what it
cost to learn.

This file is for **arriving**; [`SPECIALIZE.md`](SPECIALIZE.md) is for **acting**.
