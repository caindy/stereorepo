---
slug: choreography
context: solorepo
synonyms:
  - choreographed coordination
minted: 2026-09-17
---

# Choreography

**Choreography** is the coordination style in which each participant carries only its own rules and reacts to events on a shared substrate, so that no coordinator holds the process and the flow is what the local rules produce together (solorepo's DR-214, solorepo's DR-216).

## Choreography and orchestration

The two are exhaustive and opposite. Under **orchestration** a central coordinator holds the process and tells each participant what to do next; it alone knows the whole flow, and a participant needs no view beyond the instruction it was handed. Under choreography there is no such actor: each participant reads the shared substrate, applies its own rules, and acts, so the flow exists only as the sum of those local decisions.

Solorepo choreographs. The coder pass reacts to a difficulty label landing on an [[challenge|Issue]], the reviewer to a review request, the merge manager to `main` moving, and the [[dev-loop|Dev Loop]] as a whole holds no process: `just next` is a view that reads GitHub and renders it, never a coordinator that dispatches. The substrate is what GitHub records — labels, review requests, threads, branch refs and check states — under solorepo's DR-214.

The distinction is independent of where the substrate lives. A coordinator can hold a process over a local filesystem, and participants can react to events on one; choosing GitHub settled where coordination happens and not whether anything coordinates it.

## Why it is a property rather than a component

Nothing in the repository is the choreography. It is the shape the [[dev-loop|Dev Loop]] has, in the way a graph is acyclic rather than containing an acyclicity. That is why the two concepts sit beside each other as `confusable_with`: the Dev Loop is the engine, and this is what is true of how its passes relate.

The practical test is what a new pass must be given. Under orchestration it is given a place in a plan the coordinator holds. Here it is given a trigger and its own rules, and the flow changes because the set of local rules changed.

## The solo is a participant

Choreography leaves no coordinator for a human to be an audience of, so the solo acts on the same substrate the Jobs act on, through a Role account like any other [[actor|Actor]] (solorepo's DR-107). Work moves between the loop and an interactive session by changing one label on the shared record: `easy` and `medium` are the loop's, and a session takes up a pull request the loop holds by moving the Issue to `hard` first, after which the loop's next pass stands down.

This is why [[pr-first|PR First]] can say that authorship cannot answer which Job owns a branch, since every pull request here is the solo's. There is no human-authored and agent-authored distinction at the identity layer, because both act through Roles on one substrate. An arrangement that reported to the solo rather than admitting them would be orchestration with a person at the top of it.

## Relationship to Externalized Memory

The two commitments are one commitment seen from two sides. [[externalized-memory|Externalized Memory]] removes the private copy a participant could carry; choreography removes the coordinator a participant could ask. What remains in both cases is the observable record, and an agent holding neither privilege must reconstruct the state of things from it — which is what makes a missing observation point fail loudly as a Job that cannot proceed, rather than quietly as one that improvised: solorepo's DR-216 draws that pairing, and solorepo's Article 22 states the rule it produces.

---

**See also:** [[dev-loop]], [[externalized-memory]], [[pr-first]], [[knowledge-management]], [[ubiquitous-language]], solorepo's DR-107, solorepo's DR-214, solorepo's DR-216, solorepo's Article 22.
