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
  its root (modified in the working tree or with changes staged, as
  `git diff --quiet HEAD -- <file>` reports) stays listed: a developer who
  fills real values into a tracked `.env.example` without committing them has
  put keys on disk that are not in the history.
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
  committing, to set `SOME_KEY=x`: it is listed in `unreadable` again and
  `SOME_KEY` is in `withheld`; staging the edit without committing keeps it
  listed.
- The same test, or another, shows a tracked `.env.link` symlink to a file
  outside the repository is still listed, with its target.
- The existing key-file tests pass unchanged.

## Out of scope

- Which variables the landing gate loads, which DR-357 settles.
- Files other than `.env` and `.env.*` at a root, and key files below a root.
- Detecting or removing a key that has already been committed.
