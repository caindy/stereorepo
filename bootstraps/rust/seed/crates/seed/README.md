The crate a Rust Project starts from. This file is its crate-level
documentation: `src/lib.rs` includes it, so there is one copy and rustdoc reads
it.

It holds one module, [`example`], which exists so that the documentation
layout has an instance and the gates have something to fail on. Replace it with
the first real module and keep the layout: prose beside the code, routed by
what it tells the reader, each file included by the module it belongs to.

Examples in this prose are executed by `cargo test`, not merely asserted:

```
use seed::example::lines;

assert_eq!(lines("one\n\ntwo"), ["one", "two"]);
```
