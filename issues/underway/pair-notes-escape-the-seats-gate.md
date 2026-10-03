# A seat's pair note escapes the gate that seat ran

`Loop.keep_note` in `pair/loop.py` quotes a seat's closing message under
`## Pair notes` in the Issue file after the turn ends, so the `just gate meta`
the seat ran never saw it. When the note cites a stale `path:line`, the
`path and line claims` step fails on the next seat's turn, and that seat
spends its turn rewording the other seat's note. On
`release-recipe-is-scaffold-only` this happened on two turns running: each
note described the fix by quoting the stale citations it had just removed.

## Wanted

A note cannot leave the Issue file failing a step that the seat's own
turn left passing. One fit: `keep_note` writes the note with `path:line`
citations defanged (for example, with the line number dropped or the
citation taken out of code formatting), since a note records a turn
rather than making claims a later reader should follow by line.

## Out of scope

- Changing what `path and line claims` checks in other files.
