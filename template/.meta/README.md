# .meta — the staging ground

Two kinds of thing belong here:

1. Tools and ideas that make sense of the repository structure.
2. The assertions this portfolio makes about itself, and the tooling that
   renders and checks them.

Everything else in the repo is product material. "Staging" means pre-product, not
temporary.

**This file is the core, and the only one here that always loads. Keep it small.**
Every other file in `.meta/` is a satellite, loaded on demand and authoritative
for what it owns. This file routes. It does not restate.

## The load map

| Touching… | Load first |
| :-- | :-- |
| naming anything, or reaching for a word | [`vocabulary.md`](vocabulary.md) — and do not mint a Concept without the human |
| what this repo asserts | [`assertions/`](assertions/) — the ABox. The prose satellites derive from it. |
| a term for **this** domain | `assertions/domain_vocabulary.yaml` — owned here, never synced |
| anything under `assertions/imported/` | do not edit it. It came from the scaffold, and a sync overwrites it. |
| a schema, or checking one | [`schemas.md`](schemas.md), then the module its own load map names |
| how work is meant to proceed here | [`disciplines.md`](disciplines.md) |
| a rule you can cite, or check something against | [`charter.md`](charter.md) — the Articles |
| **why** something is built this way | [`decisions.md`](decisions.md) — find its DR, then read [`assertions/decisions/DR-0nn.yaml`](assertions/decisions/) |
| reasoning that keeps recurring across decisions | [`principles.md`](principles.md) |
| changing or defending a rule | its DR in `assertions/decisions/`, **and** the file that states it |
| an id you need to resolve — `work:persona/the-human`, say | `grep -rn -A2 "id: <the curie>" .meta/assertions/`. Every identified object is declared once, there |
| what to work on next, or what is intended but unbuilt | the board, `issues/` at the root: `backlog/` is the queue, `roadmap/` what is intended and not yet elaborated |
| primitives compiled for a harness | [`.apm/`](.apm/) — derived from `assertions/` |
| writing a Decision | [`templates/decision.md`](templates/decision.md) — the form |

**A digest tells you a rule exists and where it lives; only the file it points at
is sufficient to apply it.** This map is deliberately insufficient.

## Where a paragraph goes — route it as you write it

| It tells a future reader… | It goes to |
| :-- | :-- |
| a word, and what it means | `assertions/vocabulary.yaml`, then re-render |
| what **happened** on this change | the Issue file |
| work **noticed and not done** | a new Issue in `issues/backlog/` — never a summary |
| **why** a decision was taken | a new `assertions/decisions/DR-nnn.yaml`, its number the highest number the record holds plus one, then re-render — and name in `enacted_in` where its rule now lives |
| a **mandate** — what someone must do | the Discipline or Article that owns it, never the DR. A20: a rule that lives only in the record is not in force |
| **how** work must proceed, always | `assertions/disciplines.yaml`, then re-render |
| a checkable one-line rule | `assertions/imported/charter.yaml`, then re-render |
| reasoning that recurs across several decisions | `principles.md` |
| what is intended, or still undecided | an Issue in `issues/roadmap/` |
| what a schema means and why it is shaped so | the schema itself, per Literate Programming |

Route each paragraph *as you write it*. That is the only moment the routing
decision is cheap. **A commit message is not a destination** (A14): reasoning
left in git history is reached only by a blame walk, which is expensive, lost to
rebase and squash, and attempted only by a reader these artifacts have already
failed. Where no row of the table claims a paragraph, it is residue, and residue
goes to the Issue file.

**`vocabulary.md`, `disciplines.md`, `charter.md` and `decisions.md` are
generated.** They derive from `assertions/`, which is the source. So does the
Decision form at `templates/decision.md`, which derives from the `Decision`
class itself. Edit the source and re-render:

```bash
uvx --python 3.13 --with pyyaml python .meta/render.py
```

**The verbs are `just` recipes, at the root.** `just --list` names them; each
invokes a tool under `.meta/` and implements nothing, and the file is rendered
from the assertions. `just` is installed per machine, or run as
`uvx --from rust-just just`.

**The gate for `.meta` is `check.py`.** Green before anything here is called
done. It enforces the invariants the schemas state and cannot check, and
subsumes the staleness check above:

```bash
uvx --python 3.13 --with linkml --with pyyaml python .meta/check.py
```

**One verb runs any Project's gate, or a Product's: `.meta/gate`.** It reads
`assertions/structure.yaml` for what to run and each gate's report for what
happened, and a gate that prints no step in A21's shape fails — as does a run
that selected nothing. A Project is gated by being asserted: the pair loop runs
`just gate` before an Issue lands, and names no Project itself.

```bash
.meta/gate                  # every Project
.meta/gate meta             # one Project: check.py alone
```
