"""The body of `.meta/say/on`: the autonomous-loop doors (solorepo's DR-217, DR-264).

`common` holds shared values, reading-door helpers, and the command seam.
`review` holds both reviewer-door phases; `coder_door` holds the coder door's
`before` and `between` phases, and `handoff` holds its `after` phase. `cli`
is the command-line surface.

`common` imports nothing in the package. `review` and `coder_door` import
`common`; `handoff` imports `coder_door`; and `cli` imports `coder_door`,
`common`, and `review`. `coder_door` defers its import of `handoff` until
`coder()` runs, because `handoff` imports `coder_door` when the package loads;
the cycle therefore loads before either lifecycle runs.
"""
