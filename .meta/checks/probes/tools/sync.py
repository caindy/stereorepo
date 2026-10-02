"""`bundle.py sync`, run on scratch repositories against what it must change, keep
and refuse (stereorepo's DR-315).
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import os
import pathlib
import subprocess
import tempfile
import types
from collections.abc import Callable

from checks.collect import META, check
from checks.probes.harness import load_module

OLD_BUNDLE = """schema_version: 1
source_revision: old
items:
  - {path: kit/, kind: dir, ownership: managed}
  - {path: .meta/lib/, kind: dir, ownership: managed}
  - {path: dropped.txt, kind: file, ownership: managed}
  - {path: .meta/bundle.yaml, kind: file, ownership: managed}
  - {path: README.md, source: template/README.md, kind: file, ownership: template}
"""
"""The portfolio's bundle, from before the checkout dropped `dropped.txt` and added `added.txt`."""

NEW_BUNDLE = OLD_BUNDLE.replace("source_revision: old", "source_revision: new").replace(
    "dropped.txt", "added.txt")
"""The checkout's bundle."""

SOURCE = {
    ".meta/bundle.yaml": NEW_BUNDLE,
    "kit/same.txt": "unchanged\n",
    "kit/stale.txt": "new content\n",
    "added.txt": "added\n",
    ".meta/lib/keep.py": "kept = True\n",
    ".meta/lib/adapt/plan.py": "scaffold only\n",
    "template/README.md": "# Template\n",
}
"""The checkout's tracked files: `kit/gone.txt` deleted, `kit/stale.txt` changed, and a
scaffold-only file inside a managed directory."""

PORTFOLIO = {
    ".meta/bundle.yaml": OLD_BUNDLE,
    "kit/same.txt": "unchanged\n",
    "kit/stale.txt": "old content\n",
    "kit/gone.txt": "deleted upstream\n",
    "dropped.txt": "no longer managed\n",
    ".meta/lib/keep.py": "kept = True\n",
    ".meta/lib/adapt/plan.py": "scaffold only\n",
    "README.md": "# Portfolio\n",
    "own.txt": "the portfolio's own\n",
    ".meta/baselines/comments.baseline.yaml": "own.txt: 3\n",
}
"""The portfolio's tracked files, synced once from the old bundle."""

UNTRACKED = "kit/scratch.txt"
"""An untracked file inside a managed directory, which no sync deletes."""

Snapshot = tuple[str, str, dict[str, str]]
"""A repository's HEAD, its `git status`, and the hash of every file outside `.git/`."""


def _git(repo: pathlib.Path, *args: str) -> str:
    """Runs git in `repo` with no inherited locators, identity or signing, and returns stdout."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=probe", "-c", "user.email=probe@local",
         "-c", "commit.gpgsign=false", *args],
        check=True, capture_output=True, text=True, env=env).stdout


def _repo(root: pathlib.Path, files: dict[str, str]) -> pathlib.Path:
    """A git repository at `root` with `files` committed."""
    root.mkdir(parents=True)
    _git(root, "init", "-q")
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "start")
    return root


def _portfolio(root: pathlib.Path) -> pathlib.Path:
    """A synced-once portfolio, with an untracked file inside a managed directory."""
    repo = _repo(root, PORTFOLIO)
    (repo / UNTRACKED).write_text("untracked\n", encoding="utf-8")
    return repo


def _snapshot(repo: pathlib.Path) -> Snapshot:
    """What a refused sync must leave exactly as it was."""
    hashes = {
        path.relative_to(repo).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }
    return (_git(repo, "rev-parse", "HEAD"), _git(repo, "status", "--porcelain"), hashes)


def _run(cli: types.ModuleType, source: pathlib.Path, portfolio: pathlib.Path) -> tuple[int, str]:
    """Runs `bundle.py --root PORTFOLIO sync SOURCE` and returns its exit code and stdout."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = int(cli.main(["--root", str(portfolio), "sync", str(source)]))
    return code, out.getvalue()


def _check_sync(cli: types.ModuleType, tmp: pathlib.Path, source: pathlib.Path) -> list[str]:
    """A sync removes, adds and updates what the bundles say, and keeps everything else."""
    portfolio = _portfolio(tmp / "synced")
    before = _snapshot(portfolio)
    code, out = _run(cli, source, portfolio)
    if code != 0:
        return [f"sync: exited {code} on a clean portfolio"]
    after = _snapshot(portfolio)
    problems = []
    for gone in ("dropped.txt", "kit/gone.txt", ".meta/lib/adapt/plan.py"):
        if (portfolio / gone).exists():
            problems.append(f"sync: {gone} is still present")
        if f"removed {gone}" not in out:
            problems.append(f"sync: {gone} is not printed as removed")
    if (portfolio / ".meta/lib/adapt").exists():
        problems.append("sync: the emptied .meta/lib/adapt/ was not pruned")
    for path, verb in (("added.txt", "added"), ("kit/stale.txt", "updated"),
                       (".meta/bundle.yaml", "updated")):
        if (portfolio / path).read_text(encoding="utf-8") != SOURCE[path]:
            problems.append(f"sync: {path} does not hold the checkout's content")
        if f"{verb:8s}{path}" not in out:
            problems.append(f"sync: {path} is not printed as {verb}")
    return problems + _kept(before, after, out)


def _kept(before: Snapshot, after: Snapshot, out: str) -> list[str]:
    """What a sync must leave byte for byte, and must not report, and that it commits nothing."""
    problems = []
    for kept in ("README.md", "own.txt", ".meta/baselines/comments.baseline.yaml", UNTRACKED,
                 "kit/same.txt", ".meta/lib/keep.py"):
        if after[2].get(kept) != before[2].get(kept):
            problems.append(f"sync: {kept} changed")
    if "kit/same.txt" in out:
        problems.append("sync: an identical file is reported as changed")
    if after[0] != before[0]:
        problems.append("sync: committed")
    return problems


def _check_refusals(cli: types.ModuleType, tmp: pathlib.Path, source: pathlib.Path) -> list[str]:
    """Each refusal exits non-zero and leaves the portfolio's working tree as it was."""
    not_a_checkout = _repo(tmp / "not-a-checkout", {"other.txt": "no bundle\n"})

    def dirty(repo: pathlib.Path) -> None:
        (repo / "kit/stale.txt").write_text("edited, not committed\n", encoding="utf-8")

    def occupied(repo: pathlib.Path) -> None:
        (repo / "added.txt").write_text("the portfolio's untracked file\n", encoding="utf-8")

    def scaffold(repo: pathlib.Path) -> None:
        (repo / "template").mkdir()
        (repo / "template/README.md").write_text("# template\n", encoding="utf-8")

    cases: tuple[tuple[str, pathlib.Path, Callable[[pathlib.Path], None] | None], ...] = (
        ("a source with no .meta/bundle.yaml", not_a_checkout, None),
        ("an uncommitted change to a file it would copy over", source, dirty),
        ("an untracked file where it would add one", source, occupied),
        ("a portfolio that holds template/", source, scaffold),
    )
    problems = []
    for number, (name, from_path, prepare) in enumerate(cases):
        portfolio = _portfolio(tmp / f"refused-{number}")
        if prepare is not None:
            prepare(portfolio)
        before = _snapshot(portfolio)
        code, _ = _run(cli, from_path, portfolio)
        if code == 0:
            problems.append(f"sync: accepted {name}")
        if _snapshot(portfolio) != before:
            problems.append(f"sync: changed the portfolio while refusing {name}")
    return problems


@check("bundle sync probes", pre=True)
def bundle_sync_probes() -> list[str]:
    """`bundle.py sync` brings a portfolio level with a checkout, and refuses where it
    would lose work (stereorepo's DR-315).

    A checkout drops one managed file item, deletes one file in a managed
    directory, changes another and adds a managed file, and its managed
    `.meta/lib/` holds the scaffold-only `.meta/lib/adapt/`. Synced from it, a
    portfolio of the old bundle loses the dropped item, the deleted file and
    its own copy of the scaffold-only path, gains the added file and the
    checkout's bundle, and keeps its template item, its own file, its
    baseline under `.meta/baselines/` and an untracked file in a managed
    directory byte for byte. Each change is printed, and nothing is
    committed. The sync refuses, exiting non-zero and changing nothing, a
    source with no bundle, an uncommitted change or an untracked file at a
    path it would write, and a target that holds `template/`.
    """
    cli = load_module(META / "bundle.py", name="bundle_cli")
    with tempfile.TemporaryDirectory(prefix="stereorepo-sync-probe-") as directory:
        tmp = pathlib.Path(directory)
        try:
            source = _repo(tmp / "checkout", SOURCE)
            return _check_sync(cli, tmp, source) + _check_refusals(cli, tmp, source)
        except (OSError, subprocess.CalledProcessError) as exc:
            return [f"sync: could not build a scratch repository: {exc}"]
