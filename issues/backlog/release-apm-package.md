# Cut an APM release with a recipe instead of a workflow

The APM package (`.meta/apm.yml`, stereorepo's DR-206) was released by a GitHub
Actions workflow on a `v*` tag: it ran the gate, `just apm validate` and
`just test-specialization`, then created a GitHub Release. The bootstrap
removed every workflow, since the pair loop gates each Issue locally before it
lands, so nothing now cuts a release.

Add a `just` recipe that does the same from the human's checkout: refuse on a
dirty tree or a `main` that is not the remote's, run the three checks, tag, and
create the release. It invokes a tool under `.meta/`, like every recipe.

Done when a release can be cut with one recipe, it refuses rather than
publishes when any check fails, and `.meta/.apm/README.md` names the recipe.
