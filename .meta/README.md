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
| what this repo asserts | [`assertions/`](assertions/) — the ABox. The prose satellites derive from it. |
| a term for **this** domain | `assertions/domain_vocabulary.yaml` — owned here, never synced |
| anything under `assertions/imported/` | do not edit it. It is solorepo's, and a sync overwrites it. |
| a schema, or checking one | [`schemas.md`](schemas.md), then the module its own load map names |
| how work is meant to proceed here | [`disciplines.md`](disciplines.md) |
| a rule you can cite, or check something against | [`charter.md`](charter.md) — the Articles |
| turning a clone into a portfolio | [`disciplines.md`](disciplines.md) → Specialization |
| **why** something is built this way | [`decisions.md`](decisions.md) — find its DR, then read [`decisions/DR-0nn.md`](decisions/) |
| reasoning that keeps recurring across decisions | [`principles.md`](principles.md) |
| changing or defending a rule | its DR in `assertions/decisions.yaml`, **and** the file that states it |
| what is intended but unbuilt, or still open | [`roadmap.md`](roadmap.md) |
| primitives compiled for a harness | [`.apm/`](.apm/) — derived from `assertions/` |
| opening a pull request, or filing an Issue | [`templates/`](templates/) — the forms; `.github/` is generated from them |

**A digest tells you a rule exists and where it lives; only the file it points at
is sufficient to apply it.** This map is deliberately insufficient.

## Where a paragraph goes — route it as you write it

| It tells a future reader… | It goes to |
| :-- | :-- |
| a word, and what it means | `assertions/vocabulary.yaml`, then re-render |
| what **happened** on this change | the pull request body, using `.meta/templates/pull-request.md` |
| work **noticed and not done** | a linked Issue, before review — never a summary or a file |
| **why** a decision was taken | `assertions/decisions.yaml`, as a DR, then re-render |
| **how** work must proceed, always | `assertions/disciplines.yaml`, then re-render |
| a checkable one-line rule | `assertions/imported/charter.yaml`, then re-render |
| reasoning that recurs across several decisions | `principles.md` |
| what is intended, or still undecided | `roadmap.md` |
| what a schema means and why it is shaped so | the schema itself, per Literate Programming |

Route each paragraph *as you write it*. That is the only moment the routing
decision is cheap. **A commit message is not a destination** (A14): reasoning
left in git history is reached only by a blame walk, which is expensive, lost to
rebase and squash, and attempted only by a reader these artifacts have already
failed. Where no row of the table claims a paragraph, it is residue, and residue
goes to the pull request.

**`vocabulary.md`, `disciplines.md`, `charter.md` and `decisions.md` are
generated.** They derive from `assertions/`, which is the source. So does the ADR
form at `templates/adr.md`, which derives from the `Decision` class itself. Edit
the source and re-render:

```bash
uvx --with pyyaml python .meta/render.py
```

**The gate for `.meta` is `check.py`.** Green before anything here is called
done. It enforces the invariants the schemas state and cannot check, and
subsumes the staleness check above:

```bash
uvx --with linkml --with pyyaml python .meta/check.py
```

**The gate for a pull request is `check_pr.py`.** It reads GitHub rather than
the tree, so it is a separate command with a separate lifecycle — nothing to say
except on a pull request. It holds A15: every item under *what was noticed and
not done* is a link, so the body cannot close over an observation that has
nowhere to live afterwards.

```bash
python3 .meta/check_pr.py 12
```

Both run in [`.github/workflows/gate.yml`](../.github/workflows/gate.yml), which
is the point — a check that runs when someone remembers is not a check.
