# solorepo

A scaffold for building software products as a **team of one in the agentic AI
era**. The end state is a repository you clone to start a new product repo.

`.meta/` holds the tools and ideas that make sense of the structure and that
specialize a fresh clone into a new portfolio. Everything outside `.meta/` is product
material.

Judge any proposal by whether it still works with one human and a fleet of
agents. A process that assumes several people — hand-offs, review rotas, team
ceremonies — is a poor fit here unless an agent can hold the other seat.

## Directory

| Path | What it is |
|---|---|
| [`README.md`](README.md) | The landing page. What solorepo is, for anyone arriving. |
| [`SPECIALIZE.md`](SPECIALIZE.md) | Generated. The steps for turning a clone into a portfolio. |
| [`.meta/README.md`](.meta/README.md) | **Start here.** A load map routing to everything else. Deliberately small. |
| `.meta/` | The staging ground. Never ships as product content. |
| `.meta/.agents/` | Agent definitions supporting the scaffold. Contents not yet decided. |
| `stakeholders/` | Product-side stakeholder material. Taxonomy not yet decided. |

## Conventions

- `CLAUDE.md` is a symlink to this file. Edit `AGENTS.md`.
- `SPECIALIZE.md` is generated from the Specialization Discipline. Edit the
  assertion, not the file.
- Use the vocabulary from the ontology of work in preference to synonyms: a
  *Challenge*, not a ticket or story; an *Actor*, not a user or a bot.
- When a decision is settled and implemented, add an entry to the decision record
  in `.meta/decisions.md` and commit it together with the change.
