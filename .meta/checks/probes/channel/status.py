"""A Decision's status as `move` reads it off the record.
"""

import yaml

from checks.collect import META, check
from checks.probes.harness import (
    load_channel,
)


@check("channel status probes", pre=True)
def channel_status_probes():
    """`move`'s reading of the status a Decision's entry gives itself, against
    `yaml`'s, over every entry in the record (solorepo's DR-164).

    `supersede --by DR-nnn` asks whether the entry was adopted, because a
    listing cannot tell an answer from a hole: a number written back as
    WITHDRAWN is a file at that path like any other. The channel cannot import
    `yaml` — those programs run under plain `python3`, where this gate takes
    its own from a `uvx` shebang — so the status is matched in the entry's
    text, and what the match assumes about that text is checked here. Held
    against the whole record and not a fixture, because the assumption is about
    the entries that exist: the day one is written some other way, this is what
    says so, and the verb reads `None` and refuses rather than reading whichever
    line matched.

    Two shapes the match cannot speak to, and must read as `None`, are written
    out as fixtures because neither is in the record: two entries in one text,
    and an entry with no status at all. A refusal that fires only on a file
    nobody has written yet is one nothing has run.
    """
    _, _, programs = load_channel()
    move = programs["move"]
    problems = []
    for path in sorted((META / "assertions" / "decisions").glob("DR-*.yaml")):
        entries = (yaml.safe_load(path.read_text()) or {}).get("decisions") or []
        said = move.entry_status(path.read_text())
        if len(entries) != 1:
            if said is not None:
                problems.append(f"channel status: {path.name} holds {len(entries)} entries and "
                                f"the channel read {said!r} out of it, where a status is one "
                                "entry's own")
            continue
        want = entries[0].get("status")
        if said != want:
            problems.append(f"channel status: the channel reads {path.name} as {said!r} and "
                            f"`yaml` reads it as {want!r}")
    for shape, text in (("two entries", "decisions:\n  - id: a\n    status: ADOPTED\n"
                                        "  - id: b\n    status: WITHDRAWN\n"),
                        ("no status", "decisions:\n  - id: a\n    name: n\n")):
        if (said := move.entry_status(text)) is not None:
            problems.append(f"channel status: {shape} read as {said!r}, where nothing in that "
                            "text is the status of one entry")
    return problems
