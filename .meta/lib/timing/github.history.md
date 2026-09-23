# History

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Evidence: `<path>::<symbol>`
-->

### The reviewer's own worktree deleted the shared runner this module imports

The pull request that moved the `gh` invocation into `.meta/lib/gh.py` also
named that file in the reviewer workflow's trunk-restore pathspec, and
`origin/main` did not hold it yet: the no-overlay restore deleted it, while
trunk's restored `.meta/lib/move/reconcile.py` went on importing `NOT_RUN` from
this module and so importing the module that was gone. Every `.meta/say/move`
invocation in that one reviewer run died on the `ImportError`. Established: the
import is guarded for the single run in which trunk cannot yet hold the runner,
and the guard exits saying the runner is absent rather than standing in a
reader that answers `None`, which `screen.py` reports as a token without the
`actions` scope and would have made a deleted module read as a credential
fault.

Evidence: `.meta/checks/files/control_plane.py::control_plane_packages`

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
