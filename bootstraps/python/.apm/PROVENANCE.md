# Vendored skills — provenance and licences

These skills are **vendored**, not installed: they travel with the repository, work offline,
and are pinned to a known version. A collaborator, a fresh clone and CI therefore all have
the same capabilities, which a per-machine install cannot guarantee.

`.gitignore` ignores `.claude/*` but negates `!.claude/skills/`, so edits here show up in
`git status` normally rather than needing `git add -f`.

## Upstreams

| Skills | Upstream | Licence | Copyright |
|---|---|---|---|
| `py-*` (8) | [l-mb/python-refactoring-skills](https://github.com/l-mb/python-refactoring-skills) | MIT | © 2025 Lars Marowsky-Brée |
| lifecycle skills (8) | derived from [obra/superpowers](https://github.com/obra/superpowers) | MIT | © 2025 Jesse Vincent |

**Licence obligation.** Both are MIT, which requires the copyright and permission notice to
travel with the code. Because these are seeded into *every* generated project, an omission
propagates N times rather than once. The upstream this pattern was copied from ships its
vendored copy **without** a LICENSE file; that is the mistake being avoided here.
`LICENSE-python-refactoring-skills` and `LICENSE-superpowers` are those notices.

## Local modifications

| Skill | Modified? | What changed |
|---|---|---|
| `py-*` | **No** | Byte-identical to upstream. Refresh freely. |
| `verification-before-completion` | Rewritten | The verification command is `make check`; adds the worktree caveat below. |
| `using-git-worktrees` | **Heavily rewritten** | Setup is `uv sync`, not `pip`/`poetry`. The "clean baseline" step is the substantive change — see the skill. |
| `systematic-debugging` | Extended | Four diagnosis rules injected. |
| `brainstorming`, `writing-plans`, `executing-plans`, `finishing-a-development-branch`, `writing-skills` | Adapted | Project-specific commands and doc routing. |

**Deliberately not vendored:** `test-driven-development` (its one irreplaceable rule — watch
the test fail, or you do not know what it tests — is carried more generally by
`docs/TESTING.md`'s mutation-probe doctrine, which also covers tests written after the code);
`requesting-code-review` / `receiving-code-review` (the harness has better-integrated review
tooling); `using-superpowers` (a dispatcher, meaningless when cherry-picking);
`dispatching-parallel-agents` and `subagent-driven-development` (see `docs/PARKED.md`).

## Refreshing

`make skills-refresh` re-copies the unmodified upstreams and prints a diff for the modified
ones, so vendoring does not silently rot. Anything listed as modified above is **not**
overwritten — sync treats it as locally owned.
