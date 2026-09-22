---
slug: door
context: solorepo
synonyms:
  - workflow door
  - reading door
  - take door
minted: 2026-09-22
---

# Door

**Door** is the seam at which a loop workflow admits a Role's run: the event it
fires on, what the run reads and decides before its harness session starts,
and what it reads and writes after the session ends (solorepo's DR-264).

Each workflow of the [[dev-loop]] is a door. `triage.yml` is the reviewer's
reading door, fired by `challenge` landing on an [[issue]] with no level or by a
level taken off one (solorepo's DR-230). `review.yml` is the reviewer's review
door, fired by a review requested of the reviewer's account and by a push
while one stands. `coder.yml` is the coder's door, fired by a level a loop
takes landing on a [[challenge]] and by the reviewer's verdict, with four
passes behind it: the take, the rebase, the answer to a request for changes,
and the promotion on approval (solorepo's DR-159).

## The Two Phases

Around the harness session every door has two phases, and they are the whole
of what the door does that is not the session. *Before*, the door decides
whether the delivery is still the Role's, since an event's payload is frozen at
delivery and the Issue may have moved while the run waited; chooses the
harness by the Challenge's own label; and writes under `.review/` what the
session will read, because the session's reading hook runs only the programs
`.meta/lib/worktree_only/grammar.py` lists, and `gh issue` is not among them.
*After*, the door reads what the session left, since the
harness reports success when the model's turn ends and a turn ends without a
verdict as readily as with one (solorepo's DR-122): a level landed, a verdict
given, a pull request handed off. What it finds missing it says out loud, and a
run that could not finish hands its Challenge back.

The phases are typed as one program of the channel, `.meta/say/on --role
<role> <role> <phase> <n>`, one verb per Role and the flag naming the
credential that reads, so that a probe can hold every decision a door makes
and the YAML keeps only its triggers, concurrency, permissions, credentials,
and the harness steps. The number says which of a Role's doors is meant: the
reviewer reads a Challenge and reviews a pull request. What only the workflow
knows after the session, such as which harness step ran it and where its
transcript is, reaches the door's *after* as flags, so the run log says where
every number the door judged by came from.

The review door's *before* also chooses the depth, by `.meta/depth.py`
(solorepo's DR-188), and writes what the session reads: the diff as a file,
the head's copies of the trunk paths under `.review/head/`, the trunk paths
being the control-plane paths the run replaces with `origin/main`'s copies
before the session so that what runs is trunk's and the pull request's version
is read there without being run (solorepo's DR-217), and the constraints
every agent the review spawns is bound by, filled from
`.meta/templates/constraints.md`. Its *after* counts the reviewer's verdicts
against the count *before* took (solorepo's DR-122), reads the evidence the
reading hook left, and holds the transcript to the fan-out ceiling
(solorepo's DR-191).

The coder's door takes which pass the event opened as a flag, since the event,
the review's state and the dispatch's inputs are the workflow's to read, and
its *before* finds the pull request a second pass answers and checks its branch
out, chooses the harness by label and input, reads whether the delivery is
still the loop's through the take door (solorepo's DR-142), chooses the depth
by the pass and the level, and on approval counts the threads held for
promotion.

## Doors and the Reconciler

A door is edge-triggered: it fires once, on its event, and a delivery that is
dropped, or a run that ends without answering, is lost to it. The reconciler
of solorepo's DR-264 is the complement, reading every open Issue and pull
request on the clock and re-delivering what a door missed, so that the doors
are the accelerator and the clock is the floor.

---

**See also:** [[dev-loop]], [[pr-first]], [[challenge]], [[issue]]
