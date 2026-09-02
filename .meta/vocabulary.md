## Vocabulary

_The words this repo uses, and what they mean._

The ontology of work exists to give solorepo a shared language. It is a
deliberate rough-in: expect it to move, and raise tensions found while using it
rather than quietly routing around them.

| Term | Definition |
|---|---|
| **Personality** | A SOUL.md plus a communication style. The character an Actor presents. |
| **Persona** | A user archetype the product is designed *for*, in Cooper's sense. Interrogable by an Actor that adopts its Personality. |
| **Capability** | A kind of thing that can be done or used. Tools are atomic (`bash`, `echo`); skills compose tools ("reading and writing files"). |
| **Securable** | A set of objects, by enumeration or by a selector rule. |
| **Permission** | The authority to employ a Capability on a Securable. |
| **Role** | A named set of Capabilities. |
| **Challenge** | A problem to address: defect, epic, feature, task. Supplies *specific*. |
| **Definition of Done** | The completion test. Supplies *measurable*. |
| **Job to be Done** | The need, stated from a Role's point of view. Supplies *achievable* and *relevant*, and names the Role. |
| **Goal** | A SMART goal: Challenge + Definition of Done + JTBD + Deadline. All four required. |
| **Remit** | Permissions + Goal. What may be done, and what for. |
| **Agency** | Role + Remit. |
| **Actor** | Personality + Identity + Memory. |
| **Job** | Actor + Agency. An assignment. |
| **Collaboration** | For a Challenge C, the Jobs that meet on it. |

The schema adds a **runtime half**, because the terms above are all design-time —
they describe work that has been *assigned*, never work being *done*:

| Term | Definition |
|---|---|
| **Identity** | Abstract. Either a **PrincipalIdentity** (durable, credential-held) or a **WorkloadIdentity** (attested per run, short-lived, delegating via `acts_on_behalf_of`). |
| **Execution** | One carrying-out of a Job. Records the workload identity, the BOM, and what was actually visible. |
| **AgentBillOfMaterials** | What an Actor was made of at a moment: the Actor and Agency graph resolved to immutable references. |
| **AuditRecord** | One employment of a Capability on a Securable. A Permission in the past tense. |
