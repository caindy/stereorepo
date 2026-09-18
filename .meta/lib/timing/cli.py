"""The command line of `.meta/timing.py`: which workflows, how many runs, and whether to show steps.
"""
import argparse

from lib.timing import github, screen


def main(description):
    """Parses arguments and outputs workflow timing statistics.

    Args:
        description: The script's docstring, shown by `--help`.
    """
    p = argparse.ArgumentParser(description=description,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("workflow", nargs="*", default=None,
                   help="which workflows, by file name; all four by default")
    p.add_argument("--limit", type=int, default=20,
                   help="runs per workflow to summarise (default 20)")
    p.add_argument("--deep", default="5",
                   help="how many of those to open for the wait/run split (default 5, or 'all')")
    p.add_argument("--by", choices=["model", "difficulty"], default=None,
                   help="break down runs by 'model' (opus/sonnet) or 'difficulty' (hard/medium/easy)")
    p.add_argument("--by-model", action="store_const", dest="by", const="model",
                   help="shortcut for --by model")
    p.add_argument("--by-difficulty", action="store_const", dest="by", const="difficulty",
                   help="shortcut for --by difficulty")
    p.add_argument("--steps", action="store_true",
                   help="also the slowest steps across the runs opened")
    p.add_argument("--show", type=int, default=15,
                   help="how many steps to list with --steps (default 15)")
    args = p.parse_args()
    names = args.workflow or list(github.WORKFLOWS)
    names = [n if n.endswith(".yml") else f"{n}.yml" for n in names]
    if args.deep == "all":
        deep = args.limit
    else:
        try:
            deep = max(0, int(args.deep))
        except ValueError:
            p.error(f"invalid --deep value: {args.deep!r}")
    screen.screen(names, screen.Window(args.limit, deep, args.by), args.show, args.steps)
