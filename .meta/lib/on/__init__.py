"""The body of `.meta/say/on`: the autonomous-loop doors (solorepo's DR-217, DR-264).

`routing` holds the policy: every model, effort and cap a door emits, and the
chain of harnesses that may run a pass (solorepo's DR-281). `prompts` renders
a rung's prompt from its pass's form. `common` holds shared values,
reading-door helpers, the `between` phase both Roles share, and the command
seam. `review` holds the reviewer-door phases; `coder_door` holds the coder
door's `before` and `between` phases, and `handoff` holds its `after` phase.
`cli` is the command-line surface.

`routing` imports nothing in the package, so `.meta/depth.py` can import it
alone; `prompts` imports `routing`; `common` imports both. `review` and
`coder_door` import `common` and `routing`; `handoff` imports `coder_door`;
and `cli` imports `coder_door`, `common`, and `review`. `coder_door` defers
its import of `handoff` until `coder()` runs, because `handoff` imports
`coder_door` when the package loads; the cycle therefore loads before either
lifecycle runs.
"""
