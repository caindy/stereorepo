---
difficulty: developer
---

# Groom an Issue that asks for a decision as `developer`

The grooming prompts, `pair/prompts/stage-backlog.md` and
`pair/prompts/stage-grooming.md`, say when to set `difficulty: developer`:
"when the result needs the developer to check it by hand before it goes to
main". They say nothing about an Issue that leaves a choice open, so the
seats may settle the choice while grooming and land it without the developer
seeing it.

`drop-note-line-citation-rewrite` did that. Its text said "Decide whether to
drop the rewrite". The primary seat's first backlog turn wrote a `## Decision`
section choosing to drop it and set `difficulty: easy`; the secondary seat
agreed, and it landed (`5ba95507`). The choice was sound, small and
reversible, but the developer learned of it only afterwards, by reading the
Issue file. Nothing would stop a larger choice going the same way.

## Wanted

- Both grooming prompts add that an Issue which asks for a choice to be made,
  rather than stating one, is `developer`. Grooming still writes the options
  and a recommendation into the Issue, so the developer decides at the desk
  check from what the seats found, and does not have to rework it.
- An Issue whose text already states the choice (as a `## Decision` section
  written by the developer, or plain wording such as "drop the rewrite") is
  groomed as before.
- Change no other wording in the prompts. The first version of
  `pair-notes` changed what seats are told and was refused by the model's
  safeguards (`6fd1ea94`), so keep the addition to one sentence in each
  prompt.
- Put the sentence straight after "Use developer when the result needs the
  developer to check it by hand before it goes to main." in each prompt, so
  the two rules for `developer` read together. A wording that fits both:
  "Use developer too when the Issue asks for a choice to be made rather than
  stating one, and write the options and your recommendation into it instead
  of a decision."

## How anyone will know it is done

- Both prompts carry the sentence straight after the existing `developer`
  rule, and nothing else under `pair/prompts/` differs from `main`.
- A grooming pass over a throwaway Issue that reads "Decide whether to X"
  sets `difficulty: developer` and writes a recommendation rather than a
  decision. The developer runs that pass by hand at the desk check, since a
  seat cannot run a grooming pass on prompts it has just changed (the loop
  reads its prompts from the checkout it runs from).
- `difficulty: developer` is set on this Issue for that reason: the
  throwaway pass is the developer's check, and the change alters what seats
  are told.

## Out of scope

- Reviewing past Issues the seats decided while grooming.
- Any change to the supervisor or to how a `developer` Issue is routed; the
  existing desk check is the place the developer decides.

## Pair notes

> **primary, backlog turn 1**
>
> I'm leaving the Issue as it is. It is already precise enough to plan, and `difficulty: developer` is the right setting.
>
> - **What is wanted:** add one sentence to each of the two grooming prompts. Both prompts still contain the existing `developer` rule word for word, so there is a clear place to insert it in each.
> - **What is out of scope:** the Issue lists the work to leave alone.
> - **How anyone will know it is done:** the only prompt text that changes is that sentence, and a hand-run grooming pass over a throwaway "Decide whether to X" Issue should come out as `developer` with a recommendation, not a decision.
> - **Why `developer`:** that hand-run pass can only be done at the desk check. A seat can't run a grooming pass on prompts it has just changed, because the loop reads its prompts from the checkout it runs from.

> **secondary, backlog turn 2**
>
> I'm leaving `issues/underway/groom-open-decisions-as-developer.md` unchanged. It's already precise enough to plan from:
>
> - **The change is small and placed exactly.** The rule "Use developer when the result needs the developer to check it by hand before it goes to main." appears word for word in both `pair/prompts/stage-backlog.md` and `pair/prompts/stage-grooming.md`, so the new sentence has a clear spot in each. The suggested wording works in both, including the batch prompt, which grooms several Issues at once and calls each "one".
> - **Out of scope is listed:** reviewing past Issues the seats decided while grooming, and any change to the supervisor or to how a `developer` Issue is routed.
> - **Done is behaviour, not a gate.** Only that sentence changes under `pair/prompts/`. And a grooming pass over a throwaway Issue reading "Decide whether to X" should set `difficulty: developer` and write a recommendation instead of a decision.
> - **`difficulty: developer` is right.** No seat can run that throwaway pass, because the loop reads its prompts from the checkout it runs from, so the developer runs it at the desk check. I also checked `pair/pair.py`: when the prompts change on disk, the loop restarts itself before its next Issue, so landing this change takes effect cleanly on the Issue after it.
>
> I agree with my partner's note that nothing needs changing.

## The plan

1. In `pair/prompts/stage-backlog.md` and `pair/prompts/stage-grooming.md`,
   insert one sentence straight after "Use developer when the result needs the
   developer to check it by hand before it goes to main.": "Use developer too
   when the Issue asks for a choice to be made rather than stating one, and
   write the options and your recommendation into it instead of a decision."
   Touch nothing else on either line.
2. Check that `git diff main -- pair/prompts/` shows only those two
   insertions.

Seams: nothing in code reads the wording. The loop's `prompt` step in
`pair/loop.py` reads `stage-{stage}.md` and fills it with `str.format`, so
the sentence must contain no `{` or `}` (it contains none). The loop's code
digest in `pair/pair.py` counts `prompts/`, so a running loop restarts itself
before its next Issue, and the change takes effect from then on. No
documentation repeats when to choose `developer`: `pair/README.md` cites the
two prompts only for the gate rule, and `wiki/stereorepo/issue.md` and
`wiki/stereorepo/desk-check.md` say what a `developer` Issue does, not when
grooming chooses it. So neither needs editing.

Tests: no unit test covers prompt wording, and none is added. The behaviour
check is the hand-run grooming pass over a throwaway "Decide whether to X"
Issue, which the developer runs at the desk check.

Risk: prompt edits have been refused before (`6fd1ea94`). Keeping the change
to one neutral sentence per prompt is the mitigation.

## Pair notes

> **primary, todo turn 1**
>
> I added a `## The plan` section to `issues/todo/groom-open-decisions-as-developer.md`. Nothing is implemented yet.
>
> - **Change:** put the one new sentence straight after the existing `developer` rule in `pair/prompts/stage-backlog.md` and in `pair/prompts/stage-grooming.md`. Then check that a diff against `main` of everything under `pair/prompts/` shows only those two insertions.
> - **What else it touches:** nothing in the code depends on the wording. The prompt-building code in `pair/loop.py` fills each prompt in with Python's `str.format`, so a `{` or `}` in the sentence would break the prompt; the proposed sentence has neither. When prompt files change, the running loop restarts itself before its next Issue (`pair/pair.py`), so the change takes effect from that Issue on.
> - **Tests:** no unit test checks prompt wording, and the plan adds none. The real check is the developer's hand-run grooming pass over a throwaway "Decide whether to X" Issue at the desk check.
> - **Risk:** an earlier change to what seats are told was refused by the model's safeguards (`6fd1ea94`). Keeping this to one plain sentence in each prompt is how the plan guards against that.

> **secondary, todo turn 2**
>
> I added one paragraph to my partner's plan and left the rest as written.
>
> I checked each claim the plan makes against the code, and they hold:
> - **Prompt loading:** the code that builds each prompt, in `pair/loop.py`, reads `stage-{stage}.md` and fills it in with Python's `str.format`. A `{` or `}` in the new sentence would break that, and the sentence has neither.
> - **Restart on change:** `pair/pair.py` keeps a fingerprint of the loop's code that covers `prompts/`, so a running loop restarts itself before its next Issue once the prompts change.
> - **Tests:** no test in `pair/test_pair.py` checks the wording of a prompt.
>
> What the plan was missing is whether any documentation needs the same change. It doesn't: no document repeats the rule for when grooming chooses `developer`.
> - `pair/README.md` cites the two grooming prompts only for the gate rule.
> - `wiki/stereorepo/issue.md` and `wiki/stereorepo/desk-check.md` say what happens to a `developer` Issue, not when grooming chooses it.
>
> I added a paragraph saying so, so whoever implements it knows to leave those files alone.

> **primary, todo turn 3**
>
> I'm changing nothing this turn. I checked the paragraph my partner added and it is correct, so the plan stands as it is.
>
> I searched every Markdown file outside `issues/` for "check it by hand". Only three places use it:
>
> - the two grooming prompts, `pair/prompts/stage-backlog.md` and `pair/prompts/stage-grooming.md`, which this Issue changes;
> - `wiki/stereorepo/stage.md`, where the phrase only describes what the `desk-check` stage holds. It doesn't say when grooming should choose `developer`, so it doesn't need the new sentence.

## Implementation notes

Done as planned. Each prompt gains the one sentence straight after the
existing `developer` rule, and a word diff of `pair/prompts/` against `main`
shows only those two insertions. The plan held; nothing else changed. What
is left is the developer's hand-run grooming pass over a throwaway "Decide
whether to X" Issue at the desk check.

## Pair notes

> **primary, in-progress turn 1**
>
> I've made the change: both grooming prompts now carry the new sentence, straight after the existing `developer` rule. The sentence is "Use developer too when the Issue asks for a choice to be made rather than stating one, and write the options and your recommendation into it instead of a decision."
>
> - **Scope:** comparing every file under `pair/prompts/` with `main` word by word shows only those two insertions. Nothing else in either prompt changed.
> - **Checks:** `just gate meta` and `just gate pair` both pass, including all 292 pair tests. None of those tests checks prompt wording, as the plan expected.
> - **Issue file:** I added implementation notes saying the plan held as written. The behaviour check is still to come: the developer runs a grooming pass over a throwaway "Decide whether to X" Issue at the desk check, and it should come out `developer` with a recommendation rather than a decision.

> **secondary, in-progress turn 2**
>
> I'm changing nothing this turn. My partner's implementation matches the plan exactly.
>
> - **The change:** each grooming prompt, `pair/prompts/stage-backlog.md` and `pair/prompts/stage-grooming.md`, has the one new sentence straight after the existing `developer` rule. It reads well in the batch prompt too, which grooms several Issues at once.
> - **Nothing else:** compared with `main`, the branch changes only those two prompt lines and the Issue file. The sentence has no `{` or `}`, so filling in the prompt template still works.
> - **Checks:** I re-ran `just gate meta` and `just gate pair`, and both pass, including all 292 pair tests.
>
> The developer still has to check the behaviour by hand at the desk check. A grooming pass over a throwaway Issue reading "Decide whether to X" should set `difficulty: developer` and write the options with a recommendation, not a decision.

Gated by the supervisor at 11:58: `meta`, `pair`; 98 steps passed.
