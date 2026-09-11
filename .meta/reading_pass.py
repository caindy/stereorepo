#!/usr/bin/env python3
"""Whether the coder's pre-review reading pass ran, read from the run's own
execution file (solorepo's DR-165).

The last paragraph of `coder.yml`'s take prompt buys a reader who did not write
the diff: one subagent, on the smaller model, told to read the branch against
its base and report. The paragraph also says the pass is silent — no comment,
no verb, no state of its own — so nothing GitHub holds distinguishes a run that
spawned it from one that skipped the sentence and went straight to the review
request (solorepo's #255). A prompt half with no falsifier is the failure
solorepo's DR-122 records, one Role over: three reviewer runs ended "waiting for
the agents", the check reported success each time, and from the coder's side
that looked like a review not yet begun.

    python3 .meta/reading_pass.py <execution-file> --model M --reader R

The fact it reads is the run's own, not GitHub's. `anthropics/claude-code-action`
writes every SDK message of the session to a JSON file and names it in its
`execution_file` output, and the last of them is the `result`, which carries a
per-model breakdown. The SDK's own declaration of that field is what makes the
read sound:

    Per-model totals for every model call made through the query pipeline
    during this query() call — main loop, Task subagents, sidechains, and
    internal calls such as compaction and Workflow agents.
        — @anthropic-ai/claude-agent-sdk, `SDKResultMessage.modelUsage`

against the sibling field, which is where the naive read would have gone:

    MAIN AGENT LOOP ONLY — excludes Task subagent, sidechain, and auxiliary
    model calls
        — the same declaration, `usage`

So a subagent's tokens land in `modelUsage` under the model it ran on, and on a
`medium` run — the coder at Opus, the reader at Sonnet — a Sonnet entry in the
breakdown is a call the main loop did not make. That is the mark, and it costs
no ceremony: the file is on the runner, the read is local, and what it reports
is the step's exit status and nothing on the pull request.

**What it cannot tell**, stated because a check trusted past its reach is worse
than none:

- On a run whose own model is the reader's, the breakdown answers nothing. That
  is `easy`, where both are Sonnet, and the answer is `indistinguishable` rather
  than a pass it did not earn.
- A Sonnet call is a necessary condition and not a sufficient one. It says a
  subagent ran on the smaller model; it does not say the subagent read the diff,
  and nothing short of reading the transcript would. The pass this catches is
  the one that never started, which is the one that was observed.
- A breakdown that cannot be read — no file, no `result`, no `modelUsage` — is
  `unreadable` and red. The pass is the branch that has to be reached, as in
  solorepo's DR-122: a read that did not arrive is not a green.
"""
import argparse
import json
import pathlib
import sys

# The states the step passes on. `indistinguishable` is among them because a
# read that cannot tell has found nothing wrong; `unreadable` is not, because a
# read that did not arrive has not found nothing.
GREEN = ("ran", "indistinguishable")


def family(model):
    """The word in a model id that survives a version bump.

    Ids here are `claude-<family>-<version>`, and the version moves under a
    running workflow: `claude-sonnet-5` is what the prompt names and
    `claude-sonnet-5-20260201` is what a breakdown may key on. Taken from the
    id rather than from a list of families, so a model this file has never
    heard of is read the same way as the two the workflow uses today.
    """
    parts = model.split("-")
    return parts[1] if len(parts) > 2 and parts[0] == "claude" else model


def result_of(messages):
    """The last `result` message, or None.

    The last and not the first: a streaming-input session carries a running
    total and each result restates it, which the field's own declaration says
    to read that way round.
    """
    results = [m for m in messages if isinstance(m, dict) and m.get("type") == "result"]
    return results[-1] if results else None


def reading(messages, model, reader):
    """What the breakdown says about the reading pass: a state and the words
    for it.

    `ran` and `indistinguishable` are green, `silent` and `unreadable` red.
    """
    result = result_of(messages)
    if result is None:
        return "unreadable", "the execution file holds no `result` message"
    usage = result.get("modelUsage") or {}
    if not usage:
        return "unreadable", "the `result` message carries no `modelUsage` breakdown"
    used = ", ".join(sorted(usage))
    want = family(reader)
    if family(model) == want:
        return "indistinguishable", (
            f"this run's own model is {model}, so a {want} call in the breakdown "
            f"is the main loop's and says nothing about the reading pass; "
            f"the breakdown was {used}")
    if any(want in key for key in usage):
        return "ran", (f"a {want} call is in the breakdown of a run whose own model "
                       f"is {model}, so the reading pass spawned its subagent; "
                       f"the breakdown was {used}")
    return "silent", (f"no {want} call is in the breakdown of a run whose own model "
                      f"is {model}, so no subagent ran on the reader's model and "
                      f"the diff went to the reviewer with nobody but its author "
                      f"having read it; the breakdown was {used}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("execution_file",
                   help="the action's `execution_file` output: the session's SDK "
                        "messages, as JSON")
    p.add_argument("--model", required=True,
                   help="the model this run was given")
    p.add_argument("--reader", required=True,
                   help="the model the reading pass's subagent was told to use")
    args = p.parse_args()

    path = pathlib.Path(args.execution_file)
    try:
        messages = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        state, words = "unreadable", f"{path}: {exc}"
    else:
        if not isinstance(messages, list):
            state, words = "unreadable", f"{path}: not a list of SDK messages"
        else:
            state, words = reading(messages, args.model, args.reader)

    print(f"{state}: {words}")
    sys.exit(0 if state in GREEN else 1)


if __name__ == "__main__":
    main()
