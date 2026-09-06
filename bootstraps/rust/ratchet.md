# Ratchet, in Rust

Quality moves one way. The compiler is most of the mechanism; the rest is
refusing the ways round it.

## Lints are raised once, and only ever raised

`[workspace.lints]` in the seed's root manifest sets the levels, and every
member crate takes them with `[lints] workspace = true`. Nothing in that table
is `allow`, and **`cargo xtask lints`** refuses one — in any manifest's lints
table, and in `.cargo/config.toml`'s rustflags. A2: a suppression names its rule
and its reason, at the site, never in configuration.

`cargo clippy` runs with every warning an error and `pedantic` on. Pedantic is
a floor, not a taste: the lints it adds are the ones that make a reviewer ask
"why not `#[must_use]`?", and answering that in code once is cheaper than
answering it in review forever.

## A suppression is an expectation, with a reason

`#[allow]` is refused by `clippy::allow_attributes`. The suppression this seed
permits is `#[expect(lint, reason = "…")]`, and it differs in the direction
that matters: an `expect` whose lint stops firing is a compile error. A
suppression that outlives its cause is found by the compiler rather than by
someone reading the code, which is the ratchet running forward on its own.
`clippy::allow_attributes_without_reason` holds the reason.

## Formatting is checked, never applied

**`cargo xtask fmt`** is `cargo fmt --check`. A gate step that rewrites the tree
leaves the author unsure what they committed (A5). Formatting is `cargo fmt`,
run by a person.

## The toolchain is pinned

`rust-toolchain.toml` names a version and its components, so a lint that
arrives in a newer compiler cannot turn a green tree red on the one machine
that updated. Moving the pin is an edit, reviewed like any other.

## No baseline yet

Nothing in the seed needs a ratchet of the third kind — a checker that cannot
be clean at once, held to a baseline that may improve and may not regress.
`cargo mutants` is clean and stays clean by construction. The first checker
adopted that cannot be clean on arrival gets a baseline then, and the reason
goes beside the number.
