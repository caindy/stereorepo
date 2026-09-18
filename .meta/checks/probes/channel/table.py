"""The verb table: which Role holds which verb, and what a program's `--help` lists.
"""
import argparse
import os
from typing import Any

import yaml

from collect import META, ROOT, check
from probes.harness import (
    load_channel,
)


@check("channel table probes", pre=True)
def channel_table_probes():
    """The verb table is the parsers, and a Role's reading is the table (solorepo's DR-117).

    Every verb the table names parses in the program it names, every verb a
    program parses is in the table, every program the table names is where it
    says and executable, every `held_by` is a Role the authority assertions
    know or one of the two readers that are not Roles, and PR First's own
    steps type no command — the verbs are the steps, and a step that spelled
    one would be the second copy found drifting on solorepo's #117.

    The Roles are read from `imported/authority.yaml`, because they are the
    channel's and live with it under `imported/`; a portfolio's own
    `authority.yaml` holds the accounts they use (solorepo's DR-123). `solo` and
    `workflow` are the two readers of the table that are not Roles.
    """
    _, table, programs = load_channel()
    roles = {r["name"] for r in (yaml.safe_load(
        (META / "assertions" / "imported" / "authority.yaml").read_text()) or {}).get("roles") or []}
    readers = roles | {"solo", "workflow"}
    problems = [problem for program in table.get("programs") or []
                for problem in _program_problems(program, programs[program["name"]].build_parser(), readers)]
    return problems + _steps_typing_commands(table.get("discipline"))


def _program_problems(program: Any, parser: Any, readers: Any) -> list[str]:
    """One program's disagreements with the table: its path, its executability, the verbs one side names and the other does not, and each `held_by` that is not a reader."""
    name = program["name"]
    path = ROOT / program["path"]
    problems = []
    if path != META / "say" / name:
        problems.append(f"{name}: the table says {program['path']}, and the channel is .meta/say/{name}")
    if not path.is_file() or not os.access(path, os.X_OK):
        problems.append(f"{program['path']} is not an executable file")
    subs = next((a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)
    parsed = set(subs.choices) if subs else {name}
    asserted = {v["name"] for v in program["verbs"]}
    problems += [f"{name}: the table names `{verb}`, which the program does not parse" for verb in sorted(asserted - parsed)]
    problems += [f"{name}: the program parses `{verb}`, which the table does not name" for verb in sorted(parsed - asserted)]
    for verb in program["verbs"]:
        problems += [f"{name} {verb['name']}: held by {who!r}, which is not a Role or a reader"
                     for who in verb.get("held_by") or [] if who not in readers]
        if not verb.get("held_by"):
            problems.append(f"{name} {verb['name']}: held by nobody")
    return problems


def _steps_typing_commands(discipline: Any) -> list[str]:
    """Each step of the Discipline the table names that types a channel command: the verbs are the steps."""
    disciplines = yaml.safe_load((META / "assertions" / "imported" / "disciplines.yaml").read_text()) or {}
    return [f"{d['name']} step {i} types a command; the verbs are the steps"
            for d in disciplines.get("disciplines") or [] if d["name"] == discipline
            for i, step in enumerate(d.get("steps") or [], 1) if ".meta/say" in step]
