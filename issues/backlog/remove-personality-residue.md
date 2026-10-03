# Personality is gone from the ontology, and three places still name it

The ontology of work has no Personality class; DR-327 records that the
register an agent speaks in is now a Role's `communication_style`. Found
while trimming DR-002 to DR-048:

- `.meta/work/personas.yaml` lists a `personality` slot on `Persona`, and no
  module defines that slot.
- `.meta/assertions/imported/structure.yaml` (the `/technical-writing`
  skill's preamble) cites `work:personality/technical-writer`, an id nothing
  defines.
- `.meta/.apm/README.md` maps "a Personality, or a Persona to interrogate"
  to `agents`.

## Wanted

Each of the three either names what exists now (a Role and its
`communication_style`, or a Persona) or is removed, and whatever the
`personality` slot on `Persona` was meant to hold is either defined or
dropped.
