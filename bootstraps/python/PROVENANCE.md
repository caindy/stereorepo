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
| `py-*` (8) | **Yes — locally owned** | Each carries a **Target contexts** section routing it between inherited `.meta/` tooling and a Project workspace (stereorepo's DR-212). See below. |
| `verification-before-completion` | Rewritten | The verification command is `make check`; adds the worktree caveat below. |
| `using-git-worktrees` | **Heavily rewritten** | Setup is `uv sync`, not `pip`/`poetry`. The "clean baseline" step is the substantive change — see the skill. |
| `systematic-debugging` | Extended | Four diagnosis rules injected. |
| `brainstorming`, `writing-plans`, `executing-plans`, `finishing-a-development-branch`, `writing-skills` | Adapted | Project-specific commands and doc routing. |

### What changed in `py-*`, and why they stopped being refreshable

They arrived byte-identical, and that was worth keeping while the difference from
upstream was cosmetic. It is not: these skills assume a standalone application
package with a root `pyproject.toml`, a `tests/` directory and `.git/hooks/`
under its own control, and following them against inherited `.meta/` tooling
damages it. The guard has to sit inside the skill that carries the hazard,
because a skill is loaded by its own trigger and by nothing else — which is why
it could not be an overlay, and so why the byte-identical copy had to go
(stereorepo's DR-212, solorepo's #446).

| Skill | The hazard it now names |
|---|---|
| `py-quality-setup` | Holds the contract in full: the two targets, how to tell which, no root `pyproject.toml`, and every checker given its configuration by name. The permissions it writes no longer grant `Bash(git commit *)`, since A19 holds a commit that does not name its Actor to be unattributable |
| `py-code-health` | `# noqa: F401  # reason:` registration imports and `@check`-decorated steps are live, not dead; what `vulture` reports at 80 against what it reports at 60 |
| `py-git-hooks` | `core.hooksPath` is set, so `pre-commit install` refuses and the remedy it prints is destructive; the lint gate routes by target, runs no formatter, and drops `basedpyright` |
| `py-test-quality` | `.meta/` has no pytest suite; its behavioural tests are the probes, and `uv run gate mutants` admits no survivor rather than a 75% score |
| `py-modernize` | `.meta/` consolidates into no manifest and is not migrated to `uv run`; `pyupgrade` reads no `noqa`, so a suppression cannot stop it rewriting a line |
| `py-complexity` | `C90` is selected in a Project and not in `.meta/`; the other tools are advisory and no gate reads them |
| `py-security` | `S` is selected in a Project and not in `.meta/`; a finding is answered by a reasoned suppression at the site, which A2 requires, and never in configuration |
| `py-refactor` | Routes every phase it dispatches, and does not stand up a Project by hand where `just bootstrap` exists |

`lint-gate.py` is the one executable change: it resolves each modified file to its
target and checks it under that target's own configuration, passing `--config` on
every ruff call so no fixer runs under a ruleset the target did not declare.

**Deliberately not vendored:** `test-driven-development` (its one irreplaceable rule — watch
the test fail, or you do not know what it tests — is carried more generally by
`docs/TESTING.md`'s mutation-probe doctrine, which also covers tests written after the code);
`requesting-code-review` / `receiving-code-review` (the harness has better-integrated review
tooling); `using-superpowers` (a dispatcher, meaningless when cherry-picking);
`dispatching-parallel-agents` and `subagent-driven-development` (see `docs/PARKED.md`).

## Refreshing

A refresh re-copies the unmodified upstreams and prints a diff for the modified
ones, so vendoring does not silently rot. Anything listed as modified above is
**not** overwritten — a refresh treats it as locally owned, and that now includes
all eight `py-*`.

Reading a `py-*` diff against upstream, the question is whether an upstream
change touches a Target contexts section or the reasoning behind it. Where it
does not, take it. Where it does, the contract wins: it exists because following
upstream's assumption here breaks something.

After changing any skill under `skills/`, run `just apm` to project it into
`.apm/skills/`, which is a generated byte-copy and is never edited directly.
Bare `just apm`, with no subcommand: `just apm compile` is a different action,
which calls out to the `apm` CLI against the harness targets.
