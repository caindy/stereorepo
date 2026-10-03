---
difficulty: easy
---

# Stop the template excluding `.meta/say/`, a directory that is gone

`template/.meta/assertions/structure.yaml` lists `.meta/say/` under
`excluded_paths`, the operational paths a specialized portfolio's
completeness check passes over. `.meta/say/` no longer exists in the
scaffold, so no portfolio inherits it, and stereorepo's own
`.meta/assertions/structure.yaml` does not name it. Found while grooming
`citations-of-retired-articles`.

## Wanted

The `.meta/say/` line comes out of the template's `excluded_paths`, and
nothing else changes. Nothing writes that list. `load_excluded_paths` in
`.meta/checks/graph/artifacts.py` only reads it, as globs to pass over, so
removing an entry that matches nothing changes no check's result.

## Out of scope

- The `.meta/say/` mentions in `bootstraps/python/skills/py-quality-setup/`,
  which `citations-of-retired-articles` removes.
- The decision log and the done Issues, which mention it as history.

## Done when

- A grep for `meta/say` under `template/` finds nothing.
- `.meta/test_specialization.py` still passes: a portfolio specialized
  from the scaffold has a completeness check that passes without the line.

## Pair notes

> **primary, backlog turn 1**
>
> I made a few small edits to `issues/underway/template-excludes-retired-say-path.md`. It was already groomed, and I checked its claims against the code.
>
> **What I checked:**
> - `.meta/say/` is named only once, in `excluded_paths` in `template/.meta/assertions/structure.yaml`.
> - Nothing writes that list. `load_excluded_paths` in `.meta/checks/graph/artifacts.py` only reads its entries as patterns for paths to skip. An entry that matches nothing changes no check's result.
> - The specialization test that "Done when" relies on exists: `.meta/test_specialization.py`.
>
> **What I changed:**
> - **Line number removed:** the issue cited the line as "line 33", which DR-355 forbids. It now names the list.
> - **Open question settled:** the "Wanted" section said "if anything writes or checks that list…". It now states that nothing writes the list, so only the template line changes.
> - **Test named:** "Done when" now cites `.meta/test_specialization.py` instead of describing "the specialization test".
>
> I left `difficulty: easy` as it was: the fix is deleting one line.

> **secondary, backlog turn 2**
>
> I'm leaving the issue file unchanged. It is ready to plan, and `difficulty: easy` is right.
>
> I checked your edits against the code, and each claim holds:
> - **The one mention:** `.meta/say/` appears only once under `template/`, in `excluded_paths` in `template/.meta/assertions/structure.yaml`.
> - **The directory is gone:** `.meta/say/` no longer exists in the scaffold.
> - **Nothing writes the list:** `load_excluded_paths` in `.meta/checks/graph/artifacts.py` only reads it. An entry that matches no path changes no check's result.
> - **The test exists:** `.meta/test_specialization.py` specializes a portfolio from the scaffold and runs that portfolio's own gate. Citing it under "Done when" is a real test of the behaviour, not a reference to `just gate`.

## The plan

One file changes: `template/.meta/assertions/structure.yaml`.

1. Delete the `- .meta/say/` entry from `excluded_paths`. Leave the other
   three entries (`.meta/*.py`, `.meta/lib/`, `.meta/checks/`) and the
   comment above them alone.
2. Confirm that a grep for `meta/say` under `template/` finds nothing.

No code changes. `load_excluded_paths` in `.meta/checks/graph/artifacts.py`
reads the list as globs, and the duplicate-key and parse checks in
`.meta/checks/files/templates.py` only need the YAML to stay valid.

**Test.** `.meta/test_specialization.py` copies this template into a
portfolio and runs that portfolio's own gate, which includes the artifact
completeness check that reads `excluded_paths`. That test is the gate of
the Project `specialization` (DR-321), so the loop runs it before landing,
and no new test is needed.

**Risk.** Almost none. The one way it could fail is if a specialized
portfolio somehow ends up with a `.meta/say/` path. It cannot:
`.meta/say/` does not exist in the scaffold, so specialization copies
nothing there.

## Pair notes

> **primary, todo turn 1**
>
> I added a `## The plan` section to `issues/todo/template-excludes-retired-say-path.md`. It's short because the change is one line.
>
> - **File:** only `template/.meta/assertions/structure.yaml` changes. The `- .meta/say/` entry comes out of `excluded_paths`, and the other three entries and their comment stay. No code changes, because `load_excluded_paths` in `.meta/checks/graph/artifacts.py` only reads the list.
> - **Steps:** delete the line, then grep for `meta/say` under `template/` and expect no matches.
> - **Test:** `.meta/test_specialization.py` copies the template into a test portfolio and runs that portfolio's own checks, including the one that reads `excluded_paths`. It is the gate of the Project `specialization`, so the loop runs it before landing and no new test is needed.
> - **Risk:** almost none. `.meta/say/` doesn't exist in the scaffold, so no portfolio can end up with a path the old entry was covering.

> **secondary, todo turn 2**
>
> I checked the plan against the code and am leaving it unchanged.
>
> - **The edit:** `excluded_paths` in `template/.meta/assertions/structure.yaml` lists four entries under one comment, exactly as the plan describes. Deleting `- .meta/say/` leaves valid YAML.
> - **The YAML checks:** the duplicate-key and parse checks in `.meta/checks/files/templates.py` scan every YAML file under `template/`, and the file still passes them after the line goes.
> - **The test:** `.meta/test_specialization.py` is the right one. It runs the gate of the specialized portfolio, and that gate includes the completeness check that reads `excluded_paths`.
> - **Size:** the plan fits a one-line change.

## Implementation notes

Done as planned: the `- .meta/say/` entry is gone from `excluded_paths` in
`template/.meta/assertions/structure.yaml`, and a grep for `meta/say` under
`template/` finds nothing. No other file changed, and nothing rides along:
no Decision Record, render output or wiki page names the template's
`excluded_paths` entries.

## Pair notes

> **primary, in-progress turn 1**
>
> I removed the `- .meta/say/` entry from `excluded_paths` in `template/.meta/assertions/structure.yaml`, as the plan said. A grep for `meta/say` under `template/` now finds nothing.
>
> - **Checks:** `just gate meta` passes. The change doesn't touch `pair/` or either bootstrap seed, so no other targeted gate applies. The specialization test, `.meta/test_specialization.py`, runs when the loop gates the branch before landing; I haven't run it myself.
> - **Issue file:** I added a short `## Implementation notes` section. It says the work went as planned, no other file changed, and no document needed updating with it.
> - **Plan:** unchanged; the work matched it.
> - **Backlog:** I found no outside work, so I added no new Issues.
>
> It's committed as `27ac53ba`.

> **secondary, in-progress turn 2**
>
> The change is done as planned, so I'm leaving it as it is. The `.meta/say/` line is gone from `excluded_paths` in `template/.meta/assertions/structure.yaml`, and a search for `meta/say` under `template/` finds nothing.
>
> - **Check:** `just gate meta` passes on my turn (94 steps). The change doesn't touch `pair/` or either bootstrap seed, so no other targeted gate applies.
> - **Not run:** I didn't run the specialization test, `.meta/test_specialization.py`. The loop runs it when it gates the branch before landing.
> - **Issue file:** the plan and the implementation notes match the change, so I didn't edit them.
> - **Backlog:** I found no work outside this issue, so I added no new issues.
