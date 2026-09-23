---
slug: incidental-commit
context: solorepo
minted: 2026-09-18
---

# Incidental Commit

**Incidental Commit** is a fix a branch can already reach, made in a commit of
its own rather than ejected to an Issue (solorepo's DR-236).

Four parts must all hold, or the observation is
[[noticed-and-not-done|Noticed and Not Done]] instead. The fix must be
mechanical, owe no [[decision-record|Decision]], imply no [[challenge]] of its
own, and be proved by the gate the change is already running. The fourth is
what makes the first three checkable rather than asserted: a fix whose
correctness needs an argument is not mechanical, whatever its line count.

The commit's subject begins `Incidental:`. The prefix is the whole form, and it
exists to be counted — `git log --grep '^Incidental:'` is the first direction
of the falsifier solorepo's DR-236 carries, and without a fixed form two Jobs
write two subjects and nobody can enumerate them.

## Why the Bound Is Drawn Here

The two routes divide what a change encounters outside its remit, and they
divide it by who pays. Ejecting an item to an [[issue]] costs a Job's start,
and that start costs about the same whether three lines wait or three hundred:
a Job arriving holds no filesystem, no shell and no conversation, so it loads
the whole problem from the record. On a team the same fix is a separate pull
request because a colleague reads three lines in thirty seconds and nobody
reloads anything; here the follow-up is an agent starting from nothing, which
inverts the imported advice.

solorepo's #624 is the worked case. A reviewer found a reference in a
[[decision-record|Decision]] naming the wrong artifact, on a branch that
already had the file open and the renderer running. It was ejected because the
record belonged to a different Decision, and the delivery — three additions and
three deletions across two files — cost a claim, a branch, a body, a review and
a merge.

## Contrast with Industry Synonyms

- **Drive-by:** the coinage solorepo's DR-236 carried before
  solorepo's #642 minted this Concept, and the one this entry replaces. It
  reads as casual, where the four-part bound says the fix is cheap and
  checkable.
- **Opportunistic fix:** names the moment rather than the licence, and carries
  no bound at all.

The word is avoided rather than forgotten: it is recorded on the concept's
`avoid` list, so the rejected name stays recoverable by anyone reading the
history of solorepo's DR-236.

## Who May Make One

Both clauses of solorepo's DR-236 are in [[pr-first|PR First]], and they reach
different parties.

- **The coder, at the moment of noticing.** This is where scope creep lives,
  since nobody else is reading yet, and the four-part bound is what keeps a
  licence to fix from becoming a licence to wander.
- **The coder, at approval, on a point another party raised.** A surviving
  [[review-thread|Review Thread]] inside the bound is answered by a commit on
  the branch before the merge, the reply naming the commit and no Issue filed.
  The reviewer is already reading, and a commit pushed before the merge is
  re-reviewable where an Issue is a promise to reload the problem later.

A coder's own notice is not reachable by either clause. The channel refuses
`post answer` on a thread this Actor solely authored unless the reply links a
promotion (solorepo's DR-127), so a coder that decides its own notice is moot
can still only hand it on. The way in is the reviewer saying on the thread that
the point is inside the bound, which makes it another party's and the
judgement one two Roles have made.

## Invariants

- **Its own commit.** Folding the fix into the change's own commit is what the
  topical test existed to prevent: the reviewer loses the ability to read
  either, and the argument loses its subject. A reviewer who objects to a
  separate commit objects to one commit rather than to the change.
- **A floor, not a licence.** An item failing any of the four parts is a notice
  and then an [[issue]]. Scope creep answered with "it was mechanical" is the
  shortcut this bound teaches, and the falsifier of solorepo's DR-236 watches
  for it: a commit under the prefix that a reviewer has to argue about, or that
  carries a Decision nobody minted.
- **Countable.** `git log --grep '^Incidental:'` enumerates the commits taking
  this licence, and no check refuses a missing or malformed prefix. Nothing can
  refuse at the moment a coder decides an item is mechanical, because the
  judgement is the whole content of the rule; what is mechanizable is the
  outcome, after the fact.

---

**See also:** [[noticed-and-not-done]], [[pr-first]], [[challenge]], [[issue]],
[[review-thread]], [[knowledge-management]], [[ubiquitous-language]],
solorepo's Article 15, solorepo's Article 16, solorepo's DR-127,
solorepo's DR-236.
