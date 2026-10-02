# Drop the removed channel verb from Claim's scope note

The scope note of `work:concept/claim` in
`.meta/assertions/imported/vocabulary.yaml` still explains a collision with
"the channel verb `claim`, which takes an Issue by assigning it to a Role's
account" and with "the claim released" in `move stop`. Both went with the
signed channel when the pair loop replaced PR First (`dfeaf73`), so the
paragraph warns about a collision that can no longer happen. Found by
`why-fork-inherited-terms`.

## Wanted

The paragraph is removed, or rewritten if anything in the pair loop still
uses *claim* as a verb for taking an Issue (check `pair/` first). Re-render.

## Done when

The scope note names no verb, recipe or command that does not exist, and
`.meta/vocabulary.md` matches it after re-rendering.
