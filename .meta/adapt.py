#!/usr/bin/env -S uvx --python 3.13 --with pyyaml python
"""Brownfield repository adoption planner and CLI dispatcher (solorepo's DR-217).

Analyzes target repositories against the versioned solorepo installation bundle
and product configuration to plan collision-aware adoption.
"""

from __future__ import annotations

import argparse
import importlib.util
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

_META_DIR = pathlib.Path(__file__).resolve().parent
if str(_META_DIR) not in sys.path:
    sys.path.insert(0, str(_META_DIR))

from lib.adapt import (  # noqa: E402  # reason: sys.path order
    AdoptionPlan,
    build_adoption_plan,
    load_bundle,
    load_product_config,
)

__all__ = [
    "build_adoption_plan",
    "load_product_config",
    "main",
]


def _format_plan(plan: AdoptionPlan, fmt: str) -> str:
    """Formats an adoption plan according to the specified output format."""
    if fmt == "json":
        return plan.to_json()
    if fmt == "yaml":
        return plan.to_yaml()
    return plan.to_text()


def _cmd_plan(args: argparse.Namespace) -> int:
    """Executes adoption planning against target repository."""
    target_path = pathlib.Path(args.target).resolve()
    scaffold_path = pathlib.Path(args.root).resolve() if args.root else _META_DIR.parent
    bundle_path = pathlib.Path(args.bundle).resolve() if args.bundle else _META_DIR / "bundle.yaml"

    try:
        bundle = load_bundle(bundle_path=bundle_path, repo_root=scaffold_path)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Error loading installation bundle: {exc}", file=sys.stderr)
        return 1

    try:
        config = load_product_config(args.config)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Error loading product config: {exc}", file=sys.stderr)
        return 1

    try:
        plan = build_adoption_plan(
            target_dir=target_path,
            bundle=bundle,
            config=config,
            scaffold_dir=scaffold_path,
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Error building adoption plan: {exc}", file=sys.stderr)
        return 1

    fmt = "json" if args.json else ("yaml" if args.yaml else args.format)
    output = _format_plan(plan, fmt)

    if not args.quiet:
        print(output)

    if args.fail_on_conflict and plan.has_conflicts:
        return 1
    return 0


def main() -> None:
    """CLI dispatcher for brownfield repository adoption."""
    parser = argparse.ArgumentParser(
        description="Plan collision-aware brownfield adoption for existing Product repositories."
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    plan_p = subparsers.add_parser(
        "plan",
        help="Generate collision-aware adoption plan for a target repository",
    )
    plan_p.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Target repository directory (defaults to current directory)",
    )
    plan_p.add_argument(
        "--root",
        "-r",
        default=None,
        help="Scaffold repository root directory (defaults to parent of .meta/)",
    )
    plan_p.add_argument(
        "--bundle",
        "-b",
        default=None,
        help="Path to bundle YAML manifest (defaults to .meta/bundle.yaml)",
    )
    plan_p.add_argument(
        "--config",
        "-c",
        default=None,
        help="Path to optional product configuration YAML file",
    )
    plan_p.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "yaml"],
        default="text",
        help="Output format (defaults to text)",
    )
    plan_p.add_argument(
        "--json",
        action="store_true",
        help="Convenience alias for --format json",
    )
    plan_p.add_argument(
        "--yaml",
        action="store_true",
        help="Convenience alias for --format yaml",
    )
    plan_p.add_argument(
        "--fail-on-conflict",
        action="store_true",
        help="Exit with non-zero status if any conflicts are detected",
    )
    plan_p.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress normal output",
    )
    plan_p.set_defaults(func=_cmd_plan)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
