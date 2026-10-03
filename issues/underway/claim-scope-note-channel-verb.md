---
difficulty: easy
---

# Drop the removed channel verb from Claim's scope note

The scope note of `work:concept/claim` in
`.meta/assertions/imported/vocabulary.yaml` still explains a collision with
"the channel verb `claim`, which takes an Issue by assigning it to a Role's
account" and with "the claim released" in `move stop`. Both went with the
signed channel when the pair loop replaced PR First (`dfeaf73`), so the
paragraph warns about a collision that can no longer happen. Found by
`why-fork-inherited-terms`.

Checked while grooming: nothing in `pair/` uses *claim* as a verb for taking
an Issue. The only match is a test name about claiming a seat's session
(`test_a_refused_resumed_turn_restarts_fresh_without_claiming_a_session`),
which is not the collision the paragraph describes.

## Wanted

Remove the paragraph that begins "The label collides with the channel verb
`claim`" and ends "a claim is taken and released.", leaving the paragraphs
before and after it as they are. Re-render.

## Out of scope

- How a multi-paragraph scope note renders
  (`vocabulary-scope-note-paragraphs`).
- The rest of Claim's scope note and its definition.

## Done when

- `git grep -n -e "channel verb" -e "move stop" -- .meta/assertions/imported/vocabulary.yaml .meta/vocabulary.md`
  finds nothing. The Decision Records that still say "channel verb"
  (DR-228, and DR-268 in another sense) keep it: they record what was true
  when they were written.
- `.meta/vocabulary.md` after re-rendering no longer carries the paragraph.
