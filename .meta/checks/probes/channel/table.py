"""The verb table: which Role holds which verb, and what a program's `--help` lists.
"""
import argparse
import os

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
    problems = []
    roles = {r["name"] for r in (yaml.safe_load(
        (META / "assertions" / "imported" / "authority.yaml").read_text()) or {}).get("roles") or []}
    readers = roles | {"solo", "workflow"}
    for program in table.get("programs") or []:
        name = program["name"]
        path = ROOT / program["path"]
        if path != META / "say" / name:
            problems.append(f"{name}: the table says {program['path']}, and the channel is .meta/say/{name}")
        if not path.is_file() or not os.access(path, os.X_OK):
            problems.append(f"{program['path']} is not an executable file")
        parser = programs[name].build_parser()
        subs = next((a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)
        parsed = set(subs.choices) if subs else {name}
        asserted = {v["name"] for v in program["verbs"]}
        for verb in sorted(asserted - parsed):
            problems.append(f"{name}: the table names `{verb}`, which the program does not parse")
        for verb in sorted(parsed - asserted):
            problems.append(f"{name}: the program parses `{verb}`, which the table does not name")
        for verb in program["verbs"]:
            for who in verb.get("held_by") or []:
                if who not in readers:
                    problems.append(f"{name} {verb['name']}: held by {who!r}, which is not a Role or a reader")
            if not verb.get("held_by"):
                problems.append(f"{name} {verb['name']}: held by nobody")
    disciplines = yaml.safe_load((META / "assertions" / "imported" / "disciplines.yaml").read_text()) or {}
    for d in disciplines.get("disciplines") or []:
        if d["name"] == table.get("discipline"):
            for i, step in enumerate(d.get("steps") or [], 1):
                if ".meta/say" in step:
                    problems.append(f"{d['name']} step {i} types a command; the verbs are the steps")
    return problems
