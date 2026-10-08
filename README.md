# stereorepo

`<human>`

👋 Hi! I built this to teach my other repos how to work. Everything--issues,
vocabulary, roadmap, etc.--is written to the working repo. For now it assumes
one human directing one set of agents' pairing loop. It's not meant to
tmux/herdr a bunch of WezTerm panes. Nor is this trying to be a
[meta-harness](./wiki/stereorepo/meta-harness.md), though I do use it with
Codex, Claude, agy, and Copilot. There are much better options out there if you
want to work that way: [firstmate](https://github.com/kunchenguid/firstmate) [swarmforge](https://github.com/unclebob/swarm-forge) [openrig](https://github.com/mvschwarz/openrig).

No, this is serialized and incremental, almost ponderous. I got tired of a huge
merge queue and backing out major missteps. You can add issues asynchronously,
but all delivery runs through a pair of agents collaborating on one issue at a
time.

`</human>`

**Stereo** for the pairing: two seats work each issue, like two channels
carrying one signal. And for the **stereotype**, a printing plate cast from a
mould to stamp out copies, which is what this repository is: a template you
specialize to start a product repository. The result is a **Portfolio**: one
repository, one Bounded Context, one Ubiquitous Language, holding however many
Products and Projects.

The premise it is built on: judge any way of working by whether it still holds
with one developer and agents. A process that assumes several people — hand-offs,
review rotas, ceremonies — is a poor fit. Work reaches `main` through the pair
loop: two agent seats take one issue at a time from the board in `issues/`,
taking turns in one worktree, and a deterministic program moves the issue along
from what it can observe. The seats know nothing of the protocol, and there are
no pull requests.

## Start here

**Point an agent at this repository and tell it to read
[`SPECIALIZE.md`](SPECIALIZE.md).** That is the whole entry point. The steps are
an instruction to follow rather than a program to run, because the work is
judgement about one specific portfolio. Running repository tooling on a fresh
clone requires Python >= 3.13 (DR-351).

A repository that already holds a product is adopted rather than specialized:
point the agent at [`ADOPT.md`](ADOPT.md) instead, with this repository checked
out beside it.

## What you inherit

| | |
|---|---|
| **A vocabulary** | An ontology of work — Portfolio, Product, Project, Discipline, Decision, Persona, Role, Issue — reified in LinkML, alongside DDD itself. Your domain language stays your own; this is the language for talking about the work. |
| **Disciplines** | Structured ways of working that must be adhered to because they are not programs: Specialization, Literate Programming, Progressive Disclosure, Dogfooding. |
| **A gate** | `check.py` enforces six invariants the schemas state and cannot check, including reference resolution across files. |
| **A load map** | One small always-loaded file that routes to everything else, and is deliberately insufficient on its own. |
| **A board** | `issues/`, where each issue is a file and the directory it sits in is its stage. The pair loop works it from outside your tree. |

## Working on the scaffold itself

[`AGENTS.md`](AGENTS.md) — and `CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md`, which are symlinks
to it — orients an agent working on stereorepo rather than on a portfolio made
from it. From there, [`.meta/README.md`](.meta/README.md) is the load map.

## Provenance

The Disciplines and gates here are not invented. They are drawn from Domain-Driven
Design, from Alan Cooper's persona work, from SKOS, and from a working
`python_bootstrap` repository whose load map and template-as-data argument are
adopted almost whole. Where a rule exists, `.meta/decisions.md` records what it
cost to learn.

This file is for **arriving**; [`SPECIALIZE.md`](SPECIALIZE.md) and
[`ADOPT.md`](ADOPT.md) are for **acting**.

## License

MIT; see [`LICENSE`](LICENSE). The skills vendored under `bootstraps/python/`
keep their upstream MIT licenses, recorded in
[`bootstraps/python/PROVENANCE.md`](bootstraps/python/PROVENANCE.md).
