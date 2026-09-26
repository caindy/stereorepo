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

- `CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md` are symlinks to this file. Edit `AGENTS.md`.
- `SPECIALIZE.md` is generated from the Specialization Discipline. Edit the
  assertion, not the file.
- Use the vocabulary from the ontology of work in preference to synonyms: a
  *Challenge*, not a ticket or story; an *Actor*, not a user or a bot.
- When a question that demanded an answer is settled, mint its number with
  `.meta/say/move mint`, which reserves it on GitHub so that two branches
  cannot take the same one (DR-128); reading the record for the next free
  number is what every open branch does alike. Write it as
  `.meta/assertions/decisions/DR-0nn.yaml`, re-render, and commit it with the
  change — one commit per settled decision. `.meta/decisions.md` is an index
  generated from them; the entry itself is the assertion file.
- Maintainer-facing exposition lives in `wiki/<context>/` following the Knowledge Management discipline (solorepo's DR-184, solorepo's DR-196) and the Diátaxis Compass (solorepo's DR-194). Route prose before writing: Reference in docstrings, Explanation in `wiki/` and DRs, How-To in `justfile` recipes, and unrouted residue in PR bodies (Article 15). Storage placement (gloss, section, page, or folder) is subordinate to reader posture. Every concept in the Ubiquitous Language carries a corresponding wiki entry maintaining 1:1 parity (A17, solorepo's DR-190). Use the `/wikisplain` skill or `.meta/wikisplain.py` to scaffold and check wiki pages (solorepo's DR-187, solorepo's DR-259).
- Two regimes govern writing (solorepo's DR-198): when communicating in conversation (dialogue, PR review threads, turn responses), speak in the Technical Writer register (`work:personality/technical-writer`: spelled out, self-contained, citations dereferenced, eliminating abstruse shorthand). When authoring durable artifacts, follow the Diátaxis compass. Coder agents implement naturally in Pass 1, then apply the `/technical-writing` skill to clean up docstrings, comments, and documentation before handoff (keeping code docstrings dry Reference contracts without reviewer litigation under solorepo's DR-175, holding source comments to the four permissible exceptions, routing defect histories to `<module>.history.md` under solorepo's DR-171, mechanizing informal constraints before pruning, and auditing suppressions as defects under solorepo's DR-207).
- A difficulty level is the reviewer's verdict, and an agent never guesses one.
  Asked to file a Challenge, file it with `challenge` alone — no `--difficulty`
  on `.meta/say/move file` or `.meta/say/post promote` — and put the level you
  would have chosen under `**Difficulty.**` in the body, where it is a proposal
  the reviewer answers (DR-230). A level is the solo's verdict given in advance,
  so pass `--difficulty` only where the solo named the level himself in this
  session, and quote what he typed in `--mandate "<his words>"`, which the
  channel refuses the level without (DR-278). A level carried over from an
  earlier turn, or inferred from how hard the work looks, is not a mandate.
  `human` is the exception and needs no mandate: it starts no Job and asks for
  the solo, so filing at `human` is how a Job says the next step is not its own
  (DR-235).
- An empty directory carries a README saying what will live there.
- Operational agency is partitioned across three distinct planes (solorepo's DR-252):
  - **Local Operator Plane (`just`)**: Local verification gates (`just gate`), rendering derived assertions (`just render`), citation auditing (`just dereference`), status polling (`just watch`, `just sweep`, `just next`), and pull request checking (`just pr <n>`). The repository operator surface is `just --list`, run at the root (DR-106). Recipes take only flags, subcommands, and atomic identifiers; passing bare multi-word prose positionals across the root verb surface is prohibited, and authoring or search workflows with prose arguments belong in dedicated agent skills invoking underlying tools directly (solorepo's DR-259, solorepo's DR-272). Invoking internal scripts under `.meta/` directly when an equivalent `just` recipe exists is prohibited. Do not run `just gate` at session start or against an unmodified checkout: `main` is evergreen. The gate is an exit condition, not an entrance condition. Run verification gates only after authoring changes and before pushing. When verifying scoped changes during development, prefer targeted gates (`just gate meta`, `just gate python-seed`, `just gate rust-seed`) over the full repository gate.
  - **Attested Mutation Plane (`.meta/say/`)**: State transitions altering shared state on GitHub or in git history (`move`, `post`, `commit`). Role-held, signed via `Actor:` and `Agent:` trailers (Article 19, DR-233), consuming multiline Markdown on `stdin`. Mutating GitHub or git state out-of-band via raw `gh` commands (e.g., `gh issue close`, `gh pr merge`) or unmediated `git commit` is prohibited.
  - **GitHub Inspection Plane (`gh`)**: Unstructured, strictly read-only inspection queries against GitHub (`gh pr view --json`, `gh issue list`, reading diffs, inspecting check runs).
- Before starting work on any change, claiming a Challenge, or handling a pull request, coder agents MUST read the `/pr-first` skill (`.agents/skills/pr-first/SKILL.md`); reviewer agents MUST read `/pr-first-reviewer`. PR First governs the life cycle of every change: formulating the plan under **The plan.** before writing code on `hard` and `human` Challenges (DR-249), opening the pull request at work commencement, attributing every commit via `.meta/say/commit` (Article 19), answering and resolving every review thread (A16), establishing handoff semaphores, and rereading the diff against `origin/main` before handoff, the in-session pass solorepo's DR-181 unified across harnesses. On `hard` and `human` Challenges, modifying tracked repository files or running verification gates prior to opening the pull request via `.meta/say/move open` is strictly prohibited (solorepo's DR-269). A coder records the initial plan under **The plan.** in the pull request body on a zero-diff Seed Commit authored via `.meta/say/commit --allow-empty -m "Record initial plan for Challenge #<n>"` before writing code, and opens that pull request with `.meta/say/move open`. The plan passes two gates before any code, both required (solorepo's DR-273): the solo's approval in session, which permits proceeding under PR First and skips none of it, then the reviewer's approval of the plan on the draft. A reviewer's top-level comment on it is owed until a `.meta/say/post comment` links it. Once both gates pass, push the implementation and request review again while the pull request remains draft. Final reviewer approval marks it ready to merge; a merge conflict returns it to draft until the coder resolves it and requests review again.
- A reviewer-assigned `hard` Challenge first enters the decomposition pass under solorepo's DR-292. The coder proposes child Challenges and their dependencies in an Issue comment; the solo approves by commenting exactly `Approve decomposition` on that Issue; only then may the coder create the Epic's child Challenges with `.meta/say/move decompose`. The Epic is parent work and has no leaf pull request: implementation pull requests close child Challenges, and the merge manager closes the Epic after all children close. The reviewer assigns each child's actual difficulty; the coder's `easy` or `medium` level in its body is only a proposal. This Epic workflow replaces the parent Challenge's implementation pull request plan gate, while each child follows PR First in full.
- A pull request this session opened is handed off and watched until it closes:
  the handoff is an active semaphore, so request review with
  `.meta/say/move request-review <n>` the moment the pull request is open and
  clean; then start `just watch <n>` under a persistent Monitor, monitoring the
  handoff (solorepo's DR-248) to wake the session whenever coder action is
  required or status changes, so a review is answered when it lands and not when
  someone looks. When one closes, `just sweep` names the branches whose remote
  is gone and the command that removes each; run them. Both are the harness's
  business, not a Discipline's step.
- Asked open-endedly what to work on next, run `just next` and read the
  screen. The answer is an Issue: the next Milestone, then the ripe list. An
  open pull request on that screen is the loops' work in progress, not the
  answer; do not go and read its threads. Do not read Issue bodies to find
  out what waits on what: their first line says. Directed instead at a
  specific pull request or Issue, skip `just next` and go straight to that
  target.
- Nothing about this repository is written to the harness's memory. What a
  session needs remembered goes into an artifact that already exists: the
  Python script whose behaviour it changes; failing that, the skill that
  wraps the script; failing that, the prompt hierarchy, this file being its
  top. A memory file is a fact only one session can read.
