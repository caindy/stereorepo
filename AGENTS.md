# stereorepo

A scaffold for building software products with **one human and a pair of
agents**. The end state is a repository you clone to start a new product repo.

`.meta/` holds the tools and ideas that make sense of the structure and that
specialize a fresh clone into a new portfolio. Everything outside `.meta/` is product
material.

Judge any proposal by whether it still works with one human and agents. A
process that assumes several people — hand-offs, review rotas, team ceremonies —
is a poor fit here.

## Directory

| Path | What it is |
|---|---|
| [`README.md`](README.md) | The landing page. What stereorepo is, for anyone arriving. |
| [`SPECIALIZE.md`](SPECIALIZE.md) | Generated. The steps for turning a clone into a portfolio. |
| [`.meta/README.md`](.meta/README.md) | **Start here.** A load map routing to everything else. Deliberately small. |
| `.meta/` | The staging ground. Never ships as product content. |
| `.meta/.apm/` | APM primitives, compiled to whatever harness is needed. Derived from `assertions/`. |
| `issues/` | The board: one Markdown file per Issue, and the directory it sits in is its stage. |
| `pair/` | The pair loop, which carries Issues from the backlog to `main`. Scaffold-only. |
| `stakeholders/` | Product-side stakeholder material: a customer is a Persona, an internal stakeholder a Role, and the word is not a term (DR-041). |

## Delivery

Work reaches `main` through the pair loop. Two seats take one Issue at a time
from `issues/backlog/` to `main`, taking turns in one worktree, and a
deterministic supervisor moves the Issue between stages from what it can
observe. There are no pull requests.

- To add work, commit a file to `issues/backlog/` (or `issues/roadmap/`, if it
  is not yet elaborated) on `main`. Its filename slug is its id. Front matter
  holds only `difficulty`, `waits_on` and `parent`, and all three are optional.
- `just pair` runs the loop; `just pair-status` shows the board and the Issue in
  flight; `just pair-accept` and `just pair-resume` answer a desk check.
- A seat that finds work outside its Issue writes it as a new file in
  `issues/backlog/` instead of doing it.

## Conventions

- `CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md` are symlinks to this file. Edit `AGENTS.md`.
- `SPECIALIZE.md` is generated from the Specialization Discipline. Edit the
  assertion, not the file.
- Use the vocabulary from the ontology of work in preference to synonyms: an
  *Issue*, not a ticket or story; a *seat*, not a coder or reviewer; the
  *human*, not the user or the owner.
- When a question that demanded an answer is settled, write it as
  `.meta/assertions/decisions/DR-nnn.yaml`, where the number is the highest number the record holds plus one,
  re-render, and commit it with the change.
  `.meta/decisions.md` is an index generated from them; the entry itself is the
  assertion file.
- Maintainer-facing exposition lives in `wiki/<context>/` following the Knowledge Management discipline (stereorepo's DR-184, stereorepo's DR-196) and the Diátaxis Compass (stereorepo's DR-194). Route prose before writing: Reference in docstrings, Explanation in `wiki/` and DRs, How-To in `justfile` recipes, and unrouted residue in the Issue file. Every concept in the Ubiquitous Language carries a corresponding wiki entry (A17, stereorepo's DR-190). Use the `/wikisplain` skill to scaffold and check wiki pages (stereorepo's DR-187).
- Two regimes govern writing (stereorepo's DR-198): in conversation, speak in the
  Technical Writer register (spelled out, self-contained, citations
  dereferenced). When authoring durable artifacts, follow the Diátaxis compass,
  and apply the `/technical-writing` skill to docstrings, comments and
  documentation (stereorepo's DR-175, stereorepo's DR-207).
- An empty directory carries a README saying what will live there.
- The repository operator surface is `just --list`, run at the root
  (stereorepo's DR-106). Recipes take only flags, subcommands and atomic
  identifiers (stereorepo's DR-259, stereorepo's DR-272); do not invoke a script
  under `.meta/` directly where a recipe wraps it. `just gate` is an exit condition, not an entrance condition:
  run it after authoring changes, not at session start. Prefer a targeted gate
  (`just gate meta`, `just gate python-seed`, `just gate rust-seed`) while
  working.
- Nothing about this repository is written to the harness's memory. What a
  session needs remembered goes into an artifact that already exists: the
  Python script whose behaviour it changes; failing that, the skill that
  wraps the script; failing that, the prompt hierarchy, this file being its
  top. A memory file is a fact only one session can read.
