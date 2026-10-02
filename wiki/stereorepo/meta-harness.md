---
slug: meta-harness
context: stereorepo
minted: 2026-10-02
---

# Meta-harness

**Meta-harness** is a tool that runs coding-agent harnesses and passes work between them.

The pair loop is a meta-harness: its [[supervisor]] runs two [[seat|seats]]
and hands an [[issue|Issue]] between them. Several others existed when the
loop was designed. This page records the survey of them, made on 2026-09-28,
and why none was adopted.

## Three ways to hold a session

A meta-harness has to keep a harness session alive across turns, and know
when a turn has ended.

- **Terminal multiplexer and injected keystrokes.** The harness runs in a tmux
  or herdr pane, and messages are typed into it with `send-keys`. The prompt
  cache stays warm, and a person can take over trivially. The end of a turn,
  though, can only be guessed at, and injecting text is fragile.
- **Relaunch every turn with `--resume`.** Each turn is a clean process, but
  every turn pays for a process start, and the cache misses whenever the
  prompt's prefix drifts.
- **A long-lived structured stream:** Claude's `stream-json` mode, Codex's
  `app-server`, or the Agent Client Protocol (ACP). Turn boundaries are
  explicit and the cache stays warm.

Each seat is a `claude -p` process in `stream-json` mode, kept for the whole
Issue (stereorepo's DR-309). Relaunching with `--resume` is how the
[[developer]] takes over a seat: stop the loop with Ctrl-C, which lets the
current turn finish, then run `claude --resume <id>` in `worktrees/pair` with
the id `just pair-status` prints, and run `just pair` again afterwards.

## Tool by tool

As observed on 2026-09-28; none of it has been re-checked since.

| Tool | What it is | What the loop borrows | Why it is not adopted |
|---|---|---|---|
| firstmate (kunchenguid/firstmate) | A "captain" agent that supervises a crew. Runs in tmux, herdr or Zellij; sends briefs with `send-keys`; keeps status files and inbox/outbox directories; a watcher script that costs no tokens; Stop hooks. | The zero-token watcher that wakes only on change. The Stop hook as a turn-end signal. Append-only status files. | An agent sits at the top. Crew members are started fresh for each task, which throws away the cache. The person talks only to the captain. |
| SwarmForge (unclebob/swarm-forge) | A fixed set of role agents in tmux, a `handoffd` daemon, hand-offs as git commits plus inbox/outbox queues, and a web dashboard. | Persistent role seats. Git commits as the hand-off medium. A daemon that only wakes things up. | One worktree per role, which adds a sync step to every turn. A queue protocol the agents must follow. Written in Babashka. |
| OpenRig (mvschwarz/openrig) | Teams declared in YAML; a daemon, CLI, MCP server and web UI on top of tmux; seats that can be snapshotted and restored. | Seats declared in configuration. Resuming a seat from its session id. A shared terminal view. | Agents manage their own team through 17 MCP tools, which is a protocol to carry. Heavy. A recorded failure on `send-keys` payloads over 128 KB. |
| herdr | A terminal multiplexer, written in Rust, that shows whether each agent is working, blocked or idle, with a socket API. | A possible base for the [[cockpit]]. | Unverified: on 2026-09-28 its reported star count looked implausible, and which repository is the real one was unclear. |
| Claude Code agent teams | Experimental: a lead session with teammates, JSON mailboxes, and `TeammateIdle` and `TaskCompleted` hooks. | Hooks as the signal that an agent is idle. | Experimental and interactive only; teammates cannot be resumed; the lead is an agent at the top; Claude only. |
| vibe-kanban | A kanban board that launches agents over `stream-json`, `app-server` and ACP. Being wound down. | One structured-protocol adapter per harness. | Being wound down. Its issue #2993 shows that sessions are keyed by folder path, so the worktree path must stay stable. |
| Backlog.md (MrLesk/Backlog.md) | One Markdown file per task, with front matter, and a board view. | A Markdown file per task. A board view. | It keeps state in a `status` field. Directories and `git mv` do that job here. |
| claude-squad, uzi | Parallel agent sessions in tmux. | Pausing and resuming one instance. A "checkpoint" as a rebase onto `main`. | Parallel within one repository, and no hand-off between agents. |
| Crystal, Conductor, Polygraph | A desktop app that relaunches per turn (deprecated); a closed desktop app; a largely hosted service for cross-repository memory. | Crystal's cost of relaunching per turn, as a lesson. | Deprecated, closed, or hosted. |

## Why none is adopted

- Most put an agent at the top: a captain, a lead, or agents managing
  themselves through MCP tools. The loop's supervisor is a program that
  decides from what it observes (stereorepo's DR-306).
- Several make the agents follow a messaging protocol, which stalls whenever
  an agent ignores an instruction. In the loop, agreement is observed as a
  [[quiet-turn|quiet turn]], never declared (stereorepo's DR-307).
- Their main value is parallel work within a repository. Here a repository is
  the unit of parallelism, and its Issues run one at a time
  (stereorepo's DR-311).
- Several start a new session for each task, or a new process for each turn.
  A seat keeps one session for the whole Issue (stereorepo's DR-309).
- Several are closed, deprecated, or being wound down.
- They keep their state in databases and daemons. The loop keeps it in files
  and git: an Issue's [[stage]] is the directory its file sits in
  (stereorepo's DR-308).
- None of them runs a pair in which both seats write code and agreement is
  observed rather than declared.

---

**See also:** [[supervisor]], [[seat]], [[cockpit]]
