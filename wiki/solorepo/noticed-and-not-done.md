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

**Noticed and Not Done** is work observed but left unexecuted during a change, formally parked as an unresolved review thread or a linked Issue to preserve its context without blocking delivery.

Rather than letting passive observations drift into a private backlog, a file of bullet points, or a generic "todo" comment within the source code, observations made during development are immediately committed to the review process. This discipline guarantees that every item seen and left alone is explicitly tracked, evaluated, and resolved without delaying the parent pull request (solorepo's DR-064, solorepo's DR-159).

## Handling Leftover Work

When a developer finishes a task and there is leftover work, the question of what to do with it is answered by this discipline. Instead of ignoring the leftover work, archiving it in a private todo file, or committing unfinished changes, the leftover work is explicitly parked as a noticed and not done item. This preserves the context and allows the current pull request to land clean.

## The Life of an Observation

Under the [[pr-first|PR First]] discipline, work noticed and not done adheres to a strict, lifecycle-enforced pipeline:

1. **Discovery & Placement (A15):** The observation must be raised immediately as an active conversation on the diff of the pull request at the precise line where it was noticed, using the `.meta/say/post notice` tool (solorepo's DR-064). Raising it inside a summary or an isolated file is forbidden, as these lack temporal and spatial context.
2. **Review & Evaluation:** A thread opened as a notice is held open and marked with `**Noticed and not done.**`. This distinguishes it from an active review comment that requires a code change before merging. The conversation blocks the merge until the solo developer decides how to handle it.
3. **Promotion on Approval:** At approval, any surviving noticed-and-not-done thread is promoted to a tracked [[issue|Issue]] with the original context preserved. The pull request's body is revised to list the promoted Issue under **What was noticed and not done.**, and the original review thread is resolved.

## Structural Advantages

By keeping unfinished residue bound to the active review thread, the solorepo harness avoids the typical pitfalls of task tracking:
- **No Lost Context:** The item keeps the exact git diff and code context it was noticed during. Anyone reviewing the Issue later can immediately understand the original situation.
- **Controlled Queue Growth:** Because creating an Issue requires the deliberate act of promoting an unresolved thread, the backlog remains a clean queue rather than a passive pile of forgotten points.
- **Unambiguous Resolution:** Unlike a file of notes where a deleted line is indistinguishable from an abandoned or resolved item, Issues carry clear open/closed states.

---

**See also:** [[knowledge-management]], [[ubiquitous-language]], [[pr-first]], [[issue]], solorepo's DR-064, solorepo's DR-159.
