# Let each stage name the model its seats run

Both seats run one model for the whole issue (`--model` on `just pair`). The
stages ask different things of them: grooming reads the backlog and the code,
and implementation writes and checks it. A different model may suit each.

Let the stage choose the seats' model. A seat's session is kept for the whole
issue so its prompt cache stays warm, so changing model between stages starts
fresh sessions and re-writes the cache (see
`resume-seat-sessions-across-issues.md`); decide whether that cost is worth it,
and measure it in `.pair/turns.jsonl`. Primary and secondary name only which
seat takes the first turn in a stage, and should keep meaning only that.

Done when a stage's model can be set without changing code, the default is
what it is today, and the pair tests cover a model change between stages.
