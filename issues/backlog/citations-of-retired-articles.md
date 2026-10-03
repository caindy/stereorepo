---
difficulty: easy
---

# Stop citing retired Articles as though they were in force

Article 15, Article 16, Article 18 and Article 19 are retired (`.meta/charter.md`
shows each as "Retired."), but live prose still cites two of them for a rule:

- Article 15, for avoiding the word "Article" to protect "the Charter's
  empirical clauses (stereorepo's Article 1, stereorepo's Article 15)":
  - `.meta/assertions/imported/vocabulary.yaml`, the Concept's `scope_note`
    (rendered into `.meta/vocabulary.md`);
  - `wiki/stereorepo/concept.md`;
  - `wiki/stereorepo/knowledge-management.md`.
- Article 19, for "a commit that does not name its Actor is unattributable":
  - `bootstraps/python/skills/py-quality-setup/SKILL.md`, twice (lines 70
    and 323). This is the source; `.meta/lib/apm_compile/bootstrap.py` reads
    `bootstraps/python/skills/` and `just render` writes the copy under
    `bootstraps/python/.apm/skills/`. Both passages also send commits through
    `.meta/say/commit` and its Actor Trailer, and send `gh`'s writing verbs
    through `.meta/say/post` and `.meta/say/move`, and the permissions block
    at line 316 allows `Bash(.meta/say/commit *)`. `.meta/say/` and the
    Actor class are gone too, and `.claude/settings.json` denies no `gh`
    verb today, so each of those sentences describes a tree that no longer
    exists.
  - `bootstraps/python/PROVENANCE.md`, the `py-quality-setup` row.

Found while trimming DR-179 to DR-217 (`trim-decision-records-179-217`).

## Wanted

- Each citation of a retired Article either names a current Article or
  Decision that carries the rule, or goes, with the sentence restated so it
  does not lean on it. For the Article 15 passages, Article 1 alone may carry
  the reason; check the charter.
- The `py-quality-setup` skill no longer mentions `.meta/say/` (`commit`,
  `post` or `move`), the Actor Trailer or the Actor, and its permissions
  block no longer allows `Bash(.meta/say/commit *)`. Seats and the developer
  commit with `git commit` today, so unless the tree gives another reason to
  withhold it, "Never grant `Bash(git commit *)`" and the step-5 paragraph
  after the permissions block go, and the block is upstream's again in that
  entry. The claim that `.claude/settings.json` denies `gh`'s writing verbs
  goes unless that file says so.
- The `py-quality-setup` row of `bootstraps/python/PROVENANCE.md` records
  what the skill now does about `Bash(git commit *)`, without A19.
- Re-render, so `.meta/vocabulary.md` and the skill copy follow their sources.

## Out of scope

- The probe case in `.meta/checks/probes/tools/comments.py` that quotes A19
  and Article 19: it is a test string for comment shapes and stays.
- The decision log, the Issues and the history logs.
- `.meta/say/` in `excluded_paths` of
  `template/.meta/assertions/structure.yaml`, which is
  `template-excludes-retired-say-path`.

## Done when

Outside `.meta/assertions/decisions/`, `.meta/decisions.md`, `issues/`, the
history logs and the probe's test string, a grep for `Article 1[5689]` and
`\bA1[5689]\b` finds only the charter's four "Retired." headings, and a grep
for `.meta/say` finds nothing under `bootstraps/`.
