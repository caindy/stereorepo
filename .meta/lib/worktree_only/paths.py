"""Filesystem containment: whether a path a tool reads lies inside the worktree (solorepo's DR-110).

Tool calls for `Read`, `Grep` and `Glob`, and the harness tool names `TOOLS`
maps onto them, must resolve inside the active repository worktree and outside
`.git/`, which holds workflow tokens, or within a harness scratch directory
(`HARNESS`). A key of `READERS` holding a glob pattern is bounded by the literal
path its matches lie under rather than resolved as one, and refused where it can
leave that bound whatever the bound is: a component matching `..`, or brace
alternation, neither of which the literal prefix speaks for. A reader naming no
key of `READERS` at all is refused, a search being the exception that may mean
the worktree by naming nothing.

A working directory a call names in `dir_path` (Gemini CLI) or `Cwd`
(Antigravity CLI), while `run_command` names its command line `CommandLine`,
must resolve inside the worktree: run elsewhere, an allowed command reads what
`git -C` is refused for pointing at. That is its own predicate, `elsewhere`, a
directory commands run in carrying neither exemption a path read from carries.
"""
import os
import pathlib
import subprocess
from typing import Any

from lib.worktree_only import ROOT

# Harness tool names mapped onto the canonical four. Gemini CLI's `BeforeTool`
# payload carries the same `tool_name` and `tool_input` fields as Claude Code's
# `PreToolUse`, so the names are all that differ: `grep_search` was
# `search_file_content` and Gemini CLI still answers to both, `read_many_files`
# is the `@` syntax's bulk read, and `list_directory` reads a directory as
# `Glob` does. Antigravity CLI dispatches `run_command`, `view_file`,
# `grep_search`, and `list_directory`.
TOOLS = {
    "run_shell_command": "Bash",
    "run_command": "Bash",
    "read_file": "Read",
    "read_many_files": "Read",
    "view_file": "Read",
    "grep_search": "Grep",
    "search_file_content": "Grep",
    "glob": "Glob",
    "list_directory": "Glob",
}

PATH, PATTERN = "path", "pattern"

# Each canonical reader with the input keys a harness names its paths in, and
# whether a key holds a path or a glob pattern. Paired with the tool that sends
# each: Claude Code's `Read` names `file_path`, its `Grep` names `path` and
# filters with `glob`, its `Glob` names `path` and `pattern`; Gemini CLI's
# `read_file` names `file_path`, its `read_many_files` names `include`, its
# `grep_search` names `path` and filters with `include`, its `glob` names `path`
# and `pattern`, and its `list_directory` names `dir_path`; Antigravity CLI's
# `view_file` names `AbsolutePath`, its `grep_search` filters with `Includes`
# and bounds with `SearchDirectory` or `Path`, and its `list_directory` names
# `SearchDirectory`, `Path`, or `Directory`.
READERS = {
    "Read": {"file_path": PATH, "include": PATTERN, "AbsolutePath": PATH},
    "Grep": {
        "path": PATH,
        "include": PATTERN,
        "glob": PATTERN,
        "SearchDirectory": PATH,
        "Path": PATH,
        "Directory": PATH,
        "Dir": PATH,
        "Includes": PATTERN,
    },
    "Glob": {
        "path": PATH,
        "dir_path": PATH,
        "pattern": PATTERN,
        "SearchDirectory": PATH,
        "Path": PATH,
        "Directory": PATH,
        "Dir": PATH,
        "Pattern": PATTERN,
    },
}

# Search argument keys that specify matching criteria, output modes, or flags
# rather than filesystem target locations or path filter patterns. Keys naming
# target directories or paths (`path`, `SearchDirectory`, `Path`, `Directory`,
# `Dir`) or pattern filters (`glob`, `include`, `Includes`) live in
# `READERS[tool]` so that every admitted filesystem path is resolved and bounded.
# Admitted keys for any search tool are derived as
# `set(READERS[tool]) | NON_PATH_SEARCH_KEYS`, ensuring no search argument can be
# admitted without being resolved (solorepo's #682).
#
# The unknown-key rule cuts both ways: for keys that name a location, an
# unrecognized spelling must refuse, because a floating upstream must never buy a
# permit outside the worktree; for keys that name options or formatting flags,
# unrecognized arguments risk refusing legitimate reviewer search calls whenever
# an upstream harness adds flags. The admitted non-path keys enumerated here cover
# each supported harness:
# - Claude Code (`Grep`): `output_mode`, `type`, `head_limit`, `offset`,
#   `multiline`, `context`, and ripgrep flags `-i`, `-n`, `-o`, `-A`, `-B`, `-C`.
# - Antigravity CLI (`grep_search`): `Query`, `IsRegex`, `CaseInsensitive`,
#   `MatchPerLine`, `AllowAccessGitignore`.
# - Gemini CLI (`grep_search`, `search_file_content`): `query`, `pattern`.
NON_PATH_SEARCH_KEYS = frozenset({
    # Common / query text:
    "pattern",
    "query",
    "Query",
    # Antigravity CLI options:
    "IsRegex",
    "CaseInsensitive",
    "MatchPerLine",
    "AllowAccessGitignore",
    # Claude Code options and ripgrep flags:
    "output_mode",
    "type",
    "head_limit",
    "offset",
    "multiline",
    "context",
    "-i",
    "-n",
    "-o",
    "-A",
    "-B",
    "-C",
})


# The one reader that may name no path: a search with no `path` searches the
# worktree, which the bound permits anyway. Every other reader names what it
# reads, so an input naming none of its keys is an argument spelling this hook
# does not know — `google-github-actions/run-gemini-cli@v0` floats, so a key can
# be renamed or added upstream between runs — and is refused rather than taken
# for the worktree, a permit being the one failure a floating upstream must not
# have.
SEARCHES = ("Grep",)


# Characters a glob matcher acts on. A component holding one of them matches
# more than itself, so the literal path a pattern is bounded by ends before it.
# Brace alternation is the one this hook refuses rather than bounds: an
# alternative carries its own root, so one of them may be absolute or ascending
# whatever the components around it say, and which alternations a matcher
# honours is its grammar rather than this hook's.
ALTERNATION = set("{}")
GLOBBY = set("*?[]") | ALTERNATION


# Harness scratch directories permitted for reviewer scratch artifacts and tool
# outputs: Claude Code's project directory, and Gemini CLI's per-project
# temporary directory. Neither harness's configuration directory is named, the
# credentials beside it being what the boundary exists to keep out.
HARNESS = (
    (pathlib.Path.home() / ".claude" / "projects").resolve(),
    (pathlib.Path.home() / ".gemini" / "tmp").resolve(),
)


def outside(path: str | pathlib.Path, root: pathlib.Path | None = None) -> str | None:
    """Validate whether a target filesystem path remains within permitted boundaries.

    Parameters:
        path: Relative or absolute target path to evaluate.
        root: Optional repository root to validate against (defaults to ROOT).

    Returns:
        str | None: Error message detailing the boundary violation if the resolved
        path escapes the repository root or enters `.git/` (and is not within a
        harness scratch directory); None if access is permitted.
    """
    base = (root or ROOT).resolve()
    target = pathlib.Path(path).expanduser()
    if not target.is_absolute():
        target = base / target
    target = target.resolve()
    if any(scratch in target.parents for scratch in HARNESS):
        return None
    if target != base and base not in target.parents:
        return f"{path} is outside the worktree {base}"
    if target == (base / ".git") or (base / ".git") in target.parents:
        return f"{path} is inside .git/, where the action keeps a token"
    return None


def ascends(part: str) -> bool:
    """Judge whether one pattern component is an ascent that can leave its bound.

    Catches literal `..` and pattern components whose literal characters are
    dots alone (`..*`, `.?`, `[.][.]`). Pattern components expanding wildcards
    without literal dots (`??`, `[!a][!a]`) do not match `.` or `..` across the
    supported matchers (Python glob, ripgrep, and node glob) during filesystem
    traversal.

    Parameters:
        part: One component of a glob pattern.

    Returns:
        bool: True where every character the component spells literally is a
        dot, identifying an ascending component; False otherwise.
    """
    literal = set(part) - GLOBBY
    return literal == {"."}


def outside_pattern(pattern: str) -> str | None:
    """Validate whether every path a glob pattern can match remains within permitted boundaries.

    A pattern is not the path it reads: `pathlib` takes each matcher
    metacharacter for an inert path component, so `**/.git/config` resolves to a
    path the worktree holds and `.git/` is no parent of, while a matcher for
    which `**` spans no directory reads `.git/config`. A pattern is therefore
    bounded by the components before its first metacharacter — the deepest
    directory every match lies under — and that bound holds only over what
    descends from it. Three things do not, and each is refused wherever it
    appears rather than bounded: a component naming `.git`, a component that can
    match `..` (`ascends`), and brace alternation, whose alternative carries a
    root of its own. The prefix rule alone cannot see any of them, its first
    metacharacter being where it stops looking: the literal prefix of
    `**/../../etc/passwd` is the worktree, as the prefix of `{/etc,.}/passwd`
    is, and neither pattern stays there.

    Precondition (solorepo's DR-251):
        Assumes the repository worktree contains no outbound symlinks (enforced
        via `audit_symlinks()` at checkout and gate). A wildcard component
        cannot traverse beyond a permitted literal prefix when every symlink
        beneath it resolves within repository boundaries.

    Parameters:
        pattern: Glob pattern a reader names the files it reads with.

    Returns:
        str | None: Error message detailing the boundary violation if a path the
        pattern can match escapes the repository root or enters `.git/`, or if
        the pattern is one this hook cannot bound; None if every such path is
        permitted.
    """
    if set(pattern) & ALTERNATION:
        return (f"{pattern} alternates, and an alternative carries its own root, "
                "which this hook does not bound")
    parts = pathlib.PurePath(pattern).parts
    if ".git" in parts:
        return f"{pattern} matches inside .git/, where the action keeps a token"
    if any(ascends(part) for part in parts):
        return f"{pattern} can match `..`, which leaves whatever bounds it"
    literal = []
    for part in parts:
        if set(part) & GLOBBY:
            break
        literal.append(part)
    prefix = str(pathlib.PurePath(*literal)) if literal else "."
    problem = outside(prefix)
    if problem is None or prefix == pattern:
        return problem
    return f"{pattern} matches under {prefix}, and {problem}"


def elsewhere(where: str | pathlib.Path) -> str | None:
    """Validate whether a working directory a shell call names is the worktree or under it.

    A working directory is not a read, so neither exemption `outside` carries
    belongs to it: a harness scratch directory is where the reviewer's artifacts
    go and not where its commands run, and `.git/` is refused nothing by the
    allowed grammar, which reads the same repository from either.

    Parameters:
        where: Directory the command is to run in, absolute or relative to the
            repository root.

    Returns:
        str | None: Error message naming the directory if it resolves outside the
        repository root; None if the command may run there.
    """
    target = pathlib.Path(where).expanduser()
    if not target.is_absolute():
        target = ROOT / target
    target = target.resolve()
    if target != ROOT and ROOT not in target.parents:
        return f"{where} is outside the worktree {ROOT}"
    return None


def targets(tool_input: dict[str, Any], keys: dict[str, str]) -> list[tuple[str, str]]:
    """Collect every path and pattern a reader's input names under the given keys.

    Parameters:
        tool_input: Input arguments passed to the tool call.
        keys: Input keys the reader may name a path in, each mapped to `PATH` or
            `PATTERN`.

    Returns:
        list[tuple[str, str]]: Each value named with the kind its key holds, in
        key order, a list-valued key contributing every entry; empty when the
        input names none of the keys.
    """
    found: list[tuple[str, str]] = []
    for key, kind in keys.items():
        value = tool_input.get(key)
        if isinstance(value, list):
            found.extend((entry, kind) for entry in value if entry)
        elif value:
            found.append((value, kind))
    return found


def outside_symlink(path: str | pathlib.Path, root: pathlib.Path | None = None) -> str | None:
    """Validate whether a target symlink resolves strictly within repository boundaries (solorepo's DR-251).

    Unlike runtime tool filesystem access (which permits harness scratch directories),
    repository symlinks have no exemption: every symlink must resolve strictly
    within the repository worktree root and never enter `.git/`.

    Parameters:
        path: Relative or absolute target path to evaluate.
        root: Optional repository root to validate against (defaults to ROOT).

    Returns:
        str | None: Error message detailing the boundary violation if the resolved
        path escapes the repository root or enters `.git/`; None if containment holds.
    """
    base = (root or ROOT).resolve()
    target = pathlib.Path(path).expanduser()
    if not target.is_absolute():
        target = base / target
    resolved = target.resolve()
    if resolved != base and base not in resolved.parents:
        return f"{path} is outside the worktree {base}"
    if resolved == (base / ".git") or (base / ".git") in resolved.parents:
        return f"{path} is inside .git/, where the action keeps a token"
    return None


def _readlink_safe(path: pathlib.Path) -> str:
    """Read symlink target path safely, returning 'unreadable' on filesystem error."""
    try:
        return str(path.readlink())
    except OSError:
        return "unreadable"


def _tracked_symlinks(base: pathlib.Path) -> tuple[list[str], set[pathlib.Path]]:
    """Audit git-tracked symlinks within the base repository."""
    problems: list[str] = []
    scanned: set[pathlib.Path] = set()
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-s", "-z"],
            cwd=base,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if proc.returncode == 0:
            for entry in proc.stdout.split(b"\0"):
                if not entry:
                    continue
                parts = entry.split(b"\t", 1)
                if len(parts) == 2 and parts[0].startswith(b"120000"):
                    rel = parts[1].decode("utf-8", errors="replace")
                    target_path = base / rel
                    scanned.add(target_path)
                    problem = outside_symlink(target_path, root=base)
                    if problem:
                        problems.append(f"tracked symlink `{rel}` -> `{_readlink_safe(target_path)}`: {problem}")
    except OSError:
        pass
    return problems, scanned


def _worktree_symlinks(base: pathlib.Path, scanned: set[pathlib.Path]) -> list[str]:
    """Audit filesystem symlinks across the worktree excluding ignored trees."""
    problems: list[str] = []
    ignored = (".git", ".venv", "node_modules", ".pytest_cache")
    for dirpath, dirnames, filenames in os.walk(base):
        dir_path = pathlib.Path(dirpath)
        all_entries = list(filenames) + list(dirnames)
        dirnames[:] = [
            d for d in dirnames
            if d not in ignored and not (dir_path / d).is_symlink()
        ]
        for name in all_entries:
            p = dir_path / name
            if p.is_symlink() and p not in scanned:
                scanned.add(p)
                problem = outside_symlink(p, root=base)
                if problem:
                    rel = str(p.relative_to(base)) if base in p.parents or p == base else str(p)
                    problems.append(f"worktree symlink `{rel}` -> `{_readlink_safe(p)}`: {problem}")
    return problems


def audit_symlinks(root: pathlib.Path | None = None) -> list[str]:
    """Audit all symlinks within a worktree to ensure none escape repository boundaries (solorepo's DR-251).

    Validates both git-tracked symlinks and untracked filesystem symlinks within the
    worktree. Refuses any symlink whose resolved destination escapes the repository
    root or enters `.git/`, with no harness scratch exemption.

    Parameters:
        root: Base directory to audit (defaulting to ROOT).

    Returns:
        list[str]: Descriptions of all symlink boundary violations detected; empty
        when all symlinks remain strictly within repository boundaries.
    """
    base = (root or ROOT).resolve()
    tracked_problems, scanned = _tracked_symlinks(base)
    worktree_problems = _worktree_symlinks(base, scanned)
    return sorted(tracked_problems + worktree_problems)


