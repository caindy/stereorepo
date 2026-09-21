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
- Two regimes govern writing (solorepo's DR-198): when communicating in conversation (dialogue, PR review threads, turn responses), speak in the Technical Writer register (`work:personality/technical-writer`: spelled out, self-contained, citations dereferenced, eliminating abstruse shorthand). When authoring durable artifacts, follow the Diátaxis compass. Coder agents implement naturally in Pass 1, then apply the `/technical-writing` skill to clean up docstrings, comments, and documentation before handoff (keeping code docstrings dry Reference contracts without reviewer litigation under solorepo's DR-175, holding source comments to the four permissible exceptions, routing defect histories to `<module>.history.md` under solorepo's DR-171, mechanizing informal constraints before pruning, and auditing suppressions as defects under solorepo's DR-207).
- An empty directory carries a README saying what will live there.
- Operational agency is partitioned across three distinct planes (solorepo's DR-252):
  - **Local Operator Plane (`just`)**: Local verification gates (`just gate`), rendering derived assertions (`just render`), citation auditing (`just dereference`), status polling (`just watch`, `just sweep`, `just next`), and pull request checking (`just pr <n>`). The repository operator surface is `just --list`, run at the root (solorepo's DR-106). Invoking internal scripts under `.meta/` directly when an equivalent `just` recipe exists is prohibited. Do not run `just gate` at session start or against an unmodified checkout: `main` is evergreen. The gate is an exit condition, not an entrance condition. Run verification gates only after authoring changes and before pushing. When verifying scoped changes during development, prefer targeted gates (`just gate meta`, or a declared Project gate) over the full repository gate.
  - **Attested Mutation Plane (`.meta/say/`)**: State transitions altering shared state on GitHub or in git history (`move`, `post`, `commit`). Role-held, signed via `Actor:` and `Agent:` trailers (Article 19, solorepo's DR-233), consuming multiline Markdown on `stdin`. Mutating GitHub or git state out-of-band via raw `gh` commands (e.g., `gh issue close`, `gh pr merge`) or unmediated `git commit` is prohibited.
  - **GitHub Inspection Plane (`gh`)**: Unstructured, strictly read-only inspection queries against GitHub (`gh pr view --json`, `gh issue list`, reading diffs, inspecting check runs).
- Before starting work on any change, claiming a Challenge, or handling a pull request, coder agents MUST read the `/pr-first` skill (`.agents/skills/pr-first/SKILL.md`); reviewer agents MUST read `/pr-first-reviewer`. PR First governs the life cycle of every change: formulating the plan under **The plan.** before writing code on `hard` and `human` Challenges (solorepo's DR-249), opening the pull request at work commencement, attributing every commit via `.meta/say/commit` (Article 19), answering and resolving every review thread (A16), and establishing handoff semaphores.
- A pull request this session opened is handed off and watched until it closes:
  the handoff is an active semaphore, so request review with
  `.meta/say/move request-review <n>` the moment the pull request is open and
  clean; then start `just watch <n>` under a persistent Monitor, so a review is
  answered when it lands and not when someone looks. When one closes, `just
  sweep` names the branches whose remote is gone and the command that removes
  each; run them. Both are the harness's business, not a Discipline's step.
- Asked open-endedly what to work on next, run `just next` and read the screen.
  The answer is an Issue: the next Milestone, then the ripe list. An open pull
  request on that screen is the loops' work in progress, not the answer; do not
  go and read its threads. Do not read Issue bodies to find out what waits on
  what: their first line says. Directed instead at a specific pull request or
  Issue, skip `just next` and go straight to that target.
- Nothing about this repository is written to the harness's memory. What a
  session needs remembered goes into an artifact that already exists: the Python
  script whose behaviour it changes; failing that, the skill that wraps the
  script; failing that, the prompt hierarchy, this file being its top. A memory
  file is a fact only one session can read.
