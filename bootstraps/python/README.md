# The Python standard

What a Python project in a portfolio inherits, and the gates that hold it there.

The seed is [`seed/`](seed/): a uv workspace of one package and the gate that
holds it. **`uv run gate` is the gate.** Each Discipline below says how it is
satisfied in Python and which step of the gate holds it there.

| Discipline | How, in Python | Held by |
|---|---|---|
| Literate Programming | [`literate-programming.md`](literate-programming.md) | `doc`, `test`, `orphans` |
| Ratchet | [`ratchet.md`](ratchet.md) | `lints`, `ruff`, `types` |
| Observed Failure | [`observed-failure.md`](observed-failure.md) | `mutants`, and the gate's own probes |
| Nothing Unconsumed | [`nothing-unconsumed.md`](nothing-unconsumed.md) | `orphans`, `evidence` |
| Seeded Artifacts | [`seeded-artifacts.md`](seeded-artifacts.md) | [`render`](render), and the `python seed` job in the workflow |
| Written Decisions | [`written-decisions.md`](written-decisions.md) | nothing here — the portfolio's gate, and it says why |

The other Disciplines bind the Portfolio rather than a Project — Progressive
Disclosure, Ubiquitous Language, Dogfooding, Modelling the Solo, PR First,
Journaling — so a Bootstrap has nothing to implement for them.

Four Articles bind the gate itself rather than being implemented by it: A5 —
no gate step rewrites the tree; A6 — every step has three outcomes; A7 — a
check-mark is a claim about scope; A21 — every gate prints one report shape.
[`seed/gate/README.md`](seed/gate/README.md) says how the gate keeps each.

The Disciplines are in `.meta/assertions/imported/disciplines.yaml`. This
directory only ever says **how** — a Bootstrap that restated a Discipline would
be a second copy of it, and the second copy is the one that drifts.

## Taking it into a portfolio

Specialization's *Choose languages and bootstrap* step, for Python:

```bash
bootstraps/python/render <destination> <package-name>
```

That copies the seed out and names its package. What arrives is the workspace,
its pinned tools, its lockfile, and its gate; run `uv run gate` in the
destination before the first commit, which is also what the workflow does to
prove the seed is sound.

The seed is a real workspace named `seed`, not a tree of placeholder tokens,
so that its own gate can run on it where it sits (DR-091). The one placeholder
is the package's name, and `render` is the one copy of how it is substituted.

## Capabilities and the APM Package

The Python standard declares sixteen agent skills as Capabilities in
[`assertions/capabilities.yaml`](assertions/capabilities.yaml) (solorepo's DR-208, solorepo's #59): eight refactoring
skills (`py-*`) from `l-mb/python-refactoring-skills` and eight lifecycle skills adapted from `obra/superpowers`.

Rather than vendoring raw skills into the project seed, they are compiled into
an APM package at [`apm.yml`](apm.yml) under `.apm/skills/`. When a portfolio
adopts Python (`just bootstrap python <dest>` or Specialization), the package is
brought in as an APM dependency and projected into the active agent harnesses,
keeping the seed workspace minimal and unencumbered. Upstream attribution and
modifications are preserved in [`PROVENANCE.md`](PROVENANCE.md),
[`LICENSE-python-refactoring-skills`](LICENSE-python-refactoring-skills), and
[`LICENSE-superpowers`](LICENSE-superpowers).

## Where it came from

The seed is `python_bootstrap`'s template with its memory architecture taken
out, because that architecture is the Portfolio's `.meta/` here: its charter
is `AGENTS.md`, its decision tracks are the record with `product` or
`project` set, its bets are each entry's falsifier, and its journal is what
Journaling routes. DR-094 is the account of what came and what stayed, and
DR-095, DR-096, DR-097, DR-193 and DR-208 are its decisions about the standard, filed at the
level they bind. The generator stays behind (DR-099): its `new` is [`render`](render),
and its sync, never built, is kept there as the shape a portfolio's sync
will take.

