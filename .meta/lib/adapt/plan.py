"""Brownfield repository adoption planning library (stereorepo's DR-217).

Provides data structures, path classification, and collision-aware planning
to adapt existing Product repositories into stereorepo management.
"""

from __future__ import annotations

import dataclasses
import enum
import fnmatch
import json
import pathlib
from collections.abc import Sequence
from typing import Any

import yaml

from lib.adapt.omit import OMIT_REASON, below, scaffold_only_inside
from lib.adapt.tracked import git_tracked_files
from lib.bundle import Bundle, BundleItem, load_bundle

DEFAULT_INTEGRATIONS: frozenset[str] = frozenset({"AGENTS.md", "README.md"})

DEFAULT_IGNORES: frozenset[str] = frozenset({
    ".git", ".git/*", ".git/**", "__pycache__", "__pycache__/*", "*.pyc",
    ".venv", ".venv/*", ".mypy_cache", ".ruff_cache", "target", "node_modules",
})


class PathClassification(str, enum.Enum):
    """Classification of target repository path during brownfield adoption."""

    CREATE = "create"
    RETAIN = "retain"
    INTEGRATE = "integrate"
    CONFLICT = "conflict"
    OMIT = "omit"


@dataclasses.dataclass(frozen=True)
class ProductConfig:
    """Configuration specifying product-specific adoption rules and tokens.

    Attributes:
        integrations: Paths to treat as integrative merges rather than collisions.
        retain: Path patterns explicitly retained untouched without modification.
        ignore: Path patterns ignored during target repository scanning.
        tokens: Dictionary of template replacement tokens.
    """

    integrations: tuple[str, ...] = ()
    retain: tuple[str, ...] = ()
    ignore: tuple[str, ...] = ()
    tokens: dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class PlannedAction:
    """A classified adoption action for a specific repository path.

    Attributes:
        path: Relative path within target repository.
        classification: Target action classification (create, retain, integrate, conflict, omit).
        reason: Explanation for the classification.
        kind: Filesystem type ('file', 'dir', or 'symlink').
        source: Optional scaffold source path if different from target path.
    """

    path: str
    classification: PathClassification
    reason: str
    kind: str = "file"
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializes the planned action to a dictionary."""
        d: dict[str, Any] = {
            "path": self.path,
            "classification": self.classification.value,
            "reason": self.reason,
            "kind": self.kind,
        }
        if self.source is not None:
            d["source"] = self.source
        return d


@dataclasses.dataclass(frozen=True)
class AdoptionPlan:
    """Complete deterministic brownfield adoption plan.

    Attributes:
        target_dir: Target repository directory path string.
        source_revision: Scaffold source revision hash or string.
        actions: Sequence of planned actions sorted deterministically by path.
    """

    target_dir: str
    source_revision: str
    actions: tuple[PlannedAction, ...] = ()

    @property
    def conflicts(self) -> tuple[PlannedAction, ...]:
        """Returns sequence of planned actions classified as conflicts."""
        return tuple(a for a in self.actions if a.classification == PathClassification.CONFLICT)

    @property
    def has_conflicts(self) -> bool:
        """Returns True if any conflicts are detected in the adoption plan."""
        return bool(self.conflicts)

    @property
    def summary(self) -> dict[str, int]:
        """Returns action count dictionary keyed by classification value."""
        counts = {c.value: 0 for c in PathClassification}
        for a in self.actions:
            counts[a.classification.value] += 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        """Serializes the adoption plan into a dictionary."""
        return {
            "target_dir": self.target_dir,
            "source_revision": self.source_revision,
            "summary": self.summary,
            "conflicts_count": len(self.conflicts),
            "actions": [a.to_dict() for a in self.actions],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serializes the adoption plan to formatted JSON."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_yaml(self) -> str:
        """Serializes the adoption plan to YAML."""
        return yaml.dump(self.to_dict(), sort_keys=False)

    def to_text(self) -> str:
        """Formats the adoption plan into human-readable text."""
        lines = [
            f"Adoption plan for {self.target_dir} (scaffold revision: {self.source_revision}):",
            "-" * 80,
        ]
        for a in self.actions:
            lines.append(f"{a.classification.value.upper():9s} {a.kind:7s} {a.path} ({a.reason})")
        lines.append("-" * 80)
        counts = [f"{c.value}: {self.summary[c.value]}" for c in PathClassification]
        lines.append(f"Summary: {', '.join(counts)}")
        if self.conflicts:
            lines.append(f"\nConflicts ({len(self.conflicts)}):")
            for c in self.conflicts:
                lines.append(f"  - {c.path}: {c.reason}")
        return "\n".join(lines)


def load_product_config(config_path: pathlib.Path | str | None) -> ProductConfig:
    """Loads ProductConfig from an optional YAML file path.

    Parameters:
        config_path: Path to configuration YAML file, or None for empty defaults.

    Returns:
        ProductConfig parsed from disk, or default empty configuration.

    Raises:
        FileNotFoundError: If the specified config file does not exist.
        ValueError: If config file is not a valid YAML mapping.
    """
    if config_path is None:
        return ProductConfig()
    path = pathlib.Path(config_path)
    if not path.is_file():
        msg = f"Product config file not found: {path}"
        raise FileNotFoundError(msg)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = f"Product config expected YAML mapping, got {type(raw).__name__}"
        raise ValueError(msg)
    integrations = tuple(str(x).strip() for x in raw.get("integrations", ()) if str(x).strip())
    retain = tuple(str(x).strip() for x in raw.get("retain", ()) if str(x).strip())
    ignore = tuple(str(x).strip() for x in raw.get("ignore", ()) if str(x).strip())
    raw_tokens = raw.get("tokens", {})
    tokens = {str(k): str(v) for k, v in raw_tokens.items()} if isinstance(raw_tokens, dict) else {}
    return ProductConfig(
        integrations=integrations,
        retain=retain,
        ignore=ignore,
        tokens=tokens,
    )


def _is_ignored(path_str: str, ignores: Sequence[str] | frozenset[str]) -> bool:
    """Checks whether a relative path matches any ignore pattern."""
    return _matches_pattern(path_str, ignores)


def _matches_pattern(path_str: str, patterns: Sequence[str] | frozenset[str]) -> bool:
    """Checks whether a relative path matches any inclusion pattern."""
    pure = pathlib.PurePosixPath(path_str)
    for pat in patterns:
        if pat.endswith("/*") or pat.endswith("/**"):
            prefix = pat.rstrip("/*")
            if path_str == prefix or path_str.startswith(f"{prefix}/"):
                return True
        elif (
            fnmatch.fnmatch(path_str, pat)
            or fnmatch.fnmatch(pure.name, pat)
            or path_str == pat
            or path_str.startswith(f"{pat.rstrip('/')}/")
        ):
            return True
    return False


def _scan_target_files(
    target_dir: pathlib.Path,
    ignores: frozenset[str] | tuple[str, ...],
) -> list[str]:
    """Lists the target's relative file and symlink paths that are not ignored.

    In a git repository these are the tracked paths that exist on disk as a
    file or symlink, which leaves out deleted paths and submodule
    directories. They are deduplicated, since during an unfinished merge
    `ls-files` prints an unmerged path once per stage. Elsewhere the working
    tree is walked.
    """
    if not target_dir.is_dir():
        return []
    tracked = git_tracked_files(target_dir)
    if tracked is not None:
        return sorted({
            p
            for p in tracked
            if not _is_ignored(p, ignores)
            and ((target_dir / p).is_symlink() or (target_dir / p).is_file())
        })
    rel_paths: list[str] = []
    for root, dirnames, filenames in target_dir.walk(follow_symlinks=False):
        rel_root = root.relative_to(target_dir).as_posix()
        if rel_root != "." and _is_ignored(rel_root, ignores):
            dirnames.clear()
            continue
        dirnames[:] = [
            d
            for d in dirnames
            if not _is_ignored((root / d).relative_to(target_dir).as_posix(), ignores)
        ]
        for f in filenames:
            rel_file = (root / f).relative_to(target_dir).as_posix()
            if not _is_ignored(rel_file, ignores):
                rel_paths.append(rel_file)
    return sorted(rel_paths)


def _content_matches(
    target_file: pathlib.Path,
    source_file: pathlib.Path,
    tokens: dict[str, str] | None = None,
) -> bool:
    """Checks whether target file content matches scaffold source directly or via tokens."""
    if not target_file.is_file() or not source_file.is_file():
        return False
    target_bytes = target_file.read_bytes()
    source_bytes = source_file.read_bytes()
    if target_bytes == source_bytes:
        return True
    if not tokens:
        return False
    try:
        source_text = source_bytes.decode("utf-8")
        target_text = target_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return False
    for k, v in tokens.items():
        placeholder = f"__{k}__"
        source_text = source_text.replace(placeholder, v)
    return source_text == target_text


def _classify_dir(
    item: BundleItem,
    target_path: pathlib.Path,
) -> PlannedAction:
    """Classifies a bundle item declared as a directory."""
    dest = item.dest_path().rstrip("/")
    if target_path.is_dir() and not target_path.is_symlink():
        return PlannedAction(
            path=dest,
            classification=PathClassification.RETAIN,
            reason="directory already exists in target",
            kind="dir",
            source=item.source,
        )
    actual_kind = "symlink" if target_path.is_symlink() else "file"
    return PlannedAction(
        path=dest,
        classification=PathClassification.CONFLICT,
        reason=f"type mismatch: scaffold declares dir but target is {actual_kind}",
        kind="dir",
        source=item.source,
    )


def _classify_symlink(
    item: BundleItem,
    target_path: pathlib.Path,
) -> PlannedAction:
    """Classifies a bundle item declared as a symlink."""
    dest = item.dest_path().rstrip("/")
    if not target_path.is_symlink():
        actual_kind = "dir" if target_path.is_dir() else "file"
        return PlannedAction(
            path=dest,
            classification=PathClassification.CONFLICT,
            reason=f"type mismatch: scaffold declares symlink but target is {actual_kind}",
            kind="symlink",
            source=item.source,
        )
    target_dest = str(target_path.readlink())
    expected = item.source_path()
    if target_dest == expected:
        return PlannedAction(
            path=dest,
            classification=PathClassification.RETAIN,
            reason="symlink already points to expected target",
            kind="symlink",
            source=item.source,
        )
    return PlannedAction(
        path=dest,
        classification=PathClassification.CONFLICT,
        reason=f"symlink points to {target_dest}, expected {expected}",
        kind="symlink",
        source=item.source,
    )


def _classify_file(
    item: BundleItem,
    target_path: pathlib.Path,
    scaffold_dir: pathlib.Path,
    tokens: dict[str, str],
) -> PlannedAction:
    """Classifies a bundle item declared as a regular file."""
    dest = item.dest_path().rstrip("/")
    if target_path.is_dir() or target_path.is_symlink():
        actual_kind = "dir" if target_path.is_dir() else "symlink"
        return PlannedAction(
            path=dest,
            classification=PathClassification.CONFLICT,
            reason=f"type mismatch: scaffold declares file but target is {actual_kind}",
            kind="file",
            source=item.source,
        )
    source_file = scaffold_dir / item.source_path()
    if _content_matches(target_path, source_file, tokens):
        return PlannedAction(
            path=dest,
            classification=PathClassification.RETAIN,
            reason="target content matches scaffold",
            kind="file",
            source=item.source,
        )
    return PlannedAction(
        path=dest,
        classification=PathClassification.CONFLICT,
        reason="target file content differs from scaffold without integration policy",
        kind="file",
        source=item.source,
    )


def _classify_bundle_item(
    item: BundleItem,
    target_dir: pathlib.Path,
    scaffold_dir: pathlib.Path,
    config: ProductConfig,
) -> PlannedAction:
    """Classifies a single bundle item against the target repository."""
    dest = item.dest_path().rstrip("/")
    target_path = target_dir / dest

    if not target_path.exists() and not target_path.is_symlink():
        return PlannedAction(
            path=dest,
            classification=PathClassification.CREATE,
            reason="scaffold item absent in target repository",
            kind=item.kind,
            source=item.source,
        )

    if _matches_pattern(dest, config.retain):
        return PlannedAction(
            path=dest,
            classification=PathClassification.RETAIN,
            reason="explicitly configured for retention",
            kind=item.kind,
            source=item.source,
        )

    if dest in DEFAULT_INTEGRATIONS or _matches_pattern(dest, config.integrations):
        return PlannedAction(
            path=dest,
            classification=PathClassification.INTEGRATE,
            reason="preserves target content while integrating stereorepo conventions",
            kind=item.kind,
            source=item.source,
        )

    if item.kind == "dir":
        return _classify_dir(item, target_path)
    if item.kind == "symlink":
        return _classify_symlink(item, target_path)
    return _classify_file(item, target_path, scaffold_dir, config.tokens)


def build_adoption_plan(
    target_dir: pathlib.Path | str,
    bundle: Bundle | None = None,
    bundle_path: pathlib.Path | str | None = None,
    config: ProductConfig | None = None,
    scaffold_dir: pathlib.Path | str | None = None,
) -> AdoptionPlan:
    """Builds a deterministic, collision-aware adoption plan for a target repository.

    Parameters:
        target_dir: Target repository directory to inspect.
        bundle: Optional pre-loaded Bundle manifest.
        bundle_path: Optional path to bundle YAML manifest.
        config: Optional ProductConfig specifying overrides and tokens.
        scaffold_dir: Optional root directory of scaffold repository.

    Returns:
        AdoptionPlan containing classified actions sorted deterministically by path.

    Raises:
        FileNotFoundError: If target_dir does not exist.
    """
    target_p = pathlib.Path(target_dir).resolve()
    if not target_p.exists():
        msg = f"Target repository directory not found: {target_p}"
        raise FileNotFoundError(msg)

    scaffold_p = (
        pathlib.Path(scaffold_dir).resolve()
        if scaffold_dir
        else pathlib.Path(__file__).resolve().parents[3]
    )
    active_bundle = bundle or load_bundle(
        bundle_path=pathlib.Path(bundle_path) if bundle_path else None,
        repo_root=scaffold_p,
    )
    active_config = config or ProductConfig()

    actions: list[PlannedAction] = []
    seen_destinations: set[str] = set()
    dir_dests: list[str] = []

    for item in active_bundle.items:
        dest = item.dest_path().rstrip("/")
        if not dest or dest in seen_destinations:
            continue
        seen_destinations.add(dest)
        if item.kind == "dir":
            dir_dests.append(dest)
        action = _classify_bundle_item(item, target_p, scaffold_p, active_config)
        actions.append(action)

    omitted_paths = scaffold_only_inside(dir_dests)
    actions.extend(
        PlannedAction(path=p, classification=PathClassification.OMIT, reason=OMIT_REASON,
                      kind="dir" if (scaffold_p / p).is_dir() else "file")
        for p in omitted_paths
    )

    all_ignores = tuple(DEFAULT_IGNORES) + tuple(active_config.ignore)
    target_files = _scan_target_files(target_p, all_ignores)

    for p in target_files:
        if p in seen_destinations or below(p, omitted_paths):
            continue
        kind = "symlink" if (target_p / p).is_symlink() else "file"
        if _matches_pattern(p, active_config.retain):
            cls = PathClassification.RETAIN
            reason = "explicitly configured for retention"
        elif p in DEFAULT_INTEGRATIONS or _matches_pattern(p, active_config.integrations):
            cls = PathClassification.INTEGRATE
            reason = "preserves target content while integrating stereorepo conventions"
        else:
            cls = PathClassification.RETAIN
            reason = "existing product artifact retained untouched"
        actions.append(PlannedAction(path=p, classification=cls, reason=reason, kind=kind))

    sorted_actions = tuple(sorted(actions, key=lambda a: a.path))
    return AdoptionPlan(
        target_dir=str(target_p),
        source_revision=active_bundle.source_revision,
        actions=sorted_actions,
    )
