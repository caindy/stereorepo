# Ratchet, in Python

Quality moves one way. The tools are most of the mechanism; the rest is
refusing the ways round them.

## Rules are raised once, and only ever raised

`[tool.ruff.lint]` in the seed's workspace manifest selects the rule set
(DR-096), and `ignore` is empty. **`uv run gate lints`** refuses an entry in
it, or in `extend-ignore`, or a mypy override that switches checking off. A2:
a suppression names its rule and its reason, at the site, never in
configuration. A `per-file-ignores` entry is configuration too, and is
allowed only with a reason on its line, because the alternative — a
suppression on every assert in every test — is a rule nobody would keep.

`mypy --strict` runs over every package's source and tests, with no
per-module exemption.

## A suppression carries a reason, and a dead one is an error

The suppression this seed permits is `# noqa: RULE  # reason: …`, and
`lints` refuses one without the reason. `RUF100` is in the rule set, so a
`noqa` whose rule stops firing is an error: a suppression that outlives its
cause is found by the tool rather than by someone reading the code, which is
the ratchet running forward on its own. `# type: ignore[code]  # reason: …`
is held the same way, and mypy's `warn_unused_ignores`, on under strict,
does for it what `RUF100` does for `noqa`.

## Formatting is checked, never applied

**`uv run gate fmt`** is `ruff format --check`. A gate step that rewrites the
tree leaves the author unsure what they committed (A5). Formatting is
`ruff format`, run by a person.

## The tools and the interpreter are pinned

The gate's tools are pinned exactly in the workspace manifest and the test
tools float (DR-097), so a rule that arrives in a newer release cannot turn a
green tree red on the one machine that updated. `.python-version` pins the
interpreter developed on, and `requires-python` states the support floor,
which is lower; the linters target the floor (DR-095), so they catch code
that works on the newer interpreter and breaks on the oldest this workspace
claims. Moving any pin is an edit, reviewed like any other.

## No baseline yet

Nothing in the seed needs a ratchet of the third kind — a checker that cannot
be clean at once, held to a baseline that may improve and may not regress.
`mutmut` is clean and stays clean by construction. The first checker adopted
that cannot be clean on arrival gets a baseline then, and the reason goes
beside the number. When it does, the shape to take is `python_bootstrap`'s
two-sided ratchet, which fails below the baseline as well as above it: an
un-banked improvement is slack that grows back where nobody is looking.
