"""The body of `.meta/check_pr.py`: the GitHub half of the gate, as nine modules.

In dependency order, read off each module's `from lib.check_pr import` line.
`form` and `github` depend on nothing in the package: `form` reads the
template, `github` asks GitHub. `review` reads what was said on a pull request
and draws on `github`. `state` classifies lifecycle states and predicates,
drawing on `review`. `branch`, `polling` and `verdict` draw on those:
`branch` reads the tree and draws on `github` and `review`; `polling` reports
what has happened on a pull request since, on `github`, `review` and `state`;
`verdict` composes the checks into the gate, on `form`, `github` and `review`.
`sweep` runs the gate over every open pull request and draws on `github`,
`polling`, `state` and `verdict`. `cli` is the argument surface the script
delegates to and draws on all eight.
"""
import pathlib

META = pathlib.Path(__file__).resolve().parents[2]
"""The `.meta/` directory, two levels above this package."""
ROOT = META.parent
"""The repository root."""
