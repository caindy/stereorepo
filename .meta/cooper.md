The comment in your code is spot on. In *The Inmates Are Running the Asylum* (1999), Cooper popularized the core concept of personas and introduced the distinction between **primary** and **secondary** personas, but the formal, multi-tier taxonomy and the goal classification were codified later in the second through fourth editions of ***About Face: The Essentials of Interaction Design*** (co-authored with Robert Reimann, Dave Cronin, and Christopher Noessel).

---

### 1. The Persona Taxonomy (`PersonaKind`)

In *About Face* (Chapter: *Modeling Users: Personas and Goals*), the Cooper methodology defines a strict **six-type persona taxonomy** used during the modeling phase:

| Persona Type | Definition & Operational Rule |
| --- | --- |
| **Primary** | The main target of interface design. A primary persona’s goals cannot be satisfied by an interface tailored to another persona without unacceptable compromise. **Rule:** There is typically only one primary persona per interface/context (or at most one per distinct interface interface/workspace). |
| **Secondary** | A user who is largely satisfied by the primary persona's interface, but has a small number of additional, specific requirements that must be accommodated without compromising the primary experience. |
| **Supplemental** | A user whose needs are completely satisfied by a combination of the primary and secondary personas’ interface requirements. They are modeled for political or organizational reasons (e.g., to ensure a stakeholder department knows their user type is represented). |
| **Customer** | Addresses the needs of the *buyer* rather than the day-to-day user (common in enterprise/B2B procurement). They usually dictate purchasing decisions, administrative security, or compliance constraints. |
| **Served** | Individuals directly impacted by the product's use, even though they never touch the interface themselves (e.g., the patient whose vitals are recorded on an EHR tablet by a nurse). |
| **Negative** (or Anti-Persona) | Explicitly modeled to define who the system is **not** being built for (e.g., power hackers for an everyday consumer app, or overly specialized technicians who would pull the architecture off-course). |

> Your current enum (`primary`, `secondary`, `supplemental`, `negative`) captures the four core user-facing and anti-user archetypes, but omits **`Customer`** and **`Served`**. If your domain involves procurement hierarchies or third-party beneficiaries, those two are worth adding.

---

### 2. The Goal Taxonomy

In *Inmates*, Cooper emphasized that personas must be defined by goals rather than tasks or demographic profiles, but *About Face* formalizes user goals into a three-tiered hierarchy mapped against Don Norman’s visceral, behavioral, and reflective cognitive processing levels:

* **Experience Goals (Visceral):**
* *What it answers:* How does the user want to feel while using the product?
* *Focus:* Affective response, visual tone, microinteractions, and immediate emotional feedback (e.g., *"Feel competent and in control"*, *"Don't feel stupid"*, *"Have fun"*).


* **End Goals (Behavioral):**
* *What it answers:* What does the user want to accomplish?
* *Focus:* The direct, tangible outcomes of interaction that eliminate tasks (e.g., *"Process an invoice without manual reconciliation"*, *"Find relevant research papers in under two minutes"*). These drive the actual information architecture, workflows, and functional requirements.


* **Life Goals (Reflective):**
* *What it answers:* Who does the user want to be?
* *Focus:* Long-term identity, personal aspirations, and self-image (e.g., *"Be recognized as an expert by my peers"*, *"Live a balanced life with more family time"*). These rarely dictate button placements, but they underpin brand loyalty, positioning, and overall product strategy.



#### Supplementary Non-User Goals

In addition to the three user goals above, *About Face* explicitly defines non-user goals that must be tracked separately from personas so they don't pollute user models:

* **Business Goals:** Organizational objectives (e.g., increase conversion, lower support overhead, retain recurring revenue).
* **Technical Goals:** Architectural constraints (e.g., maintain sub-100ms latency, maintain offline-first synchronization, comply with data residency).

---

### Suggested Schema Representation

If you want to reflect Cooper's mature Goal-Directed Design model faithfully:

```text
enum PersonaKind {
  Primary,
  Secondary,
  Supplemental,
  Customer,
  Served,
  Negative,
}

enum GoalType {
  Experience, // Visceral: how the user feels
  End,        // Behavioral: what the user accomplishes
  Life,       // Reflective: who the user aspires to be
}

```
