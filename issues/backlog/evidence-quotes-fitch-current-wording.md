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

## Out of scope

- The wiki page's own prose, which says that Evidence "lends weight" to a
  claim in explaining why "proof" is avoided. It is stereorepo's sentence,
  not a quotation.
- The first sentence of the `Evidence` class ("Hard ground truths, telemetry,
  or verified physical/digital data streams"), which the Issue in fitch-mvp did
  not change, and the definitions of any other concept.
- Minting `Grounds`, `Backing` or `Warrant` here, which DR-228 leaves open.
