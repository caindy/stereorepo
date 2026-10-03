---
difficulty: easy
---

# Retire the count slots nothing cites

DR-154 made a count about the record a `{#name}` slot that `render.py`
fills, and wrote its own falsifier: "prose that stops citing counts at all
retires this: the table empties, `counted()` fills nothing, and both come
out." No assertion holds a `{#name}` slot any more (a grep of
`.meta/assertions/` finds `{#` only in DR-154 itself), so the falsifier has
been met. `counts()` still derives `prechecks`, and nothing reads it. Found
while planning `trim-decision-records-065-177`.

## Wanted

These come out of `.meta/lib/render/record.py`, with every reference to
them:

- `COUNT`, the comment above it that cites DR-154, `NUMBERS`, `prechecks()`,
  `counts()` and `counted()`;
- the messages only they raise, `NO_PRECHECK` and `NO_COUNT`;
- the `record.counted(...)` wrapping in `.meta/lib/render/targets.py`
  (`return {name: record.counted(text) ...}` becomes a plain return of the
  pages);
- the five names `.meta/render.py` re-exports from `lib.render.record`
  (`COUNT`, `NUMBERS`, `counted`, `counts` and `prechecks`), in both its
  import block and its `__all__`;
- "and counts" in the module docstring of `record.py`, which says the prose
  helpers weave "authored blocks and counts" into the pages.

DR-154 is withdrawn: `status: WITHDRAWN` with a `withdrawn_because:` that
quotes its falsifier as met, in the shape DR-036 uses. DR-036 carries no `enacted_in`;
DR-154's two entries (`work:artifact/meta-render` and
`work:artifact/meta-lib-render-record`) go if a withdrawn record may not
name an Artifact it no longer governs. Re-render, so `.meta/decisions.md`
shows it withdrawn.

## Out of scope

- Any other renderer behaviour.
- The word "prechecks" elsewhere (`.meta/check.py`, `.meta/checks/`), which
  names the gate's prechecks and not this count.

## Done when

- A grep for `{#`, and a whole-word grep (`grep -w`, so `accounted_by`
  does not match) for `COUNT`, `NUMBERS`, `counted`, `counts` and
  `prechecks`, in `.meta/lib/render/*.py` and `.meta/render.py` finds only
  the comment in `writers.py` that describes `pair-status` ("and the counts
  (--json)").
- A grep for `DR-154` outside `.meta/assertions/decisions/`,
  `.meta/decisions.md` and `issues/` finds nothing.
- `just render` run twice leaves the tree unchanged after the first run, so
  every page renders the same without the fill.
- DR-154's file says `status: WITHDRAWN` with a `withdrawn_because:`.
