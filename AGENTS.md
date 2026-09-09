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
| `.meta/.apm/` | APM primitives, compiled to whatever harness is needed. Derived from `assertions/`. |
| `stakeholders/` | Product-side stakeholder material: a customer is a Persona, an internal stakeholder a Role, and the word is not a term (DR-041). |

## Conventions

- `CLAUDE.md` is a symlink to this file. Edit `AGENTS.md`.
- `SPECIALIZE.md` is generated from the Specialization Discipline. Edit the
  assertion, not the file.
- Use the vocabulary from the ontology of work in preference to synonyms: a
  *Challenge*, not a ticket or story; an *Actor*, not a user or a bot.
- When a question that demanded an answer is settled, write it as
  `.meta/assertions/decisions/DR-0nn.yaml`, re-render, and commit it with the
  change — one commit per settled decision. `.meta/decisions.md` is an index
  generated from them; the entry itself is the assertion file.
- An empty directory carries a README saying what will live there.
- A pull request this session opened is watched until it closes: `just watch <n>`
  under a persistent Monitor, started the moment it is open, so a review is
  answered when it lands and not when someone looks. When one closes, `just
  sweep` names the branches whose remote is gone and the command that removes
  each; run them. Both are the harness's business, not a Discipline's step.
- Asked what to work on next, run `just next` and read the screen. The
  answer is an Issue: the next Milestone, then the ripe list. An open pull
  request on that screen is the loops' work in progress, not the answer;
  do not go and read its threads. Do not read Issue bodies to find out what
  waits on what: their first line says.
- Nothing about this repository is written to the harness's memory. What a
  session needs remembered goes into an artifact that already exists: the
  Python script whose behaviour it changes; failing that, the skill that
  wraps the script; failing that, the prompt hierarchy, this file being its
  top. A memory file is a fact only one session can read.
