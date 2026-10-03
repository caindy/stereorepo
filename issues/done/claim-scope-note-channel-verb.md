---
difficulty: easy
---

# Drop the removed channel verb from Claim's scope note

The scope note of `work:concept/claim` in
`.meta/assertions/imported/vocabulary.yaml` still explains a collision with
"the channel verb `claim`, which takes an Issue by assigning it to a Role's
account" and with "the claim released" in `move stop`. Both went with the
signed channel when the pair loop replaced PR First (`dfeaf73`), so the
paragraph warns about a collision that can no longer happen. The wiki entry
`wiki/stereorepo/claim.md` repeats the same warning in the paragraph that
begins "What is not a Claim is the channel verb `claim`". Found by
`why-fork-inherited-terms`.

Checked while grooming: nothing in `pair/` uses *claim* as a verb for taking
an Issue. The only match is a test name about claiming a seat's session
(`test_a_refused_resumed_turn_restarts_fresh_without_claiming_a_session`),
which is not the collision the paragraph describes.

## Wanted

Remove the paragraph that begins "The label collides with the channel verb
`claim`" and ends "a claim is taken and released.", leaving the paragraphs
before and after it as they are, and re-render with `just render`. Remove the
matching paragraph from `wiki/stereorepo/claim.md` ("What is not a Claim is
the channel verb `claim`" through "a claim is taken and released.").

## Out of scope

- How a multi-paragraph scope note renders
  (`vocabulary-scope-note-paragraphs`).
- The rest of Claim's scope note and its definition.

## Done when

- `git grep -n -e "channel verb" -e "move stop" -e "ownership lock" -e "taken and released" -- .meta/assertions/imported/vocabulary.yaml .meta/vocabulary.md wiki/stereorepo/claim.md`
  finds nothing, so neither paragraph survives in part. The Decision Records that still say "channel verb"
  (DR-228, and DR-268 in another sense) keep it: they record what was true
  when they were written.
- `.meta/vocabulary.md` after re-rendering no longer carries the paragraph.

## Pair notes

> **primary, backlog turn 1**
>
> The issue was already groomed and is still marked `difficulty: easy`. One thing was missing, and I've added it to the issue file.
>
> **What I checked:** The stale paragraph is at lines 523–527 of `.meta/assertions/imported/vocabulary.yaml`. The rendered copy is at line 191 of `.meta/vocabulary.md`.
>
> **What I added:** The wiki page `wiki/stereorepo/claim.md` (lines 51–54) repeats the same stale warning, in a paragraph that starts "What is not a Claim is the channel verb `claim`". The issue didn't mention it, so I updated it in three places:
> - **Description:** now names the wiki page.
> - **Wanted:** now says to remove that wiki paragraph too, and gives `just render` as the re-render step.
> - **Done when:** the `git grep` check now also searches `wiki/stereorepo/claim.md`.
>
> I left the rest of the issue as it was.

> **secondary, backlog turn 2**
>
> I made one small change to the issue file; the rest stays as my partner left it, at `difficulty: easy`.
>
> **What I checked:** The out-of-date paragraph is where the issue says it is in three places:
> - the source, `.meta/assertions/imported/vocabulary.yaml`, lines 523–527;
> - the rendered copy, `.meta/vocabulary.md`, line 191;
> - the wiki page, `wiki/stereorepo/claim.md`, lines 51–54.
>
> I searched the whole repository for the paragraph's phrases, and no other file has it.
>
> **What I changed:** The "Done when" search only looked for the paragraph's opening phrases ("channel verb" and "move stop"). If someone deleted only the start of the paragraph, the closing sentences would remain and the check would still pass. I added two phrases from the end of the paragraph, "ownership lock" and "taken and released", so the check now fails unless the whole paragraph is gone.

> **primary, backlog turn 3**
>
> I'm keeping my partner's change as it is and changing nothing else.
>
> Their edit adds "ownership lock" and "taken and released" to the "Done when" search. I checked both phrases: in all three files they appear only inside the paragraph that's being removed. So the search can no longer pass when only the start of that paragraph is deleted, and it won't flag any text that's meant to stay. The issue is precise enough to plan, and it stays at `difficulty: easy`.

## The plan

1. In `.meta/assertions/imported/vocabulary.yaml`, delete lines 523–528 of
   `work:concept/claim`'s `scope_note`: the paragraph beginning "The label
   collides with the channel verb `claim`" and the blank line after it. The
   note is a `>-` folded scalar, so one blank line must remain between the
   Toulmin paragraph ("…not minted here.") and "What a history entry
   asserts…" to keep them as separate paragraphs.
2. Run `just render`, which regenerates `.meta/vocabulary.md` (line 191 goes).
   No other file renders the note: "a Claim is argued about" appears only in
   these two files.
3. In `wiki/stereorepo/claim.md`, delete lines 51–54 ("What is not a Claim is
   the channel verb `claim`" through "a claim is taken and released.") and one
   of the blank lines around them. The paragraph has no wikilinks, so no link
   check is affected. The "Contrast with industry synonyms" section is kept as
   it is.
4. Run the "Done when" `git grep` and confirm it prints nothing. Then check
   that `git diff --stat` touches only these three files and the issue.

No Python test names the paragraph's phrases, so no test needs to change.
Risk is low. The only trap is folding: if the blank line goes, the scalar
merges two paragraphs into one line in `.meta/vocabulary.md`.

## Pair notes

> **primary, todo turn 1**
>
> I've added a `## The plan` section to `issues/todo/claim-scope-note-channel-verb.md`. Nothing is implemented yet. The change touches three files:
>
> 1. **`.meta/assertions/imported/vocabulary.yaml`, lines 523–528:** delete the stale paragraph from Claim's scope note. Keep exactly one blank line between the paragraphs on either side. The note is a folded YAML block, so without that blank line those two paragraphs would merge into one.
> 2. **`.meta/vocabulary.md`:** run `just render`, which drops the rendered copy of the paragraph at line 191. I checked that no other file renders this note.
> 3. **`wiki/stereorepo/claim.md`, lines 51–54:** delete the matching paragraph. It has no wiki links, so no link check is affected.
> 4. **Check:** run the issue's `git grep` and confirm it prints nothing, then confirm the diff touches only these three files and the issue file.
>
> No Python test mentions the paragraph's wording, so no test needs to change. The risk is low; the blank line in step 1 is the one thing that could go wrong.

> **secondary, todo turn 2**
>
> I'm leaving the plan as it is. I checked it against the files:
>
> - **The YAML deletion is correct.** Line 528 in `.meta/assertions/imported/vocabulary.yaml` is the blank line after the paragraph. Deleting lines 523–528 leaves exactly one blank line between the paragraphs on either side, which keeps them separate.
> - **The wiki deletion leaves nothing dangling.** "Verb" and "lock" appear only in lines 51–54 of `wiki/stereorepo/claim.md`, so nothing else on the page refers to the paragraph being removed. Afterwards the list of examples runs straight into the "Contrast with industry synonyms" heading, which reads fine.
> - **The final check is adequate.** Confirming that the diff touches only the three files and the issue file would catch `just render` regenerating anything else.

## Done

Implemented as planned. The paragraph is gone from the scope note, from
`.meta/vocabulary.md` (`just render` wrote only that file), and from
`wiki/stereorepo/claim.md`. The "Done when" `git grep` prints nothing.
Rendered scope-note paragraphs still sit on consecutive lines with no blank
line between them; that predates this change and is
`vocabulary-scope-note-paragraphs`.

## Pair notes

> **primary, in-progress turn 1**
>
> I removed the out-of-date paragraph about the old `claim` channel verb from all three places, and `just gate meta` passes (92 steps). Committed as `1d2f00d`.
>
> - **`.meta/assertions/imported/vocabulary.yaml`:** deleted the paragraph from Claim's scope note. The paragraphs on either side are still separate.
> - **`.meta/vocabulary.md`:** `just render` regenerated only this file, and the paragraph is gone from it.
> - **`wiki/stereorepo/claim.md`:** deleted the matching paragraph. The list of examples now leads straight into the "Contrast with industry synonyms" heading.
>
> The issue's `git grep` check, searching for "channel verb", "move stop", "ownership lock" and "taken and released", finds nothing in the three files. The plan held as written, and I've added a short "Done" note to the issue file.
>
> That note also records something I noticed but didn't change: in the rendered `.meta/vocabulary.md`, the scope note's paragraphs run on consecutive lines with no blank line between them. This was already the case before my change, and the backlog issue `vocabulary-scope-note-paragraphs` covers it.

> **secondary, in-progress turn 2**
>
> I changed nothing this turn. My partner's implementation matches the plan, and everything I checked holds:
>
> - **The paragraph is gone everywhere.** The issue's `git grep` check, searching for "channel verb", "move stop", "ownership lock" and "taken and released", finds nothing in any of the three files.
> - **Nothing else changed.** Compared with `main`, the branch touches only the Claim vocabulary entry (`.meta/assertions/imported/vocabulary.yaml`), its rendered copy (`.meta/vocabulary.md`), the wiki page (`wiki/stereorepo/claim.md`) and the issue file.
> - **The paragraphs around the deletion are still separate** in both the vocabulary entry and its rendered copy.
> - **The follow-up is already tracked.** My partner noticed that rendered scope-note paragraphs run on without a blank line between them, and `issues/backlog/vocabulary-scope-note-paragraphs.md` already covers that.
>
> I didn't rerun `just gate meta` because I edited nothing. My partner reports it passed on this same state.
