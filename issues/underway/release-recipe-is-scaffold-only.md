# Count `release` among the recipes only the scaffold renders

Every portfolio's `meta` gate fails `justfile recipe shape` with "the contract
declares 'release', which the rendered surface does not hold". `f1bb5d3`
added `release` to `CONTRACT` in `.meta/checks/files/justfile.py`, and the
render writes the recipe only where `work:artifact/meta-release` is asserted
(`.meta/lib/render/writers.py`), which is in stereorepo alone. The recipe was
not added to `SCAFFOLD_RECIPES`, the tuple of recipes a portfolio's surface
does not hold. fitch-mvp hit it on its first sync after `f1bb5d3`.

It is the third check today that is right in stereorepo and wrong in every
portfolio, after `_probe_adopt` and the wiki parity probe
(`portfolio-gate-before-landing`).

## Wanted

A portfolio's `meta` gate passes `justfile recipe shape` without a `release`
recipe, and stereorepo's still requires it.

## How anyone will know it is done

A probe of the step over a rendered portfolio surface without `release`
passes, and stereorepo's own surface without it fails.
