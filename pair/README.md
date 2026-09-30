# The pair loop

The pair loop carries one Issue at a time from `issues/backlog/` on `main` to
`main`. Two seats, each one long-lived `claude -p` process in stream-json mode,
take turns in one worktree, `worktrees/pair`, on a branch named `pair/<slug>`.
A deterministic supervisor, `loop.py`, decides every transition from what it can
observe: where the Issue file sits, whether a turn changed anything, and the
exit code of `just gate`. The seats are never told a protocol exists. A seat
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
the seat left uncommitted, with a `Seat:` trailer.

1. **Acceptance.** A turn that changes nothing is a quiet turn: that seat
   accepts the state it found. A turn that changes something makes its author
   the only seat that has accepted the new state. An edit the developer makes
   between turns clears acceptance for both.
2. **Advancing.** When both seats have accepted the same state, the stage
   advances with `git mv` if its requirement holds:

   | Stage | Requirement | Next |
   |---|---|---|
   | `backlog/` | `difficulty` is set; a `hard` Issue has children | `todo/`; for `hard`, landing the children, with the parent left in `backlog/` as a Flight |
   | Flight check (file stays in `backlog/`) | a new child for each gap, or a new `## Desk-check brief` section, and nothing outside `issues/` changed; after desk-check notes, a child for each note listed in one new `## Desk-check children` section, and no brief | landing; the Flight goes to `desk-check/` unless a child left it waiting |
   | `todo/` | a `## The plan` section | `in-progress/` |
   | `in-progress/` | code outside `issues/` changed, and `just gate` passes after a rebase onto `main` | `desk-check/` for `developer`, otherwise landing |
   | `desk-check/` | `just pair-accept` | landing; `just pair-resume` sends it back to `in-progress/`. A Flight here holds nothing: see below |

   If the requirement does not hold, acceptance is cleared and the next turn is
   told what is missing, with the gate's output where the gate failed.
3. **Sending back.** An Issue file that gains a `Needs elaboration` section, or
   a stage that runs past its round cap, sends the Issue to `issues/backlog/` on
   `main` with that section, without its code. It sits out of the running order
   until the developer answers the section and removes it.
4. **Landing.** The loop rebases the branch onto `main`, squashes it into one
   commit that includes the move to `done/`, and fast-forwards `main` in the
   developer's checkout with `--ff-only`, which refuses rather than overwrite local
   edits. A Flight that still has a child outside `done/` lands without the
   move, and keeps its place in `ORDER`.

An Issue that other Issues name in `parent:` is a Flight. It is not ripe while
any of its children is outside `done/`. Once the last one lands, the loop takes
the Flight through the Flight check (`prompts/stage-flight-check.md`) instead of
its backlog stage: the seats check its "Done when" end to end on `main`, and
either write each gap as a new child, which puts the Flight back to waiting, or
write a desk-check brief into the Flight file, which lands it in `desk-check/`
and out of `ORDER`.

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
  `backlog/` and the slug put first in `ORDER`. The Flight is then ripe, and
  its next Flight check writes each note as a child and lists their slugs in a
  `## Desk-check children` section, which marks the notes answered. Once those
  children land, the check after them writes a new brief, and the Flight comes
  back to `desk-check/`. Each round's brief, notes and children stay in the
  file.

Both commit only the Flight file and `ORDER`, and refuse, changing nothing, a
slug that is not a Flight in `desk-check/`, a checkout off `main`, and a resume
with no notes after the latest brief. A commit that lands on `main` in the
moment the loop is landing makes the loop pause; run it again.

A seat that crashes is restarted once from its session id. A supervisor that
is killed restarts the turn being worked on the same session.

## Grooming the backlog

`just pair` takes the Issues in the running order as it stands, and never
grooms. Grooming is a separate command, `just groom`. An Issue is groomed when
its front matter sets a valid `difficulty` and it has no `Needs elaboration`
section, so an Issue the developer writes with a `difficulty` counts as groomed,
and deleting an Issue's `difficulty` asks for it to be groomed again. An Issue
no pass has groomed is groomed by its own backlog stage when the loop takes it.

`just groom` takes up the backlog Issues on `main` that are not groomed and
have no `Needs elaboration` section, and runs a pass over them on the branch
`pair/grooming`, from `prompts/stage-grooming.md`. The seats groom each one as
the backlog stage grooms one, and place it below the `# groomed below` line of
`issues/backlog/ORDER` without moving the Issues already there
(`prompts/grooming-place.md`). `just groom --rerank` ranks the whole order
below the marker again instead (`prompts/grooming-rerank.md`). Either way the
developer's lines above the marker stay as they are.

The pass takes turns and ends the way a stage does. Its requirement is that
each Issue it took up, and each part it wrote, has a `difficulty`, that each
such `hard` Issue has children, that `ORDER` names every Issue the developer
has not placed, that without `--rerank` the Issues already ranked keep their
relative order, that nothing was deleted, and that `just gate` passes. The loop
then lands the pass as one commit, `Groom the backlog`; each split `hard` Issue
stays in `backlog/` and in `ORDER` as a Flight. A `Needs elaboration` section written in a pass parks that
Issue and does not end the pass. A pass that runs past its round cap pauses,
and `just groom` gives it another. With nothing to groom and nothing to place,
`just groom` says so and exits.

A pass and an Issue share `worktrees/pair`, so one waits for the other:
`just groom` refuses while an Issue is underway, and `just pair` refuses while
a pass is, saying to finish it with `just groom`.

## Using it

| To… | Do… |
|---|---|
| add work | commit `issues/backlog/<slug>.md` to `main` |
| groom | `just groom`, or `just groom --rerank` to rank the whole backlog again |
| run | `just pair`, or `just pair --once`; add `--push` to push `main` after each landing |
| watch | `just pair-status`; `tail -f .pair/primary.log .pair/secondary.log` |
| steer an Issue underway | edit files in `worktrees/pair` between turns; the next seat sees the change |
| take over a seat | Ctrl-C (the current turn finishes first), then `cd worktrees/pair && claude --resume <id>` with the id `just pair-status` prints; `just pair` again afterwards |
| desk check | test in `worktrees/pair`, then `just pair-accept`, or write notes in the Issue file and `just pair-resume` |
| desk-check a Flight | read its brief in `issues/desk-check/<slug>.md`, then `just pair-accept <slug>`, or write `## Desk-check notes` in it and `just pair-resume <slug>` |

In a portfolio, run the same commands through the script, from the portfolio's
root: `uv run --script <stereorepo>/pair/pair.py run`, `groom`, `status`,
`accept` or `resume`, each with a Flight's slug where it has one.

Runtime state lives in `.pair/` at the repository root, which is gitignored:
`state.json` is the Issue or grooming pass underway, `turns.jsonl` has one
row per turn with tokens and cache reads, and `<seat>.log` and `<seat>.jsonl` are each seat's
output.

The loop's tests run as the `pair` Project's gate, `just gate pair`, against
fake seats over a temporary git repository.
