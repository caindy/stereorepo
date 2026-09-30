---
difficulty: medium
---

# Publish the loop's status by a convention a cockpit can read

A cockpit, one view across every repository the developer runs a pair loop
in, comes later. What it needs from each repository now is one convention for
publishing what the loop knows: the Issue underway, its stage, its round,
whether it needs the developer, and why.

## Wanted

- Whenever the supervisor's state changes, it writes a read-only projection of
  it to `~/.pairs/<repo>.json`, where `<repo>` is the basename of the
  developer's checkout. The file also holds the checkout's absolute path, so a
  reader can tell two checkouts with the same basename apart. It is written to
  a temporary file and renamed, so a reader never sees half of it.
- It holds: the Issue underway (or none), its stage, its round, and whether
  and why it needs the developer. The reasons are those the loop already
  distinguishes: a desk check waiting for `just pair-accept` or
  `just pair-resume`; an Issue sent back with a `Needs elaboration` section; a
  seat that crashed again after its one restart; a grooming pass or stage past
  its round cap; a fast-forward of `main` that `--ff-only` refused.
- It holds nothing the board, `.pair/` and git do not. A cockpit reads it and
  writes nothing back.
- The schema is documented in `pair/README.md`, where a cockpit's author will
  look for it.

## Out of scope

The cockpit itself, notifications, and taking over a seat. The requirements
for those are written up by `why-fork-harness-survey`.

## Done when

For every state `pair/test_pair.py` drives the loop into, the published file
and `just pair-status` agree (the tests point `~/.pairs` at a scratch
directory), the schema is in `pair/README.md`, and `just gate` passes.
