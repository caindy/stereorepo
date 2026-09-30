---
difficulty: medium
waits_on:
  - seat-cache-write-per-session
---

# Let each stage name the model its seats run

Both seats run one model for the whole Issue (`--model` on `just pair`). The
stages ask different things of them: grooming reads the backlog and the code,
and implementation writes and checks it. A different model may suit each.

A seat's session is kept for the whole Issue so its prompt cache stays warm,
so changing model between stages starts fresh sessions and re-writes the
cache. This waits on `seat-cache-write-per-session`, whose measurement of
that re-write is what decides whether a change is worth it.

## Wanted

- A flag per stage on `just pair` (`--grooming-model`, `--backlog-model`,
  `--todo-model`, `--in-progress-model`), each defaulting to `--model`, which
  keeps its meaning. A value is a model id, an atomic identifier.
- When the next stage's model differs from the current one, both seats start
  fresh sessions for it; when it is the same, the sessions carry on.
- `pair/README.md` says what a change costs, from the measured re-write, so
  the developer can judge it.
- Primary and secondary keep meaning only which seat takes the first turn in
  a stage.

## Out of scope

Choosing different models for the two seats within one stage, and choosing
models automatically.

## Done when

With no stage flag the seats' command lines are what they are today,
`pair/test_pair.py` covers a model change between two stages (fresh sessions
on the new model) and a stage that keeps the model (sessions resumed), and
`just gate` passes.
