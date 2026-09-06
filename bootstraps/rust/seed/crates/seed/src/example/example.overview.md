A placeholder module, showing where prose goes in a Rust source tree.

Three markdown files sit beside `mod.rs`, and the module includes each with
`#![doc = include_str!(…)]`. What to **do** with an item is inline `///` on the
item, because a reader of the source needs it in front of them. **Why** the
module is the way it is goes in `example.rationale.md`. What **happened**, this
once, goes in `example.history.md`. A file named for what it holds tells the
reader whether it is worth opening before they open it.

Nothing in this module is worth keeping. Delete it with the first real module,
or rename it and keep its three files.
