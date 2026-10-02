---
difficulty: medium
parent: onboard-fitch-mvp
---

# Resolve cited schema slots against the portfolio's own schemas

The `cited schema slots` step (`.meta/checks/citations/slots.py`) reads prose
across the repository and resolves each `Class.slot` it finds against
stereorepo's LinkML schemas (`SCHEMA_PATHS`). A product that has LinkML
schemas of its own fails the step wherever its documentation cites them.
fitch-mvp is a decision management product, and its `README.md` and
`ROADMAP.md` cite `Decision.outcomes`, `Decision.posits` and 25 more of its
own slots. Each one fails against stereorepo's `Decision` (a Decision Record),
which has a class of the same name and different slots.

## How to reproduce it

In a temporary portfolio, add a LinkML schema outside `.meta/` that declares
class `Decision` with slot `outcomes`, and a `README.md` that mentions
`Decision.outcomes`. Run the `meta` gate. `cited schema slots` fails with
"cites slot 'outcomes', which is not declared on class Decision".

## Wanted

- A portfolio can declare its product's LinkML schemas. Prose that cites a
  slot one of them declares passes.
- Where a class name is in both a product schema and stereorepo's schemas,
  a citation passes when either one declares the slot. Telling which class a
  sentence means is out of reach.
- With no product schemas declared, the step behaves as it does today.

## How anyone will know it is done

A test over a temporary portfolio with a product schema: the citation of
its slot passes, a citation of an undeclared slot still fails, and a
citation of a stereorepo slot still passes.

## Out of scope

- Renaming either `Decision`. fitch-mvp's domain term and stereorepo's
  Decision Record are a confusable pair, which fitch-mvp's domain vocabulary
  records.
