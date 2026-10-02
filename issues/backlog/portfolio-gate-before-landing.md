# Run a portfolio's gate before a change to what portfolios receive lands

A defect that shows only in a portfolio can land in stereorepo unseen.
`_probe_adopt` failed every portfolio's `meta` gate, specialized or adopted,
and landed, because nothing runs a portfolio's gate before landing:
`just test-specialization` builds a portfolio and runs its gate (step 8), but
neither the loop nor `just gate` runs that recipe. `adopt-probe-passes-in-a-portfolio`
made stereorepo's own gate run that one probe's portfolio branch, which
covers that probe and no other. It was found by hand, in fitch-mvp.

## Wanted

Before a change lands that alters what a portfolio receives (the bundle's
managed and template items in `.meta/bundle.yaml`, and what the render
writes from them), a specialized portfolio's gate runs against it, and a
failure there holds the landing as any gate failure does. A change that
touches none of it lands without that cost, in the spirit of DR-303.

## How anyone will know it is done

- A change to a managed check that fails only in a portfolio, such as a
  probe that reads a file only stereorepo has, fails before it lands.
- A change only to `issues/` or `pair/` does not run the specialization.

## Out of scope

- Adopting a repository in the test, as well as specializing one.
