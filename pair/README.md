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

Both seats run the model `--model` names, or the CLI's default. A stage can
name its own with `--backlog-model`, `--flight-check-model`, `--todo-model`
or `--in-progress-model` on `just pair`, `just pair-accept` or
`just pair-resume`, each falling back to `--model`. A seat keeps one session
for the whole Issue while the model stays the same. When a seat's next turn
is in a stage with another model, the seat starts a fresh session on it
(`align_model` in `loop.py`). That costs the seat its conversation, so it
knows the Issue only from the Issue file and the branch. It also costs at
least about 10,500 tokens written to the prompt cache per seat, the floor
for a fresh session measured in `seat-cache-write-per-session`. The cost is
more when the new model has nothing cached yet, because each model has its
own cache. A loop restarted without the same stage flags counts its stages
as running `--model`, and switches seats back to it; one restarted with
another `--model` starts the seats fresh on it too.

The loop's code lives here, outside every portfolio's tree. It was proven in a
spike in booktutor, where the seats read the loop's own code when it sat in the
repository they worked on; a portfolio runs it from a stereorepo checkout so
that cannot happen.

## How an Issue moves

Each turn, a seat is told the Issue file, what the current stage is for
(`prompts/stage-*.md`), and what changed since its last turn. The primary seat
takes the first turn in each stage. A turn ends when the seat's session is
idle: its last `result` is in and no background task it started is still
running, so a gate a seat runs in the background belongs to the turn that
started it. A seat whose turn would end with such a task running is asked,
once, to wait for it or stop it. After every turn the loop commits whatever
the seat left uncommitted, with a `Seat:` trailer. It then keeps the turn's
closing message in the Issue file: it appends the message under a
`## Pair notes` heading, labelled with the seat, the stage and the turn, and
commits it on its own (`Loop.keep_note`). The other seat reads the note in
its next diff. A seat learns nothing else of what the other said, and the
notes land in `issues/done/` with the Issue. Every line is quoted with `> `,
so a note never adds a heading the loop reads, such as `Needs elaboration` or
`The plan`. A code span citing a path and a line comes out as the path
followed by `line` and the number (`board.with_note`): the seat's gate never
saw its note, so a line citation in it would otherwise fail the
`no line citations` step on the next seat's turn. The note is not the seat's
change: a turn whose only change is its note is quiet. The section is the
loop's, too: before it judges a turn, the loop puts the `Pair notes` back as
they stood when the turn began (`Loop.restore_notes`), so a note a seat writes
there itself, or its tidying of earlier notes, is dropped and never counts as
a change. Everything outside the section, a seat's `# Needs elaboration` after
the notes included, stays as the seat left it. The turn's row in
`turns.jsonl` says `"notes_restored": true` when that put anything back. A
grooming pass, a turn that lost its Issue file, and an empty message keep no
note. An implementing seat runs only the gate of each Project its change touches: `just gate meta` always, and
`just gate pair` when it changes `pair/`, for example
(`prompts/stage-in-progress.md`). The loop's own gate runs before the Issue
lands (see the table below), and a failure goes back to the seats with its
output and the targets gated. It gates the Projects whose directories the
branch changes against `main`, a path under none of them counting as `meta`'s
(or, when a Project is named `.`, as that root Project's, unless the board,
`.meta/` or `.meta/bundle.yaml` places it), and every Project of each Product
built from one of them (`touched.py`, stereorepo's DR-303). A change to what a
portfolio receives, an item `.meta/bundle.yaml` marks `managed` or the source
of one it marks `template`, also gates the Project `specialization` where the
structure declares it, which specializes a portfolio and runs that
portfolio's gate (stereorepo's DR-321). When that is every
Project it is the whole `just gate`, and a branch with no change passes
without one. A break that the directories do not show, through a shared tool
or a generated file, lands unchecked: the decision accepts that risk for the
minutes the whole gate cost on every landing. No seat runs the whole
`just gate` in any stage, even when an Issue names it
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
   | `in-progress/` | code outside `issues/` changed, and the gate of what it touches passes after a rebase onto `main` | `desk-check/` for `developer`, otherwise landing; a landing overtaken by another whose rebase then conflicts leaves the Issue in `done/`, and the next run sends it back to `in-progress/`. No turn runs in `done/` |
   | `desk-check/` | `just pair-accept` | landing; `just pair-resume` sends it back to `in-progress/`, as does an accept whose gate fails or whose rebase conflicts. No turn runs in this stage. A Flight here holds nothing: see below |

   If the requirement does not hold, acceptance is cleared and the next turn is
   told what is missing. Where the gate failed, that turn goes to the primary
   seat with the gate's output, whichever seat went quiet last; otherwise it
   goes to the seat that did not take the settling turn.

   A gate that passes with a step that could not run (a `?` line, Article 6)
   is not a pass here, though it is where a person runs the gate. A seat
   cannot supply what the step lacks, such as a Docker daemon, so the loop
   pauses instead, naming each step and why, and keeps the stage, approvals
   and note. Once the developer has supplied it, `just pair` runs that gate
   again before any seat takes a turn. This holds for the gate at the end of
   a stage and for the gate while landing.

   Every gate the loop runs logs a `gated` event (see [the event
   log](#the-event-log)). The gate that closes `in-progress/` also appends a
   line to the end of the Issue file and commits it, whatever the outcome,
   such as "Gated by the supervisor at 11:58: `meta`; 96 steps passed."
   (`Loop.keep_gate`). The seats' sandbox cannot run every step, so a desk
   check or a Flight's brief then shows what the supervisor checked beside
   what the seats could.

   A gate that fails only on `rendered prose` pages the seats cannot write
   pauses the same way. Such pages sit under `.claude/skills/`, which Claude
   Code's sandbox denies the seats (`SANDBOX_DENIED` in `pair/seats.py`), or
   under a path `confinement()` denies. The pause names each page; the
   developer runs `just render` in the worktree outside the sandbox, and
   `just pair` commits that render as the developer's edit, keeping the
   approvals, before it runs the gate again. A gate that fails on anything
   else as well goes back to the seats whole.

   A test that needs a key from the portfolio's `.env` finds none in the
   worktree, since git does not check out an ignored file and the seats may
   not read it (`confinement()`). The gate gets the keys `.env` holds whose
   names `portfolio.gate_keys` in `main`'s `.meta/assertions/structure.yaml`
   lists, in its own process's environment and nowhere else (`Loop.gate_env`
   in `pair/loop.py`). Each such value in the gate's output is replaced by
   its name in angle brackets before a seat reads it (stereorepo's DR-357).
3. **Sending back.** An Issue file that gains a `Needs elaboration` section, or
   a stage that runs past its round cap, sends the Issue to `issues/backlog/` on
   `main` with that section, without its code. It sits out of the running order
   until the developer answers the section and removes it.
4. **Landing.** The loop rebases the branch onto `main`, squashes it into one
   commit that includes the move to `done/`, and fast-forwards `main` in the
   developer's checkout with `--ff-only`, which refuses rather than overwrite local
   edits. The squashed commit sits on the `main` the branch was rebased onto,
   so a commit made on `main` while the gate runs is never reverted: the loop
   rebases onto it and gates again. Where that gate fails, the Issue stays in
   its stage and the next turn goes to the primary seat with the gate's
   output, as for a failed requirement. A Flight that still has a child outside
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
`backlog/` and is not underway. When the other process lands first, the
landing is built again on the new `main`; when git refuses the fast-forward for
any other reason, such as a commit in flight holding the index or `main`'s
ref, it is tried again. Either way it goes round a few times before the loop
pauses with git's error. Only local edits in the developer's checkout to a
path the landing changes pause it at once.

## Using it

| To… | Do… |
|---|---|
| add work | commit `issues/backlog/<slug>.md` to `main` |
| groom | `just groom`, or `just groom --rerank` to rank the whole backlog again |
| run | `just pair`, or `just pair --once`; add `--push` to push `main` after each landing |
| run one Flight | `just pair --flight <slug>` |
| watch | `just pair-status`: what waits on you (a send-back, a desk check or a pause, with its reason), what is underway with its last gate, the running order with each Flight's parts and what holds each item back, and the counts per stage; `just pair-status --json` prints the same state as one JSON object, keyed `waiting`, `underway`, `order`, `to_groom`, `counts`, `sessions` and `turns`, whose fields `status_view` in `loop.py` describes, and which the loop also publishes for a cockpit (see [The published status](#the-published-status)); `tail -f .pair/primary.log .pair/secondary.log`, or `.pair/groom/` for a pass |
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
tokens, cache reads, and the tool calls the harness refused (`denials`, a
count, and `denied`: a refused Bash call's command, or another tool's name),
`events.jsonl` is the event log below, `<seat>.log` and `<seat>.jsonl` are each seat's
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
| `gated` | the supervisor runs the gate, outside the seats' sandbox, on closing `in-progress`, a Flight check or a grooming pass, or on landing after a rebase moved the branch; a branch that changes nothing runs no gate and logs none | `stage` (`in-progress`, `flight-check`, `grooming` or `landing`), `targets` (null for the whole gate), `outcome` (`passed`, `failed` or `could-not-run`), `steps`, `failed` (step names), `could_not_run` (step name to why); closing `in-progress` also appends a `Gated by the supervisor at …` line to the Issue file |
| `paused` | the loop pauses for any other reason | `reason`, `retry` |
| `seat-refused` | the model refuses a seat's message, and the seat restarts with a fresh session | `role`, `error` |
| `seat-model` | a seat's next turn is in a stage that names another model than its session's, and the seat starts a fresh session on it | `role`, `from`, `to` (null for the CLI's default) |
| `stopped` | the loop stops after a Ctrl-C | `reason`, `retry` |
| `empty` | nothing is ripe, or there is nothing to groom; no `slug` | `message` |
| `restarted` | between Issues, the loop working Issues finds its own code (`pair/*.py` and `pair/prompts/`) changed on disk and re-executes itself in place on the same arguments, so the pid in `run.lock` when it started lives on as the `uv` above the new loop; no `slug` | none |
| `ended` | the supervisor process ends; no `slug` | `outcome`, as `pair:` prints it, or `abandoned` (a second Ctrl-C) or `crashed` |

`just pair-watch --until <condition>` prints each event appended after it
starts, one line apiece, and exits 0 when its condition is met: `landed`,
`developer` (`desk-check`, `paused`, `sent-back`, or an `ended` whose outcome
is `desk-check` or `paused`), or `flight <slug>` (a `desk-check` event for
that Flight). It watches the supervisors whose pid is in `run.lock` or
`groom.lock` when it starts. It exits 12 once each of them has logged
`ended` or died without a match, and 13 at once if none is running. A watcher
therefore never outlives the loop it watches. A restart logs no `ended` and
leaves the watched pid alive, so a watcher follows the loop across it; the restarted loop
takes `run.lock` again, or exits 11 if another loop took it in between.
`uv run` passes a Ctrl-C on to the loop as more than one SIGINT, so the loop
counts every SIGINT within half a second of the last Ctrl-C it counted as
that same Ctrl-C.
Answering a Flight's desk check
with `just pair-accept <slug>` or `just pair-resume <slug>` holds no lock and
logs nothing.

The loop's tests run as the `pair` Project's gate, `just gate pair`, against
fake seats over a temporary git repository. The same gate then runs ruff over
`pair/` with `.meta/ruff.toml`, so a `# noqa` written here is enforced.

## The published status

A cockpit, one view across every repository the developer runs a pair loop
in, reads each loop's status from `~/.pairs/<basename>.json`, where
`<basename>` is the last component of the developer's checkout; the
environment variable `PAIRS_DIR` names another directory. The file is one
JSON object: `repo`, the checkout's absolute path, which tells apart two
checkouts with the same basename, and then the keys of `just pair-status
--json` (`waiting`, `underway`, `order`, `to_groom`, `counts`, `sessions`,
`turns`), whose fields `status_view` in `loop.py` describes.

Either loop rewrites it whenever its state changes: when it saves or clears
`state.json`, when it logs an event, and when a Flight's desk check is
answered. Each write goes to a temporary file in the same directory and is
renamed into place, so a reader never sees half of it. The file holds
nothing the board, `.pair/` and git do not, and the loop never reads it
back. A write that fails is reported on the loop's output and does not stop
it.
