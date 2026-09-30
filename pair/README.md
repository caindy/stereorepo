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
   | `backlog/` | `difficulty` is set | `todo/`; for `hard`, the child Issues land in `backlog/` and the parent goes to `done/` |
   | `todo/` | a `## The plan` section | `in-progress/` |
   | `in-progress/` | code outside `issues/` changed, and `just gate` passes after a rebase onto `main` | `desk-check/` for `developer`, otherwise landing |
   | `desk-check/` | `just pair-accept` | landing; `just pair-resume` sends it back to `in-progress/` |

   If the requirement does not hold, acceptance is cleared and the next turn is
   told what is missing, with the gate's output where the gate failed.
3. **Sending back.** An Issue file that gains a `Needs elaboration` section, or
   a stage that runs past its round cap, sends the Issue to `issues/backlog/` on
   `main` with that section, without its code. It sits out of the running order
   until the developer answers the section and removes it.
4. **Landing.** The loop rebases the branch onto `main`, squashes it into one
   commit that includes the move to `done/`, and fast-forwards `main` in the
   developer's checkout with `--ff-only`, which refuses rather than overwrite local
   edits.

A seat that crashes is restarted once from its session id. A supervisor that
is killed restarts the turn in flight on the same session.

## Using it

| To… | Do… |
|---|---|
| add work | commit `issues/backlog/<slug>.md` to `main` |
| run | `just pair`, or `just pair --once`; add `--push` to push `main` after each landing |
| watch | `just pair-status`; `tail -f .pair/primary.log .pair/secondary.log` |
| steer an Issue in flight | edit files in `worktrees/pair` between turns; the next seat sees the change |
| take over a seat | Ctrl-C (the current turn finishes first), then `cd worktrees/pair && claude --resume <id>` with the id `just pair-status` prints; `just pair` again afterwards |
| desk check | test in `worktrees/pair`, then `just pair-accept`, or write notes in the Issue file and `just pair-resume` |

In a portfolio, run the same commands through the script, from the portfolio's
root: `uv run --script <stereorepo>/pair/pair.py run`, `status`, `accept` or
`resume`.

Runtime state lives in `.pair/` at the repository root, which is gitignored:
`state.json` is the Issue in flight, `turns.jsonl` has one row per turn with
tokens and cache reads, and `<seat>.log` and `<seat>.jsonl` are each seat's
output.

The loop's tests run as the `pair` Project's gate, `just gate pair`, against
fake seats over a temporary git repository.
