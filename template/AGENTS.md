# __PORTFOLIO_NAME__

__PORTFOLIO_DESCRIPTION__

`.meta/` holds the tools and ideas that make sense of the structure. Everything
outside `.meta/` is product material.

Judge any proposal by whether it still works with one human and a fleet of
agents. A process that assumes several people — hand-offs, review rotas, team
ceremonies — is a poor fit here unless an agent can hold the other seat.

## Directory

| Path | What it is |
|---|---|
| [`README.md`](README.md) | The landing page. |
| [`.meta/README.md`](.meta/README.md) | **Start here.** A load map routing to everything else. Deliberately small. |
| `.meta/` | The staging ground. Never ships as product material. |
| `.meta/.apm/` | APM primitives, compiled to whatever harness is needed. Derived from `assertions/`. |
| `stakeholders/` | Product-side stakeholder material. |

## Conventions

- `CLAUDE.md` is a symlink to this file. Edit `AGENTS.md`.
- Use the vocabulary in `.meta/vocabulary.md` in preference to synonyms, and do
  not mint a term without an explicit decision. Check DDD first, then the
  inherited vocabulary, then ask.
- `vocabulary.md`, `disciplines.md` and anything else with a generated banner
  derive from `.meta/assertions/`. Edit the assertion and re-render.
- Never edit `.meta/assertions/imported/`. It is the scaffold's, and a sync
  overwrites it. Your terms go in `domain_vocabulary.yaml`.
- When a decision is settled and implemented, add an entry to
  `.meta/decisions.md` and commit it together with the change.
- The gate is `uvx --with linkml --with pyyaml python .meta/check.py`. Green
  before anything is called done.
