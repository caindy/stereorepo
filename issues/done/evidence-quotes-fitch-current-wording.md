---
difficulty: developer
---

# Quote fitch-mvp's current description of Evidence

stereorepo's Evidence concept quotes the `Evidence` class of fitch-mvp's
`schema/epistemology.yaml` whole and unaltered (stereorepo's DR-228), so that a
word the two repositories share keeps one meaning. fitch-mvp's
`inverse-pairs-follow-the-record` changes that description. Its pair
`lended_by` and `lends` becomes `source` and `credences`, and its prose drops
the lending metaphor for the schema's own terms. The class now continues:

> Toulmin's Grounds (Data) by default, reached from a warrant through
> `grounds`; also Backing when it is a credence's source, which is how a data
> stream gets a measured posterior.

That Issue landed in fitch-mvp as `72c5bb7` on 5 October 2026. fitch-mvp
cannot correct stereorepo's copies, because a sync overwrites them.

Three places in stereorepo still quote an older wording. Two of them hold the
continuation "also Backing when it lends a credence, which is how a data stream
earns a track record. The two are positions in an argument, not kinds of
evidence." The third quotes fragments of it:

- the scope note of `work:concept/evidence` in
  `.meta/assertions/imported/vocabulary.yaml`, in its paragraph beginning
  "The same class continues";
- `.meta/vocabulary.md`, which `just render` generates from that file and
  which is not edited by hand;
- `wiki/stereorepo/evidence.md`, whose lead quotes "Toulmin's Grounds (Data)
  by default … also Backing when it lends a credence." and whose next
  paragraph quotes "also Backing when it lends a credence" again.

## Wanted

- The scope note's quotation of the class's continuation matches, word for
  word, the `Evidence` description in fitch-mvp's `schema/epistemology.yaml`
  on its `main` at `72c5bb7` or later. That includes whether the sentence "The
  two are positions in an argument, not kinds of evidence." still follows: keep
  it only if fitch-mvp still has it.
- `.meta/vocabulary.md` is re-rendered with `just render`, not edited.
- Each fragment the wiki page quotes is a fragment of that same description.
  The prose around each quotation still says what the quotation says: the
  page's point, that one artifact can be Grounds in one argument and Backing in
  another, stands, and is restated in the new terms where it leaned on
  "lends".

Copy the wording from fitch-mvp's `schema/epistemology.yaml` if a seat can
read it. A seat's sandbox may not reach GitHub, in which case use the
quotation above, which is the wording the Issue in fitch-mvp set out to land,
and say in this file that it was not checked against fitch-mvp. The developer
checks it at the desk check either way, which is why this Issue is
`developer`.

## How anyone will know it is done

- `git grep -n -e "lends a credence" -e "track record" -- ':!issues'` finds
  nothing.
- The quotation in the scope note, in `.meta/vocabulary.md` and the fragments
  in `wiki/stereorepo/evidence.md` all appear verbatim in the `Evidence` class
  of fitch-mvp's `schema/epistemology.yaml` on its `main`; the developer
  checks this by hand at the desk check.
- `.meta/vocabulary.md` is what `just render` produces from the assertions,
  so a second `just render` changes nothing.

## The plan

The source of the new wording is the quotation in this Issue. Neither seat
could reach fitch-mvp (GitHub refused the connection, and the only local copy,
`~/code/fitch-mvp-GARBAGE`, is not a source to trust), so the new wording has
not been checked against fitch-mvp, and the developer checks it at the desk
check.

**The trailing sentence.** Nothing here says whether fitch-mvp kept "The two
are positions in an argument, not kinds of evidence." So that no seat has to
guess, both quotations end at "measured posterior." and the point that sentence
made is kept as stereorepo's own prose, not quoted. That stays true whether or
not fitch-mvp still has the sentence. If the developer finds at the desk check
that it is still there, it can be put back inside the quotation marks.

Steps, in order:

1. **Scope note.** In `work:concept/evidence` in
   `.meta/assertions/imported/vocabulary.yaml`, the paragraph beginning "The
   same class continues" quotes "Toulmin's Grounds (Data) by default, reached
   from a warrant through `grounds`; also Backing when it is a credence's
   source, which is how a data stream gets a measured posterior." Then, outside
   the quotation: the two are positions in an argument, not kinds of evidence.
   The remark that `Grounds`, `Backing` and `Warrant` are not minted here stays
   as it is. The file is folded YAML (`>-`), so the edit keeps its indentation
   and blank-line paragraph breaks.
2. **Render.** Run `just render` to regenerate `.meta/vocabulary.md`. Don't
   edit that file by hand.
3. **Wiki.** In `wiki/stereorepo/evidence.md`:
   - The lead quotes "Toulmin's Grounds (Data) by default … also Backing when
     it is a credence's source."
   - The next paragraph quotes "also Backing when it is a credence's source"
     and drops the quoted "are positions in an argument, not kinds of
     evidence". It says the same thing in its own words, for example: "Grounds
     and Backing are positions in an argument, not kinds of evidence." The
     sentence after it ("The same artifact can occupy either position …")
     stays.
   - The "lends weight" line under Contrast with industry synonyms stays as it
     is (out of scope).

The tests that show it works:

- `git grep -n -e "lends a credence" -e "track record" -- ':!issues'` finds
  nothing.
- `git grep -n "a credence's source" -- ':!issues'` finds the scope note,
  `.meta/vocabulary.md` and both places in the wiki page. (As built, the
  phrase wraps across a line break in the scope note and in the wiki page's
  second paragraph, so a line-wise `git grep` finds only `.meta/vocabulary.md`
  and the wiki lead; `git grep -n "credence's"` finds all four.)
- A second `just render` leaves `git status` clean.

Risks:

- **The new wording isn't checked against fitch-mvp.** The desk check covers
  this.
- **Fragments that aren't word for word.** The wiki's two fragments must each
  be a substring of the scope note's quotation. Check that by eye before
  committing.
- **YAML folding.** If the edited scope note breaks the YAML, `just render`
  fails. Treat that as the check that the YAML still parses.

## Out of scope

- The wiki page's own prose, which says that Evidence "lends weight" to a
  claim in explaining why "proof" is avoided. It is stereorepo's sentence,
  not a quotation.
- The first sentence of the `Evidence` class ("Hard ground truths, telemetry,
  or verified physical/digital data streams"), which the Issue in fitch-mvp did
  not change, and the definitions of any other concept.
- Minting `Grounds`, `Backing` or `Warrant` here, which DR-228 leaves open.

## Pair notes

> **primary, backlog turn 1**
>
> I'm leaving the Issue file unchanged. It is already precise enough to plan from:
>
> - **What is wanted:** match three quotations to fitch-mvp's wording, re-render `.meta/vocabulary.md` instead of editing it, and restate the wiki prose wherever it relied on "lends".
> - **Out of scope:** stereorepo's own phrase "lends weight", the first sentence of the class (which fitch-mvp didn't change), and minting `Grounds`, `Backing` or `Warrant`.
> - **How to tell it's done:** a `git grep` that should find nothing, quotations that match fitch-mvp word for word, and a second `just render` that changes nothing.
>
> `difficulty: developer` is already set and is the right call: the wording has to be checked by hand against fitch-mvp, which a seat's sandbox may not reach.
>
> I checked what it says about the current state against the code, and it holds. The old wording is in the scope note in `.meta/assertions/imported/vocabulary.yaml`, in `.meta/vocabulary.md`, and in the lead and the following paragraph of `wiki/stereorepo/evidence.md`. There's no local fitch-mvp clone to check the new wording against, so the planning seat will probably have to use the quotation in the Issue and note that it wasn't checked against fitch-mvp, as the Issue already allows.

> **secondary, backlog turn 2**
>
> I'm leaving the Issue file as it is. It's precise enough to plan from, and `difficulty: developer` is right.
>
> - **Its description of the current state is accurate.** The old wording is in exactly the three places it lists: the scope note in `.meta/assertions/imported/vocabulary.yaml`, the generated `.meta/vocabulary.md`, and two quotations in `wiki/stereorepo/evidence.md`. The phrase "lends weight" further down that wiki page is stereorepo's own sentence, and the Issue already marks it out of scope.
> - **The done-check works as a target.** Today, `git grep` for "lends a credence" and "track record" finds only those three places, so once they're fixed it should find nothing.
> - **I couldn't check the new wording against fitch-mvp.** GitHub isn't reachable from here (the certificate check failed). The only local copy is `~/code/fitch-mvp-GARBAGE`, which isn't a trustworthy source and is outside this task's scope, so I didn't use it. The Issue already covers this case: the planning seat uses the quotation written in the Issue, notes that it wasn't checked against fitch-mvp, and the developer checks it at the desk check.

> **primary, todo turn 1**
>
> I've added a `## The plan` section to `issues/todo/evidence-quotes-fitch-current-wording.md`. Nothing is implemented yet.
>
> **Where the new wording comes from.** Neither of us could reach fitch-mvp, so the plan uses the quotation already written in the Issue. It says plainly that this wasn't checked against fitch-mvp, and the developer checks it at the desk check.
>
> **The open question.** We don't know whether fitch-mvp still has the sentence "The two are positions in an argument, not kinds of evidence." The plan ends both quotations at "…measured posterior." and keeps that point as stereorepo's own prose, outside the quotation marks. That stays correct either way. If the developer finds fitch-mvp still has the sentence, it can go back inside the quotes.
>
> **Steps, in order:**
> 1. Change the quotation in the `work:concept/evidence` scope note in `.meta/assertions/imported/vocabulary.yaml`. The file is folded YAML, so the edit keeps its indentation and paragraph breaks.
> 2. Run `just render` to regenerate `.meta/vocabulary.md`, rather than editing it by hand.
> 3. Update the two quoted fragments in `wiki/stereorepo/evidence.md` to "…when it is a credence's source". Restate the "positions in an argument" point in the page's own words, and leave the out-of-scope "lends weight" line alone.
>
> **Tests:**
> - `git grep` finds no "lends a credence" and no "track record" outside `issues/`.
> - `git grep` finds "a credence's source" in all four places.
> - A second `just render` leaves `git status` clean.
>
> **Risks:** the wording isn't checked against fitch-mvp, the wiki fragments might not match the scope note word for word, and the YAML folding could break. The plan says how each is handled.

> **secondary, todo turn 2**
>
> I'm leaving the plan as it is. I checked it against the files it touches, and it holds:
>
> - **Scope note:** the `work:concept/evidence` scope note in `.meta/assertions/imported/vocabulary.yaml` contains the paragraph the plan describes, and it is folded YAML (`>-`).
> - **Wiki page:** `wiki/stereorepo/evidence.md` has the two quotations in the lead and the next paragraph. The second paragraph quotes "are positions in an argument, not kinds of evidence", which the plan rightly turns into the page's own sentence.
> - **No other copies:** the old wording ("lends a credence", "track record") appears nowhere else outside `issues/`, so no decision record or other page needs updating.
> - **Tests:** both wiki fragments in the plan are word-for-word pieces of the new quotation, so the planned search for "a credence's source" will find all four places.
>
> Ending the quotations at "measured posterior." and keeping "positions in an argument" as stereorepo's own words is the safe choice, because we still can't check whether fitch-mvp kept that sentence. The developer checks the wording against fitch-mvp at the desk check.

> **primary, in-progress turn 1**
>
> I've made the change as planned, and `just gate meta` passes. The new wording comes from the quotation in the Issue and still hasn't been checked against fitch-mvp; the developer checks it at the desk check.
>
> - **Scope note** (`work:concept/evidence` in `.meta/assertions/imported/vocabulary.yaml`): the quotation now ends "…also Backing when it is a credence's source, which is how a data stream gets a measured posterior." The sentence "The two are positions in an argument, not kinds of evidence." follows as stereorepo's own words, outside the quotation marks.
> - **`.meta/vocabulary.md`**: regenerated with `just render`, not edited by hand. Running it a second time left the file byte-for-byte the same.
> - **`wiki/stereorepo/evidence.md`**: both quoted fragments now say "…when it is a credence's source". The "positions in an argument" point is now the page's own sentence. The "lends weight" line is untouched, since it was out of scope.
>
> The planned checks:
> - `git grep` finds no "lends a credence" and no "track record" outside `issues/`.
> - One planned search was wrong. Searching for "a credence's source" finds only two of the four places, because the phrase breaks across lines in the YAML and in the wiki. Searching for "credence's" finds all four. I've corrected the test in the plan to say so.
>
> I found no other work to put in the backlog.

> **secondary, in-progress turn 2**
>
> I'm changing nothing. My partner's implementation matches the plan, and I've checked it.
>
> - **Scope note:** the quotation in `work:concept/evidence` in `.meta/assertions/imported/vocabulary.yaml` now ends "…also Backing when it is a credence's source, which is how a data stream gets a measured posterior." "The two are positions in an argument, not kinds of evidence" follows as stereorepo's own sentence, outside the quotation marks.
> - **Wiki page:** both quoted fragments in `wiki/stereorepo/evidence.md` are word-for-word pieces of that quotation. Its point, that one artifact can be Grounds in one argument and Backing in another, still stands. The "lends weight" line is untouched, as the Issue asks.
> - **Plan correction:** my partner was right about one test. Searching for "a credence's source" line by line finds only two of the four places, because the phrase breaks across lines. The plan now says so.
> - **Checks:** running `just render` again left the working tree clean, so `.meta/vocabulary.md` is exactly what it generates. `just gate meta` passes.
>
> The new wording still hasn't been checked against fitch-mvp, because neither of us could reach it. The developer checks it at the desk check, which is why this Issue is marked `developer`.

Gated by the supervisor at 19:59: `meta`, `pair`, `specialization`; 98 steps passed.
