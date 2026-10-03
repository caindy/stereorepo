---
difficulty: medium
---

# Run the checkout's sync, not the portfolio's copy of it

`just sync <checkout>` runs `.meta/bundle.py sync <checkout>`, which is the
portfolio's own copy of the sync (`_cmd_sync` in `.meta/bundle.py`, with the
logic in `.meta/lib/bundle/`), and that copy replaces itself from the
checkout as it runs. A change to the sync therefore takes effect one sync
late: the first sync after it runs the old code. In fitch-mvp, the first sync
after `sync-keeps-a-portfolios-compiled-skills` landed still removed the
portfolio's two compiled skills from `.meta/.apm/skills/`, and only the
second sync kept them.

## How to reproduce

Change what the sync keeps or removes in a stereorepo checkout, then run
`just sync <checkout>` in a portfolio synced from before the change: the
portfolio's `.meta/lib/bundle/` is updated, but the plan applied was the old
code's. A second `just sync` applies the new behaviour.

## Wanted

`just sync <checkout>` runs the sync logic the checkout holds, so that a
fix to the sync applies on the first sync after it lands. Whether the recipe
calls the checkout's `bundle.py` with `--root .`, or the portfolio's
`_cmd_sync` hands the work to the checkout's `bundle.py` (for example by
running it with `--root` set to the portfolio), is the implementer's choice.
Recipes still take only flags, subcommands and atomic identifiers (DR-259,
DR-272), and `just sync <checkout>` keeps its form.

## Out of scope

- What a sync copies, removes or merges.
- `ADOPT.md` step 4: its note explains why the first copy into a repository
  that has no `sync` recipe yet must call the checkout's `bundle.py`
  directly, and that stays true.
- The first sync of a portfolio after this Issue lands. That sync still
  runs the portfolio's old recipe and old `bundle.py`, so it is one sync late
  itself; only syncs after it run the checkout's logic.

## Done when

- A probe beside `.meta/checks/probes/tools/sync.py`, over a temporary
  portfolio and a temporary checkout whose sync logic differs from the
  portfolio's copy (for example, it writes a marker file the portfolio's copy
  does not): one sync, started the way `just sync` starts it, applies the
  checkout's logic.
- A sync from a checkout that cannot run (no `.meta/bundle.py`) refuses with
  a message and changes nothing, as a refused sync does today.
