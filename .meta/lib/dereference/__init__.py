"""The body of `.meta/dereference.py`: the reading of a citation before the hand-off.

`reading` builds the pairs, a sentence and the entry it cites, within the
scope a branch is read in; `asking` puts each to the model; `report` prints
the marks; `cli` is the command line the script delegates to.
"""
import pathlib

META = pathlib.Path(__file__).resolve().parents[2]
"""The `.meta/` directory, two levels above this package."""
ROOT = META.parent
"""The repository root."""
