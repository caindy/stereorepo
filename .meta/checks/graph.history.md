# History

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Evidence: `<path>::<symbol>`
-->

### Asking the remote first hid deletion advice on clones without origin

In solorepo's #152, checking remote tags before local commit history caused the
check to discard deletion reads on runs where the remote did not answer
(such as fresh portfolio clones without an origin remote). The single
actionable guidance explaining how to handle missing entries was withheld
where it was most needed. Established: commit history is checked first for
local deletions before falling back to remote tag reservations.

Evidence: `.meta/checks/probes/channel/reservation.py::reservation_probes`

### Unreadable remote tags advised taking reserved decision numbers

When the remote was unreachable, the check previously reported "no tag
reserving it" and advised writing the number back as WITHDRAWN, causing
sessions to inadvertently claim numbers already reserved by active branches.
Established: an unreadable remote is explicitly reported as an unknown
state rather than an unreserved hole.

Evidence: `.meta/checks/probes/channel/reservation.py::reservation_probes`

### Reservation pattern anchored at line start matched no advertised tag

`git ls-remote --tags` prints the object, a tab, then the ref, with a second
line per annotated tag dereferencing it to the commit, and an annotated tag is
how a Decision number is reserved (solorepo's DR-128). A first draft of
`graph.RESERVATION` anchored at the start of the line, so it matched none of what
the remote advertised and every hole would have read as a deletion, which no
other case in `reservation_probes` could have seen, since each stands the
remote's read in for. Established: the pattern is held to reading exactly one
reservation off a verbatim two-line fixture, one annotated tag and its
dereference, because a branch is worth probing where its input comes from
somewhere else. The pattern, the fixture and the assertion landed together on
solorepo's #152, and the start-anchored version never reached `main`.

Evidence: `.meta/checks/probes/channel/reservation.py::reservation_probes`
