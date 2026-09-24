"""The body of `.meta/coder_door.py`, the coder workflow door (solorepo's DR-284).

`coder_door` holds the coder door's `before` and `between` phases, `handoff`
holds its `after` phase, and `cli` is the command-line surface. The package
takes `common` and `routing` from the trunk-pinned `lib.on` rather than
holding its own.

`coder_door` defers its import of `handoff` until `coder()` runs because
`handoff` imports `coder_door` when the package loads; the cycle therefore
loads before either lifecycle runs.
"""
