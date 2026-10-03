---
slug: evidence
context: stereorepo
minted: 2026-09-18
---

# Evidence

**Evidence** is "hard ground truths, telemetry, or verified physical/digital
data streams" (stereorepo's DR-228).

That sentence is quoted whole and unaltered from the `Evidence` class of
`schema/epistemology.yaml` in caindy/fitch-mvp, for the reason [[claim]]'s is.
The schema places it in Toulmin's ontology: "Toulmin's Grounds (Data) by
default … also Backing when it lends a credence."

That schema adds that evidence is "also Backing when it lends a credence",
and that Grounds and Backing "are positions in an argument, not kinds of
evidence". The same artifact can occupy either position; what it is called
depends on the argument it stands in, not on what it is made of.

`Grounds` and `Backing` are that schema's words for those positions and are
quoted here rather than adopted. Neither is minted in this repository, which has
no consumer for the distinction yet; whether they are taken is
left open (stereorepo's DR-228).

## Evidence that can fail

What is distinctive in this repository is not that a history entry names
Evidence. It is that the Evidence it names can fail.

The record weighed commit hashes and pull request citations as the thing a
history entry would name, and turned them down (stereorepo's DR-171): a commit hash records where a
change happened, but if the change is undone the hash is unchanged, so nothing
can detect that the entry has gone stale. It chose a resolvable symbol instead —
a check or probe function — which disappears when the guardrail it names
disappears, and takes the entry with it.

That is the same argument [[observed-failure]] makes about guardrails, applied
to prose. Evidence nobody has seen fail is evidence of nothing.

The distinction is not carried by the word. The upstream Evidence covers a commit
hash perfectly well. It is carried by the gate: `meta history evidence` parses
the named module and resolves the symbol, so an entry whose test is gone fails
the gate rather than sitting there being read (stereorepo's DR-171). The word
does not carry that requirement; the check does.

## The `Evidence:` line

A history entry under `<module>.history.md` says what failed and what the change
established — not what changed, which the diff already holds — and names its
Evidence on a line of the form:

```
Evidence: `<path>::<symbol>`
```

The symbol is a top-level function or class, a method as `Class.method`, or the
label a decorator such as `@check` gives. `.meta/checks/files/history.py`
resolves it by `ast.parse`, without executing anything.

The line was called `Receipt:` until stereorepo's DR-228 renamed it. `receipt` had
arrived by use rather than agreement, and had come to mean both this and a
provenance citation — the sense stereorepo's DR-171 had already rejected. The word is retired
rather than minted, and the two commentary uses that meant provenance now say
provenance.

## Contrast with industry synonyms

- **Receipt** is retired here for the reason above. The retired word is
  recorded in one place, the `avoid` list on the concept (stereorepo's DR-228).
- **Proof** overclaims: Evidence lends weight to a [[claim]], and a warrant is
  what bridges the two.
- **[[citation]]** is a reference to an upstream authority, evaluated by
  [[dereference]]. The two Concepts collide rather than compete: a citation can
  be Evidence, and one that cannot go stale is the thing stereorepo's DR-171
  turned down.

## Invariants

- **The upstream sentence is quoted, not rewritten** (stereorepo's DR-228).
- **Parity.** Minted in `.meta/assertions/imported/vocabulary.yaml` with this
  page, per stereorepo's Article 17 and stereorepo's DR-335.
- **Every history entry names Evidence that resolves.** Checked by
  `meta history evidence`; an entry naming none, or naming a symbol that is
  gone, fails the gate (stereorepo's DR-171).

---

**See also:** [[claim]], [[nothing-unconsumed]], [[observed-failure]],
[[literate-programming]], [[citation]], stereorepo's Article 17, stereorepo's DR-171,
stereorepo's DR-335, stereorepo's DR-228.
