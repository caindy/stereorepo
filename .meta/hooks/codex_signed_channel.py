#!/usr/bin/env python3
"""Adapt Codex PreToolUse events to the signed-channel gate."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import codex_hooks

from lib.signed_channel import verdict


def decision(event: object) -> dict[str, object]:
    """Return Codex's nested hook decision for one tool event."""
    return codex_hooks.decision(event, verdict.blocked, verdict.record_evidence)


def main() -> int:
    """Read one Codex event and print its decision."""
    return codex_hooks.main(verdict.blocked, verdict.record_evidence)


if __name__ == "__main__":
    sys.exit(main())
