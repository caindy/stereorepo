# Deny the seats only the key files git does not track

`key_files` in `pair/seats.py` denies a seat every `.env` and `.env.*` at the
root of the checkout and of the worktree (DR-357). fitch-mvp tracks
`.env.example`, a template that names its variables and holds no values, and
the rule denies it too. On `exploration-record` in fitch-mvp, that cost the
seats several turns:

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

## Wanted

- `key_files` lists a `.env` or `.env.*` file only if git does not track it,
  in the checkout or the worktree. An untracked or ignored `.env`, `.env.local`
  or `.env.gpg` is denied as before.
- DR-357 says so, as a consequence: the seats may read a tracked template
  such as `.env.example`, and a key that has been committed is out of scope,
  since denying the copy on disk would not protect it.

## How anyone will know it is done

- A test over a temporary repository holding a tracked `.env.example` and an
  untracked `.env`: the seat's settings deny the `.env` and not the
  `.env.example`, in the checkout and the worktree.
- A seat in a portfolio with a tracked `.env.example` runs `just gate meta`
  without a step that could not run because of it.

## Out of scope

- Which variables the landing gate loads, which DR-357 settles.
