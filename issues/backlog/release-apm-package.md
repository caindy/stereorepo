---
difficulty: developer
waits_on:
  - specialized-portfolio-gate
---

# Cut an APM release with a recipe instead of a workflow

The APM package (`.meta/apm.yml`, DR-206) was released by a GitHub Actions
workflow on a `v*` tag: it ran the gate, `just apm validate` and
`just test-specialization`, then created a GitHub Release. The bootstrap
removed every workflow, since the pair loop gates each Issue locally before
it lands, so nothing now cuts a release. `.meta/.apm/README.md` says "The
procedure is not yet a recipe."

## Wanted

A recipe, `just release <version>`, with a `--dry-run` flag, invoking a tool
under `.meta/` like every recipe. In order, it:

1. refuses on a dirty tree, on a branch other than `main`, on a `main` that
   differs from the remote's after a fetch, on a tag `v<version>` that already
   exists, or on a `<version>` that is not the one `.meta/apm.yml` declares;
2. runs `just gate`, `just apm validate` and `just test-specialization`, and
   refuses if any fails;
3. tags `v<version>`, pushes the tag, and creates the GitHub Release.

With `--dry-run` it does steps 1 and 2 and prints what step 3 would do.

This waits on `specialized-portfolio-gate`, since `just test-specialization`
fails today and the recipe would refuse every release.

## Out of scope

Publishing an actual release. That is the developer's act, never the pair's:
seats run only `--dry-run` and the refusal paths.

## Done when

The refusal paths of step 1 are covered by tests against a scratch
repository, `.meta/.apm/README.md` names the recipe in place of "not yet a
recipe", and `just gate` passes. At the desk check the developer runs
`just release <version> --dry-run` on their checkout and reads what it would
publish.
