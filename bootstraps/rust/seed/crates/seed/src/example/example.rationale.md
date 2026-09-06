# Why it is this way

The one function trims and drops blank lines, which is enough to carry a
doctest, a unit test and a mutation the tests must catch. It is deliberately
too small to argue about, so that what a reader takes from this module is the
layout and not the code.

A decision about how this crate is built is a Decision with its `project` set,
in the portfolio's own record, and this file cites it — "DR-0nn — the question
it answered" — rather than restating it. The record is the one copy; this is
the exposition that reaches rustdoc.
