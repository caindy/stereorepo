---
difficulty: medium
parent: write-why-fork-into-records
waits_on:
  - why-fork-delivery-records
---

# Re-test the inherited terms against the rule for choosing terms

One part of `write-why-fork-into-records`. The rule for choosing terms
(section 10 of `WHY_FORK.md`, recorded by `why-fork-delivery-records`) says
an inherited term is re-tested before it is kept: use the common word when a
competent engineer or model would guess its meaning from the word alone, and
coin one only for a genuinely new concept. The bootstrap applied it to the
board's vocabulary but not to the terms it inherited.

## Wanted

Every term in `.meta/assertions/imported/vocabulary.yaml` that the pair
loop's bootstrap did not add is re-tested against the rule. *Client Repo*
goes first: it names what the ontology already calls a Portfolio's
repository, and has a page, `wiki/stereorepo/client-repo.md`.

For each term, one of:

- **kept**, because the common word would be guessed wrong or no common word
  exists; say so in one line in this file;
- **replaced** by the common word or an existing term: change the
  vocabulary, its `avoid` lists, the wiki page and every use in prose,
  re-render, and write one Decision Record covering the replacements made.

## Out of scope

The board's terms, which were chosen by the rule already, and the terms the
trimmed Decision Records use (the `trim-decision-records-*` parts).

## Done when

This file lists every inherited term with its verdict, every replacement is
made throughout, and `just gate` passes.
