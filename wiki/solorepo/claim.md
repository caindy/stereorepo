---
slug: claim
context: solorepo
minted: 2026-09-18
---

# Claim

**Claim** is "Toulmin's Claim: the central hypothesis or predicate assertion
being evaluated" (solorepo's DR-228).

That sentence is quoted whole and unaltered from the `Claim` class of
`schema/epistemology.yaml` in caindy/fitch-mvp, which models Toulmin's ontology
of argument on LinkML — the same technology this repository's vocabulary uses,
so the two can be compared rather than translated. The schema names Stephen
Toulmin as its source; his published one is *The Uses of Argument* (1958).

That schema adds two things the word carries here. A claim "is its text and
its warrants": it is not a free-standing sentence but a sentence together with
the paths that reach it. And a claim carries no probability of its own, so the
force with which it may be asserted is derived from what backs it rather than
declared alongside it.

## Why the word was minted here

This repository reasons about claims constantly and had no word for one. It has
a `falsifier` slot on a [[decision-record]] and on an [[article]], a line on a
history entry naming the test that would fail, `checked_by` on an Article, and
`just dereference` reading a [[citation]] against what it names — four
instruments over the same subject, none of which could say which part of an
argument it held.

The absence showed as drift. `receipt` reached the [[charter]], seven Decision
Records, the [[nothing-unconsumed]] Discipline, the gate, every history log
under `.meta/` and both Bootstraps without ever being minted, and settled into
two incompatible senses. Naming the parts is what lets the two be told apart in one
sentence: one was [[evidence]] that can fail, the other Evidence that cannot.

## What is a Claim here

- **A history entry.** The entry asserts what failed and what the change
  established. The `Evidence:` line beneath it names what would fail if the
  claim stopped being true.
- **An [[article]].** One clause of the Charter is "a claim that can be held
  against an artifact and found false" — the definition already used the word
  before the word existed.
- **A [[citation]].** A citation is composed of an identifier, the claim it
  names, and a link; `just dereference` evaluates whether the target supports
  that claim.

What is not a Claim is the channel verb `claim`, which takes an Issue by
assigning it to a Role's account — and "the claim released" in what `move stop`
does. That is an ownership lock. The two share a label and nothing else: a Claim
is argued about, a claim is taken and released.

## Contrast with industry synonyms

- **Assertion** is the programming-language sense — a runtime check that halts.
  A Claim is argued about, not executed.
- **Hypothesis** implies something awaiting a test that has not yet run. A Claim
  may be well established and still be a Claim.
- **Statement** says nothing about standing in an argument, which is the whole
  content of the term.

## Invariants

- **The upstream sentence is quoted, not rewritten.** The definition is the
  source's own opening sentence, whole and unaltered; everything this repository
  adds sits beside it rather than inside it. Four systems are intended to merge, and a shared word that
  acquires a second meaning in one of them is the drift the merge would then
  have to undo (solorepo's DR-228).
- **Parity.** Minted in `.meta/assertions/imported/vocabulary.yaml` with this
  page, per solorepo's Article 17 and solorepo's DR-190.
- **Bounded adoption.** `Claim` and `Evidence` are taken alone. `Warrant`,
  `Grounds`, `Backing`, `Credence`, `Rebuttal` and `Qualifier` are not minted
  here, because a term with no consumer is what [[nothing-unconsumed]] refuses.

---

**See also:** [[evidence]], [[article]], [[citation]], [[dereference]],
[[nothing-unconsumed]], [[ubiquitous-language]], solorepo's Article 17,
solorepo's DR-190, solorepo's DR-228.
