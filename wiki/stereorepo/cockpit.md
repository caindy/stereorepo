---
slug: cockpit
context: stereorepo
minted: 2026-10-02
---

# Cockpit

**Cockpit** is the one deterministic view across every repository the [[developer]] runs a pair loop in, from which the developer answers whatever waits on them.

It is not built yet. Each repository's [[supervisor]] runs its own loop, one
[[issue|Issue]] at a time (stereorepo's DR-311), so a developer with several
repositories has several loops to watch. No [[meta-harness]] surveyed on
2026-09-28 met the requirements below.

## Requirements

- **One view across repositories.** For each repository: the Issue underway,
  its [[stage]], its round, and whether it needs the developer.
- **One queue of what needs the developer, across repositories.** It holds:
  - [[desk-check|desk checks]];
  - Issues sent back to `backlog/`, by a `Needs elaboration` section or by a
    stage past its round cap;
  - loops paused because a [[seat]] crashed or was refused again after its
    one restart;
  - grooming passes paused past their round cap;
  - fast-forwards of `main` that `--ff-only` refused.
- **Notifications,** on the desktop first and on the phone later.
- **Deterministic and zero-token.** No agent at the top
  (stereorepo's DR-306). It wakes only when something changes, as
  firstmate's watcher does (see [[meta-harness]]).
- **Take over any seat, then give it back:** resume the seat's session
  interactively, and let the supervisor carry on afterwards.
- **Add to any repository's backlog without switching context.** An ordinary
  interactive session with filesystem access writes the backlog files: the
  job a captain agent does elsewhere, done with no captain.
- **A read-only projection of files and git,** so that several cockpits can
  be tried side by side: herdr panes, a status command, a web page. Each
  repository's supervisor publishes its status by a shared convention. That
  convention is to come: the Issue `cockpit-status-convention` will define
  it.
- **Work that spans repositories is split per repository** and linked
  through `waits_on`, for example `waits_on: [otherrepo:slug]`
  (stereorepo's DR-301).

---

**See also:** [[supervisor]], [[meta-harness]], [[developer]]
