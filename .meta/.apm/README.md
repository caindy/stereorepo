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
primitives is unbuilt (see `../roadmap.md`), and hand-writing primitives that a
compiler will later generate is the duplication that step exists to remove.

## Before authoring anything

Two things were not verifiable from the pages read and must be checked against
the source first, per the rule that an adopted convention is defined by its
canon and not by us:

- **Frontmatter fields per primitive type.** The primitive-types reference is
  marked legacy and points at *Package types* and the *Targets matrix*.
- **Where `apm.yml` sits.** If primitives live at `.meta/.apm/`, the package root
  is `.meta/`, and the manifest presumably sits beside it at `.meta/apm.yml`.
  Unconfirmed.
