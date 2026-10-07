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

## How anyone will know it is done

- Both prompts carry the sentence, and nothing else under `pair/prompts/`
  differs from `main`.
- A grooming pass over a throwaway Issue that reads "Decide whether to X"
  sets `difficulty: developer` and writes a recommendation rather than a
  decision. The developer runs that pass by hand at the desk check, since a
  seat cannot run a grooming pass on prompts it has just changed (the loop
  reads its prompts from the checkout it runs from).

## Out of scope

- Reviewing past Issues the seats decided while grooming.
