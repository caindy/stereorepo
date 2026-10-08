---
slug: quiet-turn
context: stereorepo
minted: 2026-10-02
---

# Quiet turn

**Quiet turn** is a [[seat]]'s turn that changes nothing, by which the seat accepts the state the other left.

## Agreement, observed

The [[supervisor]] has to learn when the seats are done with a [[stage]]
without asking either of them. It reads agreement from the tree
(stereorepo's DR-307): a seat that changes something has accepted the state it
made, and a seat that then changes nothing has seen that state and let it
stand. When both seats have accepted the same state, the stage advances if its
requirement holds. In single-seat mode the primary seat is the only one, so
its own quiet turn advances the stage; a turn that changes something never
does, though that seat is then the only one to have accepted.

A seat that disagrees must say so by changing something, and the turns go on.
A stage the pair keeps changing runs to its round cap, and the Issue goes back
to the backlog. An edit the [[developer]] makes between turns clears both
seats' acceptance, so neither has accepted what it has not seen.

## What a quiet turn is not

- **Not an approval, verdict or sign-off.** Nothing is declared and no seat
  rules on the other's work; a `verdict:` field would bring back a coder and a
  reviewer.
- **Not a hand-off command.** A seat that forgot to run one would stall the
  loop; the supervisor decides whose turn it is.

Whether quiet turns settle naturally, rather than rubber-stamping or never
settling, is still to be recorded from the loop's first run.

---

**See also:** [[seat]], [[supervisor]], [[ubiquitous-language]]
