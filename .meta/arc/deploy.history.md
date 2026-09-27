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

### Ephemeral runner pod startup incurred 60s Claude Code installation overhead

On every job invocation, `claude-code-action@v1` dynamically downloaded and installed
`@anthropic-ai/claude-code`, introducing over 60 seconds of latency to every review,
coder, and triage attempt. Established: pre-bake `@anthropic-ai/claude-code@2.1.283`
into `.meta/arc/Dockerfile` alongside existing CLI tooling, and configure
`path_to_claude_code_executable` in `.meta/actions/harness/action.yml` to execute the
pre-baked binary directly.

Evidence: `.meta/checks/files/history.py::meta_history_evidence`

### Missing runner container image caused scale set deployment failure

Deploying runner scale sets with an image tag not yet published to GitHub Container Registry (GHCR) or present
in the local cluster containerd cache caused ImagePullBackOff and runner pod startup
failures. Established: `verify_runner_image()` verifies runner image existence across
local Docker cache, cluster containerd cache, and GitHub Container Registry (GHCR) Open Container Initiative (OCI) registry before running
Helm upgrades, failing fast with actionable guidance.

Evidence: `.meta/checks/files/history.py::meta_history_evidence`

