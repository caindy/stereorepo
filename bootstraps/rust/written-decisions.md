# Written Decisions, in Rust

Nothing in this Bootstrap implements it, and the reason is where the record
lives.

A decision about how a Rust Project is built is a `Decision` with its `project`
set, in the portfolio's own `.meta/assertions/decisions/`, rendered in the ADR
form (DR-059). It is not a file in the crate. The portfolio's gate already holds
that record — numbering, supersession, one chosen alternative, every cited DR
resolving — and a second record in the crate would be a second copy with a
weaker checker.

What Rust adds is the citation. The crate's rationale include, the file that
says *why* it is the way it is, cites the Decision by number and question —
"DR-0nn — the question it answered" — and does not restate it. A12: a citation
in a durable artifact is dereferenced. The seed's `example.rationale.md` shows
the form with no decision to cite, because no decision has been taken about a
module that exists to be replaced.
