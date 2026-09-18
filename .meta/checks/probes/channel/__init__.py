"""The channel under `.meta/say/`, run against the calls it exists to refuse (solorepo's DR-209).

Its parsers and the verb table they are read against, a Decision's status as
`move` reads it, `claim` at each level from a run and from a session, the
refusals that keep an Issue's close an answer rather than a tidy-up, the
refusals that keep one Challenge to one Issue, the level a run may land and
the one `reread` takes off, who the Actor is, where a
Role's signing key is, the numbers `decision numbering` reads as reserved, and
a verdict held to the head its run read. Not invariants over the record: each
probe loads the channel and runs it, which is why the probes are a package of
their own rather than steps beside the checks over assertions
(solorepo's DR-150). One module per probe, imported in the order the steps
report in (solorepo's DR-218).
"""
import checks.probes.channel.parser  # noqa: I001  # reason: registration order is deliberate
import checks.probes.channel.status
import checks.probes.channel.table
import checks.probes.channel.layer
import checks.probes.channel.claim
import checks.probes.channel.obviate
import checks.probes.channel.filing
import checks.probes.channel.level
import checks.probes.channel.triage
import checks.probes.channel.actor
import checks.probes.channel.signing_key
import checks.probes.channel.reservation
import checks.probes.channel.verdict  # noqa: F401  # reason: registers check steps
