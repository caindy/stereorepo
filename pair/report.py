"""Report the replays kept under `.pair/replays/` by mode, on the four criteria.

`replay.py` keeps one directory per slug and mode. This module reads them,
and the source's own `.pair/` logs, into one column of measures per mode
(`single`, `pair`) and a third, `original`: the two-seat run that landed the
Issue, under older loop code and models. A column measures:

- Quality: the outcome, the gate runs and how many did not pass, the defect
  check, and the secondary seat's turns that changed something, with their
  files;
- Autonomy: pauses, send-backs and `Needs elaboration` headings;
- Time: wall-clock seconds and turns per stage;
- Tokens: API-equivalent cost, cache reads and cache writes, apart.

The defect check runs the tests an Issue that later fixed the replayed one
added, against the replay's result, in a temporary worktree of the clone's
`main`, so the kept clone is never written to. It reads; it never runs a
seat.
"""

from __future__ import annotations

import ast
import collections
import dataclasses
import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import board
from board import git, git_run
from loop import event_log, runtime_dir
from replay import replay_dir, replays_dir

MODES = ("single", "pair")
"""The modes a replay runs in, in the order the report prints them."""

COLUMNS = (*MODES, "original")
"""The report's columns: each mode, then the run that landed the Issue."""

ORIGINAL = "original: the run that landed it, by older loop code and models"
"""What the report says the `original` column is, once, after the last block."""

TOKENS = ("cost_usd", "cache_read", "cache_write")
"""The turn-row fields the report sums, each of which an older or failed row may lack."""

COMMAND = ("uv", "run", "--quiet", "--with", "pyyaml", "python")
"""What runs `-m unittest` for the defect check, from the test file's directory."""

SEVERITY = ("failed", "could-not-run", "passed", "none")
"""Defect results, the worst first: a replay with several fixes takes the worst."""

ELABORATION = re.compile(r"^#{1,6} Needs elaboration\s*$", re.MULTILINE)
"""A `Needs elaboration` heading, at any level."""

SUMMARY = re.compile(r"^FAILED \((.*)\)$", re.MULTILINE)
"""unittest's closing line for a run that did not pass, with its counts."""


@dataclasses.dataclass
class Measures:
    """One column of the report: one run of one slug, or the sum of several.

    `secondary` is the secondary seat's turns that changed something and all
    of its turns, or None in `single` mode, which has no secondary seat.
    `unlogged` counts the changed secondary turns whose row has no `files`,
    written before the loop logged them. `lacking` counts the rows without
    each of `TOKENS`. An empty `defects` is a run with no defect check.
    """

    runs: int = 1
    outcomes: collections.Counter[str] = dataclasses.field(default_factory=collections.Counter)
    gates: int = 0
    gate_failures: int = 0
    defects: collections.Counter[str] = dataclasses.field(default_factory=collections.Counter)
    defect_notes: list[str] = dataclasses.field(default_factory=list)
    secondary: tuple[int, int] | None = None
    files: set[str] = dataclasses.field(default_factory=set)
    unlogged: int = 0
    pauses: int = 0
    send_backs: int = 0
    elaborations: int = 0
    seconds: float = 0.0
    stages: collections.Counter[str] = dataclasses.field(default_factory=collections.Counter)
    cost_usd: float = 0.0
    cache_read: int = 0
    cache_write: int = 0
    lacking: collections.Counter[str] = dataclasses.field(default_factory=collections.Counter)

    def add(self, other: Measures) -> Measures:
        """The sum of two columns: numbers add, files join, and outcomes are tallied.

        The secondary measure stays None only if both are None.
        """
        if self.secondary is None or other.secondary is None:
            secondary = self.secondary or other.secondary
        else:
            secondary = (
                self.secondary[0] + other.secondary[0],
                self.secondary[1] + other.secondary[1],
            )
        return Measures(
            runs=self.runs + other.runs,
            outcomes=self.outcomes + other.outcomes,
            gates=self.gates + other.gates,
            gate_failures=self.gate_failures + other.gate_failures,
            defects=self.defects + other.defects,
            defect_notes=[*self.defect_notes, *other.defect_notes],
            secondary=secondary,
            files=self.files | other.files,
            unlogged=self.unlogged + other.unlogged,
            pauses=self.pauses + other.pauses,
            send_backs=self.send_backs + other.send_backs,
            elaborations=self.elaborations + other.elaborations,
            seconds=self.seconds + other.seconds,
            stages=self.stages + other.stages,
            cost_usd=self.cost_usd + other.cost_usd,
            cache_read=self.cache_read + other.cache_read,
            cache_write=self.cache_write + other.cache_write,
            lacking=self.lacking + other.lacking,
        )


def measure(  # noqa: PLR0913  # reason: each keyword is one source of a column, which replays and the original run fill differently
    turns: Iterable[Mapping[str, Any]],
    events: Iterable[Mapping[str, Any]],
    *,
    outcome: str,
    mode: str,
    seconds: float,
    elaborations: int = 0,
    defect: tuple[str, str] | None = None,
) -> Measures:
    """One column from a run's turn rows and events.

    `defect` is the defect check's result and its note, or None for a run
    that had none.
    """
    m = Measures(outcomes=collections.Counter([outcome]), seconds=seconds)
    m.elaborations = elaborations
    if defect is not None:
        m.defects[defect[0]] += 1
        if defect[1]:
            m.defect_notes.append(defect[1])
    secondary = []
    for row in turns:
        m.stages[row.get("stage", "?")] += 1
        for field in TOKENS:
            value = row.get(field)
            if value is None:
                m.lacking[field] += 1
            else:
                setattr(m, field, getattr(m, field) + value)
        if row.get("role") == "secondary":
            secondary.append(row)
    changed = [row for row in secondary if not row.get("quiet", True)]
    m.secondary = None if mode == "single" else (len(changed), len(secondary))
    for row in changed:
        m.files.update(row.get("files") or [])
        m.unlogged += "files" not in row
    for event in events:
        kind = event.get("kind")
        if kind == "gated":
            m.gates += 1
            m.gate_failures += event.get("outcome") != "passed"
        elif kind == "paused":
            m.pauses += 1
        elif kind == "sent-back":
            m.send_backs += 1
    return m


def rows(path: Path) -> list[dict[str, Any]]:
    """The JSON objects of a `.jsonl` file, one a line, or none if it is absent."""
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def replays(source: Path) -> dict[tuple[str, str], Path]:
    """Each replay directory under `source`, by the slug and mode its `outcome.json` names.

    The key is read from the file, not the directory's name, since a slug
    holds hyphens.
    """
    found = {}
    home = replays_dir(source)
    for path in sorted(home.glob("*/outcome.json")) if home.is_dir() else []:
        outcome = json.loads(path.read_text())
        found[outcome["slug"], outcome["mode"]] = path.parent
    return found


def difficulty(source: Path, slug: str) -> str:
    """The `difficulty:` of `slug`'s file in the source's `issues/done/`, or `unknown`."""
    path = source / board.ISSUES / "done" / f"{slug}.md"
    if not path.is_file():
        return "unknown"
    value = board.parse(path.read_text())[0].get("difficulty")
    return value if value in board.DIFFICULTIES else "unknown"


def elaborations(clone: Path, slug: str) -> int:
    """`Needs elaboration` headings in `slug`'s file on the clone's `main`.

    It is read from `main` rather than the checkout, which a replay that
    paused may have left dirty.
    """
    if not clone.is_dir():
        return 0
    listed = git(clone, "ls-tree", "-r", "--name-only", "main", board.ISSUES, check=False)
    for path in listed.splitlines():
        if path.endswith(f"/{slug}.md"):
            return len(ELABORATION.findall(git(clone, "show", f"main:{path}")))
    return 0


def since(events: Sequence[Mapping[str, Any]]) -> float:
    """Seconds from the first `started` event to the last `landed` one, or to the last event.

    An event's `at` is a local timestamp to the second, as `append_event`
    writes it, so the difference is to the second.
    """
    started = next((e["at"] for e in events if e.get("kind") == "started"), None)
    landed = [e["at"] for e in events if e.get("kind") == "landed"]
    end = landed[-1] if landed else (events[-1]["at"] if events else None)
    if started is None or end is None:
        return 0.0
    return (datetime.fromisoformat(end) - datetime.fromisoformat(started)).total_seconds()


def original(source: Path, slug: str) -> Measures | None:
    """The run that landed `slug`, from the source's own logs, or None if they have no turns.

    A slug sent back and started again has rows from each run, which are
    summed, and its wall-clock runs from the first start to the landing.
    """
    turns = [r for r in rows(runtime_dir(source, "pair") / "turns.jsonl") if r.get("slug") == slug]
    if not turns:
        return None
    events = [e for e in rows(event_log(source)) if e.get("slug") == slug]
    landed = any(e.get("kind") == "landed" for e in events)
    return measure(
        turns,
        events,
        outcome="landed" if landed else "not landed",
        mode="pair",
        seconds=since(events),
    )


def landing(source: Path, fix: str) -> str | None:
    """The commit on the source's `main` that landed `fix`, by its `Issue:` line."""
    line = f"^Issue: issues/done/{fix}\\.md$"
    found = git(source, "log", "main", "--format=%H", "--grep", line, check=False)
    return found.splitlines()[0] if found else None


def added_tests(source: Path, sha: str) -> dict[str, list[str]]:
    """The tests `sha` added, as dotted `Class.test` names by the `test_*.py` file they are in."""
    diff = git(source, "show", "--format=", "--unified=0", sha, "--", "*test_*.py")
    names: dict[str, set[str]] = collections.defaultdict(set)
    path = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif path and (match := re.match(r"^\+\s*def (test_\w+)\(", line)):
            names[path].add(match[1])
    found = {}
    for path, added in names.items():
        tree = ast.parse(git(source, "show", f"{sha}:{path}"))
        found[path] = [
            f"{node.name}.{item.name}"
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            for item in node.body
            if isinstance(item, ast.FunctionDef) and item.name in added
        ]
    return {path: tests for path, tests in found.items() if tests}


def judge(out: str, code: int) -> tuple[str, str]:
    """The defect result of one unittest run that printed `out` and exited `code`.

    Failures alone are the defect; an error, on import or in a test, is
    `could-not-run`, as is anything unittest did not summarise.
    """
    if code == 0:
        return "passed", ""
    summary = SUMMARY.search(out)
    parts = (part.partition("=") for part in summary[1].split(", ")) if summary else ()
    counts = {key: int(value) for key, _, value in parts if value.isdigit()}
    error = next(
        (line for line in out.splitlines() if re.match(r"^\w+(Error|Exception)\b", line)),
        out.strip().splitlines()[-1] if out.strip() else "no output",
    )
    if counts.get("failures") and not counts.get("errors"):
        return "failed", error
    return "could-not-run", error


def check(source: Path, clone: Path, fix: str, command: Sequence[str]) -> tuple[str, str]:
    """Run the tests `fix` added against the clone's `main`; its result and a note.

    The tests run in a detached worktree of the clone's `main` in a temporary
    directory, removed however the run ends.
    """
    sha = landing(source, fix)
    if sha is None:
        return "could-not-run", f"{fix}: no commit on main lands it"
    tests = added_tests(source, sha)
    if not tests:
        return "none", ""
    scratch = Path(tempfile.mkdtemp(prefix="pair-defect-"))
    tree = scratch / "tree"
    try:
        git(clone, "worktree", "add", "-q", "--detach", str(tree), "main")
        results = []
        for path, names in sorted(tests.items()):
            target = tree / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(git(source, "show", f"{sha}:{path}") + "\n")
            module = Path(path).stem
            done = subprocess.run(
                [*command, "-m", "unittest", *(f"{module}.{name}" for name in names)],
                check=False,
                cwd=target.parent,
                capture_output=True,
                text=True,
            )
            results.append(judge(done.stdout + done.stderr, done.returncode))
        return worst(results, prefix=f"{fix}: ")
    finally:
        git_run(clone, "worktree", "remove", "--force", str(tree))
        git_run(clone, "worktree", "prune")
        shutil.rmtree(scratch, ignore_errors=True)


def worst(results: Iterable[tuple[str, str]], prefix: str = "") -> tuple[str, str]:
    """The worst of several defect results, by `SEVERITY`, with its note."""
    ranked = sorted(results, key=lambda r: SEVERITY.index(r[0]))
    if not ranked:
        return "none", ""
    result, note = ranked[0]
    return result, f"{prefix}{note}" if note else ""


def defect(
    source: Path, clone: Path, fixes: Sequence[str], command: Sequence[str] = COMMAND
) -> tuple[str, str]:
    """The defect check of a replay whose change `fixes` later fixed: the worst of theirs."""
    return worst(check(source, clone, fix, command) for fix in fixes)


def column(
    home: Path,
    source: Path,
    fixed_by: Mapping[str, Sequence[str]],
    command: Sequence[str] = COMMAND,
) -> Measures:
    """The column of the replay kept in `home`.

    Its fixing Issues are `fixed_by`'s for the slug, which wins, or else the
    `fixed_by:` list in its `outcome.json`. A replay that did not land left
    its change off the clone's `main`, where the fix's tests would find only
    the code it started from, so its check is `could-not-run`.
    """
    outcome = json.loads((home / "outcome.json").read_text())
    slug, mode, ended = outcome["slug"], outcome["mode"], outcome["outcome"]
    clone = home / f"replay-{slug}-{mode}"
    fixes = fixed_by.get(slug, outcome.get("fixed_by") or [])
    if not fixes:
        found = ("none", "")
    elif ended != "landed":
        found = ("could-not-run", f"{slug} {mode}: {ended}, so its change is not on main")
    else:
        found = defect(source, clone, fixes, command)
    return measure(
        rows(home / "turns.jsonl"),
        rows(home / "events.jsonl"),
        outcome=ended,
        mode=mode,
        seconds=float(outcome.get("seconds", 0)),
        elaborations=elaborations(clone, slug),
        defect=found,
    )


def tally(counts: collections.Counter[str]) -> str:
    """A tally such as `landed 2, paused 1`; a single run's value alone."""
    if sum(counts.values()) == 1:
        return next(iter(counts))
    return ", ".join(f"{key} {n}" for key, n in sorted(counts.items()))


def lines(m: Measures) -> list[tuple[str, str]]:
    """Each measure of a column as a label and its value."""
    secondary = "n/a" if m.secondary is None else f"{m.secondary[0]} of {m.secondary[1]}"
    files = ", ".join(sorted(m.files)) or "-"
    if m.unlogged:
        files += f" ({m.unlogged} turns' files not logged)"

    def lacked(field: str, value: str) -> str:
        return f"{value} ({m.lacking[field]} rows lacked it)" if m.lacking[field] else value

    return [
        ("outcome", tally(m.outcomes)),
        ("gate runs (not passed)", f"{m.gates} ({m.gate_failures})"),
        ("defect check", tally(m.defects) if m.defects else "n/a"),
        ("secondary turns changed", secondary),
        ("secondary turns' files", "n/a" if m.secondary is None else files),
        ("pauses", str(m.pauses)),
        ("send-backs", str(m.send_backs)),
        ("needs elaboration", str(m.elaborations)),
        ("wall-clock seconds", f"{m.seconds:.0f}"),
        ("turns per stage", ", ".join(f"{k} {n}" for k, n in sorted(m.stages.items())) or "-"),
        ("cost (USD)", lacked("cost_usd", f"{m.cost_usd:.2f}")),
        ("cache read tokens", lacked("cache_read", str(m.cache_read))),
        ("cache write tokens", lacked("cache_write", str(m.cache_write))),
    ]


def block(title: str, columns: Mapping[str, Measures]) -> str:
    """One table: a row per measure, a column per `COLUMNS`, `missing` where one is absent."""
    labels = [label for label, _ in lines(Measures())]
    cells = {
        name: dict(lines(columns[name])) if name in columns else dict.fromkeys(labels, "missing")
        for name in COLUMNS
    }
    table = [["", *COLUMNS], *([label, *(cells[c][label] for c in COLUMNS)] for label in labels)]
    widths = [max(len(row[i]) for row in table) for i in range(len(COLUMNS) + 1)]
    out = [title]
    out += ["  " + "  ".join(cell.ljust(w) for cell, w in zip(row, widths, strict=True)).rstrip()
            for row in table]
    notes = [n for name in MODES if name in columns for n in columns[name].defect_notes]
    out += [f"  defect: {note}" for note in notes]
    return "\n".join(out)


def report(
    source: Path,
    fixed_by: Mapping[str, Sequence[str]] | None = None,
    command: Sequence[str] = COMMAND,
) -> str | None:
    """The report over every replay `source` keeps, or None when it keeps none."""
    kept = replays(source)
    if not kept:
        return None
    by_slug: dict[str, dict[str, Measures]] = collections.defaultdict(dict)
    for (slug, mode), home in kept.items():
        by_slug[slug][mode] = column(home, source, fixed_by or {}, command)
    for slug, columns in by_slug.items():
        first = original(source, slug)
        if first is not None:
            columns["original"] = first
    by_difficulty: dict[str, dict[str, Measures]] = collections.defaultdict(dict)
    blocks = []
    for slug in sorted(by_slug):
        level = difficulty(source, slug)
        blocks.append(block(f"{slug} ({level})", by_slug[slug]))
        summed = by_difficulty[level]
        for name, m in by_slug[slug].items():
            summed[name] = summed[name].add(m) if name in summed else m
    for level in sorted(by_difficulty, key=lambda d: (*board.DIFFICULTIES, "unknown").index(d)):
        columns = by_difficulty[level]
        runs = max(m.runs for m in columns.values())
        blocks.append(block(f"difficulty {level}, {runs} slugs summed", columns))
    return "\n\n".join([*blocks, ORIGINAL]) + "\n"


def diffs(source: Path, slug: str) -> str:
    """Each mode's `landed.diff` for `slug`, under a heading naming the mode."""
    out = []
    for mode in MODES:
        path = replay_dir(source, slug, mode) / "landed.diff"
        if path.is_file():
            out.append(f"=== {slug}, {mode} ===\n{path.read_text()}")
        else:
            out.append(f"=== {slug}, {mode} ===\nmissing: no {mode} replay of {slug}\n")
    return "\n".join(out)
