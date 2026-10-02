# Run the checkout's sync, not the portfolio's copy of it

`just sync <checkout>` runs `.meta/bundle.py sync`, which is the portfolio's
own copy of the sync, and that copy replaces itself from the checkout as it
runs. A change to the sync therefore takes effect one sync late: the first
sync after it runs the old code. In fitch-mvp, the first sync after
`sync-keeps-a-portfolios-compiled-skills` landed still removed the
portfolio's two compiled skills from `.meta/.apm/skills/`, and only the
second sync kept them. `ADOPT.md` step 4 notes that the recipe cannot run the
checkout's `bundle.py` with `--root`, because the recipe places its arguments
after `sync`.

## Wanted

`just sync <checkout>` runs the sync logic the checkout holds, so that a
fix to the sync applies on the first sync after it lands. Whether the recipe
calls the checkout's `bundle.py`, or the portfolio's `bundle.py` hands the
work to the checkout's, is open. Recipes still take only flags, subcommands
and atomic identifiers (DR-259, DR-272).

## How anyone will know it is done

A test over a temporary portfolio and a temporary checkout whose sync logic
differs from the portfolio's copy: one `just sync` applies the checkout's
logic. `ADOPT.md` step 4 no longer needs its note about the first sync.

## Out of scope

- What a sync copies, removes or merges.
