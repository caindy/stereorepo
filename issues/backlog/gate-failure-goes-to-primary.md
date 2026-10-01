# Hand a failed gate back to the primary seat

Once both seats leave a stage as it stands, `Loop.decide` in `pair/loop.py`
checks the stage's requirement, and in the in-progress stage that runs the
full `just gate`. When the gate fails, the failure goes to `other(role)`: the
seat after the one whose quiet turn settled the stage. That is the secondary
seat whenever the primary seat was the last to go quiet, so the seat whose
part is to review is the one told to repair the build.

## Wanted

A requirement that fails because `just gate` fails sends the next turn, with
the gate's output, to the primary seat, whichever seat went quiet last. Other
unmet requirements keep going to `other(role)`.

## Out of scope

When the gate runs, and what the seats run during their turns.

## Done when

A test in `pair/test_pair.py` settles an in-progress stage with the primary
seat's quiet turn, makes the gate fail, and finds that the next turn goes to
the primary seat with the gate's output; and the requirement table in
`pair/README.md` says where a failed gate goes.
