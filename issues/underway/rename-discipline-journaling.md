---
difficulty: developer
---

# Rename the Journaling Discipline to a word that is guessed right

`why-fork-inherited-terms` re-tested *Journaling* against the rule for
choosing terms (DR-313) and found it fails: the common word means keeping a
journal or log, but the Discipline means routing narrative to the artifact
that owns it, and the residue to the Issue file, never to a commit message.
A reader who guesses from the word alone would write a log. The rename was
deferred because the name is more than a label.

## Wanted

The Discipline and its concept are renamed to *Routing*, the word
`AGENTS.md` already uses ("Route prose before writing") and that the
Discipline's own step ids use (`route-as-you-write`,
`route-findings-in-same-change`). If DR-313's test shows *Routing* collides
with an existing term, choose another and say why here. Then rename
throughout:

- `work:discipline/journaling` and its step ids in
  `.meta/assertions/imported/disciplines.yaml`;
- `work:concept/journaling` in `.meta/assertions/imported/vocabulary.yaml`,
  with *Journaling* on its `avoid` list;
- `enforces: work:discipline/journaling` in
  `.meta/assertions/imported/charter.yaml`;
- the compiled `.meta/.apm/instructions/journaling.instructions.md` and its
  line in `.gitattributes`;
- prose in `.meta/assertions/structure.yaml` and the generated
  `bootstraps/python/README.md` and `bootstraps/rust/README.md`;
- the search benchmark's expected ids in `.meta/lib/search/benchmark.py` and
  the probe in `.meta/checks/probes/tools/search.py`, which expects the
  Discipline or Concept in the top 5 for "leftover work". If the new name
  moves it out of the top 5, say so here rather than weakening the probe.

Record the rename in a new Decision Record and re-render.

## Out of scope

- Existing Decision Records, which keep the old word, and so the generated
  `.meta/decisions.md` that indexes them.
- Issue files in `issues/`.

## Done when

- The developer has read the new name and its Decision Record and accepts
  them. A Discipline's name is the developer's word, and *Routing* sits
  close to the routing that the Knowledge Management Discipline already
  describes ("the pre-writing routing decision tree"), so the choice is
  checked by hand before it lands.
- `git grep -il journaling -- ':!issues/' ':!.meta/assertions/decisions/'
  ':!.meta/decisions.md'` lists only `.meta/assertions/imported/vocabulary.yaml`,
  where the word is on the `avoid` list, and the generated
  `.meta/vocabulary.md`, which renders that list in its Avoid column.
- The renamed Discipline renders into `.meta/disciplines.md` under its new
  name, and `.meta/.apm/instructions/` holds its instructions file under
  the new name and no `journaling.instructions.md`.
- The search probe still finds the Discipline or Concept in the top 5 for
  "leftover work".
