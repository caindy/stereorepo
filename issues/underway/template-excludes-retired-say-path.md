---
difficulty: easy
---

# Stop the template excluding `.meta/say/`, a directory that is gone

`template/.meta/assertions/structure.yaml` lists `.meta/say/` under
`excluded_paths` (line 33), the operational paths a specialized portfolio's
completeness check passes over. `.meta/say/` no longer exists in the
scaffold, so no portfolio inherits it, and stereorepo's own
`.meta/assertions/structure.yaml` does not name it. Found while grooming
`citations-of-retired-articles`.

## Wanted

The `.meta/say/` line comes out of the template's `excluded_paths`. If
anything writes or checks that list (the specialization tooling or its
test), it changes with it.

## Out of scope

- The `.meta/say/` mentions in `bootstraps/python/skills/py-quality-setup/`,
  which `citations-of-retired-articles` removes.
- The decision log and the done Issues, which mention it as history.

## Done when

- A grep for `meta/say` under `template/` finds nothing.
- The specialization test still passes: a portfolio specialized from the
  scaffold has a completeness check that passes without the line.
