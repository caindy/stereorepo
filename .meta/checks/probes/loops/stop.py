"""The `stop` verb: the claim released and the Challenge handed to the solo (solorepo's DR-112).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""

import time
from typing import Any

from checks.collect import check
from checks.probes.harness import (
    FakeIssue,
    load_channel,
    outcome,
    stood_in,
)


@check("stop probes", pre=True)
def stop_probes() -> list[str]:
    """`stop` against one Issue's labels and assignees: the hand-back, the refusal, and a GitHub that fails every call.

    A stop on a Challenge labels it `human`, removes the level it was at, and
    releases the assignee (solorepo's DR-112); a stop on an Issue that is not
    a Challenge is refused, naming the label it lacks; and a GitHub that fails
    every call, which is what a deleted Issue or a token without the scope
    looks like to the channel, is tolerated without an exit, each step warning
    on stderr rather than ending the hand-back.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    problems = []

    def stopped(fake: Any, issue: str, body: str) -> Any:
        """`stop(issue, body)` against `fake`: what it exited with, and what it printed on both streams."""
        with stood_in(channel, gh=fake), stood_in(time, sleep=lambda _: None):
            return outcome(lambda: move.stop(issue, body))

    fake = FakeIssue(["challenge", "medium"], assignees=["o-r-coder"])
    ended = stopped(fake, "7", "stopped working")
    if ended.code is not None:
        problems.append(f"stop: normal stop failed with error: {ended.code}")
    if "human" not in fake.labels:
        problems.append("stop: normal stop did not label issue as `human`")
    if "medium" in fake.labels:
        problems.append("stop: normal stop did not remove the stale level label")
    if "o-r-coder" in fake.assignees:
        problems.append("stop: normal stop did not release the assignee")

    fake = FakeIssue(["medium"], assignees=["o-r-coder"])
    ended = stopped(fake, "7", "stopped working")
    if ended.code is None or "not a Challenge" not in ended.code:
        problems.append("stop: stopping on a non-Challenge should refuse with label error, "
                        f"got: {ended.code}")

    fake = FakeIssue(["challenge", "medium"], fail=True)
    ended = stopped(fake, "7", "stopped working")
    if ended.code is not None:
        problems.append("stop: persistent API failure should be tolerated without crashing, "
                        f"but got: {ended.code}")
    if "warning" not in ended.err:
        problems.append("stop: persistent API failure should print warnings to stderr")
    return problems
