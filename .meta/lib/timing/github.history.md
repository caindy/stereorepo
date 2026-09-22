# History

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Evidence: `<path>::<symbol>`
-->

### A fallback of `None` meant the caller that most needs to degrade exited instead

`runs_of` reads the runs of a workflow on a token with no `actions` scope,
which is the failure this program is shaped around, and what it wants back
when that read fails is `None`. Written with `None` as the value standing for
"the caller gave no fallback", that ask was indistinguishable from giving no
fallback at all: the read exited the process, and the branch of the screen
that reports a workflow it could not read was unreachable. Established: the
absence of a fallback is a sentinel object no caller can pass, so `None` is a
fallback like any other and a caller asking for it is answered with it.

Evidence: `.meta/checks/probes/wrappers.py::gh_wrapper_probes`
