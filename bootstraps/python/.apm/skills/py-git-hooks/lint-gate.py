#!/usr/bin/env python3
"""Stop hook lint gate, routed by target (stereorepo's DR-212).

Runs the linters over the Python files a turn modified, before Claude returns to
the user, and blocks the stop when something actionable remains. The adaptation
this copy carries over `l-mb/python-refactoring-skills`' original is that it does
not assume one repository shape: a portfolio holds inherited tooling under
`.meta/` and Project workspaces beside it, configured differently and held by
different gates, and a checker pointed at the wrong one is worse than no checker
(stereorepo's DR-177, stereorepo's DR-210).

Each modified file is resolved to its target and checked under that target's own
configuration:

- **`.meta/`** — ruff under `.meta/ruff.toml`, reached through `uvx`. Nothing
  else. `meta ruff` admits no violation, so a ruff finding here is always
  actionable; type errors are not, because `meta types` ratchets them per file
  against `.meta/checks/types.baseline.yaml` and only the gate holds that
  baseline. Reporting a raw `mypy --strict` count against a file the ratchet
  already tolerates would block every edit, which is how a hook gets switched off.
- **A Project workspace** — the nearest ancestor holding a `pyproject.toml`.
  `ruff` and `mypy` through `uv run`, from that directory, so the Project's own
  pinned tools and configuration are the ones that run.
- **Neither** — a file under no manifest belongs to no Project, so no gate holds
  it and no configuration is the right one for it. Only `E9` and `F` run, under
  `--isolated`: a syntax error or an undefined name is a defect whatever ruleset
  a repository went on to select, so that subset is feedback without a claim
  behind it. Mypy is skipped; there is no configuration to give it.

  Letting ruff fall back to its own discovery here is the mistake this branch
  exists to avoid, and this file was the proof. `lint-gate.py` ships in a skills
  directory under no manifest and carries
  `# noqa: S603  # reason: argv built here, no shell, no input`, the form the
  seed uses for a deliberate subprocess call. Checked under ruff's defaults,
  which do not select `S`, `RUF100` calls that annotation an unused directive and
  offers to strip it — a block on the file's compliance with a standard, raised
  by a ruleset that is not the standard.

Three things the original did that this one does not.

`ruff format` is not run: mechanical formatting was retired from this standard
because it inflates agent context windows and manufactures rebase churn across
concurrent branches for no semantic gain (stereorepo's DR-193).

`basedpyright` is not invoked: nothing in this standard runs it, and blocking on
findings no gate reads holds a turn to a standard nothing else enforces.

`--config` is passed on every ruff invocation rather than left to discovery. The
fixer is the reason. Under a ruleset that selects `RUF` without `F`, `RUF100`
reads `# noqa: F401  # reason: registers check steps` as an unused suppression
and strips the comment; the next `--fix` run with `F` enabled then deletes the
import, and the gate steps it registered vanish from the report without anything
turning red. Neither run looks wrong on its own, which is what makes naming the
configuration a requirement rather than a courtesy.

Install: symlink into ~/.claude/hooks/lint-gate.py
Configure in ~/.claude/settings.json under hooks.Stop
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

MAX_LINES_PER_TOOL = 50
TOOL_TIMEOUT = 120

META = ".meta"


def modified_python_files(cwd: Path) -> list[str]:
    """Python files with uncommitted changes: staged, unstaged and untracked."""
    commands = [
        ["git", "diff", "--name-only", "--diff-filter=d", "--", "*.py"],
        ["git", "diff", "--cached", "--name-only", "--diff-filter=d", "--", "*.py"],
        ["git", "ls-files", "--others", "--exclude-standard", "--", "*.py"],
    ]
    modified: set[str] = set()
    for cmd in commands:
        try:
            result = subprocess.run(  # noqa: S603  # reason: fixed git argv, no shell, no input
                cmd, capture_output=True, text=True, cwd=cwd, timeout=10, check=False
            )
        except (subprocess.SubprocessError, OSError):
            continue
        for name in result.stdout.strip().splitlines():
            if name and (cwd / name).is_file():
                modified.add(name)
    return sorted(modified)


def project_root(path: Path, root: Path) -> Path | None:
    """Where `uv run` must be typed for `path`, at or below `root`.

    A Project is where its manifest is, not where a naming convention says: a
    portfolio instantiates one wherever it was asked for, so the manifest is the
    only thing on disk that marks the boundary. Returns None when the file sits
    under no manifest.

    The nearest manifest is not always the answer. A uv workspace declares its
    dependency groups once at the root, and the linters live in that group, so
    `uv run ruff` typed in a member directory resolves only the member's own
    environment and fails to spawn:

        $ cd bootstraps/python/seed/packages/seed && uv run ruff check src
        error: Failed to spawn: `ruff`

    while the same command from `bootstraps/python/seed` runs. So the walk
    continues past the nearest manifest and keeps the outermost one that declares
    `[tool.uv.workspace]`, falling back to the nearest when none does.
    """
    nearest = None
    workspace = None
    for parent in [path.parent, *path.parent.parents]:
        manifest = parent / "pyproject.toml"
        if manifest.is_file():
            if nearest is None:
                nearest = parent
            try:
                if "[tool.uv.workspace]" in manifest.read_text(encoding="utf-8"):
                    workspace = parent
            except OSError:
                pass
        if parent == root:
            break
    return workspace or nearest


def targets(files: list[str], root: Path) -> dict[tuple[str, str], list[str]]:
    """The modified files grouped by the target that configures them.

    A key is (kind, where): ("meta", ""), ("project", <manifest directory>), or
    ("loose", ""). Grouping rather than checking file by file is what lets each
    tool run once per target with that target's configuration.
    """
    grouped: dict[tuple[str, str], list[str]] = {}
    for name in files:
        if name == META or name.startswith(f"{META}/"):
            key = ("meta", "")
        elif (found := project_root(root / name, root)) is not None:
            key = ("project", str(found))
        else:
            key = ("loose", "")
        grouped.setdefault(key, []).append(name)
    return grouped


def ruff_argv(args: list[str]) -> list[str] | None:
    """`ruff` from the environment, or through `uvx`, or nothing.

    No version is pinned here. The gate owns the pin — `.meta/`'s is in its
    Project's `gate:` string and a Project's is in its manifest — and a second
    copy in a hook is one that drifts silently, since a hook nobody watches
    disagreeing with the gate reads as the gate being wrong.
    """
    if shutil.which("ruff"):
        return ["ruff", *args]
    if shutil.which("uvx"):
        return ["uvx", "ruff", *args]
    return None


def run(argv: list[str], cwd: Path) -> str | None:
    """A checker's output when it found something.

    None when it is clean, and None when it is not installed: a portfolio that has
    adopted no Python Project has no `uv`, and a turn there should not be blocked
    by the absence.
    """
    try:
        result = subprocess.run(  # noqa: S603  # reason: argv built here, no shell, no input
            argv, capture_output=True, text=True, cwd=cwd,
            timeout=TOOL_TIMEOUT, check=False,
        )
    except subprocess.TimeoutExpired:
        return f"(timed out after {TOOL_TIMEOUT}s)"
    except OSError:
        return None
    if result.returncode == 0:
        return None
    output = result.stdout.strip() or result.stderr.strip()
    if not output:
        return None
    if "command not found" in output or "No module named" in output:
        return None
    lines = output.splitlines()
    if len(lines) > MAX_LINES_PER_TOOL:
        extra = len(lines) - MAX_LINES_PER_TOOL
        output = "\n".join(lines[:MAX_LINES_PER_TOOL]) + f"\n... ({extra} more lines)"
    return output


def check_meta(files: list[str], root: Path) -> list[str]:
    """Ruff over modified `.meta/` files, under `.meta/ruff.toml`.

    No mypy: the module docstring says why.
    """
    config = root / META / "ruff.toml"
    if not config.is_file():
        return []
    shared = ["--config", str(config)]
    if (fix := ruff_argv(["check", *shared, "--fix", *files])) is not None:
        run(fix, root)
    if (check := ruff_argv(["check", *shared, *files])) is None:
        return []
    found = run(check, root)
    return [f"=== ruff ({META}/, under {META}/ruff.toml) ===\n{found}"] if found else []


def check_project(files: list[str], where: str, root: Path) -> list[str]:
    """Ruff and mypy through the Project's own `uv run`, typed in its directory."""
    cwd = Path(where)
    if not shutil.which("uv"):
        return []
    relative = [str((root / name).relative_to(cwd)) for name in files]
    run(["uv", "run", "ruff", "check", "--fix", *relative], cwd)
    problems = []
    for tool, args in (("ruff", ["check"]), ("mypy", [])):
        found = run(["uv", "run", tool, *args, *relative], cwd)
        if found:
            label = Path(where).name or where
            problems.append(f"=== {tool} ({label}) ===\n{found}")
    return problems


def check_loose(files: list[str], root: Path) -> list[str]:
    """`E9` and `F` only, isolated, for files under no manifest. No fixer, no mypy.

    The subset is the point: these are defects under every ruleset, so reporting
    them claims nothing about which configuration governs a file that no gate
    governs at all. Nothing is auto-fixed here either — a fixer needs a ruleset
    to be right about, and this branch is where there is none.
    """
    argv = ruff_argv(["check", "--isolated", "--select", "E9,F", *files])
    if argv is None:
        return []
    found = run(argv, root)
    return [f"=== ruff (no manifest; E9,F only) ===\n{found}"] if found else []


def problems(grouped: dict[tuple[str, str], list[str]], root: Path) -> list[str]:
    """Every target's findings, ordered so a retry reads as the same report."""
    found: list[str] = []
    for (kind, where), files in sorted(grouped.items()):
        if kind == "meta":
            found += check_meta(files, root)
        elif kind == "project":
            found += check_project(files, where, root)
        else:
            found += check_loose(files, root)
    return found


def main() -> None:
    """Reads the Stop event, checks what the turn changed, blocks on what it found."""
    event = json.load(sys.stdin)

    if event.get("stop_hook_active"):
        json.dump({"decision": "approve"}, sys.stdout)
        return

    root = Path(event.get("cwd", ".")).resolve()
    files = modified_python_files(root)
    if not files:
        json.dump({"decision": "approve"}, sys.stdout)
        return

    found = problems(targets(files, root), root)
    if found:
        reason = (
            "Fix these before returning. Each block names the target whose "
            "configuration the checker ran under:\n\n" + "\n\n".join(found)
        )
        json.dump({"decision": "block", "reason": reason}, sys.stdout)
    else:
        json.dump({"decision": "approve"}, sys.stdout)


if __name__ == "__main__":
    main()
