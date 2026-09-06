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
primitives is unbuilt (see [#28](https://github.com/caindy/solorepo/issues/28)), and hand-writing primitives that a
compiler will later generate is the duplication that step exists to remove.

## What the canon says, read on 2026-09-06

Checked against APM's own pages, per the rule that an adopted convention is
defined by its canon and not by us. Each line names where it was read.

- **A `hooks` primitive is merged into `.claude/settings.json`, and only its
  `hooks` section.** `.apm/hooks/<name>.json` is a settings-slice keyed by
  event (`PreToolUse`, `Stop`, with aliases normalised across targets); on
  install it lands in that section, and a sidecar `apm-hooks.json` records
  ownership so a removed target's entries come out cleanly. Nothing in APM
  writes a `permissions` allow or deny list; the only permission-shaped field
  is `allowed-tools` in a skill's frontmatter, read by the runtime. A hook can
  register `signed_channel.py`; the script itself, and `.meta/say`, are
  programs and not primitives, and ride only as a skill's supporting
  resources. — [hooks and commands](https://microsoft.github.io/apm/producer/author-primitives/hooks-and-commands/)
- **`apm.yml` sits at the package root, beside `.apm/`.** The pages show no
  nested root, so `.meta/` as the root with `.meta/apm.yml` fits the shape and
  is not confirmed as accepted. — [package types](https://microsoft.github.io/apm/reference/package-types/)
- **Claude Code does not take `prompts`.** For that target the matrix deploys
  `instructions` to `.claude/rules/<name>.md`, `agents` to `.claude/agents/`,
  `skills` to `.claude/skills/<name>/SKILL.md`, `commands` to
  `.claude/commands/<name>.md`, and `hooks` as above; `CLAUDE.md` is generated
  at the root, omitting what `.claude/rules/` already holds, and `AGENTS.md`
  is not generated for it. So the invoked half of the Ubiquitous Language
  regime (#35) is a `command` for this harness, not a `prompt`, and `AGENTS.md`
  is not in Claude Code's compile path. — [targets matrix](https://microsoft.github.io/apm/reference/targets-matrix/)
- **Frontmatter per primitive is still to read from the authoring pages.** The
  package-types page gives only that a skill collection's `name` must match
  its directory, `description` should be present, and every value is ASCII.
  The primitive-types reference is legacy and points at the two pages above.
