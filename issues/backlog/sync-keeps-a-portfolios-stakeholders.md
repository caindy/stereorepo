---
parent: onboard-fitch-mvp
---

# A sync keeps a portfolio's own stakeholders

`stakeholders/` is a managed directory item in `.meta/bundle.yaml`, but it
holds product-side material: a portfolio adds its own Personas under
`stakeholders/customers/` and its Roles under `stakeholders/internal/`.
`just sync` (DR-315) mirrors a managed directory, so it deletes every tracked
file there that the stereorepo checkout lacks, which is every Persona and Role
the portfolio wrote. Git can recover them, and the sync prints each one as
`removed`, but a sync should not remove the portfolio's product material.

Wanted: a sync leaves a portfolio's own stakeholders alone. Two ways to do
it: ship only the READMEs as managed file items and let the rest of the
directory belong to the portfolio, or move the scaffold's own Personas and
Roles out of the managed set. Check `wiki/stereorepo/` and
`.meta/assertions/imported/` for the same problem.
