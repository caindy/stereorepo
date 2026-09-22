"""What every module of the package shares: the levels, the pull request shape, and the
failures a call through the channel raises short of exiting (solorepo's DR-264)."""
import json
import subprocess
from typing import Any

import channel

Pull = dict[str, Any]
"""One pull request as GitHub answers for it, whichever fields were asked for."""


UNREACHED = (OSError, subprocess.CalledProcessError, json.JSONDecodeError, KeyError, TypeError)
"""What a call through `channel` raises short of exiting: `gh` would not start, it
failed where the caller passed `tolerate_fail`, or GitHub answered with something
other than the JSON the caller reads. A verb that degrades rather than exits names
this tuple, so a defect in the code it guards is not reported as a GitHub failure."""


DIFFICULTIES = ("easy", "medium", "hard", "human")


# The two levels a loop takes on the label's own event (solorepo's DR-112), which is what
# makes a Challenge at either one a run's rather than a session's.
LOOP_LEVELS = ("easy", "medium")


# The one level a run lands itself (solorepo's DR-235). The other three say which kind of
# Job takes the Challenge, which is the reviewer's verdict to give; this one says
# the next step is not a Job's at all, which is the fact a run is the first to
# hold and nobody else can see.
RUN_LEVEL = "human"


def kind(number: str | int) -> str:
    """Pull request or Issue, asked of GitHub. The numbers are one sequence and
    the verbs that take either — `comment`, `revise` — should not make a
    caller say which."""
    found = channel.gh("api", f"repos/{channel.repo()}/issues/{number}")
    return "pull request" if found.get("pull_request") else "issue"
