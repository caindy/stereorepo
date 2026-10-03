"""`release.py`, run on scratch repositories against each refusal of step 1, a failing
check of step 2, and a dry run (stereorepo's DR-320).
"""

from __future__ import annotations

import contextlib
import os
import pathlib
import subprocess
import tempfile
import types
from collections.abc import Callable, Iterator

from checks.collect import META, check
from checks.probes.harness import load_module

VERSION = "0.1.0"
"""The version every scratch manifest declares."""

PASS = (("true",),)
"""Step 2 with one command that passes, so no case runs the real gate inside the gate."""


@contextlib.contextmanager
def _isolated() -> Iterator[None]:
    """Strips every `GIT_*` variable from the environment while the cases run, so git in the
    scratch repositories ignores the checkout the gate runs from, and signs nothing."""
    saved = {k: v for k, v in os.environ.items() if k.startswith("GIT_")}
    for key in saved:
        del os.environ[key]
    os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
    os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
    try:
        yield
    finally:
        for key in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"):
            os.environ.pop(key, None)
        os.environ.update(saved)


def _git(repo: pathlib.Path, *args: str) -> str:
    """Runs git in `repo` as a fixed identity that signs nothing, and returns stdout."""
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=probe", "-c", "user.email=probe@local",
         "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
        check=True, capture_output=True, text=True).stdout


def _clone(tmp: pathlib.Path, name: str) -> tuple[pathlib.Path, pathlib.Path]:
    """A bare `origin` and a clone of it on `main`, whose one pushed commit holds a
    `.meta/apm.yml` declaring `VERSION`."""
    origin = tmp / f"{name}-origin.git"
    _git(tmp, "init", "-q", "--bare", "-b", "main", str(origin))
    clone = tmp / name
    _git(tmp, "clone", "-q", str(origin), str(clone))
    _git(clone, "checkout", "-q", "-B", "main")
    (clone / ".meta").mkdir()
    (clone / ".meta" / "apm.yml").write_text(f"name: probe\nversion: {VERSION}\n",
                                             encoding="utf-8")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-q", "-m", "start")
    _git(clone, "push", "-q", "-u", "origin", "main")
    return origin, clone


def _commit(repo: pathlib.Path, name: str) -> None:
    """Commits one new file named `name` in `repo`."""
    (repo / name).write_text(name + "\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", name)


def _tags(origin: pathlib.Path, clone: pathlib.Path) -> tuple[str, str]:
    """The tags of the clone and of `origin`, as `git tag -l` prints them."""
    return _git(clone, "tag", "-l"), _git(origin, "tag", "-l")


def _dirty(tmp: pathlib.Path, origin: pathlib.Path, clone: pathlib.Path) -> None:
    """Leaves an untracked file in the clone."""
    (clone / "untracked.txt").write_text("stray\n", encoding="utf-8")


def _off_main(tmp: pathlib.Path, origin: pathlib.Path, clone: pathlib.Path) -> None:
    """Puts the clone on a branch `other`."""
    _git(clone, "checkout", "-q", "-b", "other")


def _behind(tmp: pathlib.Path, origin: pathlib.Path, clone: pathlib.Path) -> None:
    """Pushes a commit to `origin` from a second clone, leaving the first behind."""
    other = tmp / f"{clone.name}-other"
    _git(tmp, "clone", "-q", str(origin), str(other))
    _commit(other, "elsewhere.txt")
    _git(other, "push", "-q", "origin", "main")


def _ahead(tmp: pathlib.Path, origin: pathlib.Path, clone: pathlib.Path) -> None:
    """Commits in the clone without pushing."""
    _commit(clone, "unpushed.txt")


def _tagged(tmp: pathlib.Path, origin: pathlib.Path, clone: pathlib.Path) -> None:
    """Tags `v0.1.0` in the clone."""
    _git(clone, "tag", f"v{VERSION}")


def _tagged_remote(tmp: pathlib.Path, origin: pathlib.Path, clone: pathlib.Path) -> None:
    """Pushes a `v0.1.0` tag to `origin` and deletes it from the clone."""
    _git(clone, "tag", f"v{VERSION}")
    _git(clone, "push", "-q", "origin", f"v{VERSION}")
    _git(clone, "tag", "-d", f"v{VERSION}")


def _as_is(tmp: pathlib.Path, origin: pathlib.Path, clone: pathlib.Path) -> None:
    """Leaves the clone clean and current."""


Arrange = Callable[[pathlib.Path, pathlib.Path, pathlib.Path], None]

REFUSALS: tuple[tuple[str, Arrange, str, str], ...] = (
    ("dirty", _dirty, VERSION, "DIRTY"),
    ("off-main", _off_main, VERSION, "OFF_MAIN"),
    ("behind", _behind, VERSION, "DIVERGED"),
    ("ahead", _ahead, VERSION, "DIVERGED"),
    ("tagged", _tagged, VERSION, "TAGGED"),
    ("tagged-remote", _tagged_remote, VERSION, "TAGGED_REMOTE"),
    ("wrong-version", _as_is, "0.2.0", "WRONG_VERSION"),
)
"""Each case's name, how it spoils a clean clone, the version asked for, and the name of
the message constant in `release.py` whose fixed text the refusal must carry."""


def _stem(template: str) -> str:
    """The part of a message template before its first placeholder."""
    return template.split("{", 1)[0]


def _case(module: types.ModuleType, tmp: pathlib.Path, case: tuple[str, Arrange, str],
          checks: tuple[tuple[str, ...], ...]) -> tuple[int, str, bool]:
    """Runs one dry-run release on a clone that `case` names, spoils and asks a version of:
    its status, its output, and whether the tags of clone and `origin` are what they were
    before the run."""
    name, arrange, version = case
    origin, clone = _clone(tmp, name)
    arrange(tmp, origin, clone)
    before = _tags(origin, clone)
    lines: list[str] = []
    code = module.release(clone, version, True, checks=checks, out=lines.append)
    return code, "\n".join(lines), _tags(origin, clone) == before


def _check_refusals(module: types.ModuleType, tmp: pathlib.Path) -> list[str]:
    """Each refusal of step 1 exits non-zero, says why, and tags nothing."""
    problems: list[str] = []
    for name, arrange, version, message in REFUSALS:
        code, out, untouched = _case(module, tmp, (name, arrange, version), PASS)
        if code == 0:
            problems.append(f"release: the {name} case was not refused")
        if _stem(getattr(module, message)) not in out:
            problems.append(f"release: the {name} case did not say {message}: {out!r}")
        if not untouched:
            problems.append(f"release: the {name} case changed the tags")
    return problems


def _check_failing_check(module: types.ModuleType, tmp: pathlib.Path) -> list[str]:
    """A failing check of step 2 stops the release before any tag."""
    code, out, untouched = _case(module, tmp, ("failing-check", _as_is, VERSION),
                                 (("true",), ("false",)))
    problems: list[str] = []
    if code == 0:
        problems.append("release: a failing check did not stop the release")
    if "false exited 1" not in out:
        problems.append(f"release: a failing check was not named: {out!r}")
    if not untouched:
        problems.append("release: a failing check left a tag")
    return problems


def _check_dry_run(module: types.ModuleType, tmp: pathlib.Path) -> list[str]:
    """A dry run on a clean, current `main` exits zero, prints step 3, and tags nothing."""
    code, out, untouched = _case(module, tmp, ("dry-run", _as_is, VERSION), PASS)
    problems: list[str] = []
    if code != 0:
        problems.append(f"release: a dry run on a clean, current main exited {code}: {out!r}")
    for expected in (f"git tag -a v{VERSION}", f"git push origin v{VERSION}",
                     f"gh release create v{VERSION}"):
        if expected not in out:
            problems.append(f"release: a dry run did not print {expected!r}")
    if not untouched:
        problems.append("release: a dry run left a tag")
    return problems


@check("release probes", pre=True)
def release_probes() -> list[str]:
    """`release.py` refuses, gates and dry-runs as `just release` must (stereorepo's DR-320).

    On a clone of a bare `origin` whose `.meta/apm.yml` declares 0.1.0, a dry run is
    refused, non-zero, with the reason named and no tag made, for an untracked file, a
    branch other than `main`, a `main` behind or ahead of `origin`, a `v0.1.0` tag here or
    only on `origin`, and the version 0.2.0. A failing check of step 2 stops it before any
    tag. A dry run on a clean, current `main` exits zero, prints the tag, the push and
    `gh release create`, and tags nothing. Every case is a dry run with its own checks, so
    no case pushes a tag, calls `gh`, or runs the gate inside the gate.

    A portfolio inherits `.meta/checks/` but not `.meta/release.py`, so where the script
    is absent there is nothing to probe.
    """
    script = META / "release.py"
    if not script.is_file():
        return []
    module = load_module(script, name="release_cli")
    with tempfile.TemporaryDirectory(prefix="stereorepo-release-probe-") as directory, \
            _isolated():
        tmp = pathlib.Path(directory)
        return (_check_refusals(module, tmp) + _check_failing_check(module, tmp)
                + _check_dry_run(module, tmp))
