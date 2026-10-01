# A rebase conflict after landing is overtaken leaves a turn in `done`

`Loop.merge` moves an Issue to `done/` (via `retirement`) before `land`. If
`land` answers `moved` because the other process landed first, `merge` goes
round again. If that rebase then conflicts, `rebase` pauses with `retry=None`
while `st.stage == "done"`. The next `just pair` calls `work`, which starts a
turn, and `Loop.message` reads `pair/prompts/stage-done.md`, which does not
exist, so the loop crashes with `FileNotFoundError`.

Found while planning `unused-desk-check-prompt`, which handles the
`desk-check` stage of the same sequence.
