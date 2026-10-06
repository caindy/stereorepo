---
difficulty: medium
---

# Deny the seats only the key files git does not track

`key_files` in `pair/seats.py` lists every `.env` and `.env.*` at the root of
the main checkout and of every worktree, and `confinement` makes each one
unreadable to a seat and withholds every variable it names (DR-357). fitch-mvp
tracks `.env.example`, a template that names its variables and holds no
values, and the rule denies it too. On `exploration-record` in fitch-mvp, that
cost the seats several turns:

- 13 of the `meta` gate's checks failed inside the sandbox, among them the
  conflict-marker, citation and cited-schema-slot checks. Each reads every
  file git tracks, and the read of `.env.example` was refused.
- pytest failed to collect until a seat passed `--ignore=.env.example`.
- Every note after that reported the same 13 failures as left to the
  supervisor's gate. Among them was the citation check, the step the seats
  were trying to fix.

The supervisor's gate was not affected: it runs outside the sandbox.

A file git tracks is not a key file in the sense DR-357 protects. Its contents
are already in the repository's history, so denying the seats the copy on disk
hides nothing, and every check that walks the tracked tree needs to read it.

## To reproduce

In a repository with a linked worktree, commit a `.env.example` holding
`export SOME_KEY=` and write an untracked `.env` holding `export SOME_KEY=x`.
`confinement(worktree).unreadable` lists both files, in the checkout and in
the worktree, where it should list only the `.env`.

## Wanted

- `key_files` leaves out a `.env` or `.env.*` file that git tracks at that
  root: tracked in the main checkout for a file at the checkout's root, and in
  the worktree for a file at the worktree's root (ask git at each root, for
  example with `git ls-files`, since the branches checked out may differ). An
  untracked or ignored `.env`, `.env.local` or `.env.gpg` is listed as before.
- A tracked file whose copy on disk differs from the commit checked out at
  its root stays listed: a developer who fills real values into a tracked
  `.env.example` without committing them has put keys on disk that are not in
  the history. Compare the raw bytes, not what `git diff` reports: the file
  is left out only when `git hash-object --no-filters <file>` equals the blob
  `HEAD` holds at that path and the index holds that same blob. `git diff`
  reports no change for a file marked `--skip-worktree` or
  `--assume-unchanged`, the usual way to keep local values in a tracked
  `.env`, nor for one whose clean filter encrypts it (git-crypt), where the
  history holds ciphertext and the disk holds the keys. Any failure of these
  git commands keeps the file listed.
- A tracked symlink is the exception: what it resolves to is not in the
  history, so the link and its target stay listed, as `key_files` lists any
  symlink now.
- The names in a tracked file are no longer withheld from the seat's
  environment, since `withheld` is taken from the listed files. A name an
  untracked key file also sets stays withheld.
- The docstrings of `key_files` and `confinement` say which files are left
  out and why.
- DR-357 gains a consequence saying so: the seats may read a tracked template
  such as `.env.example` while its copy on disk matches the commit, and a key
  that has been committed is out of scope, since denying the copy on disk
  would not protect it. Re-render after the edit.

## How anyone will know it is done

- A test in `pair/test_pair.py`, beside
  `test_key_files_in_every_checkout_are_denied_reading`, over a repository
  with a tracked `.env.example` and an untracked `.env` at the root of both
  the checkout and the worktree: `confinement(...).unreadable` names both
  `.env` files and neither `.env.example`, the `--settings` that `command`
  builds names no `.env.example` in `denyRead` or `permissions.deny`, and a
  name set only in `.env.example` is not in `withheld`.
- Another test edits the tracked `.env.example` in the worktree, without
  committing, to set `EDITED_KEY=x`: it is listed in `unreadable` again and
  `EDITED_KEY` is in `withheld`; staging the edit without committing keeps it
  listed.
- Another test edits the tracked `.env.example` to set `EDITED_KEY=x` and
  marks it `git update-index --skip-worktree`: it is still listed and
  `EDITED_KEY` is withheld.
- The same test, or another, shows a tracked `.env.link` symlink to a file
  outside the repository is still listed, with its target.
- The existing key-file tests pass unchanged.

## Out of scope

- Which variables the landing gate loads, which DR-357 settles.
- Files other than `.env` and `.env.*` at a root, and key files below a root.
- Detecting or removing a key that has already been committed.

## The plan

All of the code change is in `pair/seats.py`. `confinement` already takes
`withheld` from whatever `key_files` returns, and `command` builds `denyRead`
and `permissions.deny` from `unreadable`, so neither needs to change. Nothing
else calls `key_files`: `Loop.gate_env` reads the main checkout's `.env` on
its own.

1. **Add `committed(root: Path, path: Path) -> bool`** beside `key_files`.
   It is true only when `path` is a regular file, not a symlink, and all
   three of these git commands, run with `cwd=root` and `check=False`, exit
   0 and agree:
   - `git --literal-pathspecs ls-files -s -- <name>` gives exactly one entry,
     with mode `100644` or `100755` and stage 0. That rules out an untracked
     file, a symlink (mode `120000`) and a merge conflict.
   - `git rev-parse --verify --quiet HEAD:<name>` gives the same blob id as
     that entry.
   - `git hash-object --no-filters -- <name>` gives that blob id too. This
     compares the raw bytes on disk, so it does not miss an edit hidden by
     `--skip-worktree` or `--assume-unchanged`, or keys on disk that a clean
     filter encrypts in the history.

   `<name>` is `path.name`, because a key file sits at its root. Any other
   outcome, including an `OSError` from starting git, returns False, so the
   file stays listed. The literal-pathspecs flag keeps a name such as
   `.env.[x]` from being read as a glob.
2. **Change `key_files`** to skip a path when `committed(root, path)` is
   true, before it adds the path and what it resolves to. A symlink still
   lists both, because `committed` is false for one. Update its docstring to
   say which files are left out and why: their contents are already in the
   history, and every check that walks the tracked tree reads them. Add one
   sentence to the paragraph of the `confinement` docstring about
   `unreadable`, pointing to `key_files` for the exception.
3. **Add the tests** to `ConfinementTest` in `pair/test_pair.py`, after
   `test_key_files_in_every_checkout_are_denied_reading`. Each one sets up
   its files itself: commit `.env.example`, holding `export TEMPLATE_ONLY=`,
   on `main` in `self.repo`, and bring it into `self.wt` with
   `git checkout main -- .env.example` and a commit on `pair/x`. Then write
   an untracked `.env` holding `export SOME_KEY=x` in both roots. The
   `other` worktree is detached at the first commit, so it has no
   `.env.example`.
   - `test_a_tracked_env_file_that_matches_its_commit_is_readable`:
     `unreadable` is exactly the two `.env` files. Neither `denyRead` nor
     `permissions.deny` from `command(...)` names `.env.example`. `withheld`
     is `{"SOME_KEY"}`, without `TEMPLATE_ONLY`.
   - `test_a_tracked_env_file_changed_on_disk_is_denied`: rewrite
     `self.wt / ".env.example"` to `EDITED_KEY=x`. It is listed, and
     `EDITED_KEY` is withheld. The name must differ from `SOME_KEY`, which
     the untracked `.env` files already withhold, or the assertion would
     pass without the change. After `git add` it is still listed. Then reset
     it with `git checkout HEAD -- .env.example`, check it is no longer
     listed, rewrite it the same way, and mark it with
     `git update-index --skip-worktree`: it is listed again, and
     `EDITED_KEY` is withheld.
   - `test_a_tracked_env_symlink_is_denied_with_its_target`: commit a
     `.env.link` in `self.wt` that links to `self.tmp / "secrets"`. Both the
     link and the target are in `unreadable`.

   The existing key-file tests are left as they are. Their files are
   untracked, so they show that the untracked case is unchanged.
4. **Add a consequence to DR-357**
   (`.meta/assertions/decisions/DR-357.yaml`). The seats may read a tracked
   template such as `.env.example` while its bytes on disk match the blob at
   `HEAD` and in the index, as `key_files` in `pair/seats.py` checks. A key
   that has been committed is out of scope, since denying the copy on disk
   would not protect it. Then run `just render` and commit what it
   generates.

**Risks.**
- The new code runs up to three git processes for each tracked `.env*` file
  at each root, each time a seat starts. That is a handful of processes, so
  the cost is small.
- The git environment of the loop's process reaches these commands, as it
  does every other git call in `confinement`. A leaked `GIT_DIR` would point
  them at the wrong repository. If that happens, the blobs disagree and the
  file stays listed, so the failure is safe.
- A text file that `core.autocrlf` converts also stays listed. That is
  acceptable, as the pair agreed when grooming.
- The check runs once, when the seat starts, like the rest of `confinement`.
  If the developer fills keys into a tracked `.env.example` during a turn,
  the seat can read them until it next starts. This is the same window the
  `confinement` docstring already states for a key file written later, and
  the sentence added there should say it covers this case too.

## Pair notes

> **primary, backlog turn 1**
>
> I changed nothing: the Issue is already ready to plan.
>
> - **Front matter:** `difficulty: medium` is already set, and that fits. The work is one rule in `key_files` (`pair/seats.py`), the docstrings that describe it, a new consequence in DR-357, and a few tests. It is too big to call easy and too small to split.
> - **Names it cites:** `key_files`, `confinement`, `unreadable`, `withheld`, the settings `command` builds, and the test `test_key_files_in_every_checkout_are_denied_reading` all exist under those names.
> - **Content:** It says what is wanted: tracked `.env` files are left out unless the copy on disk differs from the commit checked out at its root, and tracked symlinks stay denied. It also says what is out of scope.
> - **Done criteria:** These are written as behaviour and tests, and none of them is a gate.

> **secondary, backlog turn 1**
>
> I tightened how "matches the commit" is decided. `git diff --quiet HEAD`
> reports a modified file as unchanged when it is marked `--skip-worktree` or
> `--assume-unchanged`, which is the usual way to keep local values in a
> tracked `.env`, and when a clean filter such as git-crypt encrypts it, where
> the disk holds the plaintext keys. Either would have let the seats read
> real keys. The Issue now compares the raw bytes on disk and the index entry
> with the blob at `HEAD`, keeps the file listed if any git command fails,
> and adds a test for the skip-worktree case. `difficulty: medium` stands.

> **secondary, backlog turn 2**
>
> I tightened one rule in the Issue and committed it. `difficulty: medium` stays, and nothing else needed changing.
>
> **The gap:** the Issue said a tracked `.env` file is left off the seats' deny list when `git diff --quiet HEAD -- <file>` reports no change. That check can say "unchanged" while the file on disk holds real keys:
> - **Hidden edits:** `git diff` ignores edits to a file marked `--skip-worktree` or `--assume-unchanged`. That is the usual way developers keep local values in a tracked `.env`.
> - **Encrypted files:** with a clean filter such as git-crypt, the history holds ciphertext and the disk holds the plaintext keys, but `git diff` still reports no change.
>
> Either case would have let the seats read real keys.
>
> **The fix:** a tracked file is now left out only when two things hold:
> - the raw bytes on disk (`git hash-object --no-filters`) match the blob `HEAD` holds at that path, and
> - the index holds that same blob.
>
> If any of these git commands fails, the file stays listed. I also added a test: edit the tracked `.env.example`, mark it `--skip-worktree`, and check that it is still denied and its variable is still withheld from the seat's environment.
>
> I added a note in the Issue's Pair notes explaining the change.

> **primary, backlog turn 3**
>
> I changed nothing this turn. I checked your partner's tightening against how git behaves, and it is right:
>
> - **Raw bytes, not `git diff`:** `git diff` reports no change for a file marked `--skip-worktree` or `--assume-unchanged`, or for one with a clean filter such as git-crypt. Comparing `git hash-object --no-filters` with the blob `HEAD` holds catches all three, because in each the bytes on disk differ from the blob.
> - **The index check:** requiring the index to hold that same blob keeps a staged-only edit listed.
> - **Failure handling:** a git command that fails keeps the file listed, which is the safe direction.
> - **One side effect:** a text file that git converts line endings for (`autocrlf`) will also stay listed. That is acceptable.
>
> `difficulty: medium` stands. The two partner notes at the end of the Issue repeat each other, but they do no harm, so I left them.

> **primary, todo turn 1**
>
> I added `## The plan` to `issues/todo/seats-read-tracked-env-files.md`. Nothing is implemented yet, and nothing in planning showed the Issue can't be done as written.
>
> **How it works:** a new helper, `committed(root, path)` in `pair/seats.py`, decides whether a tracked `.env` file may be left off the deny list. It returns true only when all of these hold:
> - the file is a regular file, not a symlink, and has no merge conflict, checked with `git ls-files -s`;
> - its index entry matches the blob at `HEAD`;
> - `git hash-object --no-filters` gives that same blob, so the raw bytes on disk match the commit.
>
> `key_files` skips a file when `committed` is true. Any git command that fails, or any answer that disagrees, keeps the file listed.
>
> **What else changes:**
> - `confinement` and `command` need no code change. `withheld` and the deny lists are already built from what `key_files` returns, and nothing else calls `key_files`.
> - The docstrings of `key_files` and `confinement` will say which files are left out and why.
> - DR-357 gains a consequence saying the seats may read a tracked template while it matches its commit. Then `just render` and a commit.
>
> **Tests:** three new tests go into `ConfinementTest` in `pair/test_pair.py`:
> - A tracked `.env.example` that matches its commit is readable. Only the untracked `.env` files are denied, and only their variable names are withheld.
> - A tracked `.env.example` edited on disk is denied. It stays denied after the edit is staged, and when the edit is hidden with `--skip-worktree`.
> - A tracked `.env.link` symlink is denied along with the file it points to.
>
> The existing key-file tests stay as they are; their files are untracked, so they show that case is unchanged.
>
> **Risks:**
> - Seat start-up now runs up to three extra git commands per tracked `.env*` file. That cost is small.
> - If a stray `GIT_DIR` points git at the wrong repository, the blobs won't match and the file stays denied. That is the safe direction.
> - A text file that `autocrlf` converts also stays denied. The pair already agreed that is acceptable.

> **secondary, todo turn 1**
>
> I fixed one test in the plan and added one risk.
>
> - **The test proved nothing as written.** The changed-on-disk test set
>   `SOME_KEY=x` in `.env.example` and asserted `SOME_KEY` was withheld, but
>   the untracked `.env` files in the same fixture already withhold
>   `SOME_KEY`. The assertion would pass even if the edited file were left
>   out. The edit now sets `EDITED_KEY`, in the plan and in the done
>   criteria, and the test also checks that resetting the file makes it
>   readable again.
> - **New risk:** the check runs only when a seat starts. Keys the developer
>   fills into `.env.example` during a turn are readable until the next
>   start. That window already exists for key files written later, so the
>   `confinement` docstring should name this case too.
>
> I checked the rest against the code: `ConfinementTest`'s fixture,
> `key_files`, `env_names` and how `confinement` builds `withheld` match the
> plan.

> **secondary, todo turn 2**
>
> I made one fix to the plan and added one risk, and committed both. The rest of the plan matches the code: the `ConfinementTest` setup in `pair/test_pair.py`, and in `pair/seats.py` `key_files`, `env_names`, and how `confinement` builds `withheld`.
>
> - **A test that would always pass:** the planned test for a tracked `.env.example` edited on disk set `SOME_KEY=x`, then checked that `SOME_KEY` was withheld from the seat's environment. In that test's setup the untracked `.env` files already set `SOME_KEY`, so the check would pass even if the edited file were wrongly left readable. The edit now sets a new name, `EDITED_KEY`, in both the plan and the done criteria. The test also checks that the file becomes readable again once it is reset to match its commit.
> - **New risk:** the check runs only when a seat starts. If the developer fills real keys into a tracked `.env.example` during a turn, the seat can read them until it next starts. The `confinement` docstring already notes this gap for key files written after start, and the plan now says that sentence should cover this case too.
>
> I couldn't confirm by hand that `git hash-object --no-filters -- <file>` behaves as the plan expects: the sandbox blocked the git commands in a scratch repository. The plan relies on the flags as git documents them.

> **primary, todo turn 3**
>
> I changed nothing this turn, and I've checked your partner's two changes against the code.
>
> - **The test fix is right.** The untracked `.env` files in that test's setup already set `SOME_KEY`, so checking that `SOME_KEY` is withheld would have passed even if the edited `.env.example` were wrongly left readable. Using `EDITED_KEY` makes the check meaningful. The added step, which checks that a reset file becomes readable again, also covers the case where a file matches its commit.
> - **The new risk is right.** `confinement` runs only when a seat starts. Keys the developer fills into `.env.example` during a turn stay readable until the seat's next start, which is the same gap as for a key file written after start.
>
> I also tried to run the planned git commands (`ls-files -s`, `rev-parse HEAD:<name>`, `hash-object --no-filters`, plus `--skip-worktree`) in a scratch repository. The command check refused every attempt before it ran, so that is still unconfirmed by hand. The plan relies on those flags as git documents them, and the planned tests will exercise them directly.

> **primary, in-progress turn 1**
>
> I've implemented the change as planned and committed it. `just gate pair` (278 tests and ruff) and `just gate meta` both pass.
>
> - **The rule:** a new function, `committed` in `pair/seats.py`, decides whether a tracked `.env*` file holds only what is committed. Three things must agree:
>   - the file's entry in the index (`git ls-files -s`), which must be a regular file with no merge conflict;
>   - the blob at `HEAD` for that path;
>   - the raw bytes on disk (`git hash-object --no-filters`).
>
>   If any of them differs, or any git command fails, the file stays denied. `key_files` now skips a file that passes, and the names of withheld variables follow from that without further change.
> - **Docstrings:** those of `key_files` and `confinement` now say which files are left out and why. They also say that keys written into a tracked file during a turn are denied only from the seat's next start.
> - **Tests:** three new tests in `ConfinementTest` in `pair/test_pair.py`:
>   - a tracked `.env.example` that matches its commit is readable;
>   - an edited one is denied, still denied after staging, readable again after a reset, and denied again when the edit is hidden with `--skip-worktree`;
>   - a tracked symlink is denied together with the file it points to.
>
>   The existing key-file tests are unchanged and still pass.
> - **DR-357:** it now has a consequence saying a tracked template such as `.env.example` may be read while it matches its commit. `just render` regenerated no files, because no generated page shows a decision's consequences.
>
> `pair/README.md` needed no change: it describes only the main checkout's untracked `.env`, which stays denied. My note for the next reader is in the Issue file.

> **secondary, in-progress turn 1**
>
> I reviewed the implementation against the plan. It is right, and I added
> one test.
>
> - **Untested seam:** nothing tested the reason for `--no-filters`. If that
>   flag were dropped from `committed`, every test would still pass. I added
>   `test_a_tracked_env_file_a_clean_filter_rewrites_is_denied`, which does
>   what git-crypt does with a toy `tr` clean filter: `git status` reports the
>   file clean, but its bytes on disk differ from the blob, so it stays
>   denied. Without `--no-filters`, `hash-object` would hash the filtered
>   bytes, match the blob, and leave the file readable. The sandbox would not
>   let me drop the flag to watch the test fail, so that part is reasoned,
>   not observed.
> - **Tidying:** I removed the first of two near-identical primary
>   in-progress notes; the second keeps everything the first said.
>
> All 18 `ConfinementTest` tests pass.

> **secondary, in-progress turn 2**
>
> Your partner's implementation matches the plan and I found nothing wrong in it. I added one missing test, tidied the Issue file and committed both. `just gate pair` (279 tests and ruff) and `just gate meta` pass.
>
> - **The gap:** no test covered why `committed` in `pair/seats.py` hashes the file with `--no-filters`. Dropping that flag would have broken the git-crypt protection and every test would still have passed.
> - **The new test:** `test_a_tracked_env_file_a_clean_filter_rewrites_is_denied`, in `ConfinementTest` in `pair/test_pair.py`, acts like git-crypt: a small clean filter changes the file's contents before git stores them. `git status` reports the file unchanged, but its bytes on disk differ from what was committed, and the test checks that it stays denied. Without `--no-filters`, `hash-object` would hash the filtered bytes, which match the commit, so the file would become readable and the test would fail. That last step is reasoning, not something I saw: the sandbox refused my attempt to remove the flag temporarily and watch the test fail.
> - **Tidying:** your partner had left two almost identical notes for in-progress turn 1, so I removed the first; the second says everything it did. My own note for the next reader is in the Issue file.

> **primary, in-progress turn 3**
>
> I changed nothing this turn, and I haven't re-run the gates since nothing changed. Your partner reports `just gate pair` (279 tests and ruff) and `just gate meta` passing on this code.
>
> I checked your partner's two changes:
>
> - **The new test is right.** `test_a_tracked_env_file_a_clean_filter_rewrites_is_denied` sets up a clean filter that rewrites the file before git stores it, the way git-crypt does. The commit therefore holds the rewritten text, while the disk keeps `SEALED_KEY=plain`. Hashing the raw bytes with `--no-filters` gives a different blob from the commit, so the file stays denied and `SEALED_KEY` is withheld. Without the flag, `hash-object` would hash the rewritten text, match the commit, and leave the file readable. This test is the only thing that pins the flag.
> - **Removing my duplicate note was right.** The note that remains says everything the removed one did.
>
> I tried to watch the test fail by dropping `--no-filters` for one run, but the permission check denied the command. As in your partner's note, the failure without the flag is reasoned, not observed.

Gated by the supervisor at 19:37: `meta`, `pair`; 97 steps passed.
