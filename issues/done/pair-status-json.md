---
difficulty: easy
parent: flight-instruments
waits_on: [status-lists-what-waits-on-the-developer]
---

# `just pair-status --json`

`just pair-status` prints a screen for the developer. A session driving the
loop needs the same state as data, without parsing that screen.

The single derivation already exists: `status_view` in `pair/loop.py` returns
plain data, and `status` renders the screen from it. What is missing is a way
to print that data.

## What is wanted

- `pair.py status` takes `--json` and prints one JSON object instead of the
  screen. The rendering is a function in `pair/loop.py` beside `status`
  (say `status_json(repo, main)`, returning `json.dumps(status_view(...))`),
  so the tests, which mostly call `loop` directly rather than the CLI, can reach it;
  `pair.py` only chooses between the two. The `pair-status` recipe passes its
  flags through (`pair-status *args`), as `groom` does.
- The object is `status_view` as it stands: `waiting`, `underway`, `order`,
  `to_groom`, `counts`, `sessions` and `turns`. Without `--json` the output
  is unchanged.
- `pair/README.md` documents `--json` beside `just pair-status` and lists the
  object's keys, pointing to `status_view`'s docstring for their fields
  rather than copying it.

## Out of scope

- Publishing the state outside the repository (`cockpit-status-convention`).
- Changing what `status_view` derives, or adding anything the screen does not
  show.
- A stable versioned schema; the keys follow `status_view`.

## Done when

- A test in `pair/test_pair.py` drives the loop into a state with something
  waiting on the developer, an Issue underway and a Flight in the running
  order (the fixtures near the existing `status` tests already build these),
  and checks that `json.loads` of the `--json` rendering equals `status_view`
  for that state.
- `just pair-status --json` prints valid JSON on this repository.
- `pair/README.md` documents it, and `just gate` passes.

## The plan

1. **`pair/loop.py`**: add `status_json(repo, main="main") -> str` right after
   `status`, returning `json.dumps(status_view(repo, main))` on one line (so
   it pipes to `jq`). Everything in `status_view` is already JSON-native: the
   state and turn rows come from `json.loads`, the rest are strings, lists,
   dicts and bools. Its docstring says it is `status_view` as JSON and
   points there for the fields.
2. **`pair/pair.py`**: import `status_json`; give the `status` subparser a
   `--json` flag (`action="store_true"`); in `main`, print `status_json(repo)`
   when it is set, `status(repo)` otherwise.
3. **`justfile`**, which is generated: in `.meta/lib/render/writers.py`,
   `pair-status *args:` passing `{{args}}` to `pair.py status`, as `groom`
   does; in `CONTRACT` in `.meta/checks/files/justfile.py`, `pair-status`
   takes `(("args", FLAGS),)`; then `just render`. A flag only, so it keeps
   to DR-259. Its comment, which `just --list` shows, ends `(--json)` the
   way `groom`'s ends `(--rerank)`.
4. **`pair/README.md`**: in the "watch" row of *Using it*, add that
   `just pair-status --json` prints the same state as one JSON object with
   keys `waiting`, `underway`, `order`, `to_groom`, `counts`, `sessions`
   and `turns`, whose fields `status_view`'s docstring describes; add
   `status --json` to the portfolio paragraph below the table.
5. **`pair/test_pair.py`**: in `StatusTest`, import `status_json` and
   `status_view` from `loop`, and add
   `test_json_holds_what_the_screen_shows`. It builds one board with a
   send-back in the backlog (as in `test_a_send_back_waits_with_its_first_line`),
   an Issue underway with saved `State` and a session (as in
   `test_take_over_lines_follow_the_counts`), and a Flight with a done part
   and two backlog parts in `ORDER` (as in
   `test_the_running_order_shows_ripeness_and_flights`). It asserts
   `json.loads(status_json(repo)) == status_view(repo)`, and spot-checks
   that the send-back is in `waiting`, the Issue in `underway` with its turn,
   and the Flight's parts nested in `order` in run order. Then it runs
   `pair.py status --json` as a subprocess, the way
   `test_the_script_exits_with_its_code` does, and checks that its stdout
   parses to the same object, which covers the flag and the import.

Then `just gate pair` while working, `just gate`
at the end, and `just pair-status --json | python3 -m json.tool` on this
repository.

**Risk.** Little. Equality with `status_view` would hide a tuple turned into
a list, but `status_view` builds lists throughout. The subprocess run reads
`.pair/` of the bench repository, not this one, so it does not depend on the
live loop.

## Notes for the next reader

- **The plan missed that the `justfile` is generated.** Step 3 changed
  `.meta/lib/render/writers.py`, which renders the recipe, and `CONTRACT` in
  `.meta/checks/files/justfile.py`, which pins each recipe's parameters:
  `pair-status` now takes `(("args", FLAGS),)`, like `groom`. The `justfile`
  was re-rendered with `just render`, not edited by hand.
- `just` echoes the recipe's command on stderr, so the stdout of
  `just pair-status --json` is pure JSON; `| python3 -m json.tool` parses it
  on this repository.
- `StatusTest.test_json_holds_what_the_screen_shows` also runs
  `pair.py status --json` as a subprocess against the bench repository, so
  the flag, the import and the printing are covered, not only `status_json`.
