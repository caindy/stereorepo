# Nothing Unconsumed, in Python

An artifact prevents drift only if something consumes it, and the question after
"what reads this?" is "what is it checked against?"

## Code

The rule set holds it. An unused import, variable or argument is an error
under `ruff`, and a `noqa` whose rule no longer fires is one too.

## Prose

**`uv run gate orphans`** — every markdown file under a package is named by a
source file or the manifest in that package. Python has no include, so the
consumer is a reader following a name: a docstring that says which log sits
beside the module, or a manifest that names its readme. What it is checked
against is the source tree, because a file nothing names is one no reader is
sent to, however carefully it was written. This is weaker than the Rust
check, where the consumer is rustdoc and a file it does not include is not
rendered; the page says so rather than claiming otherwise.

**`uv run gate receipts`** — every history entry names a test, and the test is
one `pytest --collect-only` reports. The entry is consumed by a reader; what
it is checked against is the test suite. An entry whose test is gone is the
Discipline's "delete what nothing consumes", made mechanical.

## The gate itself

Every step is in `STEPS`, and `uv run gate` runs `STEPS`. A step that exists
in the package but not in that table cannot be written, since the table is the
only thing the entry point reads. There is no `scripts/` directory and no
orphan-script check, because there is nowhere for an orphan script to be —
which is why `python_bootstrap`'s checker for them did not come.

The Bootstrap's own [`render`](render) is consumed by the `python seed` job of
the workflow, which runs it and then runs the gate on what it produced.
