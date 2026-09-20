---
slug: noticed-and-not-done
context: solorepo
synonyms:
  - leftover work
  - remainder
  - deferred work
minted: 2026-09-13
---

# Noticed and Not Done

**Noticed and Not Done** is the practice and protocol for handling work or
observations encountered during the execution of a change that fall outside its
remit (solorepo's Article 15, solorepo's DR-064, solorepo's DR-195).

In an autonomous or agentic codebase, an agent or engineer frequently spots
unrelated flaws, missing test coverage, or potential refactors while implementing
a focused [[challenge]]. Bundling these opportunistic changes into the
active branch expands the scope, delays review loops, and entangles unrelated
intent. Conversely, ignoring them or writing ad-hoc reminders in commit messages
guarantees they will be lost.

The [[ubiquitous-language]] establishes *noticed and not done* as the sole
legitimate mechanism for capturing this work — except where the branch can
already reach the fix under the four-part bound, which makes it an
[[incidental-commit|Incidental Commit]] instead (solorepo's DR-236).

## Contrast with Industry Synonyms

In standard software engineering discourse, this concept is commonly described
using disparate terms:
- **Leftover work** or **remainder:** Colloquial descriptions for items left
  unfinished when a sprint, task, or pull request terminates.
- **Technical debt backlog:** Accumulation of recognized deficiencies deferred to
  future planning sessions.
- **Punch list** or **follow-up tickets:** Ephemeral to-do notes drafted during
  final review passes.

Solorepo avoids these labels because they treat deferred work as an amorphous pile
without provenance or accountability. *Noticed and not done* requires that the
observation keep the concrete context in which it was discovered.

## The Parking and Promotion Lifecycle

Work noticed during a change follows a deterministic three-stage lifecycle:

1. **Parked on the Diff:** The observation is raised immediately as a
   [[review-thread]] anchored to the specific line or file where it was observed
   (solorepo's DR-064). The comment carries the heading `**Noticed and not done.**`.
   This keeps the context intact and visible to all reviewers.
2. **Survival to Approval:** An item the branch overtakes or settles during its own
   review is answered and cleared. An observation that survives the review is
   an enduring [[challenge]] candidate.
3. **Promotion at Merge:** When the pull request is approved and merged, every
   surviving noticed-and-not-done thread is promoted to a tracked [[issue]]
   (solorepo's DR-054). The issue records where the problem was found and what
   makes it worth doing.

## Verification & Invariants

- **Charter Binding (solorepo's Article 15):** *Work noticed and not done,
  recorded only in a summary, has not been noticed.* A bullet point in a PR body
  or a note in a commit message fails gate verification.
- **No Floating Signifiers:** Every item listed under `What was noticed and not done`
  in a pull request form must be an explicit link to a surviving review thread
  or promoted issue.

---

**See also:** [[incidental-commit]], [[pr-first]], [[ubiquitous-language]], [[knowledge-management]], solorepo's Article 15, solorepo's DR-054, solorepo's DR-064, solorepo's DR-195.
