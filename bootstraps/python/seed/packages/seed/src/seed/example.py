"""A placeholder module, showing where prose goes in a Python source tree.

What to **do** with an item is its docstring, because a reader of the source
needs it in front of them, and `help()` and every documentation tool read the
same copy. **Why** the module is the way it is goes here, in the module's own
docstring, under a heading somebody would search for. What **happened**, this
once, goes in `example.history.md` beside this file: history accumulates in
comments when a defect is fixed, and it is the material that should leave the
code while staying beside it.

Why it is this way
------------------
The one function trims and drops blank lines, which is enough to carry a
doctest, a unit test and a mutation the tests must catch. It is deliberately
too small to argue about, so that what a reader takes from this module is the
layout and not the code. It is a loop rather than the comprehension it could
be because mutmut mutates nothing in a function that is one comprehension,
and a module the mutation step cannot bite on would seed a green mark that
claims nothing.

A decision about how this package is built is a Decision with its `project`
set, in the portfolio's own record, and this docstring cites it — "DR-0nn —
the question it answered" — rather than restating it. The record is the one
copy; this is the exposition that reaches the reader.

Nothing in this module is worth keeping. Delete it with the first real module,
or rename it and keep its history log.
"""

from __future__ import annotations


def lines(text: str) -> list[str]:
    """Splits text into non-empty, whitespace-trimmed lines.

    Args:
        text: Multiline string to split and trim.

    Returns:
        list[str]: Sequence of non-empty line strings with surrounding
            whitespace removed.

    >>> lines(" a \\n\\n b ")
    ['a', 'b']
    """
    kept: list[str] = []
    for line in text.splitlines():
        trimmed = line.strip()
        if trimmed:
            kept.append(trimmed)
    return kept
