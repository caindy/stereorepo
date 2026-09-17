"""The body of `.meta/check_pr.py`: the GitHub half of the gate, as eight modules.

In dependency order, read off each module's `from lib.check_pr import` line.
`form` and `github` depend on nothing in the package: `form` reads the
template, `github` asks GitHub. `review` reads what was said on a pull request
and draws on `github`. `branch`, `polling` and `verdict` draw on those:
`branch` reads the tree and draws on `github` and `review`; `polling` reports
what has happened on a pull request since, on the same two; `verdict` composes
the checks into the gate, on `form`, `github` and `review`. `sweep` runs the
gate over every open pull request and draws on `github`, `polling` and
`verdict`. `cli` is the argument surface the script delegates to and draws on
all seven.
"""
import pathlib

META = pathlib.Path(__file__).resolve().parents[2]
"""The `.meta/` directory, two levels above this package."""
ROOT = META.parent
"""The repository root."""
