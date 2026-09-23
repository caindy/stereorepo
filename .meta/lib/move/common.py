"""What every module of the package shares: the levels, the pull request shape, and the
failures a call through the channel raises short of exiting (solorepo's DR-264)."""
import json
import subprocess
import sys
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


def refuse_a_level_and_a_mandate_apart(level: str | None, mandate: str | None,
                                       instead: str | None = None) -> None:
    """Refuse `--difficulty` and `--mandate` given apart from each other (solorepo's DR-278).

    A session may have the solo beside it, which is why the run refusal reads
    the run mark and stops there (solorepo's DR-235); may is not does, so a
    level typed from a session stands only where `mandate` carries the solo's
    own words asking for it. A mandate that is empty or whitespace is no
    mandate, since a caller that reaches for the flag and puts nothing in it has
    said no more than one that omitted it.

    The pair is read in both directions. A mandate with no level to stand behind
    is a flag that parses and does nothing, which includes the mandate given
    beside a flag that excludes `--difficulty`; the channel refuses what is
    typeable and inert everywhere else, and the words the caller was asked to
    quote are worth more than a silent discard. `instead` is what names that
    flag, so the refusal reads on the verb it was typed on and never mentions a
    flag the caller does not have — the two verbs that read this pair hold
    different surfaces around it, and only `move file` has `--roadmap`.

    `RUN_LEVEL` is exempt from the first direction for the reason it is exempt
    from the run refusal. It starts no Job and asks for the solo, so a Job saying
    the next step is not its own is not asked to quote a mandate whose absence is
    the thing it is reporting. It is not exempt from the second: a mandate quoted
    beside it is still a mandate that stands behind a level.

    Parameters:
        level (str | None): The level `--difficulty` names, or None where it names none.
        mandate (str | None): The solo's own words asking for `level`, or None;
            blank or whitespace counts as None.
        instead (str | None): The flag the caller gave that excludes `--difficulty`,
            written as it is typed, or None where none was given.

    Raises:
        SystemExit: If a level that is a verdict is given with no mandate behind
            it, or if a mandate is given with no level to stand behind.
    """
    quoted = bool((mandate or "").strip())
    if not level:
        if quoted:
            if instead:
                excluded = f"`{instead}` lands none"
                route = (f"Drop `--mandate`: `{instead}` and `--difficulty` exclude each other, "
                         "so there is no level here for his words to stand behind.")
            else:
                excluded = "none was given"
                route = ("Name the level he asked for: `--difficulty <level>`. Where he asked "
                         "for none, drop `--mandate` and let the reviewer read it.")
            sys.exit(f"say: `--mandate` quotes the solo asking for a level, and {excluded} "
                     "(solorepo's DR-278).\n"
                     "     Nothing was filed. `--mandate` is read only beside `--difficulty`, "
                     f"so his words reach nobody here.\n     {route}")
        return
    if level == RUN_LEVEL or quoted:
        return
    sys.exit(f"say: `{level}` skips the reviewer, and nothing here says the solo asked for it "
             "(solorepo's DR-230, solorepo's DR-278).\n"
             "     Nothing was filed. Without `--difficulty` it lands `challenge` alone, which "
             "is the reviewer's queue, and a level you inferred belongs in the body under "
             "`**Difficulty.**`, where it is a proposal the reader answers.\n"
             "     Where the solo did ask for this level, quote what he typed: "
             "`--mandate \"<his words>\"`.")


def kind(number: str | int) -> str:
    """Pull request or Issue, asked of GitHub. The numbers are one sequence and
    the verbs that take either — `comment`, `revise` — should not make a
    caller say which."""
    found = channel.gh("api", f"repos/{channel.repo()}/issues/{number}")
    return "pull request" if found.get("pull_request") else "issue"
