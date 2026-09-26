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

### A fallback harness signed two acts as a laptop session it had read about

Both halves of the Trailer came from ordinary environment variables in a shell
the agent controls, and nothing checked that a value found in a run was the
run's own. Coder run 35363666960 hit a Claude quota error and fell back to
Gemini CLI, which put two acts through the channel — `move obviate 571 --by
589` and `post landed 601` — signed `Actor: 687fe62e-cb08-4001-b126-37df9fb0f50c`,
the desktop session that had filed caindy/solorepo#597 and whose id entered the
run only on that Issue's own Trailer, and `Agent: gemini-cli-agent`, a string
that appears in no workflow and in no run log. Established: in a run `actor()`
answers `gha-<GITHUB_RUN_ID>`, GitHub's own name for the run, and refuses an
`ACTOR_SESSION` naming anything else; `agent()` reads `ACTOR_AGENT`, which the
workflow writes before the harness starts, and never `AI_AGENT`, which the
harness overwrites; and `check_pr.mine()` asks `speaker()` rather than resolving
a session of its own (solorepo's DR-233).

Evidence: `.meta/checks/probes/channel/agent.py::agent_probes`

### Workflow run mark reached container shell without credential block

Run 34554434032 read `ACTOR_SESSION=gha-34554434032` beside
`GITHUB_RUN_ID=34554434032` inside the runner, while `actor()` answered the
harness's uuid in the same shell. The credential in that same `env:` block was
omitted (solorepo's DR-134). Established: GitHub's attested `GITHUB_RUN_ID`
takes precedence over session identifiers, and `in_a_run()` evaluates the
attested run before inspecting `ACTOR_SESSION` (solorepo's DR-233).

Evidence: `.meta/checks/probes/channel/actor.py::actor_probes`

### Unwritten stdin pipe hung interactive harness sessions

A plain `sys.stdin.read()` hung indefinitely when executed by an interactive tool
harness where standard input was neither a tty nor closed. Because `isatty()`
returned false, the call blocked indefinitely on an open pipe with no incoming
data. Established: `channel.piped()` polls stdin with `select.select()` against
a timeout, returning an empty string if input is unavailable.

Evidence: `.meta/checks/probes/channel/signing_key.py::signing_key_probes`

### Empty GH_TOKEN string in role environment bypassed missing secret check

When a repository secret was not configured, the GitHub Actions environment
injected `GH_TOKEN` as an empty string. The credential loader treated an empty
string as present, allowing execution to proceed until failing later in `gh` CLI
calls during the first run of `review.yml` (solorepo's #84). Established:
`role_credential()` requires a non-empty `GH_TOKEN` and exits with an explicit
error message if the token value is blank or missing.

Evidence: `.meta/checks/probes/channel/signing_key.py::signing_key_probes`

### Unbounded gh invocations could hang a verb indefinitely

`channel.gh` ran `gh` with no `timeout=`, so a call that stopped answering — a
rate-limited API behind a CLI that refreshes its own auth — left the verb
waiting with no failure to report and no bound to reach (solorepo's #738).
`gh_with_retry` could not help: it retries `CalledProcessError`, and a call that
never returns raises nothing. Established: `channel.gh` bounds each invocation
at `GH_TIMEOUT` and reports a timeout as the failure shape its callers already
handle — `CalledProcessError` under `TIMEOUT_RETURNCODE` where failure is
tolerated, and an exit naming the call and the bound where it is not — so
`gh_with_retry` retries a hang as it retries any other failure. The bound is
the default and not the rule: the `gh stack` calls in `.meta/say/move` pass
`timeout=None`, because a stack rebase or a stack merge can outlast a minute
with nothing wrong and would be abandoned half done. The stand-in the probe
runs against answers an unbounded call successfully, so stripping `timeout=`
from the invocation fails the probe rather than leaving it asserting only that
a timeout, once raised, is handled.

Evidence: `.meta/checks/probes/channel/bound.py::gh_bound_probes`

### Channel signed() hardened against foreign trailer stacking

While historical trailer forgery bypassed `.meta/say/post` via unconfined tool
execution, confining tool execution brings comment operations in-band through the
channel; `channel.signed()` appended the attested trailer block without refusing
foreign trailers, which would stack an attested trailer beneath a caller-provided
trailer (solorepo's #639, solorepo's DR-260).
Established: `channel.signed()` inspects the end of input bodies for trailing trailer blocks;
if a foreign or hand-crafted trailer is present and does not match `channel.trailers()`, it
refuses execution with an explanatory message directing the caller to omit the trailer.

Evidence: `.meta/checks/probes/channel/actor.py::actor_probes`


### The first gh stack call on a machine was spent installing the extension

`gh stack` is an extension rather than part of the CLI, and the CLI installs it
on first use: on a machine that does not hold it, `gh stack merge 793 --squash
--yes` printed `Successfully installed github/gh-stack` on standard error,
exited 0, and never ran the merge. `channel.gh` discards both streams of a call
that exits 0, so nothing recorded it, and the only report was the read-back in
`merge()` saying the pull request was still open. A runner is such a machine
every time it starts, and a session is not, which is why three consecutive runs
of `merge.yml` on 2026-09-21 (35641044270, 35642275328, 35642532412) left
solorepo's #793 open while the same call by hand merged it at once
(solorepo's #797).
Established: `channel.gh` precedes a `gh stack` call with `_stack_extension`,
which reads `gh extension list` and installs `STACK_EXTENSION` where the
machine does not hold it, so the install has no real call left to consume. The
listing read falls back to an empty listing, so a machine that will not answer
what it holds is installed on rather than exited over; the install itself keeps
its hard exit, an install having failed being a stack call that cannot work. And
`echo=True` relays a call's exit status and both of its streams on standard
error, which is how a call that exits 0 having done nothing is named rather
than inferred from what GitHub says afterwards.

Evidence: `.meta/checks/probes/channel/extension.py::gh_stack_extension_probes`


### Antigravity session and agent identity unrecognized in local execution

In local Antigravity sessions every `say` verb exited on `say: the environment
does not say who is speaking`, and exporting `ACTOR_SESSION` by hand moved the
refusal to `say: the environment does not say what is speaking`, because
`ENV_SESSION` recognized only `CLAUDE_CODE_SESSION_ID` beside the generic
`ACTOR_SESSION` and `agent()` had no harness fallback, so signing a commit
required exporting both `ACTOR_SESSION` and `AI_AGENT` by hand
(solorepo's #708). Established: `ENV_SESSION` recognizes
`ANTIGRAVITY_CONVERSATION_ID`, and
`channel.agent()` falls back to `channel.ANTIGRAVITY`, `"antigravity-cli"` —
the name `.meta/say/on`'s `HARNESSES` gives that door (solorepo's DR-245) — when
either name in `ENV_ANTIGRAVITY` is present outside a run.

Evidence: `.meta/checks/probes/channel/actor.py::actor_probes`,
`.meta/checks/probes/channel/agent.py::agent_probes`


### Non-parsing gh invocations discarded stderr on zero-exit commands

In `.meta/lib/gh.py` and `.meta/say/channel.py`, `gh(*args, parse=False)`
returned only stripped `stdout`. When a command such as `gh stack merge` exited
0 having merged nothing (due to in-progress status checks or first-use
extension installation), diagnostic explanations output on `stderr` were
relayed under `echo=True` but discarded from the return value, preventing
callers like `pull_requests.merge` from programmatically inspecting stream
output. Established: `lib_gh.gh` and `channel.gh` support `streams=True` under
non-parsing invocations, returning a `Streams(stdout, stderr)` namedtuple that
preserves both execution streams on zero-exit commands (solorepo's #1054).

Evidence: `.meta/checks/probes/wrappers.py::gh_wrapper_probes`
