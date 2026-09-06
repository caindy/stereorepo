# Written Decisions, in Python

Nothing in this Bootstrap implements it, and the reason is where the record
lives.

A decision about how a Python Project is built is a `Decision` with its
`project` set, and one about what every Python Project inherits is a
`Decision` with its `product` set, both in the portfolio's own
`.meta/assertions/decisions/` — one record at every level, and the entry
names its level (DR-059, DR-093). It is not a file in the package.
`python_bootstrap` kept two tracks of records beside its code, indexed by
hand and held in step by a checker of its own; here the portfolio's gate
already holds the record — numbering, supersession, one chosen alternative,
every cited DR resolving — and a second record in the package would be a
second copy with a weaker checker. Its records became DR-095, DR-096 and
DR-097, filed at the level they bind.

What Python adds is the citation. The module docstring, the part that says
*why* it is the way it is, cites the Decision by number and question —
"DR-0nn — the question it answered" — and does not restate it. A12: a
citation in a durable artifact is dereferenced. The seed's `example.py` shows
the form with no decision to cite, because no decision has been taken about a
module that exists to be replaced.
