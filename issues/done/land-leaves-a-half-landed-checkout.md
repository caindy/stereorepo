---
difficulty: medium
---

# Put the checkout back when a fast-forward is refused at `main`'s ref

`git merge --ff-only` writes the landing's tree into the index and working
tree, releases `index.lock`, and only then locks `refs/heads/main` to move
it. `land-retries-a-passing-race` found this out: a fast-forward refused by
`main.lock` leaves every path the landing changes as a staged change in the
developer's checkout. Its next try finishes the fast-forward, so nothing is
left over when `main` has not moved.

When `main` has moved, `Loop.land` answers `moved` and leaves those staged
changes in place. Two processes landing in the same checkout (a grooming
pass and the loop working an Issue) can meet in that gap: A's merge has
written A's tree and holds `main.lock`; B's merge writes B's paths and is
refused at the ref; A moves `main`. The checkout now holds B's paths staged
on top of A.

The note in `land-retries-a-passing-race` says these staged changes revert
A's commit. They do not: every landing goes through `land`, so A's merge has
already written A's tree to the same index, and git's two-way merge for B
keeps it. Emulating the race with `git read-tree -m -u` and a held
`main.lock` (2026-10-02) shows A's content kept and only B's paths staged.
The harm is the leftover:

- If B rebuilds on A and fast-forwards, the checkout ends clean; nothing is
  wrong.
- If B does not land next (the rebase on the new `main` conflicts and
  pauses, the gate fails on the rebuild and the Issue goes back to the
  seats, or `main kept moving while landing`), the checkout keeps B's
  unlanded paths as staged changes. The developer's next commit, or anything
  that commits the index, puts B's unreviewed code on `main`.

## Wanted

- When `land` answers `moved`, every path a try refused at `main`'s ref
  wrote is put back to `HEAD`, in both the index and the working tree,
  before `land` returns. The paths are the ones that landing changes:
  `git diff --name-only <main before the try> <sha>`, with `main` read
  before the `merge` (after the `moved`, `main` has already moved). A try
  writes them only where no local edit stood in the way, since a
  fast-forward that meets a local edit writes nothing, so putting them back
  loses nothing of the developer's. A path outside the landing is never
  touched. A path whose checkout content does not match `sha` was not
  written by the try and is left alone too. A try counts as refused at the
  ref when its `merge` fails while `main` is still an ancestor of `sha` and
  no edit is in the way (the case `land` waits out today); a `moved` with no
  such try before it (`main` had moved before the first `merge`, which then
  writes nothing) leaves the checkout untouched.
- When `land` pauses because `main`'s ref lock stays in place, the pause
  reason also says that the checkout holds the half-done landing as staged
  changes, and how to clear them (`git restore --staged --worktree` on the
  landing's paths, or let the next run finish the landing).

## Out of scope

- The retry rules in `land` itself (`land-retries-a-passing-race`).
- A refusal at `index.lock`, which writes nothing to the checkout.
- Correcting the closed note in `issues/done/land-retries-a-passing-race.md`.

## Done when

Tests in `pair/test_pair.py`, each failing without the change where it
asserts on the checkout:

- In a `Bench`, a test calls `Loop.land` directly with a commit `sha` built
  on `main` that changes a file `b`. Before the call, it plays A's half of
  the race in the developer's checkout: build commit A on `main` changing a
  different file `a` (`git hash-object -w`, `git mktree`, `git
  commit-tree`), write A's tree with `git read-tree -m -u HEAD <A>`, and
  write `.git/refs/heads/main.lock`. `wait_for_lock` is replaced by A's
  finish: delete the lock and `git update-ref refs/heads/main <A>`. The test
  asserts that `land` answers `moved`, that `git status --porcelain` in the
  checkout is empty, and that `a` holds A's content and `b` its content on
  A.
- The same sequence with a local, uncommitted edit to a third file that
  neither commit touches: the edit is still there afterwards, and is the
  only line in `git status --porcelain`.
- A test like `test_a_lock_that_stays_pauses_and_says_so`, but with
  `.git/refs/heads/main.lock` written in `before_land` and left in place
  (`wait_for_lock` does nothing), asserts that the loop pauses, that the
  reason names `main.lock` as staying in place, and that it holds the new
  sentence about the staged changes. No such test exists today: the existing
  one leaves `index.lock`, which writes nothing to the checkout.

## The plan

One method in `pair/loop.py`, and three tests in `pair/test_pair.py`. No
caller of `land` changes (`move_underway`, `merge` and `kick_back` in
`pair/loop.py`): each
already treats `moved` as "build again on the new `main`".

1. **Remember what a ref-refused try wrote.** In `Loop.land`, read
   `before = git rev-parse <main>` ahead of each
   `merge`. When a try fails while `main` is still an ancestor of `sha` and
   `edits_in_the_way` answers nothing (the branch that calls
   `wait_for_lock` today, and the last try that breaks out to the pause),
   set `written` to the paths of `git diff --name-only -z <before> <sha>`.
   An `index.lock` refusal lands in the same branch, but it wrote nothing;
   the filter in step 2 drops its paths, so no separate case is needed.
2. **Put them back on `moved`.** In a new method `unwrite(sha, paths)`,
   called just before `return "moved"`, keep the paths whose checkout still
   holds the try's write: those in neither `git diff --name-only <sha>`
   (working tree) nor `git diff --cached --name-only <sha>` (index), and in
   at least one of `git diff --name-only HEAD` or `git diff --cached
   --name-only HEAD`. Run `git restore --source=HEAD --staged --worktree
   -- :(literal)<path>...` on them through `git_run`, which takes no stdin
   (so not `--pathspec-from-file`), each path prefixed with `:(literal)` so
   that glob characters in a name match only that name. If no paths are
   left, skip the call. The "matches `sha`" test
   leaves alone anything the developer has changed since the try, and the
   "differs from `HEAD`" test drops paths absent from `HEAD`, the index and
   the working tree, which `git restore` rejects with `pathspec did not
   match`. On 2026-10-02 a scratch repo confirmed that `git restore` with
   `--source=HEAD` puts back a path the landing deleted and removes a path
   it added.
3. **Say so in the pause.** In the `held` branch, when the lock in place is
   `main`'s ref lock and `written` is not empty, add a sentence along the
   lines of: "your checkout holds the half-done landing as staged changes;
   `git restore --staged --worktree` them, or let the next run finish it".
   The reason must still end with `(git: ...)`.
4. **Docstrings.** Extend `land`'s docstring with the put-back on `moved`,
   and give `unwrite` its own.

### Tests (`pair/test_pair.py`, next to `test_a_lock_on_mains_ref_is_waited_out`)

- A small helper builds a commit on a given parent with given file
  contents without touching the checkout. It uses a temporary index
  (`GIT_INDEX_FILE`, `read-tree <parent>`, `update-index --add
  --cacheinfo` from `hash-object -w`, `write-tree`, `commit-tree`).
- `test_a_ref_refusal_overtaken_by_main_is_put_back`: `sha` is built on
  `main`, changes `b.txt` and adds `c.txt`; A is built on `main` and changes
  `a.txt`. In the checkout, run `git read-tree -m -u HEAD <A>` and write
  `.git/refs/heads/main.lock`. Then set `b.loop.wait_for_lock` to a function
  that unlinks the lock and runs `git update-ref refs/heads/main <A>`. Call
  `b.loop.land(State(slug="x", stage="todo"), sha)` and assert:
  - it answers `moved`;
  - `git status --porcelain` is empty;
  - `a.txt` holds A's content;
  - `b.txt` holds `main`'s content;
  - `c.txt` does not exist.

  Without the change, the status shows `b.txt` and `c.txt`.
- `test_a_put_back_keeps_unrelated_local_edits`: the same race, with
  the tracked `.gitignore` (which neither commit touches) edited and not
  committed before the call. Afterwards `.gitignore` still holds the edit,
  and the status is exactly ` M .gitignore`.
- `test_a_lock_on_mains_ref_that_stays_pauses_and_says_so`: modelled on
  `test_a_lock_that_stays_pauses_and_says_so` (`:2113`). `before_land`
  writes `main.lock`, and `wait_for_lock` does nothing. Assert:
  - the run answers `paused`;
  - the reason contains `refs/heads/main.lock stayed`, the new
    staged-changes sentence, and `(git: `.

  Unlink the lock at the end.

### Risks

- **The pathspec is literal.** Landing paths are passed as pathspecs, so a
  file name holding glob characters could match other paths; hence the
  `:(literal)` prefix in step 2. On 2026-10-02 a scratch repo confirmed
  that `git restore --source=HEAD --staged --worktree -- ':(literal)g*'`
  restores `g*` and leaves a staged `gx` alone, and that the same call
  puts back a deleted path and removes an added one.
- **Only a ref-refused try writes.** `written` must come from a try that
  was refused at the ref, not from the try that answers `moved`. A
  fast-forward that git rejects as "not possible" writes nothing, and the
  `moved` check comes before `edits_in_the_way`. So `written` stays empty
  when `main` had moved before the first `merge`, and nothing is touched,
  as Wanted asks.
- **The restore might fail.** `git restore` may fail, for example while
  the other process holds `index.lock`. Run it with `check=False`, and
  leave the checkout as it is rather than raising. The next landing, or
  the developer, can still clear it.

## Notes from the work

- **The filter is its own method.** Step 2's filter is
  `Loop.half_landed(sha, paths)`; `unwrite` and the pause both use it. The
  pause's sentence therefore depends on what the checkout still holds, not
  on which lock is in place: it appears whenever an earlier ref-refused try
  left paths written, and names them. It reads "your checkout holds the
  half-done landing as staged changes to <paths>, which the next run
  finishes (or `git restore --staged --worktree` them)".
- **`written` collects over the tries.** Each try that is refused with
  nothing in the way adds `diff_names(<main before the try>, sha)`.
  A try stopped by local edits adds nothing.
- **The test helper `commit_on`** (`pair/test_pair.py`) builds a commit
  through a temporary `GIT_INDEX_FILE`, and `race_main` plays the other
  process's half of the race. Tests now say what happens while `land` waits
  for a lock through `Bench.while_waiting`, instead of assigning over
  `Loop.wait_for_lock` with a `type: ignore[method-assign]` each time. The
  three new tests fail against the `land` from before this change, and pass
  with it.
- **Renames are two paths.** `git diff --name-only` names only the new path
  of a rename unless told `--no-renames`, so a landing that moved a file
  left its old path staged as deleted after the put-back, and
  `edits_in_the_way` missed edits to it. Every such call in `land` now goes
  through `Loop.diff_names`, which passes `--no-renames`. `race_main`'s
  landing renames `r.txt` to `moved.txt` to hold this; without the flag,
  `git status` shows `D  r.txt` after the put-back.
