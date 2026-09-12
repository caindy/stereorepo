# .meta/.apm

APM primitives, authored here and compiled to whatever harness a portfolio
needs.

This is the **producer** side. `.apm/` is where primitives are written; it is not
where they land. Compilation writes per-target output to `.claude/`, `.github/`,
`.gemini/` and so on — and `.agents/` at a repo root is one of those outputs,
which is why nothing is authored there. That was the mistake this directory used
to make.

## Layout

```
.apm/
  skills/<name>/SKILL.md      a cross-tool meta-guide, with its resources
  prompts/<name>.prompt.md    an executable workflow; also becomes a command
  instructions/<name>.instructions.md   guidance, scoped by an applyTo glob
  agents/<name>.agent.md      a specialized personality
  hooks/<name>.json           lifecycle handlers
```

## What belongs here, and where it comes from

Primitives are **derived from `.meta/assertions/`**, never authored twice:

| Assertion | Primitive |
|---|---|
| a Discipline | `instructions`, with `applies_to` as the `applyTo` glob |
| the Ubiquitous Language | `instructions` scoped to everything — how the language reaches every harness |
| a Personality, or a Persona to interrogate | `agents` |
| a Capability of kind SKILL | `skills` |
| the gate | `hooks` |

**Nothing is here yet, deliberately.** The compile step from assertions to
primitives is unbuilt (see [solorepo's #28](https://github.com/caindy/solorepo/issues/28)), and hand-writing primitives that a
compiler will later generate is the duplication that step exists to remove.

## What the canon says, settled in solorepo's DR-172, DR-173, and DR-174

Checked against APM's own pages and verified on solorepo's #339, #340, and #341,
per the rule that an adopted convention is defined by its canon and not by us.

- **`apm.yml` sits at `.meta/apm.yml`, beside `.meta/.apm/` (solorepo's DR-172).** APM natively
  supports nested package roots, and both `apm compile` and `apm install` accept
  `--root <DIR>` to redirect generated harness files (`.claude/`, `.gemini/`, `.agents/`)
  and root context files (`AGENTS.md`, `CLAUDE.md`) to the repository root.
  Executing `cd .meta && apm compile --root .. --all` compiles from `.meta/` cleanly.
- **Schemas and tooling stay in scaffold inheritance (solorepo's DR-173).** LinkML schemas
  (`.meta/work/`, `.meta/ddd/`) and executable tools (`.meta/say/`, `.meta/hooks/signed_channel.py`,
  `check.py`, `.meta/gate`) are repository infrastructure and metamodels, not agent
  cognitive primitives. Packaging them as skill resources would duplicate them across
  every harness cache directory, invert CI dependencies, and break pre-compilation
  gate validation. They are inherited via Specialization's step two copy set, leaving
  `.meta/.apm/` strictly for agent cognitive primitives.
- **Hook registration is decoupled from tool permissions (solorepo's DR-174).** A `hooks` primitive
  compiles into `.claude/settings.json` under its `hooks` section, but APM has no
  primitive or schema for tool permission allow/deny lists. Security and channel
  enforcement are decoupled from hook inspection: enforced by construction (solorepo's #21)
  by withholding ambient tokens in runners so direct API calls fail with 401 across all
  harnesses, and verified at the PR First gate (`check_pr.py`).
- **Claude Code does not take `prompts`.** For that target the matrix deploys
  `instructions` to `.claude/rules/<name>.md`, `agents` to `.claude/agents/`,
  `skills` to `.claude/skills/<name>/SKILL.md`, `commands` to
  `.claude/commands/<name>.md`, and `hooks` as above; `CLAUDE.md` is generated
  at the root, omitting what `.claude/rules/` already holds, and `AGENTS.md`
  is not generated for it. So the invoked half of the Ubiquitous Language
  regime (solorepo's #35) is a `command` for this harness, not a `prompt`, and `AGENTS.md`
  is not in Claude Code's compile path. — [targets matrix](https://microsoft.github.io/apm/reference/targets-matrix/)
- **Frontmatter per primitive is verified (solorepo's #339).** `instructions` uses `applyTo`
  for scoped rules; `agents` defines name, description, model, and tools; `skills`
  conforms to `agentskills.io` standard matching parent directory name; `prompts`
  defines input parameters and double as slash commands; `hooks` defines lifecycle handlers.
