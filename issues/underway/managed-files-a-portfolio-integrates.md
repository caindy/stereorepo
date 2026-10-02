---
parent: onboard-fitch-mvp
---

# A sync keeps what a portfolio integrated into a managed file

`.gitignore` is a managed item in `.meta/bundle.yaml`, but adopting
fitch-mvp meant integrating it by hand, keeping fitch-mvp's own lines beside
stereorepo's. Any copy of the managed items, including the recipe from
`sync-portfolio-recipe`, overwrites the file and drops those lines.

Wanted: a portfolio can keep its own lines in such a file through a sync.
For example, the bundle could give the file an ownership that merges a
stereorepo block with the portfolio's, or the portfolio's lines could live in
a file the bundle never lists. Find any other managed file an adopted
repository is likely to integrate as well.
