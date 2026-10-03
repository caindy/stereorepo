"""`render.py` and `reconcile_harnesses` under a write the sandbox denies, and scope notes.

The seat's sandbox denies writes under `.claude/` (stereorepo's DR-302).

A read-only file stands in for the sandbox: render must leave a current file
untouched, write every other file when one cannot be written, and name that one
rather than end in a traceback.

A folded scope note reaches the vocabulary page with one newline at each
paragraph break, and each of its paragraphs must still render as a paragraph.
"""
import importlib
import pathlib
import shutil
import stat
import sys
import tempfile
from unittest import mock

import yaml

from checks.collect import check
from checks.probes.harness import outcome
from lib.apm_compile import harness
from lib.render import cli, pages, targets

PAGES = {"a.md": "A\n", "../x/SKILL.md": "X\n"}
"""Two pages: one inside the scratch `meta` directory, one beside it as a `.claude/` skill is."""


def _read_only(path: pathlib.Path) -> None:
    """Takes away every write permission on `path`."""
    path.chmod(path.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def _writable(root: pathlib.Path) -> None:
    """Gives back the owner's write permission under `root`, so the scratch tree can be removed."""
    for path in root.rglob("*"):
        path.chmod(path.stat().st_mode | stat.S_IWUSR)


@check("render current tree probes", pre=True)
def render_current_probes() -> list[str]:
    """Over a current tree with one file read-only, `write_pages` writes and fails nothing."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        meta = pathlib.Path(tmp) / "meta"
        cli.write_pages(meta, PAGES)
        _read_only(pathlib.Path(tmp) / "x" / "SKILL.md")
        paths = [meta / name for name in PAGES]
        before = [p.stat().st_mtime_ns for p in paths]
        result: list[tuple[int, list[str]]] = []
        got = outcome(lambda: result.append(cli.write_pages(meta, PAGES)))
        if got.code is not None:
            problems.append(f"render: a current tree raised {got.code}")
        elif result[0] != (0, []):
            problems.append(f"render: a current tree wrote or failed a file: {result[0]}")
        if [p.stat().st_mtime_ns for p in paths] != before:
            problems.append("render: a current tree changed a modification time")
        _writable(pathlib.Path(tmp))
    return problems


@check("render read-only target probes", pre=True)
def render_read_only_probes() -> list[str]:
    """A stale read-only page: the others are written, it is named, and `main` exits 1."""
    problems: list[str] = []
    changed = {name: text.replace("\n", " changed\n") for name, text in PAGES.items()}
    with tempfile.TemporaryDirectory() as tmp:
        meta = pathlib.Path(tmp) / "meta"
        cli.write_pages(meta, PAGES)
        _read_only(pathlib.Path(tmp) / "x" / "SKILL.md")
        result: list[tuple[int, list[str]]] = []
        got = outcome(lambda: result.append(cli.write_pages(meta, changed)))
        if got.code is not None:
            problems.append(f"render: a read-only target raised {got.code}")
        elif result[0] != (1, ["../x/SKILL.md"]):
            problems.append(f"render: expected (1, ['../x/SKILL.md']), got {result[0]}")
        if (meta / "a.md").read_text() != changed["a.md"]:
            problems.append("render: the writable page was not written")

        apm_compile = importlib.import_module("apm_compile")
        skill = ".agents/skills/s/SKILL.md"
        cases: tuple[tuple[list[str], list[str]], ...] = (
            ([], ["x/SKILL.md"]),
            ([harness.UNWRITTEN + skill, "ERROR: AGENTS.md is missing"], ["x/SKILL.md", skill]))
        for actions, named in cases:
            with mock.patch.object(cli, "META", meta), \
                    mock.patch.object(targets, "snapshot", lambda: {}), \
                    mock.patch.object(targets, "rendered", lambda _snap: changed), \
                    mock.patch.object(targets, "unrendered", lambda _snap: []), \
                    mock.patch.object(apm_compile, "reconcile_root", lambda _root, a=actions: a), \
                    mock.patch.object(sys, "argv", ["render.py"]):
                got = outcome(cli.main)
            if got.code != "1":
                problems.append(f"render: main exited {got.code!r}, expected 1")
            listed = [line.strip() for line in got.out.splitlines() if line.startswith("  ")]
            if listed != named:
                problems.append(f"render: main listed {listed}, expected {named}")
            if "outside the sandbox" not in got.out:
                problems.append("render: main did not say to render outside the sandbox")
        _writable(pathlib.Path(tmp))
    return problems


@check("harness projection probes", pre=True)
def harness_projection_probes() -> list[str]:
    """Without `apm`, `reconcile_harnesses` copies what differs and names what it cannot write."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp, \
            mock.patch.object(shutil, "which", lambda _name: None):
        root = pathlib.Path(tmp)
        src = root / "meta" / ".apm" / "skills" / "s"
        src.mkdir(parents=True)
        (src / "SKILL.md").write_text("S\n")
        harness.reconcile_harnesses(root / "meta", root)
        dest = root / ".agents" / "skills" / "s" / "SKILL.md"
        _read_only(dest)
        before = dest.stat().st_ctime_ns
        got = outcome(lambda: problems.extend(
            f"harness: unchanged skill reported {a}"
            for a in harness.reconcile_harnesses(root / "meta", root)
            if a.startswith(harness.UNWRITTEN)))
        if got.code is not None:
            problems.append(f"harness: an unchanged read-only skill raised {got.code}")
        if dest.stat().st_ctime_ns != before:
            problems.append("harness: an unchanged skill was rewritten")

        (src / "SKILL.md").write_text("S changed\n")
        (src / "extra.md").write_text("E\n")
        actions: list[str] = []
        got = outcome(lambda: actions.extend(harness.reconcile_harnesses(root / "meta", root)))
        if got.code is not None:
            problems.append(f"harness: a stale read-only skill raised {got.code}")
        if (harness.UNWRITTEN + ".agents/skills/s/SKILL.md") not in actions:
            problems.append(f"harness: the read-only skill was not reported, got {actions}")
        if not (dest.parent / "extra.md").is_file():
            problems.append("harness: the new skill file was not copied")
        _writable(root)
    return problems


SCOPE_NOTES = """
- id: a
  pref_label: A
  definition: D
  scope_note: >-
    first

    second
- id: b
  pref_label: B
  definition: D
  scope_note: >-
    only
"""
"""Two concepts as the loader reads them: one folded two-paragraph note, one single paragraph."""


@check("render scope note probes", pre=True)
def render_scope_note_probes() -> list[str]:
    """Each paragraph of a scope note is its own paragraph, the first led by the bold label."""
    members = yaml.safe_load(SCOPE_NOTES)
    got = pages._scheme({"name": "S"}, members, members)
    wanted = ("**A.** first\n\nsecond\n", "**B.** only\n")
    return [f"render: no scope note entry {want!r} in {got!r}"
            for want in wanted if want not in got]
