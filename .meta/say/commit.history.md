# History

### Ambient prepare-commit-msg hook risked false identity attribution

A git `prepare-commit-msg` hook previously appended attribution trailers by
reading harness variables present in the environment (solorepo's DR-074). This
relied on the solo's local shell happening to lack those variables; had any been
present, commits made by the solo would have carried an Actor trailer falsely
attributing a session he was not running. Established: `.meta/say/commit` explicitly
composes and attaches attribution trailers from verified channel state, ensuring
unmediated commits remain unsigned.

Evidence: `.meta/checks/probes/channel/signing_key.py::signing_key_probes`
