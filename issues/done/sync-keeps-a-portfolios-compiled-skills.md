---
difficulty: easy
parent: onboard-fitch-mvp
---

# A sync keeps the compiled skills of a portfolio's own

`.meta/.apm/` is a managed item in `.meta/bundle.yaml`, so `just sync
<checkout>` (`plan` in `.meta/lib/bundle/sync.py`) removes from it every path
the portfolio tracks and the checkout does not. That includes what render
compiled there from the portfolio's own `.claude/skills/`
(`skill_primitives` in `.meta/lib/apm_compile/skills.py`, third source). In
fitch-mvp both syncs reported:

```
removed .meta/.apm/skills/generate-decision-graph/SKILL.md
removed .meta/.apm/skills/generate-schema-code/SKILL.md
```

and `just render` put them back. Nothing is lost, but between the sync and
the render the working tree shows two deleted skills, and a sync committed
before rendering commits their deletion.

## Wanted

`plan` does not put in `removed` a tracked portfolio path
`.meta/.apm/skills/<name>/SKILL.md` when the portfolio holds
`.claude/skills/<name>/SKILL.md`, because render would compile that file
back. The rule mirrors render's: whatever `.claude/skills/` holds is
compiled, so whatever it holds is kept. `.claude/skills/` is not a bundle
item, so it is always the portfolio's own.

A file under `.meta/.apm/skills/<name>/` with no `.claude/skills/<name>/SKILL.md`
in the portfolio is still removed when the checkout no longer tracks it: a
skill stereorepo stops shipping goes. Copies are unchanged: where the
checkout ships `.meta/.apm/skills/<name>/SKILL.md`, the sync still
overwrites the portfolio's.

"Holds" means what render reads: a `SKILL.md` file on disk in the portfolio.
The module docstring of `sync.py`, which lists what a sync leaves alone,
adds this case to that list.

## Out of scope

- Changing where render compiles skills to.
- Keeping any other render output under `.meta/.apm/` (instructions, hooks).
- Fixing fitch-mvp itself.

## Done when

The sync probe (`.meta/checks/probes/tools/sync.py`) gains a case on its
scratch repositories: a portfolio that tracks
`.meta/.apm/skills/own/SKILL.md` and `.claude/skills/own/SKILL.md`, synced
from a checkout that tracks neither, keeps the compiled file and does not
report it removed; and in the same sync, a tracked
`.meta/.apm/skills/gone/SKILL.md` with no `.claude/skills/gone/` is removed.

## The plan

1. **`.meta/lib/bundle/sync.py`.** Add a helper `_own_skills(portfolio)`. It
   returns `.meta/.apm/skills/<name>/SKILL.md` for each directory under
   `portfolio/.claude/skills/` that holds a `SKILL.md` file. If
   `.claude/skills/` is missing, it returns an empty set. The `<name>` comes
   from the directory name, as in `skill_primitives`, which writes
   `.apm/skills/<name>/SKILL.md` relative to `.meta/`. In `plan`, the
   `removed` comprehension gains `and path not in own` and nothing else.
   `copies` is checked first, so stereorepo's own skills are still
   overwritten. `.meta/lib/bundle` does not import `apm_compile`, and that
   stays so: the rule is a few lines, and importing the compiler would pull
   in `render`. The helper's docstring cites `skill_primitives` as the rule
   it mirrors. Add the case to the list of what a sync leaves alone in the
   module docstring.
2. **`.meta/checks/probes/tools/sync.py`.**
   - Add `.meta/.apm/` as a managed dir item to `OLD_BUNDLE`, and so to
     `NEW_BUNDLE`.
   - Add three files to `PORTFOLIO`: `.claude/skills/own/SKILL.md`,
     `.meta/.apm/skills/own/SKILL.md` and `.meta/.apm/skills/gone/SKILL.md`.
     `SOURCE` tracks nothing under either directory.
   - In `_check_sync`, add `.meta/.apm/skills/gone/SKILL.md` to the paths
     that must be removed and printed as removed.
   - Add a constant `SKILL_OWN` holding `.meta/.apm/skills/own/SKILL.md`
     and `.claude/skills/own/SKILL.md`, next to `PEOPLE_OWN`. In `_kept`,
     add `*SKILL_OWN` to the byte-for-byte list, and extend the
     "is reported" check, which today covers only `PEOPLE_OWN`, to cover
     `SKILL_OWN` too. The byte-for-byte list alone does not check that a
     path is absent from the output.
   - Update the probe's docstring to match.

   Check the probe before and after step 1. Before the fix it should fail
   on the kept file; after the fix it should pass.

**Risk.** The new `PORTFOLIO` files reach every probe case, including the
refusals and merges. They are clean and tracked, so no refusal should
change. Read the probe's output to confirm that rather than assume it. The
probe needs no case for a file under `.meta/.apm/skills/own/` other than
`SKILL.md`: render compiles only `SKILL.md`, so such a file is removed as
it is now.

## Notes

Done as planned. Before the fix the probe failed: it found
`.meta/.apm/skills/own/SKILL.md` changed and printed. After the fix it
passes, and `gone` is removed and printed. The kept skills are exempt from
`removed` only. A kept skill with uncommitted changes therefore does not
cause a refusal, which is right, because the sync never touches it.
`_own_skills` copies render's rule rather than importing it. If
`skill_primitives` changes where it reads or writes skills, `_own_skills`
must change with it.

DR-318 records the rule and why the sync copies render's rule instead of
calling `skill_primitives`. Without it, the "left alone" list in DR-315 no
longer matched the code. In a sandboxed session, `just render` fails while
writing `.claude/skills/` but has already regenerated `.meta/decisions.md`.
