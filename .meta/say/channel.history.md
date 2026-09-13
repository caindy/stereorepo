# History

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Receipt: `<path>::<symbol>`
-->

### Trailer forgotten on pull request comments manufactured solo identity

When signing trailers were typed by hand, an agent omitted the `Actor:`
trailer on a pull request comment. The comment posted under the role's
default account and was read as the human solo, falsely satisfying the
two-party review requirement of A16. Established: the channel composes
and appends the Trailer directly from the environment and refuses to speak
when the environment does not specify who is speaking.

Receipt: `.meta/checks/probes.py::channel_parser_probes`

### Machine role commits were cryptographically unsigned

Commits made by `.meta/say/commit` under the coder Role injected identity
trailers but were cryptographically unsigned at the git object layer, failing
GitHub commit verification and preventing enforcement of strict branch
protection rules. Established: `channel.role_signing_key()` reads the Role's
SSH private key from outside the tree and `say/commit` dynamically configures
git commit signing when speaking under a Role credential.

Receipt: `.meta/checks/probes.py::signing_key_probes`
