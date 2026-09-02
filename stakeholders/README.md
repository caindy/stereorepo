# stakeholders

Material about the people the work answers to. Product material, not scaffold —
which is why it sits outside `.meta/`.

The directory splits along a seam the ontology already has, so it needs no term
of its own:

| | Modelled as | Their interest |
|---|---|---|
| `customers/` | a **Persona** | what the product is worth to them |
| `internal/` | a **Role** | how the work gets done |

## This is the research, not the model

A Persona is asserted in `.meta/assertions/personas.yaml`. What lives here is
what that assertion was **drawn from** — interviews, transcripts, observations,
the evidence. The two are not duplicates: one is the distilled model, the other
is its provenance.

That distinction is what makes Cooper's rule enforceable rather than
aspirational. "The detail is the discipline" and "research over invention" mean
nothing if there is nowhere to put the research, and a Persona with no
corresponding material here was invented.

## What was dropped

`external/` — investors, media, advisors — is deliberately absent for now. The
idea has value: a source to draw on when asked for a press release or a blog
post. It is recorded in `.meta/roadmap.md` rather than kept as an empty folder.
