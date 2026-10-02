# Rename the Journaling Discipline to a word that is guessed right

`why-fork-inherited-terms` re-tested *Journaling* against the rule for
choosing terms (DR-313) and found it fails: the common word means keeping a
journal or log, but the Discipline means routing narrative to the artifact
that owns it, and the residue to the Issue file, never to a commit message.
A reader who guesses from the word alone would write a log. The rename was
deferred because the name is more than a label.

## Wanted

The Discipline and its concept carry a name a competent engineer or model
would guess right; *routing* is the word `AGENTS.md` already uses ("Route
prose before writing"). Choose it, then rename throughout:
`work:discipline/journaling` in `.meta/assertions/imported/disciplines.yaml`,
`work:concept/journaling` in `.meta/assertions/imported/vocabulary.yaml`
(with *Journaling* on its `avoid` list), the compiled
`.meta/.apm/instructions/journaling.instructions.md`, and every use in prose
(`git grep -il journaling` lists about 20 files outside the Decision
Records). Record the rename in a Decision Record and re-render.

## Out of scope

Existing Decision Records, which keep the old word.

## Done when

`git grep -i journaling` finds it only in the `avoid` list, existing
Decision Records, `issues/done/` and the new Decision Record, and the
renamed Discipline renders into `.meta/disciplines.md` under its new name.
