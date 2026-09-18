# History

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Evidence: `<path>::<symbol>`
-->

### Trailer forgotten on pull request comments manufactured solo identity

When signing trailers were typed by hand, an agent omitted the `Actor:`
trailer on a pull request comment. The comment posted under the role's
default account and was read as the human solo, falsely satisfying the
two-party review requirement of A16. Established: the channel composes
and appends the Trailer directly from the environment and refuses to speak
when the environment does not specify who is speaking.

Evidence: `.meta/checks/probes/channel/parser.py::channel_parser_probes`

### Machine role commits were cryptographically unsigned

Commits made by `.meta/say/commit` under the coder Role injected identity
trailers but were cryptographically unsigned at the git object layer, failing
GitHub commit verification and preventing enforcement of strict branch
protection rules. Established: `channel.role_signing_key()` reads the Role's
SSH private key from outside the tree and `say/commit` dynamically configures
git commit signing when speaking under a Role credential.

Evidence: `.meta/checks/probes/channel/signing_key.py::signing_key_probes`

### Verdict flags bound to the wrong verb by a reused parser variable

Each subparser in `post` and `move` is built by reassigning one loop variable,
so the mutually exclusive verdict group added after the variable had moved on
landed on `issue-comment` rather than `review` (solorepo's #95), one verb over
from the shape solorepo's #91 had found. Argparse never objects to a verb owning
another verb's argument, and nothing parsed a verb without also calling `gh`, so
nothing noticed until a review was posted. Established: every program exposes
`build_parser()` so its parser is checked without dispatching, and
`channel_parser_probes` parses every verb's flags, refuses every line the
withdrawn nouns allowed (solorepo's DR-116), and holds each verb to the one
program the table says (solorepo's DR-117).

Evidence: `.meta/checks/probes/channel/parser.py::channel_parser_probes`

### Harness session id shadowed the run's workload identity in the Trailer

Inside a container run the harness sets `CLAUDE_CODE_SESSION_ID` to a uuid and
`coder.yml` sets `ACTOR_SESSION` to `gha-<run id>`, the workload identity the
Trailer is meant to carry rather than the account's (solorepo's DR-086); `actor()` took the first set of the two in
`ENV_SESSION`'s order, so every run's `Actor:` Trailer read a uuid
indistinguishable from a laptop session's, and `check_pr.mine()` resolved the
session the same wrong way, so the two agreed only while both were wrong
(solorepo's #285). Established: `ACTOR_SESSION` wins in both readers when it
carries `RUN_MARK` and `CLAUDE_CODE_SESSION_ID` wins otherwise, the mark winning
rather than mere presence (solorepo's DR-148); with neither set, `actor()`
refuses and `mine()` answers `False` for any Trailer (solorepo's #301).

Evidence: `.meta/checks/probes/channel/actor.py::actor_probes`
