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
from lib.bundle import BLOCK, Bundle, BundleItem, block_span, merge_block, validate_bundle

OLD_BUNDLE = """schema_version: 1
source_revision: old
items:
  - {path: kit/, kind: dir, ownership: managed}
  - {path: .meta/lib/, kind: dir, ownership: managed}
  - {path: dropped.txt, kind: file, ownership: managed}
  - {path: people/, kind: dir, ownership: managed}
  - {path: .gitignore, kind: file, ownership: managed}
  - {path: .meta/bundle.yaml, kind: file, ownership: managed}
  - {path: README.md, source: template/README.md, kind: file, ownership: template}
"""
"""The portfolio's bundle, from before the checkout dropped `dropped.txt` and added `added.txt`."""

NEW_BUNDLE = OLD_BUNDLE.replace("source_revision: old", "source_revision: new").replace(
    "dropped.txt", "added.txt").replace(
    "{path: people/, kind: dir, ownership: managed}",
    "{path: people/, kind: dir, ownership: portfolio}\n"
    "  - {path: people/README.md, kind: file, ownership: managed}").replace(
    "{path: .gitignore, kind: file, ownership: managed}",
    "{path: .gitignore, kind: file, ownership: managed, transformations: [block]}")
"""The checkout's bundle, which also marks `.gitignore` as a `block` file
(stereorepo's DR-316), and narrows the managed `people/` to its README inside a
`portfolio` item (stereorepo's DR-317): the portfolio's bundle does neither, as one
synced before both existed."""

BLOCK_TEXT = "# >>> stereorepo: replaced by a sync\nnew-scaffold/\n# <<< stereorepo\n"
"""The checkout's block in `.gitignore`."""

OLD_BLOCK = BLOCK_TEXT.replace("new-scaffold/", "old-scaffold/")
"""The block the portfolio's `.gitignore` holds from its last sync."""

SOURCE = {
    ".meta/bundle.yaml": NEW_BUNDLE,
    "kit/same.txt": "unchanged\n",
    "kit/stale.txt": "new content\n",
    "added.txt": "added\n",
    ".gitignore": BLOCK_TEXT,
    ".meta/lib/keep.py": "kept = True\n",
    ".meta/lib/adapt/plan.py": "scaffold only\n",
    "template/README.md": "# Template\n",
    "people/README.md": "# People, as the checkout has it\n",
    "people/example/README.md": "# The checkout's example Role\n",
}
"""The checkout's tracked files: `kit/gone.txt` deleted, `kit/stale.txt` changed, a
scaffold-only file inside a managed directory, and an example under `people/` that no
managed item names."""

PORTFOLIO = {
    ".meta/bundle.yaml": OLD_BUNDLE,
    "kit/same.txt": "unchanged\n",
    "kit/stale.txt": "old content\n",
    "kit/gone.txt": "deleted upstream\n",
    "dropped.txt": "no longer managed\n",
    ".gitignore": "own-before/\n" + OLD_BLOCK + "own-after/\n",
    ".meta/lib/keep.py": "kept = True\n",
    ".meta/lib/adapt/plan.py": "scaffold only\n",
    "README.md": "# Portfolio\n",
    "own.txt": "the portfolio's own\n",
    ".meta/baselines/comments.baseline.yaml": "own.txt: 3\n",
    "people/README.md": "# People, as the last sync left it\n",
    "people/customers/ada.md": "# Ada, the portfolio's own Persona\n",
    "people/example/README.md": "# The example Role, as the portfolio edited it\n",
}
"""The portfolio's tracked files, synced once from the old bundle."""

PEOPLE_OWN = ("people/customers/ada.md", "people/example/README.md")
"""The portfolio's files under the `portfolio` item `people/`, which no sync removes or
overwrites, even the one that narrows the old bundle's managed `people/`
(stereorepo's DR-317)."""

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


def _portfolio(root: pathlib.Path, gitignore: str | None = PORTFOLIO[".gitignore"],
               ) -> pathlib.Path:
    """A synced-once portfolio, with an untracked file inside a managed directory, and
    `gitignore` as its tracked `.gitignore`, or none where it is None."""
    files = {path: text for path, text in PORTFOLIO.items() if path != ".gitignore"}
    if gitignore is not None:
        files[".gitignore"] = gitignore
    repo = _repo(root, files)
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
                       (".meta/bundle.yaml", "updated"), ("people/README.md", "updated")):
        if (portfolio / path).read_text(encoding="utf-8") != SOURCE[path]:
            problems.append(f"sync: {path} does not hold the checkout's content")
        if f"{verb:8s}{path}" not in out:
            problems.append(f"sync: {path} is not printed as {verb}")
    if (portfolio / ".gitignore").read_text(encoding="utf-8") != \
            "own-before/\n" + BLOCK_TEXT + "own-after/\n":
        problems.append("sync: .gitignore lost its own lines or kept the old block")
    if "updated .gitignore" not in out:
        problems.append("sync: .gitignore is not printed as updated")
    return problems + _kept(before, after, out)


def _check_merges(cli: types.ModuleType, tmp: pathlib.Path, source: pathlib.Path) -> list[str]:
    """A `block` file keeps the portfolio's own lines, however it holds them."""
    cases = (
        ("no markers", "own/\n", "own/\n" + BLOCK_TEXT, "updated"),
        ("no markers or final newline", "own/", "own/\n" + BLOCK_TEXT, "updated"),
        ("the checkout's block already", "own/\n" + BLOCK_TEXT, "own/\n" + BLOCK_TEXT, None),
        ("no .gitignore", None, BLOCK_TEXT, "added"),
    )
    problems = []
    for number, (name, gitignore, merged, verb) in enumerate(cases):
        portfolio = _portfolio(tmp / f"merged-{number}", gitignore)
        code, out = _run(cli, source, portfolio)
        if code != 0:
            problems.append(f"sync: exited {code} on a .gitignore with {name}")
            continue
        if (portfolio / ".gitignore").read_text(encoding="utf-8") != merged:
            problems.append(f"sync: a .gitignore with {name} was merged wrongly")
        printed = [line for line in out.splitlines() if line.endswith(" .gitignore")]
        if printed != ([f"{verb:8s}.gitignore"] if verb else []):
            problems.append(f"sync: a .gitignore with {name} was printed as {printed}")
    return problems


def _check_block_helpers(tmp: pathlib.Path) -> list[str]:
    """The block helpers reject malformed markers, and the validator a malformed `block` item."""
    problems = []
    for name, text in (("reversed markers", "# <<< stereorepo\n# >>> stereorepo\n"),
                       ("an opening marker alone", "# >>> stereorepo\n"),
                       ("two blocks", BLOCK_TEXT + BLOCK_TEXT)):
        try:
            block_span(text)
            problems.append(f"sync: block_span accepted {name}")
        except ValueError:
            pass
    if merge_block("own\r\n", BLOCK_TEXT) != "own\r\n" + BLOCK_TEXT:
        problems.append("sync: merge_block changed the portfolio's line endings")
    (tmp / "unmarked").write_text("plain/\n", encoding="utf-8")
    (tmp / "folder").mkdir()
    for path, kind in (("unmarked", "file"), ("folder", "dir")):
        item = BundleItem(path=path, kind=kind, transformations=(BLOCK,))
        if not validate_bundle(Bundle(source_revision="probe", items=(item,)), tmp):
            problems.append(f"sync: validate_bundle accepted a {BLOCK} item that is {path}")
    return problems


def _check_portfolio_items(cli: types.ModuleType, tmp: pathlib.Path,
                           source: pathlib.Path) -> list[str]:
    """A portfolio already on the new bundle gets a deleted managed README back inside a
    `portfolio` item and keeps its own files there, and the validator accepts the ownership
    (stereorepo's DR-317)."""
    portfolio = _portfolio(tmp / "restored")
    (portfolio / ".meta/bundle.yaml").write_text(NEW_BUNDLE, encoding="utf-8")
    (portfolio / "people/README.md").unlink()
    _git(portfolio, "add", "-A")
    _git(portfolio, "commit", "-q", "-m", "on the new bundle, without the README")
    before = _snapshot(portfolio)
    code, out = _run(cli, source, portfolio)
    if code != 0:
        return [f"sync: exited {code} on a portfolio missing a managed README"]
    problems = []
    readme = portfolio / "people/README.md"
    if not readme.is_file() or readme.read_text(encoding="utf-8") != SOURCE["people/README.md"]:
        problems.append("sync: a deleted people/README.md was not restored")
    if f"{'added':8s}people/README.md" not in out:
        problems.append("sync: a restored people/README.md is not printed as added")
    after = _snapshot(portfolio)
    problems.extend(f"sync: {own} changed on a portfolio already on the new bundle"
                    for own in PEOPLE_OWN if after[2].get(own) != before[2].get(own))
    (tmp / "people").mkdir()
    for ownership, valid in (("portfolio", True), ("borrowed", False)):
        item = BundleItem(path="people/", kind="dir", ownership=ownership)
        if (not validate_bundle(Bundle(source_revision="probe", items=(item,)), tmp)) != valid:
            problems.append(f"sync: validate_bundle {'rejected' if valid else 'accepted'} "
                            f"an item owned by {ownership}")
    return problems


def _kept(before: Snapshot, after: Snapshot, out: str) -> list[str]:
    """What a sync must leave byte for byte, and must not report, and that it commits nothing."""
    problems = []
    for kept in ("README.md", "own.txt", ".meta/baselines/comments.baseline.yaml", UNTRACKED,
                 "kit/same.txt", ".meta/lib/keep.py", *PEOPLE_OWN):
        if after[2].get(kept) != before[2].get(kept):
            problems.append(f"sync: {kept} changed")
    if "kit/same.txt" in out:
        problems.append("sync: an identical file is reported as changed")
    problems.extend(f"sync: the portfolio's own {own} is reported" for own in PEOPLE_OWN
                    if own in out)
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

    def dirty_block(repo: pathlib.Path) -> None:
        (repo / ".gitignore").write_text("edited/\n" + OLD_BLOCK, encoding="utf-8")

    def unclosed(repo: pathlib.Path) -> None:
        (repo / ".gitignore").write_text("own/\n# >>> stereorepo\n", encoding="utf-8")
        _git(repo, "commit", "-q", "-am", "an unclosed block")

    def linked(repo: pathlib.Path) -> None:
        (repo / "ignores").write_text(OLD_BLOCK, encoding="utf-8")
        (repo / ".gitignore").unlink()
        (repo / ".gitignore").symlink_to("ignores")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "a linked .gitignore")

    def folder(repo: pathlib.Path) -> None:
        (repo / ".gitignore").unlink()
        (repo / ".gitignore").mkdir()
        (repo / ".gitignore/kept.txt").write_text("the portfolio's own\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "a .gitignore directory")

    def scaffold(repo: pathlib.Path) -> None:
        (repo / "template").mkdir()
        (repo / "template/README.md").write_text("# template\n", encoding="utf-8")

    cases: tuple[tuple[str, pathlib.Path, Callable[[pathlib.Path], None] | None], ...] = (
        ("a source with no .meta/bundle.yaml", not_a_checkout, None),
        ("an uncommitted change to a file it would copy over", source, dirty),
        ("an untracked file where it would add one", source, occupied),
        ("an uncommitted change to a .gitignore it would merge", source, dirty_block),
        ("a .gitignore whose block is never closed", source, unclosed),
        ("a .gitignore that is a symlink", source, linked),
        ("a .gitignore that is a directory", source, folder),
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
    committed. A `.gitignore` the checkout marks `block` keeps the
    portfolio's own lines around stereorepo's block, or gains the block at
    its end where it had none (stereorepo's DR-316), even though the portfolio's
    own bundle still lists it as a plain managed file. A managed `people/`
    the checkout narrows to its README inside a `portfolio` item keeps the
    portfolio's own files under it byte for byte, on that sync and every
    later one, while the README is updated or restored (stereorepo's DR-317). The sync refuses,
    exiting non-zero and changing nothing, a source with no bundle, an
    uncommitted change or an untracked file at a path it would write, a
    `.gitignore` with an unclosed block or that is a symlink or a directory,
    and a target that holds `template/`.
    """
    cli = load_module(META / "bundle.py", name="bundle_cli")
    with tempfile.TemporaryDirectory(prefix="stereorepo-sync-probe-") as directory:
        tmp = pathlib.Path(directory)
        try:
            source = _repo(tmp / "checkout", SOURCE)
            return (_check_sync(cli, tmp, source) + _check_merges(cli, tmp, source)
                    + _check_refusals(cli, tmp, source) + _check_block_helpers(tmp)
                    + _check_portfolio_items(cli, tmp, source))
        except (OSError, subprocess.CalledProcessError) as exc:
            return [f"sync: could not build a scratch repository: {exc}"]
