"""Installation bundle inventory, parser, and validator for repository transfer (solorepo's DR-217).

Provides structured definitions for operating machinery, template replacements,
ownership policies, transformations, and source revision tracking across Specialization.
"""

from __future__ import annotations

import dataclasses
import pathlib
import subprocess
from collections.abc import Sequence
from typing import Any

import yaml

SCHEMA_VERSION: int = 1
VALID_KINDS: tuple[str, ...] = ("file", "dir", "symlink")
VALID_OWNERSHIPS: tuple[str, ...] = ("managed", "template", "symlink")
YAML_MAPPING = "YAML mapping"


class BundleError(Exception):
    """Base exception for installation bundle errors."""


class ManifestNotFoundError(BundleError, FileNotFoundError):
    """Raised when bundle manifest file is missing."""

    def __init__(self, path: pathlib.Path | str) -> None:
        super().__init__(f"Installation bundle manifest not found at: {path}")


class InvalidManifestError(BundleError, ValueError):
    """Raised when bundle manifest YAML structure is invalid."""

    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(f"Bundle manifest expected {expected}, got {actual}")


@dataclasses.dataclass(frozen=True)
class BundleItem:
    """A single artifact or directory declared in the installation bundle.

    Attributes:
        path: Path identifier relative to repository root.
        kind: Artifact filesystem type ('file', 'dir', or 'symlink').
        ownership: Lifecycle policy ('managed', 'template', or 'symlink').
        source: Optional source path in scaffold if different from destination.
        target: Optional destination path in specialized repo if different from source.
        transformations: Sequence of transformation names to apply during transfer.
    """

    path: str
    kind: str = "file"
    ownership: str = "managed"
    source: str | None = None
    target: str | None = None
    transformations: tuple[str, ...] = ()

    def source_path(self) -> str:
        """Returns the relative source path of the item within the scaffold repository."""
        return self.source if self.source is not None else self.path

    def dest_path(self) -> str:
        """Returns the relative destination path of the item within the target repository."""
        return self.target if self.target is not None else self.path

    def has_transformation(self, name: str) -> bool:
        """Returns True if the specified transformation is assigned to this item."""
        return name in self.transformations

    def to_dict(self) -> dict[str, Any]:
        """Serializes the bundle item into a dictionary."""
        data: dict[str, Any] = {
            "path": self.path,
            "kind": self.kind,
            "ownership": self.ownership,
        }
        if self.source is not None:
            data["source"] = self.source
        if self.target is not None:
            data["target"] = self.target
        if self.transformations:
            data["transformations"] = list(self.transformations)
        return data


@dataclasses.dataclass(frozen=True)
class Bundle:
    """The complete installation bundle manifest.

    Attributes:
        schema_version: Manifest format version integer.
        source_revision: Git commit SHA or revision identifier of the scaffold source.
        items: Sequence of items declaring transferred paths and policies.
    """

    schema_version: int = SCHEMA_VERSION
    source_revision: str = "unversioned"
    items: tuple[BundleItem, ...] = ()

    def managed_items(self) -> list[BundleItem]:
        """Returns all items governed by the managed ownership policy."""
        return [item for item in self.items if item.ownership == "managed"]

    def template_items(self) -> list[BundleItem]:
        """Returns all items governed by the template ownership policy."""
        return [item for item in self.items if item.ownership == "template"]

    def symlink_items(self) -> list[BundleItem]:
        """Returns all items declared as symlinks."""
        return [item for item in self.items if item.ownership == "symlink"]

    def inherited_paths(self) -> list[str]:
        """Returns sorted destination path strings for all managed operating machinery."""
        return sorted(item.dest_path() for item in self.managed_items())

    def items_with_transformation(self, name: str) -> list[BundleItem]:
        """Returns all items requiring the specified transformation."""
        return [item for item in self.items if item.has_transformation(name)]

    def to_dict(self) -> dict[str, Any]:
        """Serializes the bundle and its items into a dictionary."""
        return {
            "schema_version": self.schema_version,
            "source_revision": self.source_revision,
            "items": [item.to_dict() for item in self.items],
        }


def get_source_revision(repo_root: pathlib.Path | None = None) -> str:
    """Resolves the current git commit revision of the repository.

    Parameters:
        repo_root: Optional root directory of the git repository.

    Returns:
        The commit SHA string, or 'unversioned' if resolution fails.
    """
    root = repo_root or pathlib.Path(__file__).resolve().parents[3]
    try:
        res = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except OSError:
        pass
    return "unversioned"


def load_bundle(
    bundle_path: pathlib.Path | None = None,
    repo_root: pathlib.Path | None = None,
) -> Bundle:
    """Loads and parses the installation bundle YAML manifest.

    Parameters:
        bundle_path: Path to the bundle.yaml file. Defaults to .meta/bundle.yaml.
        repo_root: Root directory of the repository.

    Returns:
        The parsed Bundle instance with dynamic revision resolved.

    Raises:
        ManifestNotFoundError: If the bundle manifest file does not exist.
        InvalidManifestError: If YAML syntax or required top-level structure is invalid.
    """
    root = repo_root or pathlib.Path(__file__).resolve().parents[3]
    path = bundle_path or root / ".meta" / "bundle.yaml"

    if not path.is_file():
        raise ManifestNotFoundError(path)

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise InvalidManifestError(YAML_MAPPING, type(raw).__name__)

    version = int(raw.get("schema_version", SCHEMA_VERSION))
    rev = str(raw.get("source_revision", "")).strip()
    if rev == "dynamic" or not rev:
        rev = get_source_revision(root)

    raw_items = raw.get("items")
    if not isinstance(raw_items, Sequence):
        raise InvalidManifestError("sequence", type(raw_items).__name__)

    items: list[BundleItem] = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        p = str(entry.get("path", "")).strip()
        kind = str(entry.get("kind", "file")).strip()
        ownership = str(entry.get("ownership", "managed")).strip()
        src = entry.get("source")
        target = entry.get("target")
        trans = entry.get("transformations") or ()
        items.append(
            BundleItem(
                path=p,
                kind=kind,
                ownership=ownership,
                source=str(src).strip() if src is not None else None,
                target=str(target).strip() if target is not None else None,
                transformations=tuple(str(t).strip() for t in trans),
            )
        )

    return Bundle(
        schema_version=version,
        source_revision=rev,
        items=tuple(items),
    )


def _validate_item(item: BundleItem, root: pathlib.Path) -> list[str]:
    """Validates an individual bundle item's specification and presence on disk.

    Parameters:
        item: The BundleItem to validate.
        root: Root directory against which to verify asset paths.

    Returns:
        List of error description strings, empty if validation succeeded.
    """
    problems: list[str] = []
    if not item.path:
        return ["bundle: item declared with empty path"]

    if item.kind not in VALID_KINDS:
        problems.append(
            f"bundle: item {item.path} has invalid kind '{item.kind}', "
            f"expected one of {VALID_KINDS}"
        )

    if item.ownership not in VALID_OWNERSHIPS:
        problems.append(
            f"bundle: item {item.path} has invalid ownership '{item.ownership}', "
            f"expected one of {VALID_OWNERSHIPS}"
        )

    if item.kind == "symlink":
        dest = root / item.dest_path()
        target_path = (dest.parent / item.source_path()).resolve()
        if not target_path.exists():
            problems.append(
                f"bundle: symlink {item.path} references missing target {item.source_path()}"
            )
    else:
        src = root / item.source_path()
        if not src.exists():
            problems.append(
                f"bundle: {item.ownership} item source path missing on disk: "
                f"{item.source_path()}"
            )
        elif item.kind == "file" and not src.is_file():
            problems.append(
                f"bundle: item {item.path} declared kind 'file' but is not a regular file"
            )
        elif item.kind == "dir" and not src.is_dir():
            problems.append(
                f"bundle: item {item.path} declared kind 'dir' but is not a directory"
            )

    return problems


def validate_bundle(
    bundle: Bundle,
    repo_root: pathlib.Path | None = None,
) -> list[str]:
    """Validates bundle integrity, schema conformance, and asset existence on disk.

    Parameters:
        bundle: The Bundle instance to validate.
        repo_root: Root directory against which to verify asset paths.

    Returns:
        List of error description strings, empty if validation succeeded.
    """
    root = repo_root or pathlib.Path(__file__).resolve().parents[3]
    problems: list[str] = []

    if bundle.schema_version != SCHEMA_VERSION:
        problems.append(
            f"bundle: unsupported schema_version {bundle.schema_version} "
            f"(expected {SCHEMA_VERSION})"
        )

    if not bundle.source_revision or bundle.source_revision == "unversioned":
        problems.append("bundle: source_revision is unset or unversioned")

    if not bundle.items:
        problems.append("bundle: manifest declares no items")
        return problems

    for item in bundle.items:
        problems.extend(_validate_item(item, root))

    return problems
