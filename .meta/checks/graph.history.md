# History

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Receipt: `<path>::<symbol>`
-->

### Asking the remote first hid deletion advice on clones without origin

In solorepo's #152, checking remote tags before local commit history caused the
check to discard deletion reads on runs where the remote did not answer
(such as fresh portfolio clones without an origin remote). The single
actionable guidance explaining how to handle missing entries was withheld
where it was most needed. Established: commit history is checked first for
local deletions before falling back to remote tag reservations.

Receipt: `.meta/checks/probes.py::reservation_probes`

### Unreadable remote tags advised taking reserved decision numbers

When the remote was unreachable, the check previously reported "no tag
reserving it" and advised writing the number back as WITHDRAWN, causing
sessions to inadvertently claim numbers already reserved by active branches.
Established: an unreadable remote is explicitly reported as an unknown
state rather than an unreserved hole.

Receipt: `.meta/checks/probes.py::reservation_probes`
