#!/usr/bin/env python3
"""The coder workflow door, run from the pull request head (solorepo's DR-284).

Usage:
    .meta/coder_door.py coder before <n> --pass take|rebase|answer --event <event> \
        [--harness <harness>]
    .meta/coder_door.py coder between <n> --pass take|rebase|answer --event <event> \
        [--attempt N --outcome <outcome>] [--execution-file <path>]
    .meta/coder_door.py coder rescue <n> --pass take|rebase|answer [--event <event>] \
        [--branch-prefix <harness>]
    .meta/coder_door.py coder after <n> --pass take|rebase|answer --event <event> \
        --outcomes <outcome>[,<outcome>] [--branch-prefix <harness>] \
        [--execution-file <path>]

History in coder_door.history.md (solorepo's DR-171).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "say"))

import check_pr
from lib.coder_door import cli, coder_door, handoff
from lib.on import common

cli.DESCRIPTION = __doc__ or ""

build_parser = cli.build_parser
check_pr = check_pr
coder = coder_door.coder
common = common
cut_by_cap = handoff.cut_by_cap
Delivery = coder_door.Delivery
Ended = coder_door.Ended


def main() -> None:
    """Runs the coder door command-line interface."""
    cli.main()


if __name__ == "__main__":
    main()
