# History

### Premature batch turn termination on background command detachment

When executing headless print mode (`agy -p "$PROMPT"`), `agy` interprets an idle root agent as turn finalization, triggering a 5-second exit timeout (`root agent idle; waiting up to 5s for 1 background task(s) ... terminating 1 background task(s) on exit`) when long-running commands detach to background tasks under `run_command`'s 10-second synchronous timeout limit (solorepo's DR-257, solorepo's #715). Established: `run_session()` drives `agy` via `--input-format stream-json --output-format stream-json` over standard I/O, maintaining multi-turn event loop execution while background commands complete, streaming live progress to stdout, and verifying terminal result status.

Evidence: `.meta/checks/probes/tools/fallback.py::fallback_probes`
