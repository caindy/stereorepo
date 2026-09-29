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

Two things remain:

- **What still varies.** With the project source alone, both sessions wrote
  the same ~7,300 tokens, so something the project source loads differs per
  session. Identify it, and whether it can be made byte-identical without
  losing the skills (for example by appending `AGENTS.md` and the skill texts
  in `--append-system-prompt` with every source off).
- **Convergence.** Run one real Issue through `just pair --once` and check
  that the pair converges as it did in the spike, and that `.pair/turns.jsonl`
  shows the lower first-turn writes.

Done when the per-session write is explained, either reduced or recorded as
the floor, and one real Issue has landed with the new flags.
