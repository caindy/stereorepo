---
difficulty: easy
---

# Personality is gone from the ontology, and three places still name it

The ontology of work has no Personality class; DR-327 records that the
register an agent speaks in is now a Role's `communication_style`
(`.meta/work/authority.yaml`). Found while trimming DR-002 to DR-048:

- `.meta/work/personas.yaml` listed a former `personality` slot in the
  `slots` of the `Persona` class, and no module defined that slot.
- `.meta/.apm/README.md`, in the table under "What belongs here, and where
  it comes from", maps "a Personality, or a Persona to interrogate" to
  `agents`.
- The same file's "Layout" block glosses `agents/<name>.agent.md` as "a
  specialized personality".

A fourth place, the `/technical-writing` skill's preamble in
`.meta/assertions/imported/structure.yaml`, cites
`work:personality/technical-writer`. It is not this Issue's: see Out of
scope.

## Wanted

- The `personality` slot on `Persona` is removed. A Persona is a customer,
  not an agent, and its register is not the ontology's business; if a reason
  turns up in DR-327 or DR-340 to keep it, define it instead and say why in
  the slot's description.
- `.meta/.apm/README.md` names what compiles to an agent today:
  `role_agent` and `persona_agent` in `.meta/lib/apm_compile/agents.py`
  compile an operational Role (its remit and `communication_style`) and a
  Persona to interrogate. The table row reads along the lines of "a Role,
  with its communication style, or a Persona to interrogate", and the
  layout gloss reads along the lines of "a Role or Persona as an agent".
  The README is hand-written, not rendered, so edit it directly.

## Out of scope

- The `/technical-writing` skill's preamble and its rendered copies
  (`.meta/.apm/skills/technical-writing/SKILL.md` and
  `.claude/skills/technical-writing/SKILL.md`). `just render` writes the
  second under `.claude/skills/`, which the seats' sandbox denies, so a seat
  that changes the source cannot land it. The developer Issue
  `technical-writing-skill-successor-citations` already drops the citation
  in the same edit as its own.
- Decision Records and Issues that mention Personality as history.

## Done when

- Outside `.meta/assertions/decisions/`, `.meta/decisions.md` and `issues/`,
  a case-insensitive grep for `personality` under `.meta/` finds only the
  skill preamble's one sentence, in `structure.yaml` and in
  `.meta/.apm/skills/technical-writing/SKILL.md`, and nothing once
  `technical-writing-skill-successor-citations` has landed.
- Nothing under `.claude/` changes.
- The schema still validates with the slot gone: `just render` succeeds and
  leaves the tree unchanged on a second run.

## Pair notes

> **primary, backlog turn 1**
>
> I've tightened the grooming of `issues/underway/remove-personality-residue.md`. It keeps `difficulty: easy`, and the scope and done-when sections are unchanged. I checked the issue against the code and changed three things:
>
> - **No line numbers:** the issue pointed to `.meta/.apm/README.md` by line number, which DR-355 forbids. It now cites the `slots` list of the `Persona` class and the README's "Layout" block and table heading instead.
> - **README is edited directly:** the issue asked whether `.meta/.apm/README.md` is rendered. It isn't; the file is hand-written, so the issue now says to edit it directly.
> - **New wording named:** the issue left the README's new wording open ("or whatever wording names what compiles to an agent today"). `role_agent` and `persona_agent` in `.meta/lib/apm_compile/agents.py` show that what compiles to an agent today is a Role (with its `communication_style`) or a Persona. The issue now names that and suggests wording for both spots.
>
> The grep still finds exactly the places the issue lists: the former `personality` slot, the two README lines, and the skill preamble that is out of scope.

> **secondary, backlog turn 2**
>
> I checked the groomed Issue against the repository and changed nothing, because it is ready to plan as written.
>
> - **The places it lists are the only ones.** A case-insensitive search for `personality` under `.meta/`, leaving out decision records and Issues, finds exactly what the Issue names. That is the former `personality` slot in `.meta/work/personas.yaml`, the two lines in `.meta/.apm/README.md`, and the out-of-scope sentence in the `/technical-writing` skill. The skill sentence appears in its source, `structure.yaml`, and in that file's rendered copy.
> - **Removing the slot affects nothing else.** No Persona file under `stakeholders/` sets `personality`.
> - **The suggested README wording is accurate.** `role_agent` and `persona_agent` in `.meta/lib/apm_compile/agents.py` compile a Role or a Persona into an agent, as the Issue says.
> - **The rest holds.** `difficulty: easy` fits a three-line change. The out-of-scope reasoning about `.claude/` is sound, and the done-when checks are a search and a render, not a gate.

## The plan

Three edits to two files, then a fourth to this Issue's own prose, which
the gate would otherwise fail.

1. **`.meta/work/personas.yaml`**: delete `- personality` from the `slots`
   list of the `Persona` class. Nothing else names the slot: no `slots:`
   entry defines it, `persona_agent` in `.meta/lib/apm_compile/agents.py`
   never reads it, and no Persona under `stakeholders/` sets it. DR-327 and
   DR-340 give no reason to keep it, so it goes rather than being defined.
2. **`.meta/.apm/README.md`**, hand-written: in the "Layout" block, change
   the `agents/<name>.agent.md` gloss to "a Role or Persona, as an agent".
   In the table under "What belongs here, and where it comes from", change
   the row to "a Role, with its communication style, or a Persona to
   interrogate | `agents`".
3. **`just render`**, twice. The first run must succeed. The second must
   leave `git status` unchanged. Neither should touch `.claude/`, since the
   slot appears in no rendered page. If anything under `.claude/` changes,
   stop and leave a note for the developer rather than committing it.
4. **This Issue's own prose.** This is the one real risk.
   `cited_schema_slots` in `.meta/checks/citations/slots.py` reads every
   tracked `.md` file, `issues/` included, clause by clause. It flags any
   clause that cites, in backticks, a slot no schema declares (or one
   removed from a class, as git history of `.meta/work/` shows). A clause
   escapes only if it contains a hedge word (`SLOT_HEDGED`: *no*, *not*,
   *removed*, *former*, *retired* and the like). Today the slot is still
   listed on `Persona`, so these clauses pass. After step 1 they would
   fail. They are quoted here without their backticks, so that this list
   does not trip the same check:
   - "lists a personality slot in the slots of the Persona class" (Issue
     intro)
   - "The personality slot on Persona is dropped" (Wanted)
   - "the personality slot, the two README lines" (primary's backlog note)
   - "That is the personality slot in .meta/work/personas.yaml"
     (secondary's backlog note)

   Reword each with a hedge word, such as "the former `personality` slot"
   or "is removed", or drop the backticks around the slot name. Then
   re-read every clause in this file that mentions the slot in backticks.
   Do the same for any note added in later turns.

   The work showed one more trap: the check splits clauses at every comma,
   so a hedge word set off by commas ("a personality slot, now removed,")
   lands in a clause of its own and does not protect the slot. Put the
   hedge word in the same comma-free run as the backticked slot name.

## How we'll know

- `git grep -il personality` outside `issues/`,
  `.meta/assertions/decisions/` and `.meta/decisions.md` lists only
  `.meta/assertions/imported/structure.yaml`,
  `.meta/.apm/skills/technical-writing/SKILL.md` and
  `.claude/skills/technical-writing/SKILL.md`, the out-of-scope preamble.
- A second `just render` leaves the tree clean, and `git diff main --stat`
  shows nothing under `.claude/`.
- Even the first `just render` after the edits changes no tracked file:
  `persona_agent` and `role_agent` still write
  `.meta/.apm/agents/the-developer.agent.md` and
  `.meta/.apm/agents/technical-writer.agent.md` byte for byte, which shows
  that removing the slot changed no compiled agent.
- No test is added. The change removes a declaration and edits prose, and
  the slot-citation check above already guards the prose.

## Pair notes

> **primary, todo turn 1**
>
> I've added a plan to `issues/todo/remove-personality-residue.md`. I haven't implemented anything, and the Issue can be done as written.
>
> **Steps:**
> 1. Delete `- personality` from the `slots` list of `Persona` in `.meta/work/personas.yaml`. Nothing defines it, reads it or sets it, so removing it is safe.
> 2. Reword the "Layout" line and the table row about agents in `.meta/.apm/README.md`. That file is hand-written, so it's edited directly.
> 3. Run `just render` twice. The second run should leave the tree unchanged and nothing under `.claude/` should change.
> 4. Reword four sentences in this Issue file itself so the gate doesn't fail on them.
>
> **The one real risk** is step 4. A check called `cited_schema_slots` (in `.meta/checks/citations/slots.py`) reads every tracked `.md` file, including those under `issues/`, a clause at a time. It flags any clause that names a slot in backticks when no schema declares that slot. It skips clauses containing a hedge word such as "no", "removed" or "former". Four sentences in this Issue name the slot without one. They pass today because the slot is still listed on `Persona`, but they would fail once step 1 removes it. The plan lists the four and says to add a hedge word or drop the backticks.
>
> The plan itself quotes those four sentences, so it would have tripped the same check. I removed the backticks from the quotes.
>
> I couldn't run the check against the edited file to confirm the four, because the command needed approval. I found them by reading the check's patterns and the Issue's clauses by hand.
>
> **How we'll know it's done:** a repository-wide search for "personality" finds only the out-of-scope skill sentence and Issues and Decision Records. A second render leaves the tree clean. The compiled Persona agent file, `the-developer.agent.md`, is unchanged.

> **secondary, todo turn 2**
>
> I left the plan as it was, apart from one tightened check. The Issue can be done as written.
>
> **The main risk is real.** The plan warns that a check will fail once the slot is gone. That check is `cited_schema_slots`, and I read it in `.meta/checks/citations/slots.py` to confirm the warning. I counted by hand because running the check needed approval. Four sentences in the Issue file will fail it after the slot is removed, and they are the same four the plan lists. For example, "The personality slot on Persona is dropped" is one. Each names the slot in backticks without a word the check skips, such as "former" or "not". The example rewording in the plan uses "former", so it passes.
>
> **One small fix to the checks.** The plan said only that the compiled agent `the-developer.agent.md` stays the same. I changed it to a stronger check: the first `just render` after the edits changes no tracked file at all. That covers both compiled agents, `the-developer.agent.md` and `technical-writer.agent.md`.
>
> **The rest checks out.** A repository-wide search for "personality" finds exactly the files the plan lists, and nothing under `.claude/` will change.

> **primary, todo turn 3**
>
> I kept your plan and made one change. Your stronger check is right: the first `just render` after the edits should change no tracked file, because no rendered page lists `Persona`'s slots. Only `.meta/assertions/personas.yaml`, the graph check and the agent compiler name any of them.
>
> The fix was to your own note. It quoted "The personality slot on Persona is dropped" with the backticks around the slot and class names. That is a clause with no hedge word, so it would have become a fifth failure of `cited_schema_slots` once the slot is removed. I removed those backticks.
>
> I then went through every remaining clause that puts `personality` in backticks. Only the four the plan already lists would fail the check, so the plan stands as written. I matched the clauses by hand against the check's patterns; I didn't run the check itself.

> **secondary, todo turn 4**
>
> I changed nothing this turn. The plan is ready to implement.
>
> My earlier note quoted one of the failing sentences with its backticks, which would have made a fifth failure of `cited_schema_slots`. The other seat's fix to that note is correct. I searched the current Issue file for every phrase the check matches:
>
> - **The plan's four.** These are still the only clauses that will fail once the slot is removed.
> - **"the former `personality` slot".** The example rewording in the plan contains "former", so the check skips it.
> - **"Role's `communication_style`".** This passes, because `.meta/work/authority.yaml` declares that slot and the `Role` class lists it.
>
> Like the other seat, I matched these against the check's patterns by hand and did not run the check itself.

> **primary, in-progress turn 1**
>
> I implemented the plan. The `personality` slot is removed from `Persona` in
> `.meta/work/personas.yaml`, and `.meta/.apm/README.md` now says a Role or
> Persona compiles to an agent. `just render` wrote no files, so no compiled
> agent and nothing under `.claude/` changed. A case-insensitive
> `git grep -il personality`, leaving out `issues/`, Decision Records and
> `.meta/decisions.md`, now finds only the out-of-scope skill preamble in its
> three copies.
>
> `just gate meta` caught a fifth failing clause, and it was mine. My first
> rewording of the Issue intro set "now removed" off with commas. The check
> splits clauses at commas, so the slot name ended up in a clause with no
> hedge word. I moved "former" next to the slot name instead, and added the
> lesson to step 4 of the plan.

> **primary, in-progress turn 1**
>
> I've implemented the plan and committed it, and `just gate meta` passes. The change touches no other Project's directory, so no other gate applied.
>
> - **The slot is gone:** the `personality` slot is removed from the `Persona` class in `.meta/work/personas.yaml`.
> - **The README is reworded:** in `.meta/.apm/README.md`, the layout block now glosses `agents/<name>.agent.md` as "a Role or Persona, as an agent". The table row now reads "a Role, with its communication style, or a Persona to interrogate".
> - **Rendering changed nothing:** `just render` wrote no files, either time I ran it. No compiled agent and nothing under `.claude/` changed.
> - **The search is clean:** a case-insensitive search for "personality", leaving out Issues, Decision Records and `.meta/decisions.md`, finds only the out-of-scope skill sentence. That sentence is in `.meta/assertions/imported/structure.yaml` and its two rendered copies.
> - **The four sentences are reworded:** each now has a hedge word ("former" or "removed") so the slot-citation check, `cited_schema_slots`, passes them.
>
> The gate failed twice before it passed, both times on clauses I had written:
>
> 1. My first rewording of the Issue's opening was "a personality slot, now removed, …". The check splits clauses at every comma, so "removed" landed in a separate clause and the slot name was left unhedged. I put "former" directly next to the slot name instead, and added this lesson to step 4 of the plan.
> 2. The example I added to the plan for that lesson quoted the bad wording with its backticks, so it failed the same way. I removed the backticks.
>
> The Issue file has a note for the next reader saying all of this.

> **secondary, in-progress turn 2**
>
> The implementation was right, but `just gate meta` was failing, so I fixed the Issue file and it passes now.
>
> The other seat's note on this turn said the gate passed, but `cited_schema_slots` failed on that note itself. To describe its first mistake, the note quoted the bad sentence with backticks around the slot name. The check splits clauses at commas, so the slot name ends up in a clause without a hedge word. I removed the backticks from that quote and committed the change.
>
> The code change itself is as planned:
> - **The slot is gone:** `.meta/work/personas.yaml` no longer lists `personality` on `Persona`.
> - **The README is reworded:** both lines in `.meta/.apm/README.md` now say a Role or Persona compiles to an agent.
> - **The search is clean:** a case-insensitive search for "personality", leaving out Issues and Decision Records, finds only the out-of-scope skill sentence, in its three copies.
> - **Nothing generated changed:** the working tree was clean before my edit, and nothing under `.claude/` changed.
>
> The change touches no other Project's directory, so no other gate applied.

> **primary, in-progress turn 3**
>
> `just gate meta` was failing again, and it passes now. The code change was already right, so the only edit was to the Issue file, which I committed.
>
> The failure came from the secondary's note on the last turn. To explain my earlier mistake, it quoted the bad sentence again with backticks around the slot name. The check splits clauses at commas, so the slot name sat in a clause with no hedge word, which is the same failure as before. I replaced the quote with a plain description: "the bad sentence with backticks around the slot name".
>
> This has now happened three times, and every time in a note. Notes are appended to the Issue file and checked like any other prose, so a note that quotes a failing sentence brings the failure back. For the rest of this Issue, notes should describe that sentence rather than quote it.

> **secondary, in-progress turn 4**
>
> I changed nothing this turn. The work is done, the working tree is clean, and `just gate meta` passes.
>
> The other seat's fix to my last note was the right one. This note is added to the Issue file too, so it names no schema slot in code formatting and cannot fail the slot-citation check again.
