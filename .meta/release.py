#!/usr/bin/env python3
"""Cuts a release of the APM package: a `v<version>` tag on `main` and its GitHub Release.

Cites stereorepo's DR-206 and stereorepo's DR-320.

In order, it refuses on a dirty tree, a branch other than `main`, a `main` that differs
from `origin/main` after a fetch, a `v<version>` tag that exists here or on `origin`, a
version other than the one `.meta/apm.yml` declares, and, on a real run, a `gh` that is
not logged in. It then runs the gate, `just apm validate` and `just test-specialization`,
and stops at the first that fails. Last, it tags, pushes the tag and creates the GitHub
Release. With `--dry-run` it does the first two and prints the commands of the third.

Usage:
    just release <version> [--dry-run]
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
from collections.abc import Callable, Sequence

try:
    import yaml
except ImportError:
    cmd = ["uvx", "--python", "3.13", "--with", "pyyaml", "python",
           str(pathlib.Path(__file__).resolve()), *sys.argv[1:]]
    sys.exit(subprocess.run(cmd, check=False).returncode)

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = pathlib.PurePosixPath(".meta/apm.yml")
REMOTE = "origin"
BRANCH = "main"

CHECKS: tuple[tuple[str, ...], ...] = (
    ("just", "gate"),
    ("just", "apm", "validate"),
    ("just", "test-specialization"),
)
"""The commands step 2 runs from the root, in order; a release needs every one to pass."""

DIRTY = "the working tree has uncommitted or untracked changes"
"""The refusal where `git status --porcelain` prints anything."""

OFF_MAIN = "the branch is {branch!r}, not 'main'"
"""The refusal where the checkout is on another branch, or on none."""

NO_FETCH = "could not fetch origin main: {why}"
"""The refusal where `origin/main` cannot be brought up to date to compare against."""

DIVERGED = "main is at {head} and origin/main at {remote}; they must be the same commit"
"""The refusal where local `main` is ahead of, behind or apart from `origin/main`."""

TAGGED = "the tag {tag} already exists here"
"""The refusal where the tag is in the local repository."""

TAGGED_REMOTE = "the tag {tag} already exists on origin"
"""The refusal where the tag is on `origin` but not here."""

NO_MANIFEST = "no version can be read from .meta/apm.yml: {why}"
"""The refusal where the manifest is missing, unparsable or carries no `version`."""

NO_VERSION_KEY = "it has no version key"
"""Why `declared_version` raises where the manifest parses but names no version."""

WRONG_VERSION = "the version is {version}, but .meta/apm.yml declares {declared}"
"""The refusal where the version asked for is not the manifest's."""

NO_GH = "gh is not logged in to GitHub, so the Release could not be created: {why}"
"""The refusal, on a real run only, where `gh auth status` fails or `gh` is absent."""

CHECK_FAILED = "{command} exited {code}; nothing was tagged"
"""What step 2 prints where one of its commands fails."""

HALF_MADE = ("the tag {tag} is pushed, but `gh release create` failed; "
             "create the Release by hand with:\n    {command}")
"""What step 3 prints where the tag reached `origin` and the Release did not."""

UNPUSHED = "{command} failed, so the local tag {tag} was deleted and a retry starts clean"
"""What step 3 prints where the tag was made here but did not reach `origin`."""


def _run(root: pathlib.Path, *command: str) -> subprocess.CompletedProcess[str]:
    """Runs `command` in `root` and captures its output, never raising on exit status."""
    return subprocess.run(list(command), cwd=root, check=False, capture_output=True, text=True)


def _git(root: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Runs `git` in `root`."""
    return _run(root, "git", *args)


def declared_version(root: pathlib.Path) -> str:
    """The `version` that `.meta/apm.yml` under `root` declares.

    Raises:
        ValueError: The manifest is missing, will not parse, or has no `version`.
    """
    try:
        data = yaml.safe_load((root / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(str(exc)) from exc
    if not isinstance(data, dict) or not data.get("version"):
        raise ValueError(NO_VERSION_KEY)
    return str(data["version"])


def _branch_refusals(root: pathlib.Path) -> list[str]:
    """Why the checkout is not a clean `main` at the same commit as `origin/main`."""
    found: list[str] = []
    if _git(root, "status", "--porcelain").stdout.strip():
        found.append(DIRTY)
    branch = _git(root, "branch", "--show-current").stdout.strip()
    if branch != BRANCH:
        found.append(OFF_MAIN.format(branch=branch))
    fetch = _git(root, "fetch", "-q", REMOTE, BRANCH)
    if fetch.returncode != 0:
        return [*found, NO_FETCH.format(why=fetch.stderr.strip())]
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    remote = _git(root, "rev-parse", f"{REMOTE}/{BRANCH}").stdout.strip()
    if head != remote:
        found.append(DIVERGED.format(head=head[:12], remote=remote[:12]))
    return found


def _version_refusals(root: pathlib.Path, version: str) -> list[str]:
    """Why `version` cannot be tagged: its tag exists, or the manifest declares another."""
    found: list[str] = []
    tag = f"v{version}"
    if _git(root, "rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode == 0:
        found.append(TAGGED.format(tag=tag))
    elif _git(root, "ls-remote", "--tags", REMOTE, f"refs/tags/{tag}").stdout.strip():
        found.append(TAGGED_REMOTE.format(tag=tag))
    try:
        declared = declared_version(root)
    except ValueError as exc:
        return [*found, NO_MANIFEST.format(why=exc)]
    if declared != version:
        found.append(WRONG_VERSION.format(version=version, declared=declared))
    return found


def _gh_refusals(root: pathlib.Path) -> list[str]:
    """Why `gh` could not create the Release: it is absent or not logged in."""
    try:
        auth = _run(root, "gh", "auth", "status")
    except FileNotFoundError as exc:
        return [NO_GH.format(why=exc)]
    if auth.returncode != 0:
        return [NO_GH.format(why=(auth.stderr or auth.stdout).strip())]
    return []


def refusals(root: pathlib.Path, version: str, dry_run: bool) -> list[str]:
    """Every reason step 1 has to refuse releasing `version` from `root`, empty when none.

    Each condition is checked whatever the others found, so one run names them all. `gh`
    is asked only on a real run, since a dry run publishes nothing.
    """
    found = _branch_refusals(root) + _version_refusals(root, version)
    return found if dry_run else found + _gh_refusals(root)


def publishing(version: str) -> tuple[tuple[str, ...], ...]:
    """The commands of step 3, in order: tag, push the tag, create the Release."""
    tag = f"v{version}"
    return (
        ("git", "tag", "-a", tag, "-m", tag),
        ("git", "push", REMOTE, tag),
        ("gh", "release", "create", tag, "--verify-tag", "--title", tag, "--generate-notes"),
    )


def release(root: pathlib.Path, version: str, dry_run: bool,
            checks: Sequence[Sequence[str]] = CHECKS,
            out: Callable[[str], None] = print) -> int:
    """Releases `version` from `root`, or with `dry_run` shows what it would publish.

    Returns the exit status: 0 where the release was made (or would be), 1 otherwise.
    `checks` are the commands of step 2, run from `root` with their output shown.
    """
    found = refusals(root, version, dry_run)
    if found:
        for reason in found:
            out(f"release: refused: {reason}")
        return 1
    for command in checks:
        code = subprocess.run(list(command), cwd=root, check=False).returncode
        if code != 0:
            out("release: " + CHECK_FAILED.format(command=" ".join(command), code=code))
            return 1
    commands = publishing(version)
    if dry_run:
        out(f"release: v{version} would be published by:")
        for command in commands:
            out("    " + " ".join(command))
        return 0
    tag, push, create = commands
    if subprocess.run(list(tag), cwd=root, check=False).returncode != 0:
        out(f"release: {' '.join(tag)} failed")
        return 1
    if subprocess.run(list(push), cwd=root, check=False).returncode != 0:
        _git(root, "tag", "-d", f"v{version}")
        out("release: " + UNPUSHED.format(command=" ".join(push), tag=f"v{version}"))
        return 1
    if subprocess.run(list(create), cwd=root, check=False).returncode != 0:
        out("release: " + HALF_MADE.format(tag=f"v{version}", command=" ".join(create)))
        return 1
    out(f"release: v{version} is published")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Builds the argument parser for the release CLI."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("version", help="the version .meta/apm.yml declares, without the v")
    parser.add_argument("--dry-run", action="store_true",
                        help="check and gate, then print what would be published")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for `just release`."""
    args = build_parser().parse_args(argv)
    return release(ROOT, args.version, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
