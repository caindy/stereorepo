# Literate Programming, in Python

How this Bootstrap implements the inherited Discipline. The Discipline requires
that an artifact be an exposition, that the exposition exist in **one copy**,
that the copy be the one the machine reads, and that the prose in a source file
be sorted by what it tells the reader — what to do, why, what happened. It
deliberately does not say where each kind sits. This does.

## Where each kind of prose sits

| Tells the reader | Goes | Because |
|---|---|---|
| what to **do** — how to use this item | the item's docstring | a reader of the source needs it in front of them, and `help()` reads the same copy |
| **why** it is the way it is | the module docstring, under a heading somebody would search for | the reasoning reaches every documentation tool without crowding the code |
| what **happened**, this once | `<module>.history.md` beside the module, named by its docstring | history is rarely germane while reading the code |

Python has no `include_str!`, so the docstring is the one copy rather than a
reference to one, and the history log is read beside the module rather than
rendered into it. Both satisfy the single-copy rule; the sorting is the
Discipline's, and only the mechanism differs from Rust's.

## Filenames carry the routing

The seed's one module,
[`seed/packages/seed/src/seed/example.py`](seed/packages/seed/src/seed/example.py),
is the instance:

```
seed/
  __init__.py          the package, naming its README as the distribution's page
  example.py           what to do, in docstrings; why, in the module docstring
  example.history.md   what happened, and what each change established
```

The package itself is documented the same way: `pyproject.toml` names
`README.md` as the readme, so the file a person reads first is the file the
index renders first, and its example runs under `pytest`.

## The log

Nothing Unconsumed says what an entry is: what failed and what the change
established, and its receipt — the test that would fail if the change were
undone. In Python a receipt is a test id as pytest names it from the package.

```markdown
### Tidal windows were computed in local time

Crossing a DST boundary produced a window an hour wide on two days a year, and
the error was invisible because both endpoints were plausible. Established:
every tidal computation is in UTC, and local time exists only at the edge.

Receipt: `tests/test_passage.py::test_window_survives_dst_boundary`
```

## Gates

Each is a step of `uv run gate`, and each can fail and says what it checked:

- **`doc`** — every module, and every public function, class and method under
  a package's `src/`, has a docstring. The Python `missing_docs`, read off the
  syntax tree rather than through a style checker, because what is held is
  presence and not shape.
- **`test`** — `pytest --doctest-modules`, so the examples in the prose are
  executed rather than asserted, which is the Discipline's step about making
  examples executable. The package README's example runs too, because the
  README is the package's documentation.
- **`orphans`** — every markdown file under a package is named by a source
  file or the manifest in it. *Nothing Unconsumed.*
- **`receipts`** — every history entry names a test, and the test is one
  `pytest --collect-only` reports. The form of an entry can sit in the log as
  an HTML comment without counting as one, which is how the seed's log says
  what an entry looks like before it has any.
