# .meta — the staging ground

Two kinds of thing belong here:

1. Tools and ideas that make sense of the repository structure.
2. Whatever specializes a fresh clone's contents into a new portfolio.

Everything else in the repo is product material. "Staging" means pre-product, not
temporary. `.meta/` is also the **producer-side authoring surface**: what gets
bundled up and shipped is built from these definitions.

**This file is the core, and the only one here that always loads. Keep it small.**
Every other file in `.meta/` is a satellite, loaded on demand and authoritative
for what it owns. This file routes. It does not restate.

## The load map

| Touching… | Load first |
| :-- | :-- |
| naming anything, or reaching for a word | [`vocabulary.md`](vocabulary.md) — and do not mint a term without the solo |
| what solorepo asserts about itself | [`assertions/`](assertions/) — the ABox. The prose satellites derive from it. |
| a schema, or checking one | [`schemas.md`](schemas.md), then the module its own load map names |
| how work is meant to proceed here | [`disciplines.md`](disciplines.md) |
| turning a clone into a portfolio | [`disciplines.md`](disciplines.md) → Specialization |
| **why** something is built this way | [`decisions.md`](decisions.md) — find its DR |
| reasoning that keeps recurring across decisions | [`principles.md`](principles.md) |
| changing or defending a rule | its DR in `decisions.md`, **and** the file that states it |
| what is intended but unbuilt, or still open | [`roadmap.md`](roadmap.md) |
| agent definitions supporting the scaffold | `.agents/` |

**A digest tells you a rule exists and where it lives; only the file it points at
is sufficient to apply it.** This map is deliberately insufficient.

## Where a paragraph goes — route it as you write it

| It tells a future reader… | It goes to |
| :-- | :-- |
| a word, and what it means | `assertions/vocabulary.yaml`, then re-render |
| **why** a decision was taken | `decisions.md`, as a DR |
| **how** work must proceed, always | `assertions/disciplines.yaml`, then re-render |
| reasoning that recurs across several decisions | `principles.md` |
| what is intended, or still undecided | `roadmap.md` |
| what a schema means and why it is shaped so | the schema itself, per Literate Programming |

Route each paragraph *as you write it*. That is the only moment the routing
decision is cheap. **A commit message is not a destination**: a decision recorded
only in git history has not been recorded.

**`vocabulary.md` and `disciplines.md` are generated.** They derive from
`assertions/`, which is the source. Edit the assertions and re-render:

```bash
uvx --with pyyaml python .meta/render.py
uvx --with pyyaml python .meta/render.py --check   # fails if stale
```
