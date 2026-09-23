---
slug: seed-commit
context: solorepo
minted: 2026-09-22
---

# Seed Commit

**Seed Commit** is an empty git commit authored with `.meta/say/commit --allow-empty` carrying the subject line `Record initial plan for Challenge #<n>`, pushed to open a pull request before modifying tracked repository files on hard and human Challenges (solorepo's DR-269).

The commit records a git tree identical to its parent, introducing zero file additions, deletions, or modifications. It establishes the initial commit object that allows a pull request to be opened on GitHub before any implementation code is written, reconciling the PR First discipline with GitHub's pull request API.

## Why the Bound Is Drawn Here

Under [[pr-first|PR First]] (solorepo's DR-249), `hard` and `human` [[challenge|Challenges]] require formulating the technical approach under **The plan.** and validating it with the solo before code is written. Opening the pull request at work commencement creates an active discussion surface where the reviewer Role and the solo can evaluate the proposed architecture before runner cycles and developer hours are spent enacting it into diffs.

However, GitHub's pull request creation refuses when there are zero commits between base and head. GitHub's REST API (`POST /repos/{owner}/{repo}/pulls`, solorepo's DR-249) returns HTTP 422 Unprocessable Entity (`"No commits between <base> and <head>"`), and `gh pr create` (calling GraphQL `createPullRequest`) similarly emits `GraphQL: No commits between <base> and <head> (createPullRequest)` when attempting to open a pull request without any commits ahead of base.

Without a sanctioned mechanism to record an empty commit, agents defaulted to authoring implementation files or creating exploratory edits merely to create a non-empty diff, defeating the purpose of pre-code plan review. The Seed Commit supplies exactly the required commit object without introducing unreviewed file diffs or scaffolding stubs.

## Contrast with Industry Synonyms and Incidental Commit

- **Dummy commit or placeholder commit:** vague industry coinages that imply temporary, throwaway, or unprincipled commits to be squashed or rebased away. A Seed Commit is an attested commit signed through the attested mutation plane (carrying `Actor:` and `Agent:` trailers, and SSH-signed when a role key is present) that permanently records the initial plan attribution in git history.
- **[[incidental-commit|Incidental Commit]]:** the counterpart commit class at the opposite end of the development lifecycle. Where an Incidental Commit (solorepo's DR-236) captures an opportunistic mechanical fix discovered during active work and verified by a running verification gate, a Seed Commit records the initial plan before modifying tracked repository files or running verification gates.

The rejected industry terms (`dummy commit`, `placeholder commit`, `empty commit`) are tracked on the concept's `avoid` list to prevent unminted synonyms from entering the [[ubiquitous-language|Ubiquitous Language]].

## Invariants

- **Zero file diff.** A Seed Commit introduces no file changes (`git diff --name-only <base>...HEAD` is empty). Modifying tracked repository files in a Seed Commit violates solorepo's DR-269.
- **Fixed subject form.** The commit subject must strictly match `Record initial plan for Challenge #<n>`.
- **Signed through the attested mutation plane.** Created via `.meta/say/commit --allow-empty -m "Record initial plan for Challenge #<n>"`, carrying `Actor:` and `Agent:` trailers.
- **Countable.** Repository history can enumerate all instances via `git log --grep '^Record initial plan for Challenge #'`.

---

**See also:** [[incidental-commit]], [[pr-first]], [[challenge]], [[issue]], [[review-thread]], [[decision-record]], [[ubiquitous-language]], [[knowledge-management]], solorepo's DR-249, solorepo's DR-269.
