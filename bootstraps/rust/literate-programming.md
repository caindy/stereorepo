# Literate Programming, in Rust

How this Bootstrap implements the inherited Discipline. The Discipline requires
that an artifact be an exposition, that the exposition exist in **one copy**, and
that the copy be the one the machine reads. It deliberately does not say where
the prose sits. This does.

## Prose routes by what it tells the reader

The routing test is the one that sorts paragraphs — *what to do*, *what
happened*, *why* — applied inside a source file:

| Tells the reader | Goes | Because |
|---|---|---|
| what to **do** — how to use this item | inline `///` | a reader of the source needs it in front of them |
| **why** it is the way it is | `#![doc = include_str!("…")]` | the reasoning reaches rustdoc without crowding the code |
| what **happened**, this once | an included log, separately named | history is rarely germane while reading the code |

So Rust uses a **mix**, not includes alone. Both satisfy the single-copy rule:
inline prose *is* the one copy, and an included file is read rather than
restated. Choosing between them is a routing decision, not a fidelity one.

History is the case that motivates the split. It accumulates in comments when an
agent fixes a defect, and it is exactly the material that should leave the source
file while staying in the documentation.

## Filenames carry the routing

An include's name says what it holds, so a reader knows before opening it
whether it is worth opening. The seed's one module,
[`seed/crates/seed/src/example/`](seed/crates/seed/src/example/), is the
instance:

```
example/
  mod.rs                  includes the three files below, in this order
  example.overview.md     what this module is
  example.rationale.md    why it is this way
  example.history.md      what happened, and what each change established
```

The crate itself is documented the same way: `src/lib.rs` includes the crate's
`README.md`, so the file a person reads first is the file rustdoc renders first.

## The log, and why a header changelog is not one

A header changelog fails twice: an entry is too brief to understand in context,
and there is no way to tell whether it still matters. One rule each.

**An entry says what failed and what the change established** — not what
changed. The diff already says what changed, which is why a changelog that
recounts it is both thin and redundant.

**An entry names its receipt: the test that would fail if the change were
undone.** That makes relevance mechanical rather than a matter of judgement. If
the named test is gone, the entry is stale and goes with it, and the log prunes
itself.

```markdown
### Tidal windows were computed in local time

Crossing a DST boundary produced a window an hour wide on two days a year, and
the error was invisible because both endpoints were plausible. Established:
every tidal computation is in UTC, and local time exists only at the edge.

Receipt: `passage::tests::window_survives_dst_boundary`
```

The receipt rule is **Observed Failure** and **Nothing Unconsumed** applied to
prose. An entry naming no test is debris by the same argument that a guardrail
never seen to fail is not evidence of anything.

## Gates

Each is a step of `cargo xtask gate`, and each can fail and says what it
checked:

- **`doc`** — `cargo doc` with every rustdoc warning an error, and
  `missing_docs` denied in the workspace lints. No public item goes
  undocumented, and no broken intra-doc link survives.
- **`test`** — `cargo test`, which runs the doctests. The examples in the prose
  are executed rather than asserted, which is the Discipline's step about
  making examples executable. The crate README's example runs too, because the
  README is the crate's documentation.
- **`orphans`** — every markdown file under a package is included by a source
  file in it. A missing include already fails the build; this holds the other
  direction. *Nothing Unconsumed.*
- **`receipts`** — every history entry names a test, and the test is one
  `cargo test -- --list` reports. The form of an entry can sit in the log as an
  HTML comment without counting as one, which is how the seed's log says what
  an entry looks like before it has any.
