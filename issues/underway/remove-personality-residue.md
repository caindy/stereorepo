---
difficulty: easy
---

# Personality is gone from the ontology, and three places still name it

The ontology of work has no Personality class; DR-327 records that the
register an agent speaks in is now a Role's `communication_style`
(`.meta/work/authority.yaml`). Found while trimming DR-002 to DR-048:

- `.meta/work/personas.yaml` lists a `personality` slot on `Persona`, and no
  module defines that slot.
- `.meta/.apm/README.md` maps "a Personality, or a Persona to interrogate"
  to `agents` (line 31).
- The same file's layout block glosses `agents/<name>.agent.md` as "a
  specialized personality" (line 19).

A fourth place, the `/technical-writing` skill's preamble in
`.meta/assertions/imported/structure.yaml`, cites
`work:personality/technical-writer`. It is not this Issue's: see Out of
scope.

## Wanted

- The `personality` slot on `Persona` is dropped. A Persona is a customer,
  not an agent, and its register is not the ontology's business; if a reason
  turns up in DR-327 or DR-340 to keep it, define it instead and say why in
  the slot's description.
- `.meta/.apm/README.md` maps "a Role's communication style, or a Persona to
  interrogate" to `agents` (or whatever wording names what compiles to an
  agent today), and the layout gloss says the same.
- If `.meta/.apm/README.md` is rendered, the change is made at its source
  and the file re-rendered.

## Out of scope

- The `/technical-writing` skill's preamble and its rendered copies
  (`.meta/.apm/skills/technical-writing/SKILL.md` and
  `.claude/skills/technical-writing/SKILL.md`). `just render` writes the
  second under `.claude/skills/`, which the seats' sandbox denies, so a seat
  that changes the source cannot land it. The developer Issue
  `technical-writing-skill-successor-citations` already drops the citation
  in the same edit as its own.
- Decision Records and Issues that mention Personality as history.

## Done when

- Outside `.meta/assertions/decisions/`, `.meta/decisions.md` and `issues/`,
  a case-insensitive grep for `personality` under `.meta/` finds only the
  skill preamble's one sentence, in `structure.yaml` and in
  `.meta/.apm/skills/technical-writing/SKILL.md`, and nothing once
  `technical-writing-skill-successor-citations` has landed.
- Nothing under `.claude/` changes.
- The schema still validates with the slot gone: `just render` succeeds and
  leaves the tree unchanged on a second run.
