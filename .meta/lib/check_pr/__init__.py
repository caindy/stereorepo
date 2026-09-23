"""The body of `.meta/check_pr.py`: the GitHub half of the gate, as ten modules.

In dependency order, read off each module's `from lib.check_pr import` line.
`form` and `github` depend on nothing in the package: `form` reads the
template, `github` asks GitHub. `review` reads what was said on a pull request
and draws on `github`. `state` classifies lifecycle states and predicates,
drawing on `review`. `branch`, `polling` and `verdict` draw on those:
`branch` reads the tree and draws on `github` and `review`; `polling` reports
what has happened on a pull request since, on `github`, `review` and `state`;
`verdict` composes the checks into the gate, on `form`, `github` and `review`.
`remedies` reads who takes each open pull request next, on `github`, `polling`,
`review` and `state`. `sweep` runs the gate over every open pull request and
draws on `github`, `polling`, `remedies`, `state` and `verdict`. `cli` is the
argument surface the script delegates to and draws on every module above it
but `state` and `remedies`, which it reaches through the modules that do.
"""
import pathlib

META = pathlib.Path(__file__).resolve().parents[2]
"""The `.meta/` directory, two levels above this package."""
ROOT = META.parent
"""The repository root."""
