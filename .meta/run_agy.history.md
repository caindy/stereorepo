# History

### Immediate session abort on transient Google Code Assist API errors

When executing Antigravity CLI (`agy`) under autonomous coder workers (`coder.yml`), backend API disruptions during eligibility verification (`cloudaicompanion.googleapis.com` / `loadCodeAssistResponse`) emit transient `UNAVAILABLE (code 503)` or `RESOURCE_EXHAUSTED (code 429)` errors before terminal `result: ERROR` events. `run_session()` previously treated all non-SUCCESS terminal events as fatal immediate exits with code 1, aborting fallback passes without attempting recovery. Established: `run_session()` classifies failure modes across unparsed stream lines and structured result payloads, executing bounded exponential backoff with jitter on transient 503 and 429 status codes while preserving fast-fail behavior on fatal `UNAUTHENTICATED (code 401)` errors, with safe subprocess lifecycle and file descriptor cleanup.

Evidence: `.meta/checks/probes/tools/fallback.py::fallback_probes`

### Premature batch turn termination on background command detachment

When executing headless print mode (`agy -p "$PROMPT"`), `agy` interprets an idle root agent as turn finalization, triggering a 5-second exit timeout (`root agent idle; waiting up to 5s for 1 background task(s) ... terminating 1 background task(s) on exit`) when long-running commands detach to background tasks under `run_command`'s 10-second synchronous timeout limit (solorepo's DR-257, solorepo's #715). Established: `run_session()` drives `agy` via `--input-format stream-json --output-format stream-json` over standard I/O, maintaining multi-turn event loop execution while background commands complete, streaming live progress to stdout, and verifying terminal result status.

Evidence: `.meta/checks/probes/tools/fallback.py::fallback_probes`
