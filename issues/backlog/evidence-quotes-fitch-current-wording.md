---
waits_on: [fitch-mvp:inverse-pairs-follow-the-record]
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

Three places in stereorepo still quote the old wording, "also Backing when it
lends a credence, which is how a data stream earns a measured posterior":

- the scope note of `work:concept/evidence` in
  `.meta/assertions/imported/vocabulary.yaml`;
- `.meta/vocabulary.md`, which is rendered from it;
- `wiki/stereorepo/evidence.md`, lines 15 and 17.

fitch-mvp cannot correct them, because a sync overwrites its copies. The
`waits_on` entry holds this Issue until the developer removes it, once that
Issue has landed in fitch-mvp (DR-301).

## Wanted

Each quotation matches fitch-mvp's description as it stands on its `main`
once `inverse-pairs-follow-the-record` has landed, and the prose around it
says what the quotation says. Copy the wording from fitch-mvp's
`schema/epistemology.yaml` at that point, not from this Issue, in case the
desk check changes it again.

## How anyone will know it is done

The three places quote the same sentence that fitch-mvp's `Evidence`
description holds, and no stereorepo file outside `issues/` still says that
evidence "lends a credence".

## Out of scope

- The wiki page's own prose, which says that Evidence "lends weight" to a
  claim in explaining why "proof" is avoided. It is stereorepo's sentence,
  not a quotation.
