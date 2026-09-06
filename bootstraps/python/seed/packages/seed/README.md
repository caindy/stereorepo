The package a Python Project starts from. This file is its distribution's
documentation: `pyproject.toml` names it as the readme, so there is one copy
and the index page renders it.

It holds one module, `seed.example`, which exists so that the documentation
layout has an instance and the gates have something to fail on. Replace it
with the first real module and keep the layout: what to do with a thing in its
docstring, why the module is the way it is in the module's docstring, and what
happened in a history log beside it, named by the module that owns it.

Examples in docstrings are executed by `pytest`, not merely asserted:

```
>>> from seed.example import lines
>>> lines("one\n\ntwo")
['one', 'two']

```
