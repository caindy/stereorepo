# Literate Programming, in Rust

How this Bootstrap implements the inherited Discipline. The Discipline requires
that an artifact be an exposition, that the exposition exist in **one copy**,
that the copy be the one the machine reads, and that the prose in a source file
be sorted by what it tells the reader — what to do, why, what happened. It
deliberately does not say where each kind sits. This does.

## Where each kind of prose sits

| Tells the reader | Goes | Because |
|---|---|---|
| what to **do** — how to use this item | inline `///` | a reader of the source needs it in front of them |
| **why** it is the way it is | `#![doc = include_str!("…")]` | the reasoning reaches rustdoc without crowding the code |
| what **happened**, this once | an included log, separately named | history is rarely germane while reading the code |

So Rust uses a **mix**, not includes alone. Both satisfy the single-copy rule:
inline prose *is* the one copy, and an included file is read rather than
restated. Choosing between them is a routing decision, not a fidelity one.

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

## The log

Nothing Unconsumed says what an entry is: what failed and what the change
established, and its Evidence — the test that would fail if the change were
undone. In Rust the Evidence is a test path as `cargo test -- --list` prints
it.

```markdown
### Tidal windows were computed in local time

Crossing a DST boundary produced a window an hour wide on two days a year, and
the error was invisible because both endpoints were plausible. Established:
every tidal computation is in UTC, and local time exists only at the edge.

Evidence: `passage::tests::window_survives_dst_boundary`
```

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
- **`evidence`** — every history entry names a test, and the test is one
  `cargo test -- --list` reports. The form of an entry can sit in the log as an
  HTML comment without counting as one, which is how the seed's log says what
  an entry looks like before it has any.

## The reader's test and register

Docstrings are addressed to a reader who wants to use the item, not to a
reviewer who might object (DR-175).

Docstrings litigate when they anticipate objections, debate discarded
alternatives, or narrate past bugs. A reader arriving at an item docstring needs
its contract: what it does, how to use it, parameters, return values, errors,
and invariants.

The test for any docstring is the **reader's test**:

> *Could someone use this item from its docstring alone, without reading the argument for it?*

If an item's docstring must explain *why* an invariant exists or why an
alternative was rejected, that rationale belongs in the module overview/rationale
or a Decision Record, cited by number. If it narrates what failed in a past run
or incident, that narrative belongs in `<module>.history.md` with Evidence.

The Technical Writer review pass holds prose, docstrings, and durable
artifacts to this register during review, allowing implementation passes to
remain concise while guaranteeing reader-facing exposition before landing.

