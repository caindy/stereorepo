# The pair loop

The pair loop carries one Issue at a time from `issues/backlog/` on `main` to
`main`. Two seats, each one long-lived `claude -p` process in stream-json mode,
take turns in one worktree, `worktrees/pair`, on a branch named `pair/<slug>`.
A deterministic supervisor, `loop.py`, decides every transition from what it can
observe: where the Issue file sits, whether a turn changed anything, and the
exit code of `just gate` over what the branch touches. The seats are never told a protocol exists.
Starting an Issue moves its file from `issues/backlog/` to `issues/underway/` in
a commit of its own on `main`, fast-forwarded into the developer's checkout
before the first turn, and the branch starts from that commit. If the
fast-forward is refused, the loop pauses and the Issue stays in `backlog/`. A
supervisor restarted without its state takes up the Issue it finds in
`underway/`, rather than moving another. A seat
loads the repository's own settings, `CLAUDE.md` and skills, and nothing from
the developer's machine (`CONTEXT` in `seats.py`), so its context is the
repository's and a fresh session re-uses most of the cached prompt.

The loop's code lives here, outside every portfolio's tree. It was proven in a
spike in booktutor, where the seats read the loop's own code when it sat in the
repository they worked on; a portfolio runs it from a stereorepo checkout so
that cannot happen.

## How an Issue moves

Each turn, a seat is told the Issue file, what the current stage is for
(`prompts/stage-*.md`), and what changed since its last turn. The primary seat
takes the first turn in each stage. After every turn the loop commits whatever
the seat left uncommitted, with a `Seat:` trailer. An implementing seat runs
only the gate of each Project its change touches: `just gate meta` always, and
`just gate pair` when it changes `pair/`, for example
(`prompts/stage-in-progress.md`). The loop's own gate runs before the Issue
lands (see the table below), and a failure goes back to the seats with its
output and the targets gated. It gates the Projects whose directories the
branch changes against `main`, a path under none of them counting as `meta`'s,
and every Project of each Product built from one of them (`touched.py`,
stereorepo's DR-303). When that is every Project it is the whole `just gate`,
and a branch with no change passes without one. A break that the directories
do not show, through a shared tool or a generated file, lands unchecked: the
decision accepts that risk for the minutes the whole gate cost on every
landing. No seat runs the whole `just gate` in any stage, even when an Issue names it
(`prompts/primary.md`, `prompts/secondary.md`), and grooming states how an
Issue will be known done in behaviour and tests, never as a gate
(`prompts/stage-backlog.md`, `prompts/stage-grooming.md`). A seat working
on speed measures once before its change and once after, and runs no
repeated or side-by-side comparisons (`prompts/primary.md`,
`prompts/secondary.md`).

1. **Acceptance.** A turn that changes nothing is a quiet turn: that seat
   accepts the state it found. A turn that changes something makes its author
   the only seat that has accepted the new state. An edit the developer makes
   between turns clears acceptance for both.
2. **Advancing.** When both seats have accepted the same state, the stage
   advances with `git mv` if its requirement holds:

   | Stage | Requirement | Next |
   |---|---|---|
   | backlog (file in `underway/`) | `difficulty` is set; a `hard` Issue has children | `todo/`; for `hard`, landing the children, with the parent moved back to `backlog/` as a Flight |
   | Flight check (file in `underway/`) | a new child for each gap, or a new `## Desk-check brief` section, and nothing outside `issues/` changed; after desk-check notes, a child for each note listed in one new `## Desk-check children` section, and no brief | landing; the Flight goes to `desk-check/` unless a child left it waiting |
   | `todo/` | a `## The plan` section | `in-progress/` |
   | `in-progress/` | code outside `issues/` changed, and the gate of what it touches passes after a rebase onto `main` | `desk-check/` for `developer`, otherwise landing |
   | `desk-check/` | `just pair-accept` | landing; `just pair-resume` sends it back to `in-progress/`, as does an accept whose gate fails or whose rebase conflicts. No turn runs in this stage. A Flight here holds nothing: see below |

   If the requirement does not hold, acceptance is cleared and the next turn is
   told what is missing. Where the gate failed, that turn goes to the primary
   seat with the gate's output, whichever seat went quiet last; otherwise it
   goes to the seat that did not take the settling turn.
3. **Sending back.** An Issue file that gains a `Needs elaboration` section, or
   a stage that runs past its round cap, sends the Issue to `issues/backlog/` on
   `main` with that section, without its code. It sits out of the running order
   until the developer answers the section and removes it.
4. **Landing.** The loop rebases the branch onto `main`, squashes it into one
   commit that includes the move to `done/`, and fast-forwards `main` in the
   developer's checkout with `--ff-only`, which refuses rather than overwrite local
   edits. The squashed commit sits on the `main` the branch was rebased onto,
   so a commit made on `main` while the gate runs is never reverted: the loop
   rebases onto it and gates again. A Flight that still has a child outside
   `done/` lands back in `backlog/` instead, and keeps its place in `ORDER`.

An Issue that other Issues name in `parent:` is a Flight. It is not ripe while
any of its children is outside `done/`. Once the last one lands, the loop takes
the Flight through the Flight check (`prompts/stage-flight-check.md`) instead of
its backlog stage: the seats check its "Done when" end to end on `main`, and
either write each gap as a new child, which puts the Flight back to waiting, or
write a desk-check brief into the Flight file, which lands it in `desk-check/`
and out of `ORDER`. A ripe Flight is taken ahead of the running order, before
any other ripe Issue, so it is checked as soon as its last child lands; among
ripe Flights the running order decides.

`ORDER` ranks Flights and standalone Issues, never their parts: the developer
decides which unit of value comes next, and the parts' `waits_on` already
settles their order. A part, an Issue whose `parent:` names a Flight in
`backlog/`, has no line of its own. When the running order reaches a Flight's
line, the loop takes the Flight's parts, each after any sibling its `waits_on`
names and otherwise in filename order, a part that is a Flight expanded the
same way, and then the Flight's check. A Flight whose parts all wait on an
Issue outside it is passed over, as a waiting Issue is, rather than pulling
that Issue forward. A part whose Flight has left `backlog/`, for `done/` or a
desk check, stands alone and keeps a line of its own. An unlisted Flight runs,
parts and all, where its filename falls among the unlisted slugs. The
`board order` gate step refuses a line naming a part.

The loop leaves how a product is built and deployed to the repository's
`justfile`, and runs two recipes where it defines them. `just setup` provisions
a fresh `worktrees/pair`, so the gate tests the branch in its own environment.
`just deliver` runs in the worktree just before a Flight goes to `desk-check/`,
and delivers what `main` holds, for example a redeployment to a UAT
environment, so the developer desk-checks the Flight where it runs. A passing
delivery adds a `Delivered by` line after the brief. A failing one pauses the
loop with the tail of its output and leaves the Flight where it was; running
the loop again delivers again. Each desk-check round delivers once.

A Flight's desk check does not hold the loop, because its parts are already on
`main`; the loop goes on to the next ripe Issue. The developer answers it in
their own checkout, on `main`, while the loop runs:

- `just pair-accept <slug>` moves the Flight to `done/` in one commit.
- To send it back, write a `## Desk-check notes` section at the end of the
  Flight file, one top-level bullet per note, then run
  `just pair-resume <slug>`. One commit carries the notes, the move to
  `backlog/` and the slug put first in `ORDER`, unless the Flight is itself a
  part of a Flight in `backlog/`, which gives it no line; the same commit drops
  any line naming one of its parts. The Flight is then ripe, and
  its next Flight check writes each note as a child and lists their slugs in a
  `## Desk-check children` section, which marks the notes answered. Once those
  children land, the check after them writes a new brief, and the Flight comes
  back to `desk-check/`. Each round's brief, notes and children stay in the
  file.

Both commit only the Flight file and `ORDER`, and refuse, changing nothing, a
slug that is not a Flight in `desk-check/`, a checkout off `main`, and a resume
with no notes after the latest brief. A commit that lands on `main` in the
moment the loop is landing makes the loop pause; run it again.

`just pair --flight <slug>` runs one Flight: it works only that Flight and the
Issues below it (a child that is itself a Flight, with its own children), in
running order with a ripe Flight first, whatever else is ripe, and stops when
the Flight reaches `desk-check/`. Children written during the run, by a split
or a Flight check, join it. It also stops where `just pair` would, for a pause
or a `developer` Issue's desk check, and when nothing in the Flight is ripe,
naming any Flight below it that waits on its desk check. It refuses a slug
that is not a Flight in `backlog/` or `underway/`, a Flight already in `desk-check/`, and a
run while an Issue outside the Flight is underway.

A seat that crashes is restarted once from its session id. A supervisor that
is killed restarts the turn being worked on the same session.

A seat whose message the model refuses is restarted once with a fresh session
and the plain turn message, because the refused message stays in the old
session's history and resuming it would be refused again. A restart that is
refused, whether the first failure was a refusal or a crash, pauses the loop
with `the <role> seat was refused` and keeps no session for that seat, so the
next run starts it fresh. Such a pause points at the seat's instructions or
the Issue, not at the machine.

## Grooming the backlog

`just pair` takes the Issues in the running order as it stands, a ripe Flight
first, and never grooms. Grooming is a separate command, `just groom`. An Issue is groomed when
its front matter sets a valid `difficulty` and it has no `Needs elaboration`
section, so an Issue the developer writes with a `difficulty` counts as groomed,
and deleting an Issue's `difficulty` asks for it to be groomed again. An Issue
no pass has groomed is groomed by its own backlog stage when the loop takes it.

`just groom` takes up the backlog Issues on `main` that are not groomed and
have no `Needs elaboration` section, and runs a pass over them on the branch
`pair/grooming`, from `prompts/stage-grooming.md`. The seats groom each one as
the backlog stage grooms one, and place each Flight and standalone Issue below
the `# groomed below` line of `issues/backlog/ORDER` without moving the Issues
already there (`prompts/grooming-place.md`). Splitting a `hard` Issue keeps
its line, on whichever side of the marker it stood, and that line now stands
for the Flight; its parts get none. `just groom --rerank` ranks the whole order
below the marker again instead (`prompts/grooming-rerank.md`). Either way the
developer's lines above the marker stay as they are.

The pass takes turns and ends the way a stage does. Its requirement is that
each Issue it took up, and each part it wrote, has a `difficulty`, that each
such `hard` Issue has children, that `ORDER` names every Flight and standalone
Issue the developer has not placed and no part, that without `--rerank` the Issues already ranked keep their
relative order, that nothing was deleted, and that the gate of what the pass changed passes. The loop
then lands the pass as one commit, `Groom the backlog`; each split `hard` Issue
stays in `backlog/` and in `ORDER` as a Flight. A `Needs elaboration` section written in a pass parks that
Issue and does not end the pass. A pass that runs past its round cap pauses,
and `just groom` gives it another. With nothing to groom and nothing to place,
`just groom` says so and exits.

A pass runs in its own worktree, `worktrees/groom`, and holds its own lock,
`.pair/groom.lock`, so `just groom` and `just pair` run at once; two passes
cannot, nor two Issues. The Issue underway is in `underway/`, where no pass
takes it up, and the loop does not start an Issue that a pass underway, paused
or not, took up. Whichever of the two lands second rebases onto the other. A
pass is squashed before it rebases, and keeps only its changes under
`issues/backlog/`. A conflict in `ORDER` alone does not stop a landing: the
loop rebuilds the file from `main`'s, with the pass's placements put back
after the line they followed, and without the line of any slug that has left
`backlog/` and is not underway. When the other process lands first, or holds
the index of the developer's checkout, the landing is tried again on the new
`main`, a few times, before the loop pauses; local edits in the developer's
checkout still pause it at once.

## Using it

| To… | Do… |
|---|---|
| add work | commit `issues/backlog/<slug>.md` to `main` |
| groom | `just groom`, or `just groom --rerank` to rank the whole backlog again |
| run | `just pair`, or `just pair --once`; add `--push` to push `main` after each landing |
| run one Flight | `just pair --flight <slug>` |
| watch | `just pair-status`: what waits on you (a send-back, a desk check or a pause, with its reason), what is underway, the running order with each Flight's parts and what holds each item back, and the counts per stage; `just pair-status --json` prints the same state as one JSON object, keyed `waiting`, `underway`, `order`, `to_groom`, `counts`, `sessions` and `turns`, whose fields `status_view` in `loop.py` describes; `tail -f .pair/primary.log .pair/secondary.log`, or `.pair/groom/` for a pass |
| wait for the loop | `just pair-watch --until landed`, `--until developer` (a desk check, a pause or a send-back) or `--until flight <slug>` (that Flight reaches `desk-check/`); see [The event log](#the-event-log) |
| steer an Issue or a pass underway | edit files in `worktrees/pair`, or `worktrees/groom` for a pass, between turns; the next seat sees the change |
| take over a seat | Ctrl-C (the current turn finishes first), then `cd worktrees/pair && claude --resume <id>` (`worktrees/groom` for a pass) with the id `just pair-status` prints; `just pair` or `just groom` again afterwards |
| desk check | test in `worktrees/pair`, then `just pair-accept`, or write notes in the Issue file and `just pair-resume` |
| desk-check a Flight | read its brief in `issues/desk-check/<slug>.md`, then `just pair-accept <slug>`, or write `## Desk-check notes` in it and `just pair-resume <slug>` |

In a portfolio, run the same commands through the script, from the portfolio's
root: `uv run --script <stereorepo>/pair/pair.py run`, `groom`, `status` (or
`status --json`), `accept`, `resume` or `watch`, each with a Flight's slug
where it has one.

### Exit codes

`just pair`, `just groom`, `just pair-accept` and `just pair-resume` print
their outcome as `pair: <outcome>` and exit with its code, so a session
driving the loop reads the code instead of the line.

| Code | Outcome | Meaning |
|---|---|---|
| 0 | `landed`, `groomed`, `accepted`, `resumed` | done; nothing more is needed |
| 3 | `desk-check` | an Issue or a Flight waits for your desk check |
| 4 | `paused` | the loop paused; `just pair-status` says why |
| 5 | `stopped` | the loop stopped after a Ctrl-C |
| 6 | `kicked` | the Issue was sent back to `backlog/` (`run --once`, `accept` or `resume`; a plain `run` takes up the next Issue instead) |
| 7 | `empty` | nothing in the backlog (or the Flight) is ripe |
| 8 | `nothing` | there is nothing to groom |
| 9 | `refused` | `--flight` names a Flight that cannot be run from here |
| 10 | `none` | there is no desk check to answer |
| 11 | | another loop or grooming pass holds the lock |
| 12 | | `just pair-watch`: every loop it watched ended without meeting its condition |
| 13 | | `just pair-watch`: no loop or grooming pass is running |

`just pair-watch` exits 0, 12 or 13; see [The event log](#the-event-log).
1 is a crash (an uncaught exception) and 2 a usage error.

Runtime state lives in `.pair/` at the repository root, which is gitignored:
`state.json` is the Issue underway, `turns.jsonl` has one row per turn with
tokens and cache reads, `events.jsonl` is the event log below, `<seat>.log` and `<seat>.jsonl` are each seat's
output, and `run.lock` holds the pid of the loop working Issues. A grooming
pass keeps the same files in `.pair/groom/`, and its lock in
`.pair/groom.lock`. A pass left paused in `.pair/state.json` by a loop older
than this layout is dropped by the next `just pair` or `just groom`.

## The event log

The supervisor appends one JSON object per line to `.pair/events.jsonl` for
each transition between turns, so a session running the loop learns what
happened without scraping its printed lines. The loop working Issues and a
grooming pass write the one file. The log holds nothing that the board,
`.pair/` and git do not; it records when things happened.

Every event carries `at` (local time, as in `turns.jsonl`), `kind`, `loop`
(`pair` or `groom`) and, where there is one, `slug` (`grooming` for a pass).

| `kind` | When | Other fields |
|---|---|---|
| `started` | an Issue or a grooming pass starts on its branch | `stage` |
| `moved` | the Issue's file moves from one stage to the next on its branch | `from`, `to` |
| `landed` | an Issue's branch lands on `main` | `sha`, and `stage`: where the file now sits (`done`, `desk-check` for a Flight, `backlog` for a split) |
| `groomed` | a grooming pass lands | `sha` |
| `sent-back` | an Issue lands back in `backlog/` with `Needs elaboration` | `reason`, null when a seat wrote the section |
| `desk-check` | a `developer` Issue waits for its desk check, or a Flight has landed in `desk-check/` | `stage` |
| `paused` | the loop pauses for any other reason | `reason`, `retry` |
| `seat-refused` | the model refuses a seat's message, and the seat restarts with a fresh session | `role`, `error` |
| `stopped` | the loop stops after a Ctrl-C | `reason`, `retry` |
| `empty` | nothing is ripe, or there is nothing to groom; no `slug` | `message` |
| `ended` | the supervisor process ends; no `slug` | `outcome`, as `pair:` prints it, or `abandoned` (a second Ctrl-C) or `crashed` |

`just pair-watch --until <condition>` prints each event appended after it
starts, one line apiece, and exits 0 when its condition is met: `landed`,
`developer` (`desk-check`, `paused`, `sent-back`, or an `ended` whose outcome
is `desk-check` or `paused`), or `flight <slug>` (a `desk-check` event for
that Flight). It watches the supervisors whose pid is in `run.lock` or
`groom.lock` when it starts. It exits 12 once each of them has logged
`ended` or died without a match, and 13 at once if none is running. A watcher
therefore never outlives the loop it watches. Answering a Flight's desk check
with `just pair-accept <slug>` or `just pair-resume <slug>` holds no lock and
logs nothing.

The loop's tests run as the `pair` Project's gate, `just gate pair`, against
fake seats over a temporary git repository.
