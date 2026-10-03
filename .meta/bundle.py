#!/usr/bin/env -S uvx --python 3.13 --with pyyaml python
"""Installation bundle inventory facade and CLI dispatcher (stereorepo's DR-344).

Exposes installation bundle definitions, manifest loading, validation, and listing
subcommands for Specialization and repository verification.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import subprocess
import sys

if importlib.util.find_spec("yaml") is None:
    cmd = [
        "uvx",
        "--python",
        "3.13",
        "--with",
        "pyyaml",
        "python",
        str(pathlib.Path(__file__).resolve()),
        *sys.argv[1:],
    ]
    res = subprocess.run(cmd, check=False)
    sys.exit(res.returncode)

# Ensure .meta is on sys.path for direct invocation
_META_DIR = pathlib.Path(__file__).resolve().parent
if str(_META_DIR) not in sys.path:
    sys.path.insert(0, str(_META_DIR))

from lib.bundle import (  # noqa: E402  # reason: sys.path order
    SCHEMA_VERSION,
    Bundle,
    BundleItem,
    get_source_revision,
    load_bundle,
    sync,
    validate_bundle,
)

__all__ = [
    "SCHEMA_VERSION",
    "Bundle",
    "BundleItem",
    "get_source_revision",
    "load_bundle",
    "main",
    "validate_bundle",
]


def _cmd_check(args: argparse.Namespace) -> int:
    """Validates the installation bundle against disk."""
    bundle_path = pathlib.Path(args.bundle) if args.bundle else None
    root_path = pathlib.Path(args.root) if args.root else None
    try:
        bundle = load_bundle(bundle_path=bundle_path, repo_root=root_path)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Error loading bundle: {exc}", file=sys.stderr)
        return 1

    errors = validate_bundle(bundle, repo_root=root_path)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        print(f"\nTotal errors: {len(errors)}", file=sys.stderr)
        return 1

    if not args.quiet:
        rev = bundle.source_revision
        print(f"OK: Installation bundle valid ({len(bundle.items)} items, revision {rev})")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    """Lists items in the installation bundle."""
    bundle_path = pathlib.Path(args.bundle) if args.bundle else None
    root_path = pathlib.Path(args.root) if args.root else None
    try:
        bundle = load_bundle(bundle_path=bundle_path, repo_root=root_path)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Error loading bundle: {exc}", file=sys.stderr)
        return 1

    items = list(bundle.items)
    if args.ownership:
        items = [item for item in items if item.ownership == args.ownership]
    if args.kind:
        items = [item for item in items if item.kind == args.kind]
    if args.transformation:
        items = [item for item in items if item.has_transformation(args.transformation)]

    if args.json:
        print(json.dumps([item.to_dict() for item in items], indent=2))
        return 0

    for item in items:
        trans = f" [{' '.join(item.transformations)}]" if item.transformations else ""
        src = f" (source: {item.source})" if item.source else ""
        print(f"{item.ownership:9s}{item.kind:7s} {item.path}{src}{trans}")
    return 0


def _cmd_manifest(args: argparse.Namespace) -> int:
    """Outputs the complete bundle manifest."""
    bundle_path = pathlib.Path(args.bundle) if args.bundle else None
    root_path = pathlib.Path(args.root) if args.root else None
    try:
        bundle = load_bundle(bundle_path=bundle_path, repo_root=root_path)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Error loading bundle: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(bundle.to_dict(), indent=2))
    return 0


def _checkout_tool(source: pathlib.Path) -> pathlib.Path | None:
    """Returns the checkout's `bundle.py` to hand a sync to, or None where it is this file.

    The None is what stops the hand-off from repeating: the checkout's `bundle.py`,
    started by a hand-off, finds itself here and syncs in place, as does a checkout
    synced from itself (stereorepo's DR-322).
    """
    tool = (source / ".meta" / "bundle.py").resolve()
    return None if tool == pathlib.Path(__file__).resolve() else tool


def _cmd_sync(args: argparse.Namespace) -> int:
    """Syncs the portfolio at `--root` from the stereorepo checkout named, with the
    checkout's own `bundle.py` (stereorepo's DR-315, DR-322)."""
    source = pathlib.Path(args.source).resolve()
    portfolio = pathlib.Path(args.root).resolve() if args.root else _META_DIR.parent
    if not (source / ".meta" / "bundle.py").is_file():
        print(f"sync: refused, nothing changed: {source} has no .meta/bundle.py to run its sync",
              file=sys.stderr)
        return 1
    tool = _checkout_tool(source)
    if tool is None:
        return _sync_in_place(source, portfolio)
    cmd = [sys.executable, str(tool), "--root", str(portfolio), "sync", str(source)]
    return subprocess.run(cmd, check=False).returncode


def _sync_in_place(source: pathlib.Path, portfolio: pathlib.Path) -> int:
    """Syncs `portfolio` from `source` with the sync logic this file imports, and prints
    each change."""
    try:
        changes = sync.plan(source, portfolio)
    except (sync.SyncRefusedError, ValueError, OSError) as exc:
        print(f"sync: refused, nothing changed: {exc}", file=sys.stderr)
        return 1
    try:
        sync.apply(changes, source, portfolio)
    except OSError as exc:
        print(f"sync: failed part way, so the portfolio is partly synced: {exc}; "
              "`git status` shows what changed", file=sys.stderr)
        return 1
    for verb, paths in (("updated", changes.updated), ("added", changes.added),
                        ("removed", changes.removed)):
        for path in paths:
            print(f"{verb:8s}{path}")
    print(f"sync: {len(changes.updated)} updated, {len(changes.added)} added, "
          f"{len(changes.removed)} removed; nothing committed. Run `just render` next.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI dispatcher for bundle operations."""
    parser = argparse.ArgumentParser(
        description="Inspect and validate the stereorepo installation bundle."
    )
    parser.add_argument(
        "--bundle",
        "-b",
        default=None,
        help="Path to bundle YAML manifest (defaults to .meta/bundle.yaml)",
    )
    parser.add_argument(
        "--root",
        "-r",
        default=None,
        help="Repository root directory (defaults to parent of .meta/)",
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    check_p = subparsers.add_parser(
        "check", help="Validate bundle integrity and filesystem matches"
    )
    check_p.add_argument("--quiet", "-q", action="store_true", help="Suppress success message")
    check_p.set_defaults(func=_cmd_check)

    list_p = subparsers.add_parser("list", help="List bundle items")
    list_p.add_argument(
        "--ownership", choices=["managed", "template", "symlink", "portfolio"],
        help="Filter by ownership",
    )
    list_p.add_argument("--kind", choices=["file", "dir", "symlink"], help="Filter by kind")
    list_p.add_argument("--transformation", help="Filter by required transformation")
    list_p.add_argument("--json", action="store_true", help="Output in JSON format")
    list_p.set_defaults(func=_cmd_list)

    manifest_p = subparsers.add_parser("manifest", help="Dump complete manifest as JSON")
    manifest_p.set_defaults(func=_cmd_manifest)

    sync_p = subparsers.add_parser(
        "sync",
        help="Copy a stereorepo checkout's managed items into the portfolio at --root, "
        "and remove what its bundle dropped",
    )
    sync_p.add_argument(
        "source",
        help="Path to the stereorepo checkout; under `just` a relative path is read "
        "from the portfolio's root",
    )
    sync_p.set_defaults(func=_cmd_sync)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
