# History

### Stale runner scale set annotation caused persistent GitHub 404 errors

When a runner scale set was deregistered on GitHub (such as via teardown from
another host), Helm upgrades preserved custom resource annotations on the existing
`AutoscalingRunnerSet`, retaining a dead `runner-scale-set-id`. The controller
could not recover from the resulting 404 error during Just-In-Time (JIT) configuration
generation. Established: `reset_stale_registration()` detects 404 and 409 listener
exceptions, resets stale annotation IDs, and deletes orphaned child custom resources.

Evidence: `.meta/checks/files/history.py::meta_history_evidence`

### Passing GitHub registration tokens via arguments exposed credentials

Passing personal access tokens as command-line arguments exposed secrets in process
tables (`ps`) and shell history. Established: `apply_secret()` streams generated
Kubernetes Secret manifests over process stdin without exposing tokens in argument vectors.

Evidence: `.meta/checks/files/history.py::meta_history_evidence`
