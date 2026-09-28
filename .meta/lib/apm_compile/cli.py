"""The command line of `.meta/apm_compile.py`: compile, `--check`, `--reconcile`, or an `apm` operation (stereorepo's DR-201).
"""
from __future__ import annotations

import argparse
import sys

from lib.apm_compile import harness


def main(description: str | None) -> None:
    """CLI entrypoint for APM compiler, packaging, and root reconciliation (stereorepo's DR-201).

    Args:
        description: The script's docstring, shown by `--help`.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--check", action="store_true", help="Fail if generated primitives are stale")
    parser.add_argument("--reconcile", action="store_true", help="Reconcile harness root symlinks only")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["validate", "pack", "compile", "audit", "doctor", "preview"],
        help="APM operation to perform",
    )
    parser.add_argument("extra_args", nargs=argparse.REMAINDER, help="Additional arguments forwarded to apm")
    args = parser.parse_args()

    if args.reconcile:
        actions = harness.reconcile_root()
        if actions:
            print("\n".join(actions))
        else:
            print("Harness root documentation symlinks are intact.")
        sys.exit(0)

    if args.check:
        from lib.apm_compile import primitives

        stale = primitives.check_primitives()
        if stale:
            print("APM primitives are stale:")
            for item in stale:
                print(f"  {item}")
            sys.exit(1)
        print("APM primitives are up to date.")
        sys.exit(0)

    if args.command in ("validate", "pack", "compile", "audit", "doctor", "preview"):
        from lib.apm_compile import apm

        if args.command == "validate":
            sys.exit(apm.validate_apm())
        if args.command == "pack":
            sys.exit(apm.pack_apm(args.extra_args))
        if args.command == "compile":
            sys.exit(apm.compile_apm(args.extra_args))
        sys.exit(apm.run_apm([args.command, *args.extra_args]))

    from lib.apm_compile import primitives

    count = primitives.write_primitives()
    print(f"Compiled {count} APM primitives.")
