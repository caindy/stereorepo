---
difficulty: developer
waits_on:
  - seat-sandbox-permissions
---

# Find what a fresh seat session still writes to the prompt cache

Each fresh seat session writes part of its prompt to the cache again. In the
booktutor spike (hypothesis H7) that was about 79,000 tokens per seat per
issue, because Claude Code loads the repository's `CLAUDE.md`, the skills
listing and the developer's plugins itself, and that context varied between
sessions.

Seats now start with `--setting-sources project --strict-mcp-config`
(`CONTEXT` in `pair/seats.py`): the repository's own settings, `CLAUDE.md`
and skills, and nothing from the developer's machine. Measured in a scratch
clone of stereorepo, two fresh one-turn sessions on Sonnet:

| Seat flags | 2nd session writes | Project skills |
|---|---|---|
| every setting source (before) | 12,036 | yes |
| `--setting-sources project --strict-mcp-config` (now) | 7,263 | yes |
| `--setting-sources "" --strict-mcp-config`, `AGENTS.md` appended | 4,976 | no |
| as above, plus `--disable-slash-commands` | 2,405 | no |

It waits on `seat-sandbox-permissions`, which changes the same command line.

## Wanted

- **What still varies.** With the project source alone, both sessions wrote
  the same ~7,300 tokens, so something the project source loads differs per
  session. Identify it by diffing what two fresh sessions send, and whether
  it can be made byte-identical without losing the skills (for example by
  appending `AGENTS.md` and the skill texts with `--append-system-prompt`
  and every setting source off).
- **The result in the code.** Either change `CONTEXT` to the cheaper flags,
  or record the ~7,300 tokens as the floor and why, in `CONTEXT`'s docstring,
  with the table above extended by the new measurement.

## Out of scope

Choosing a model per stage (`seat-models-per-stage`), and caching across
Issues.

## Done when

The per-session write is explained, and either reduced or recorded as the
floor, and `just gate` passes. The developer checks it by hand, since the
measurements spend their subscription and only they can judge a seat that
has lost its skills: at the desk check they re-run the two-session
measurement with the branch's flags, and after it lands they compare the
first-turn cache writes of the next Issue the loop runs, in
`.pair/turns.jsonl`, with the table, and confirm that pair converged.
