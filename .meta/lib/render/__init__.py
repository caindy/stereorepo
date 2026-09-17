"""The body of `.meta/render.py`: the prose satellites, rendered from the assertions they describe.

`record` loads the assertions and weaves prose into pages. `pages`,
`decisions` and `skills` render their families of targets from what it loads;
`writers` renders the justfile from it and the APM primitives from
`apm_compile`. `targets` holds the table of every target and its three
readers. `cli` is the command line the script delegates to.
"""
import pathlib

META = pathlib.Path(__file__).resolve().parents[2]
"""The `.meta/` directory, two levels above this package, which every target path is relative to."""
