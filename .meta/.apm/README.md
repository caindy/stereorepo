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

**Compiled by `.meta/apm_compile.py` / `.meta/render.py` from `.meta/assertions/` (stereorepo's DR-172, stereorepo's DR-173, stereorepo's DR-200).**
The primitives are generated derived artifacts rather than hand-written files.
Running `just render` re-compiles them from the assertions and verifies that no
drift has occurred.

## What the canon says, settled in stereorepo's DR-172 and DR-173

Checked against APM's own pages and verified in practice,
per the rule that an adopted convention is defined by its canon and not by us.

- **`apm.yml` sits at `.meta/apm.yml`, beside `.meta/.apm/` (stereorepo's DR-172).** APM natively
  supports nested package roots, and both `apm compile` and `apm install` accept
  `--root <DIR>` to redirect generated harness files (`.claude/`, `.gemini/`, `.agents/`)
  and root context files (`AGENTS.md`, `CLAUDE.md`) to the repository root.
  Executing `cd .meta && apm compile --root .. --all` compiles from `.meta/` cleanly.
- **Schemas and tooling stay in scaffold inheritance (stereorepo's DR-173).** LinkML schemas
  (`.meta/work/`, `.meta/ddd/`) and executable tools (`.meta/hooks/`,
  `check.py`, `.meta/gate`) are repository infrastructure and metamodels, not agent
  cognitive primitives. Packaging them as skill resources would duplicate them across
  every harness cache directory, invert CI dependencies, and break pre-compilation
  gate validation. They are inherited via Specialization's *Copy what is inherited* step copy set, leaving
  `.meta/.apm/` strictly for agent cognitive primitives.
- **Hook registration is not tool permission.** A `hooks` primitive compiles
  into `.claude/settings.json` under its `hooks` section, but APM has no
  primitive or schema for tool permission allow/deny lists, so it carries none.
- **Claude Code does not take `prompts`.** For that target the matrix deploys
  `instructions` to `.claude/rules/<name>.md`, `agents` to `.claude/agents/`,
  `skills` to `.claude/skills/<name>/SKILL.md`, `commands` to
  `.claude/commands/<name>.md`, and `hooks` as above; `CLAUDE.md` is generated
  at the root, omitting what `.claude/rules/` already holds, and `AGENTS.md`
  is not generated for it. So the invoked half of the Ubiquitous Language
  regime is a `command` for this harness, not a `prompt`, and `AGENTS.md`
  is not in Claude Code's compile path. — [targets matrix](https://microsoft.github.io/apm/reference/targets-matrix/)
- **Frontmatter per primitive is verified.** `instructions` uses `applyTo`
  for scoped rules; `agents` defines name, description, model, and tools; `skills`
  conforms to `agentskills.io` standard matching parent directory name; `prompts`
  defines input parameters and double as slash commands; `hooks` defines lifecycle handlers.

## APM Toolchain Integration (stereorepo's DR-201)

The APM package is integrated into the repository operator surface (`just`) via `.meta/apm_compile.py`:

- **Validation:** `just apm validate` verifies assertion-to-primitive alignment and runs downstream `apm compile --validate`.
- **Packaging:** `just apm pack` runs `apm pack` to bundle the package into distributable plugin artifacts (`plugin.json`, `.github/plugin/plugin.json`).
- **Compilation:** `just apm compile` compiles primitives across target harnesses (`claude`, `gemini`, `copilot`), redirecting output to the repository root via `--root ..`.
- **Gate Check:** The repository gate (`just gate meta` / `.meta/gate meta`) runs `@check("apm package")`, executing `apm compile --validate` whenever the `apm` binary is installed. When `apm` is absent the gate reports the check as unrunnable and names it in the closing block — exit code zero where a person runs the gate, non-zero under CI, which installs the CLI in the `files` job (Article 6 as narrowed by stereorepo's DR-261).

## APM Distribution & Upstream Synchronization (stereorepo's DR-206)

To enable downstream specialized portfolios, client repos, and external consumers to install and synchronize stereorepo's cognitive layer:

- **Subdirectory Packaging & Root Cleanliness:** The APM CLI natively consumes virtual subdirectory packages (`apm install caindy/stereorepo/.meta` or `{git: caindy/stereorepo, path: .meta}`). The repository root remains completely clean, preserving the staging boundary rule that `.meta/` is the staging ground (stereorepo's DR-001) and that APM packages nest under `.meta/` (stereorepo's DR-172) without requiring root symlinks.
- **Multi-Harness Authorization:** The package manifest authorizes `claude`, `gemini`, `copilot`, `codex`, and `kiro`. When installed with multi-target flags (e.g. `--target claude,codex,kiro`), APM projects primitives natively into `.claude/`, `.codex/`, and `.kiro/` without bespoke per-vendor compilers.
- **Release:** a versioned GitHub Release, cut from a tag once the gate and `just apm validate` pass. The procedure is not yet a recipe.
- **Downstream Synchronization:** Specialized client repos declare `caindy/stereorepo/.meta@^0.1.0` in their `apm.yml`. Running `apm outdated` inspects upstream tags, and `apm update` applies updates, prunes deleted disciplines, and updates `apm.lock.yaml`.

