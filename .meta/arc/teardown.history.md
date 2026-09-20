# History

### Uninstalling controller before runner set hung namespace finalizers indefinitely

The runner scale set resources register finalizers processed by the controller during
termination. Uninstalling the controller before runner resources completed finalization
prevented finalizer clearance, causing the namespace to hang terminating indefinitely.
Established: `helm_uninstall()` tears down runner scale sets with `--wait --cascade foreground`
prior to initiating controller uninstallation.

Evidence: `.meta/checks/files/history.py::meta_history_evidence`

### Helm version differences in ignore-not-found flag broke uninstall idempotency

Older Helm versions lacked `--ignore-not-found` support, causing subsequent uninstallation
runs to return non-zero exit codes. Established: `helm_uninstall()` inspects standard
error for `release: not found` to guarantee idempotent teardown across Helm major versions.

Evidence: `.meta/checks/files/history.py::meta_history_evidence`
