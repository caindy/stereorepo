# Check formatting in python-seed's gate, or stop expecting it

python-seed's gate runs `ruff check` but never `ruff format --check`, so
formatting drift goes unreported. On `pair/python-seed-gate-stdout`,
`ruff format --check` would reformat code nobody had touched: the `CITATION`
pattern in `bootstraps/python/seed/gate/src/gate/__init__.py` and the
`FLOOR_CASES` table in `bootstraps/python/seed/gate/tests/test_probes.py`.

Decide whether python-seed's gate should hold formatting. If it should, add
the check as a step, or to the `ruff` step, and reformat the drifted code in
the same change. If it should not, say why where the `ruff` step is defined.
