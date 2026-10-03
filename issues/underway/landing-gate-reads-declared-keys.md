---
difficulty: medium
parent: keys-reach-the-landing-gate-not-the-seats
waits_on: [seats-never-hold-keys]
---

# Give the landing gate the keys a portfolio declares

Part of `keys-reach-the-landing-gate-not-the-seats`. The landing gate runs
in `worktrees/pair` (`run_gate` in `pair/loop.py`, through the loop's `gate`
callable), which has no `.env` because git does not check out an ignored
file. A test that needs a key fails there or reports `?`, and since
`landing-gate-holds-on-could-not-run` a `?` holds the landing for good.
fitch-mvp's `live-generation-run` needs a Gemini key from its `.env` and
could not land.

## Wanted

- A portfolio names, in `.meta/assertions/structure.yaml` (under
  `portfolio:`, with a slot added to the schema in `.meta/work/`), the
  variables from its root `.env` that its gate may read. Names only, never
  values, so the list is auditable in git.
- The loop reads those variables, and only those, from the `.env` at the
  main checkout's root, and passes them in the environment of the gate's
  process alone. The gate runs outside the seats' sandbox. A declared
  variable missing from `.env` is simply absent, so its test reports `?` and
  the landing holds as today.
- `just gate` in the developer's own checkout is unchanged: it reads `.env`
  as the product already does.
- A coding Decision Record states the rule: keys reach the supervisor's
  gate and never a seat. It cites `seats-never-hold-keys`'s denial as the
  other half, and says that an Issue whose work is itself a live run stays a
  `developer` Issue: the developer runs it, and the pair records what it
  found.

## Out of scope

- The seats' side (`seats-never-hold-keys`).
- Secret managers or keychains: `.env` is the developer's convention.

## Done when

- A test over a temporary portfolio whose `.env` holds a declared variable
  and an undeclared one: the environment the landing gate's process is
  started with holds the declared variable and not the undeclared one.
- A portfolio that declares nothing starts the gate with the same
  environment as today.
- The Decision Record is written and `.meta/decisions.md` re-rendered.
