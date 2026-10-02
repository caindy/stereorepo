---
difficulty: developer
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

`seat-sandbox-permissions`, which changed the same command line, has landed;
measure with its `--settings` sandbox in place.

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

- The issue file names what differs between two fresh sessions' requests
  (the diff, or a summary of it), and the measured second-session write for
  the flags chosen.
- `CONTEXT`'s docstring carries the extended table and says why the chosen
  flags are the floor, or what they give up.
- If the flags change, `SeatCommandTest.test_a_seat_loads_the_project_settings_alone`
  in `pair/test_pair.py` asserts the new argv. If skills move to
  `--append-system-prompt`, a test asserts the appended text holds `AGENTS.md`
  and every skill under `.claude/skills/`, and that the loop's seat prompt still
  comes last, so the skills cannot drift from the repository.
- If a seat cannot start `claude` sessions from its sandbox (no network to
  the API, or no credentials), it leaves the exact commands for the
  two-session measurement and the request diff in the issue file, and the
  developer runs them and records the results at the desk check; the flags
  are not changed on a guess.
- Developer check: the measurements spend the developer's subscription, and
  only they can judge a seat that has lost its skills. At the desk check they
  re-run the two-session measurement with the branch's flags. After it lands,
  they compare the first-turn cache writes of the next Issue in
  `.pair/turns.jsonl` with the table, and confirm that the pair converged.

## The plan

The seat's command line is built in one place, `command()` in
`pair/seats.py`, from `CONTEXT` and the role's prompt (`pair/pair.py` reads
`primary.md` or `secondary.md` once, so the loop's own appended text is fixed
per role). The ~7,300 tokens therefore come from what Claude Code itself
assembles: the request is cached as tools, then system, then messages, and the
cache breaks at the first byte that differs. Likely candidates are the
environment block (the session's scratchpad path, the date), the `gitStatus`
snapshot, and the skills and `CLAUDE.md` reminders in the first user message.

1. **Capture two requests.** Start two fresh one-turn sessions with the seat's
   exact flags, taken from `command("p", confinement(cwd))`, with
   `ANTHROPIC_BASE_URL` pointed at a local recorder that writes each request
   body to a file and forwards it. The recorder is a throwaway script in the
   scratchpad, not repository code. Diff the two bodies field by field (tools,
   each system block, each message block) and record the first differing block
   and its size in this file.
2. **Try a byte-identical variant**, only if the difference is in what the
   project source loads: `--setting-sources ""` with `AGENTS.md` and the
   `SKILL.md` texts under `.claude/skills/` appended ahead of the role prompt.
   Measure its second-session write. If the difference is in Claude Code's own
   environment block or `gitStatus`, no flag removes it. In that case it is
   the floor.
3. **Write the result into the code.** Either:
   - **Floor:** `CONTEXT` is unchanged. Its docstring gains the extended table
     and names the per-session block that sets the floor.
   - **Cheaper flags:** `CONTEXT` changes, and a new helper in `seats.py`
     builds the appended prompt from `AGENTS.md` and the skills, sorted by
     path so the order is deterministic, with the role prompt last.
     `command()` uses that helper.
4. **Tests** in `pair/test_pair.py`, `SeatCommandTest`:
   - Floor: none needed beyond the existing
     `test_a_seat_loads_the_project_settings_alone`, which still holds.
   - Cheaper flags: update that test to the new argv, and add one that builds
     the prompt in a temporary repository with an `AGENTS.md` and two skills.
     It asserts that both skill texts and `AGENTS.md` appear, that the role
     prompt comes last, and that two builds are byte-identical.

**Risks.** The seat's sandbox (`command()` in `pair/seats.py`) lets commands
reach any domain, but it does not set `allowLocalBinding`, so the recorder in
step 1 cannot listen on a local port, and a nested `claude` may not reach the
developer's login in the macOS keychain. Steps 1 and 2 will probably not run
from a seat. Try step 1 once; if it fails on either, the
seat writes the recorder script and the exact commands into this file, the
developer runs them at the desk check, and step 3 waits for their numbers
rather than guessing. Inlining the skills turns them from on-demand skills
into always-present text: the seat could no longer invoke them as `/skill`,
and the prompt would grow. Only the developer can judge whether that is an
acceptable trade, and that is why the issue is `developer`.

## What the seat found (for the desk check)

Step 1 was tried once from the seat and failed: binding `127.0.0.1` raises
`PermissionError: [Errno 1] Operation not permitted`, so no recorder can
listen. Steps 1 and 2 are therefore the developer's, and `CONTEXT` and its
tests are unchanged on this branch.

The likely cause, from evidence short of a measurement:

- Claude Code's environment section of the system prompt names the
  session's own scratchpad directory, which contains the session id (a seat
  sees a line like `Scratchpad directory: /private/tmp/claude-501/<project>/<session-uuid>/scratchpad`).
  The section also holds the working directory, the date and the git status. A
  per-session byte in the system prompt means that everything after it is
  written fresh: the rest of the system prompt, the loop's role prompt
  appended by `--append-system-prompt`, and the first message.
- `claude --help` (2.1.287) has `--exclude-dynamic-system-prompt-sections`:
  "Move per-machine sections (cwd, env info, memory paths, git status) from
  the system prompt into the first user message. Improves cross-user
  prompt-cache reuse." That flag would keep the project source and its
  skills and still make the system prompt, the role prompt included,
  identical across sessions. It is a stronger candidate than step 2's
  inlining, which loses `/skill` invocation. Its help says it is "ignored
  with --system-prompt"; the seat uses `--append-system-prompt`, which keeps
  the default system prompt, so the flag should apply. The moved sections
  still differ per session, but from the first message on, after the cached
  system prompt.

The desk check below disproved this suspected cause. See "Outcome" at the end.

### Measuring at the desk check

In a scratch clone of this branch, save the script below as `measure.py` at
the root, and run it three times. Each run spends two short Sonnet sessions:

```sh
python3 measure.py --model sonnet
python3 measure.py --model sonnet --exclude-dynamic-system-prompt-sections
python3 measure.py --model sonnet --setting-sources "" --disable-slash-commands
```

Later flags override `CONTEXT`'s, so the third run is the table's cheapest row
without the `AGENTS.md` text. Each run prints both sessions' cache writes and the
first request block that differs, with a diff of it, and leaves the two
main requests in `session-1.json` and `session-2.json`.

Then send the issue back with the numbers. What the next turn does with them:

- If the second run's session-2 write is clearly below ~7,300, add
  `--exclude-dynamic-system-prompt-sections` to `CONTEXT`. Extend its
  docstring's account with the new row. In
  `test_a_seat_loads_the_project_settings_alone`, assert the flag is present.
- Otherwise, record the ~7,300 tokens as the floor in `CONTEXT`'s docstring,
  naming the first differing block the script printed. Then reconsider step 2
  only if that block is something the project source loads.

The script's diff logic was checked offline on synthetic requests, including
two with different numbers of system blocks, where it names both blocks
rather than stopping at the shorter request. Its proxy and its sessions have
not run.

```python
"""Measure what a fresh seat session writes to the prompt cache, and why.

Runs two fresh one-turn primary-seat sessions with the seat's exact command
line through a local recording proxy, prints each session's cache write and
read, and names the first request block that differs between the two.

Usage, from the root of a scratch clone of the branch:
    python3 measure.py [extra claude flags...]
"""

import difflib
import http.server
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, "pair")
from seats import command, confinement  # noqa: E402

UPSTREAM = "https://api.anthropic.com"
HOP = {"host", "content-length", "accept-encoding", "connection", "transfer-encoding"}
bodies: list[dict] = []


class Recorder(http.server.BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("content-length", 0)))
        if self.path.split("?")[0] == "/v1/messages":
            bodies.append(json.loads(body))
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        request = urllib.request.Request(
            UPSTREAM + self.path, body or None, headers, method=self.command
        )
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as error:
            response = error
        self.send_response(response.status)
        for k, v in response.headers.items():
            if k.lower() not in HOP:
                self.send_header(k, v)
        self.end_headers()
        read = getattr(response, "read1", response.read)
        while chunk := read(8192):
            self.wfile.write(chunk)
            self.wfile.flush()

    do_GET = do_POST


def blocks(body: dict) -> list[tuple[str, str]]:
    """The request in cache order: tools, system blocks, every message's blocks."""
    out = [("tools", json.dumps(body.get("tools", []), indent=1, sort_keys=True))]
    out += [(f"system[{i}]", s["text"]) for i, s in enumerate(body.get("system", []))]
    for m, message in enumerate(body["messages"]):
        content = message["content"]
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        out += [
            (f"messages[{m}][{i}] ({message['role']})", c.get("text", json.dumps(c)))
            for i, c in enumerate(content)
        ]
    return out


def first_difference(a: dict, b: dict) -> str:
    left, right = blocks(a), blocks(b)
    pad = [("(missing)", "")] * abs(len(left) - len(right))
    pairs = list(zip(left + pad, right + pad))
    for at, ((name, x), (other, y)) in enumerate(pairs):
        if (name, x) != (other, y):
            after = sum(len(p[0][1]) for p in pairs[at:])
            diff = difflib.unified_diff(
                x.splitlines(), y.splitlines(), name, other, lineterm="", n=1
            )
            head = f"first difference: {name} / {other}, {after} chars from there on\n"
            return head + "\n".join(list(diff)[:40])
    return "the two main requests are byte-identical in every block"


def main() -> None:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Recorder)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{server.server_port}"
    prompt = Path("pair/prompts/primary.md").read_text()
    argv = command(prompt, confinement(Path.cwd())) + sys.argv[1:]
    turn = {"type": "user", "message": {"role": "user", "content": "Reply: ok."}}
    main_requests = []
    for session in (1, 2):
        start = len(bodies)
        out = subprocess.run(
            argv, input=json.dumps(turn) + "\n", env=env, capture_output=True, text=True
        ).stdout
        events = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
        usage = [e for e in events if e.get("type") == "result"][-1]["usage"]
        print(
            f"session {session}: "
            f"cache write {usage.get('cache_creation_input_tokens')}, "
            f"read {usage.get('cache_read_input_tokens')}"
        )
        main_requests.append(max(bodies[start:], key=lambda b: len(b.get("tools", []))))
        Path(f"session-{session}.json").write_text(json.dumps(main_requests[-1], indent=1))
    print(first_difference(*main_requests))


if __name__ == "__main__":
    main()
```

### Measured at the desk check

Run on 2026-10-02 with Claude Code 2.1.287, Sonnet, from a linked worktree of
a scratch clone of this branch at `fc03d5d`. The script as written fails in a
plain clone, because `confinement` accepts only a linked worktree, so it was
run from one. Each row is one run of `measure.py`: two fresh one-turn
sessions, back to back.

| Extra flags | Session 1 write / read | Session 2 write / read |
|---|---|---|
| none (the seat's flags) | 61,565 / 0 | 10,472 / 51,181 |
| `--exclude-dynamic-system-prompt-sections` | 12,802 / 48,792 | 11,259 / 50,337 |
| `--setting-sources "" --disable-slash-commands` | 65,132 / 0 | 5,394 / 59,742 |

The first row's session 1 wrote everything because nothing was cached yet;
the second row's session 1 read what the first row had cached.

The cause first drawn from these runs was wrong. See "Desk-check notes"
below. `measure.py` compares only the tools, the system blocks and the first
message. Within those it found a difference in the git status, because the
script had just written `session-1.json` into the clone. It never saw the
per-session `system`-role message that comes after the first message, and
that message is the real cause. `--exclude-dynamic-system-prompt-sections`
still lowers nothing (11,259 against 10,472). Why these numbers differ from
the table's earlier ones (7,263 for the seat's flags) is not known; they may
come from another version of Claude Code. The rows above and in the notes
replace them.

### Outcome

The floor branch of step 3 was taken. `CONTEXT` is unchanged, and so is its
test, `test_a_seat_loads_the_project_settings_alone`. `CONTEXT`'s docstring
now records about 10,500 tokens per fresh session as the floor. It names the
cause found in the desk-check notes below: a per-session `system`-role
message after the first message, which carries the last cache breakpoint and
differs in the scratchpad line, the sandbox allowlist's `tasks` directory and
the skills listing. Its table holds the desk check's rows, including
`CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1`. They replace the earlier rows.
Claude Code builds that message itself, so no seat flag lowers the floor.
The follow-up `seat-git-status-snapshot` was deleted, because its setting was
measured and saves nothing. `measure.py` above now compares every message,
not only the first, and labels each with its role; this was checked offline
on two synthetic requests that differ only in a later `system`-role message,
and has not been re-run against Claude Code.

## Desk-check notes (developer, 2026-10-02)

The cause recorded under "Measured at the desk check" and in `CONTEXT`'s
docstring is wrong. Further runs, from the same linked worktree with
`session-*.json`, `measure.py` and `measure2.py` in its `info/exclude`, so
the git status was the same in both sessions:

| Extra setting | Session 2 write / read |
|---|---|
| none (the seat's flags) | 10,468 / 51,181 |
| `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1` | 10,014 / 51,034 |
| none, with each call's usage recorded | 10,470 / 51,181 |

The environment variable removed the git status snapshot and the built-in
commit instructions, as documented, and the write did not fall. Each session
makes one API call, and every cache write has the 1-hour lifetime.

`measure.py` compares only the tools, the system blocks and the first
message, and reported the two requests as identical. They are not. Each
request carries a second message, role `system`, about 20,000 characters,
after the user's message, and the request's last cache breakpoint is on it.
Between two sessions it differs in:

- the scratchpad directory line, which names the session id;
- the sandbox's filesystem allowlist, which names a per-session
  `<session-id>/tasks` directory;
- the skills listing, which listed `plugin-authoring` in one session and not
  the other.

So the cache read ends at the system prompt, and the first message and that
block, about 26,000 characters, are written in every fresh session. Claude
Code 2.1.287 builds that block itself, and no seat flag removes it. An older
report (Hacker News item 47754795, Claude Code 2.1.104) found a repeated
identical session read everything from the cache. That no longer holds,
because of this per-session block.

To finish:

1. In `CONTEXT`'s docstring, replace the stated cause with the one above,
   and add the `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1` row. Keep the flags
   as they are.
2. Delete `issues/backlog/seat-git-status-snapshot.md` from this branch. The
   setting it proposes was measured above and saves nothing.
3. Correct "Measured at the desk check" and "Outcome" in this file to point
   at these notes.
4. Run no more measurements.
