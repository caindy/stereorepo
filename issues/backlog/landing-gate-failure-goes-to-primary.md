# Hand a gate that fails while landing back to the primary seat

When `main` has moved since the stage settled, `Loop.merge` rebases and runs
the gate again. If the gate fails and the Issue is still in its stage, `merge`
clears acceptance, sets the gate's output as the note, and returns `None`, so
the pair takes another turn. That turn goes to `other(role)`, which
`Loop.decide` set before it advanced: it goes to the secondary seat whenever
the primary seat settled the stage. `gate-failure-goes-to-primary` sends a
failed requirement gate to the primary seat; this path still does not.

Wanted: that turn goes to the primary seat as well. Testing it needs `main`
to move between the settling turn and the landing.

Found while implementing `gate-failure-goes-to-primary`, whose "Out of scope"
first said, wrongly, that this path gives no seat a turn.
