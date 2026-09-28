# Stop re-writing each seat's prompt cache on every issue

Every issue starts two fresh Claude Code sessions, and each one re-writes about
79,000 tokens of prompt cache before its first turn (booktutor spike,
hypothesis H7). Fresh sessions share only the first ~23,500 tokens of prefix,
because something per-session sits early in Claude Code's own prompt; it is not
the branch name or git state. A resumed session does hit the cache.

Choose and implement one of the two ways out the spike named:

- resume each seat's session across issues, which hits the cache but grows the
  conversation until it needs compacting; or
- an Agent SDK or API seat adapter beside `ClaudeSeat`, whose system prompt is
  byte-identical between sessions.

Measure the choice against `.pair/turns.jsonl`: cache writes on each seat's
first turn of an issue, before and after. The size of this repository's own
context (`AGENTS.md` and the installed skills) is the part of the cost the
project controls, so note it in the measurement.

Done when a second issue in a run writes markedly less cache on its seats'
first turns than the first issue did, and the pair tests cover the choice.
