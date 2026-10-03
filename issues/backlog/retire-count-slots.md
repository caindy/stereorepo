# Retire the count slots nothing cites

DR-154 made a count about the record a `{#name}` slot that `render.py`
fills, and wrote its own falsifier: "prose that stops citing counts at all
retires this: the table empties, `counted()` fills nothing, and both come
out." No assertion holds a `{#name}` slot any more, so the falsifier has been
met. `counts()` still derives `prechecks`, and nothing reads it. Found while
planning `trim-decision-records-065-177`.

## Wanted

`counts()`, `counted()` and the code only they use come out of
`.meta/lib/render/record.py`. DR-154 is withdrawn, with its falsifier as the
reason, and the citation at `.meta/lib/render/record.py:130` goes with the
code.

## Out of scope

Any other renderer behaviour.

## Done when

No `{#` slot handling is left in `.meta/lib/render/`, `just render` leaves
the tree unchanged, and DR-154 is `WITHDRAWN` with a `withdrawn_because:`.
