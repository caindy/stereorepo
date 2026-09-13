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

- `CLAUDE.md` and `GEMINI.md` are symlinks to this file. Edit `AGENTS.md`.
- Use the vocabulary in `.meta/vocabulary.md` in preference to synonyms, and do
  not mint a term without an explicit decision. Check DDD first, then the
  inherited vocabulary, then ask.
- `vocabulary.md`, `disciplines.md` and anything else with a generated banner
  derive from `.meta/assertions/`. Edit the assertion and re-render.
- Never edit `.meta/assertions/imported/`. It is the scaffold's, and a sync
  overwrites it. Your terms go in `domain_vocabulary.yaml`.
- When a question that demanded an answer is settled, mint its number with
  `.meta/say/move mint`, which reserves it on GitHub so that two branches
  cannot take the same one; reading the record for the next free number is what
  every open branch does alike. Write it as
  `.meta/assertions/decisions/DR-0nn.yaml`, re-render, and commit it with the
  change — one commit per settled decision. `.meta/decisions.md` is an index
  generated from them; the entry itself is the assertion file.
- Maintainer-facing exposition lives in `wiki/<context>/` following the Knowledge Management discipline (solorepo's DR-184, solorepo's DR-196) and the Diátaxis Compass (solorepo's DR-194). Route prose before writing: Reference in docstrings, Explanation in `wiki/` and DRs, How-To in `justfile` recipes, and unrouted residue in PR bodies (Article 15). Storage placement (gloss, section, page, or folder) is subordinate to reader posture. Every concept in the Ubiquitous Language carries a corresponding wiki entry maintaining 1:1 parity (A17, solorepo's DR-190). Use `just wikisplain <concept>` or `.meta/wikisplain.py` to scaffold and check wiki pages (solorepo's DR-187).
- Two regimes govern writing (solorepo's DR-198): when communicating in conversation (dialogue, PR review threads, turn responses), speak in the Technical Writer register (`work:personality/technical-writer`: spelled out, audience named, citations dereferenced, eliminating abstruse shorthand). When authoring durable artifacts, follow the Diátaxis compass. Coder agents implement naturally in Pass 1, then apply the `/technical-writing` skill to clean up docstrings, comments, and documentation before handoff (keeping code docstrings dry Reference contracts, routing defect histories to `<module>.history.md`, and routing conceptual explanation to `wiki/` or Decision Records).
- An empty directory carries a README saying what will live there.
- The full repository operator surface is `just --list`, run at the root:
  every recipe invokes one tool under `.meta/`, is self-documented by its own
  comment, and the file is rendered from the assertions, so a second list kept
  here would drift the moment a recipe did. Run it before reaching for a raw
  script, an ad-hoc API call, or a human. Not installed? `uvx --from rust-just
  just`.
- A pull request this session opened is handed off and watched until it closes:
  the handoff is an active semaphore, so request review with
  `.meta/say/move request-review <n>` the moment the pull request is open and
  clean; then start `just watch <n>` under a persistent Monitor, so a review is
  answered when it lands and not when someone looks. When one closes, `just
  sweep` names the branches whose remote is gone and the command that removes
  each; run them. Both are the harness's business, not a Discipline's step.
- Asked what to work on next, run `just next` and read the screen. The answer is
  an Issue: the next Milestone, then the ripe list. An open pull request on
  that screen is the loops' work in progress, not the answer; do not go and read
  its threads. Do not read Issue bodies to find out what waits on what: their
  first line says.
- Nothing about this repository is written to the harness's memory. What a
  session needs remembered goes into an artifact that already exists: the Python
  script whose behaviour it changes; failing that, the skill that wraps the
  script; failing that, the prompt hierarchy, this file being its top. A memory
  file is a fact only one session can read.
