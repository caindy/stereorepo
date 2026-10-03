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
quotes its falsifier as met, in the shape DR-036 uses. Its `enacted_in`
(`work:artifact/meta-render` and `work:artifact/meta-lib-render-record`)
comes out too: the code it named is gone, so it no longer accounts for
either file. Nothing requires this. Other withdrawn records, such as DR-084,
keep theirs, and the `enacting citations` step in
`.meta/checks/citations/record.py` passes either way, because both files
cite other entries that name them. Re-render, so `.meta/decisions.md` shows
DR-154 withdrawn and drops it from the **By artifact** rows for both files.

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
- `git grep DR-154` outside `.meta/assertions/decisions/`,
  `.meta/decisions.md` and `issues/` finds nothing. Use `git grep` and not a
  plain recursive grep: the ignored `apm_modules/_local/` holds a stale copy
  of the tree that still cites it.
- `just render` run twice leaves the tree unchanged after the first run, so
  every page renders the same without the fill.
- DR-154's file says `status: WITHDRAWN` with a `withdrawn_because:`, and
  has no `enacted_in`.
- No test needs to change: nothing outside `record.py`, `targets.py` and
  `render.py` refers to the removed names.

## The plan

One commit, in this order, because each step leaves the renderer importable:

1. **`.meta/lib/render/targets.py`.** In `rendered()`, return `out` directly
   in place of the `record.counted(...)` comprehension. Delete the
   docstring paragraph that begins "Counts are filled last", since it
   describes the fill.
2. **`.meta/render.py`.** Drop `COUNT`, `NUMBERS`, `counted`, `counts` and
   `prechecks` from the `from lib.render.record import` block and from
   `__all__`.
3. **`.meta/lib/render/record.py`.**
   - Delete `NO_PRECHECK` and `NO_COUNT`, with their docstrings.
   - Delete the block from the comment above `COUNT` (the one ending in
     DR-154) through `counted()`: that is `COUNT`, the `NUMBERS` comment and
     tuple, `prechecks()`, `counts()` and `counted()`.
   - Drop the `import ast` and `import re` lines. Nothing else in the module
     uses them, and ruff would flag them as unused.
   - Change "authored blocks and counts" in the module docstring to
     "authored blocks".
4. **`.meta/assertions/decisions/DR-154.yaml`.** Set `status: WITHDRAWN`.
   Add a `withdrawn_because:` after it, in the one-line quoted shape of
   DR-036 and DR-084, quoting the falsifier ("prose that stops citing counts
   at all retires this") and saying it is met: no assertion holds a
   `{#name}` slot, and `counts()` and `counted()` are gone. Delete the
   `enacted_in` key and its two entries. Leave the rest of the entry as it
   stands, as the record of what was decided.
5. **`just render`**, then a second `just render` with `git status` clean
   between them. Expect only `.meta/decisions.md` to change: DR-154's
   status in the index, and its removal from the **By artifact** rows for
   `.meta/render.py` and `.meta/lib/render/record.py`. No other page should
   change, because no page carries a slot. If any other page changes, a
   slot existed that the grep missed, so stop and look before going on.

**Tests.** The greps in *Done when*, and the two renders. No test refers to
the removed names, so none is added or changed. Withdrawing DR-154 must
satisfy the `withdrawn decisions` step in `.meta/checks/graph/record.py`
(a WITHDRAWN entry needs `withdrawn_because`); the `withdrawn decisions
probes` precheck only tests that step against made-up entries. Removing `enacted_in` cannot trip the
`enacted decisions` step in `.meta/checks/graph/artifacts.py`, which reads
only ADOPTED entries.

**Risk.** Small. `rendered()` is also what the `rendered prose` staleness
check calls, so leaving `counted` half-removed would break both render and
gate together. The order above avoids that.

### What the work changed in the plan

- `targets.py` also lost `record` from its `from lib.render import ...`
  line: `counted()` was the module's only use of it. Nothing outside the
  module reaches it as `targets.record`.
- As the plan expected, `just render` changed only `.meta/decisions.md`:
  DR-154 moved from the adopted index to the withdrawn list and left the
  **By artifact** rows for `record.py` and `render.py`. A second render
  changed nothing.

## Pair notes

> **primary, backlog turn 1**
>
> I made one change to `issues/underway/retire-count-slots.md` and committed it. I left `difficulty: easy` as it was.
>
> I checked the issue's claims against the code, and they hold:
> - **The slots:** no assertion uses a `{#name}` slot except DR-154 itself.
> - **The removal list:** it names every reference to the names being removed, in `record.py`, `targets.py` and `render.py`.
> - **Tests:** none of them use those names.
>
> **The change:** the issue left one point undecided. DR-154's `enacted_in` (the list of files a decision record governs) was to come out only "if a withdrawn record may not name an Artifact it no longer governs." Nothing forbids that. Other withdrawn records, such as DR-084, keep their lists, and the check in `.meta/checks/citations/record.py` that compares these lists with citations in the files passes either way. I made it definite: the list comes out, because the code it pointed to is gone. I added that to the done-when list, plus a line saying no tests need to change.

> **secondary, backlog turn 2**
>
> I checked the issue against the code and made one fix to it, which I committed. `difficulty: easy` stays as it was. The issue is ready to plan.
>
> **What holds:**
> - No assertion uses a `{#name}` slot except DR-154 itself.
> - The removal list covers every reference to the removed names in `record.py`, `targets.py` and `render.py`.
> - Nothing else in the tracked tree refers to those names.
> - `withdrawn_because:` in DR-036 is the right model for withdrawing DR-154.
>
> **What I fixed:** one done-when check would never pass. It said a grep for `DR-154` outside the decision records, `.meta/decisions.md` and `issues/` "finds nothing". But the ignored `apm_modules/_local/` folder holds an old copy of the tree, and it still cites DR-154 in its own `record.py`, `decisions.md` and decision record. A plain recursive grep would find those even after the work is done. The check now says to use `git grep`, which only searches tracked files, and explains why.

> **primary, backlog turn 3**
>
> I'm changing nothing this turn. My partner's fix is right: `apm_modules/` is listed in `.gitignore`, and the copy under `apm_modules/_local/` still cites DR-154. A plain recursive grep would therefore find DR-154 even after the work is done, while `git grep` only searches tracked files. The rest of the issue matches the code, `difficulty: easy` fits its size, and it is ready to plan.

> **primary, todo turn 1**
>
> I wrote the plan under `## The plan` in `issues/todo/retire-count-slots.md` and committed it. Nothing is implemented yet.
>
> **Steps,** in one commit, ordered so the renderer still imports after each one:
> 1. **`targets.py`:** `rendered()` returns its pages directly, without the count fill, and its docstring paragraph about filling counts goes.
> 2. **`render.py`:** drop the five re-exported names from both the import block and `__all__`.
> 3. **`record.py`:** delete the two error messages, the block from the DR-154 comment through `counted()`, and "and counts" in the module docstring. The plan also drops the `import ast` and `import re` lines, which the issue didn't mention. Only the removed code uses them, so they would otherwise be flagged as unused.
> 4. **DR-154's record:** mark it withdrawn, add a `withdrawn_because:` in the one-line form that DR-036 and DR-084 use, and remove its `enacted_in`. The rest of the record stays as written.
> 5. **Render twice.** Only `.meta/decisions.md` should change. If any other page changes, some page still had a count slot the grep missed, and the work should stop there.
>
> **Tests:** the greps in the issue's done-when list, plus the two renders. No test refers to the removed names, so none changes. Two existing checks bear on it:
> - The check on withdrawn records needs the `withdrawn_because:` line, which step 4 adds.
> - The `enacted decisions` check in `.meta/checks/graph/artifacts.py` only looks at adopted records, so removing `enacted_in` from a withdrawn one can't fail it.
>
> **Risk:** small. The gate's check for stale pages calls `rendered()` too, so removing the fill halfway would break both rendering and the gate at once. The step order prevents that.

> **secondary, todo turn 2**
>
> I checked my partner's plan against the code and made one fix, which I committed. The plan is otherwise ready to implement.
>
> **What holds:**
> - **`import ast` and `import re`:** in `record.py`, only `COUNT`, `prechecks()` and `counted()` use them, so taking both imports out is right.
> - **The `targets.py` docstring:** the "Counts are filled last" paragraph is there to delete, and `rendered()` ends with the `record.counted(...)` line the plan replaces.
> - **Removing `enacted_in`:** the `enacted decisions` step in `.meta/checks/graph/artifacts.py` only looks at adopted records, so this can't trip it.
>
> **What I fixed:** the plan named the wrong check for the `withdrawn_because:` line. It cited the `withdrawn decisions probes` precheck in `.meta/checks/probes/knowledge.py`, but that only tests the rule on made-up records. The step that reads DR-154 itself is `withdrawn decisions` in `.meta/checks/graph/record.py`. The plan now names that step and says what the precheck does.

> **primary, todo turn 3**
>
> I'm changing nothing this turn. My partner's fix is right: the `withdrawn decisions` step in `.meta/checks/graph/record.py` is the one that reads DR-154's record and needs its `withdrawn_because:` line. The precheck I had named only tests that rule on made-up records. The plan is ready to implement.

> **primary, in-progress turn 1**
>
> The count slots are gone from the renderer and DR-154 is withdrawn, both committed. `just gate meta` passes all 94 steps.
>
> **What changed:**
> - **`.meta/lib/render/targets.py`:** `rendered()` now returns its pages without filling in counts, and the docstring paragraph about that is gone.
> - **`.meta/render.py`:** the five re-exported names are removed from the import block and from `__all__`.
> - **`.meta/lib/render/record.py`:** the two error messages are deleted, along with everything from the DR-154 comment through `counted()`, the now-unused `import ast` and `import re`, and "and counts" in the module docstring.
> - **DR-154:** marked `WITHDRAWN`, with a `withdrawn_because:` that quotes its falsifier and says it is met. Its `enacted_in` is removed.
> - **`.meta/decisions.md`:** re-rendered. DR-154 moves from the adopted list to the withdrawn list and drops out of the "By artifact" rows for `record.py` and `render.py`. No other page changed, and a second `just render` changed nothing.
>
> **One step the plan missed:** `targets.py` also no longer needs `record` in its `from lib.render import` line, because `counted()` was its only use there. I removed it, and noted it in the issue file under "What the work changed in the plan".
>
> The issue's checks for being done all pass. The `grep -w` search for the removed names finds only the `pair-status` comment in `writers.py`, and `git grep DR-154` outside the decision records, `.meta/decisions.md` and `issues/` finds nothing.

> **secondary, in-progress turn 2**
>
> I'm changing nothing this turn: my partner's work is complete and matches the plan. `just gate meta` passes all 94 steps.
>
> I checked these things:
> - **Done-when checks:** `git grep` across the tracked tree, leaving out `issues/`, the decision records and `.meta/decisions.md`, finds no `{#` slot, no `counted()` or `counts()`, and no `NUMBERS`, `NO_COUNT`, `NO_PRECHECK` or `targets.record`. No wiki page mentions the count slots either.
> - **Imports in `record.py`:** after `ast` and `re` came out, `META` is still imported and still used.
> - **The extra step:** removing `record` from the import line in `targets.py`, which the plan missed, is right. My partner already recorded it in the issue file.
> - **DR-154:** the withdrawal is in place and the rendered index shows it correctly.
