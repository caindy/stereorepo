"""Where the repository is, the registry, and the assertions read into an index.

Every step of the gate reaches what this module holds: the paths, the schemas,
the one pass over `.meta/assertions/` that turns the documents into identified
objects and reference sites, and `@check`, which is how a step says it is one.
Nothing here checks anything, which is why every other module of the gate may
import it and it imports none of them (stereorepo's DR-150).

The registry is here rather than in `check.py` for that reason alone: a step
registers itself at its definition, so the decorator has to be importable by
every module that defines one, and `check.py` imports those modules.

Which slots hold references is read off the schema rather than listed here: a
slot is a reference when its range is a class with an identifier and it is not
inlined. Listing them by hand would drift from the schemas the moment either
moved.
"""
import collections
import dataclasses
import functools
import inspect
import pathlib
import re
import typing
from collections.abc import Callable, Sequence
from typing import Any

import yaml
from linkml_runtime import SchemaView

META = pathlib.Path(__file__).resolve().parent.parent
ROOT = META.parent
TEMPLATE = ROOT / "template"
TOKEN = re.compile(r"__[A-Z][A-Z0-9_]*__")
SCHEMAS = ("work_ontology.yaml", "ddd_ontology.yaml")

Step = collections.namedtuple("Step", "label run pre sources")
# Every step of the gate, in the order they are defined. A table of labels kept
# somewhere else is a second place to edit for every step, and it sits far from
# the function it names, so the label and the docstring that explains the step
# are never read together; the decorator puts them together.
STEPS: list[Step] = []
# What `main` has to give a step, and the only parameter names a step may
# require. A step takes the ones it names, in the order it names them.
SOURCES = ("index", "refs", "views", "asked", "pages")

UNKNOWN_SOURCES = ("{step} requires {unknown}, which the gate has nothing to pass; "
                   "a step's sources are {known}")
"""What registering a step raises on a parameter `SOURCES` does not name."""

Index = dict[str, tuple[str, dict[str, Any], str]]
"""The identified objects one pass over the assertions found: identifier to `(class, object, file)`."""

Refs = list[tuple[str, str, str]]
"""Every reference site one pass over the assertions found: `(identifier, class, where)`."""

Recorded = tuple[dict[str, int], dict[str, int]]
"""What a pair of ratchet baselines allows, as `Baselines.recorded` reads it: the bundle's first,
then the portfolio's (stereorepo's DR-314)."""


class CouldNotRun:
    """The step did not run, and carries why.

    Loud and unmarked: the gate reports it and exits zero where a person runs
    the gate, non-zero under CI (Article 6, stereorepo's DR-261)."""
    def __init__(self, why: str) -> None:
        self.why = why


class Passed:
    """The step ran and found nothing. Carries what it checked (its scope)."""
    def __init__(self, scope: str) -> None:
        self.scope = scope


class Found:
    """The step found problems. One line per problem."""
    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = problems


StepOutcome = Passed | Found | CouldNotRun
"""What a step comes to. Named apart from `probes.harness`'s `Outcome`, which is what a call
under a probe exited with."""

StepResult = StepOutcome | Sequence[str]
"""What a step returns: an outcome, or the bare sequence of problem lines that `report` reads as
a `Found` with no scope to print. The bare shape is what every step returned before `Passed`
carried a scope, and `check.py` still accepts it."""

StepFunction = typing.TypeVar("StepFunction", bound=Callable[..., StepResult])
"""A step, whatever sources it names. `check` hands back the same function, so a step keeps its
own signature and whatever annotations it carries."""


def check(label: str, pre: bool = False) -> Callable[[StepFunction], StepFunction]:
    """Register a step under the label the gate prints, at its definition.

    A parameter with a default is not a source: it is a seam a probe passes a
    fake through, and nothing is passed for it here. A parameter without one
    must name a source, and a step that asks for anything else is refused at
    import — which is the moment to find it, since the alternative is a gate
    that dies on the step rather than on the typo.

    `pre` runs the step before the schemas load. LinkML's loader raises on the
    first repeated key with no file and no line, so a duplicate in `work/*.yaml`
    used to take the whole gate down before the check that names both had a
    chance to run. A precheck is a step that must not stand
    behind that door.

    Args:
        label: What the gate prints for this step.
        pre: Whether the step runs before the schemas load.

    Returns:
        Callable[[StepFunction], StepFunction]: A decorator that appends the
        step to `STEPS` and hands it back unchanged, and that raises `TypeError`
        where the step requires a parameter `SOURCES` does not name.
    """
    def register(fn: StepFunction) -> StepFunction:
        sources = tuple(name for name, p in inspect.signature(fn).parameters.items()
                        if p.default is inspect.Parameter.empty)
        unknown = [name for name in sources if name not in SOURCES]
        if unknown:
            raise TypeError(UNKNOWN_SOURCES.format(step=fn.__name__, unknown=", ".join(unknown),
                                                  known=", ".join(SOURCES)))
        STEPS.append(Step(label, fn, pre, sources))
        return fn

    return register


@dataclasses.dataclass(frozen=True)
class Baselines:
    """The two files one ratchet reads: the bundle's, and the portfolio's own (stereorepo's DR-314).

    A copy of the bundle's managed items replaces `managed`, so its entries are
    the paths that copy brings. `portfolio` sits under `.meta/baselines/`, which
    no managed item contains, so a copy never touches it and it holds every
    other path. A key that is not a path, such as a `repeated suppressions`
    group, may sit in either file and is allowed the sum.

    Attributes:
        managed: The baseline beside the checks, shipped with the bundle.
        portfolio: The portfolio's baseline, absent until it holds an entry.
        manages: Whether a copy of the managed items brings a path. A probe
            passes its own; None reads `.meta/bundle.yaml` through
            `bundle_manages`.
    """

    managed: pathlib.Path
    portfolio: pathlib.Path
    manages: Callable[[str], bool] | None = None

    @classmethod
    def named(cls, stem: str) -> "Baselines":
        """The pair a ratchet named `stem` reads, `<stem>.baseline.yaml` in each place."""
        name = f"{stem}.baseline.yaml"
        return cls(META / "checks" / name, META / "baselines" / name)

    def recorded(self) -> Recorded:
        """What each file records, managed first, each empty where the file is absent."""
        return recorded_baseline(self.managed), recorded_baseline(self.portfolio)

    def where(self) -> tuple[str, str]:
        """Both files as a failure names them, repository-relative, managed first."""
        return (self.managed.relative_to(ROOT).as_posix(),
                self.portfolio.relative_to(ROOT).as_posix())

    def owner(self) -> Callable[[str], bool] | None:
        """`manages`, or `bundle_manages()` where none was given."""
        return self.manages if self.manages is not None else bundle_manages()


def summed(recorded: Recorded, groups: bool) -> dict[str, int]:
    """The count each key may hold across both files of a pair, summed.

    A `repeated suppressions` group, keyed by a rule and a reason joined with
    ` — `, can have sites in managed files and in a portfolio's own, so neither
    file alone holds its number (stereorepo's DR-314). A path belongs in one
    file, and is summed only so that a misplaced entry is still counted.

    Args:
        recorded: What `Baselines.recorded` read, managed first.
        groups: True for the group keys, False for the path keys.

    Returns:
        dict[str, int]: Each key of the kind asked for, to its summed count.
    """
    total: collections.Counter[str] = collections.Counter()
    for one in recorded:
        total.update({key: count for key, count in one.items() if (" — " in key) == groups})
    return dict(total)


def recorded_baseline(path: pathlib.Path) -> dict[str, int]:
    """A ratchet baseline read off disk: repository-relative path to the debt it may still hold.

    Args:
        path: The baseline file, a YAML mapping of path to count.

    Returns:
        dict[str, int]: The recorded counts, empty where the file is absent.
    """
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@functools.cache
def bundle_manages() -> Callable[[str], bool] | None:
    """`Bundle.manages` over `.meta/bundle.yaml`, or None where the bundle cannot load.

    The import is deferred, as `sources.inherited` defers it, so that the module
    every step imports does not load the bundle until a ratchet asks.
    """
    try:
        from lib.bundle import load_bundle

        return load_bundle(bundle_path=META / "bundle.yaml", repo_root=ROOT).manages
    except (ImportError, OSError, ValueError):
        return None


def misplaced(recorded: Recorded, baselines: Baselines,
              manages: Callable[[str], bool]) -> list[str]:
    """Every path entry held in the baseline that does not own it, naming the one that does.

    A portfolio entry for a managed path would add to the bundle's count where a
    copy should replace it, and a managed entry for a portfolio path would be
    lost at the next copy.

    Args:
        recorded: What `baselines.recorded()` read, managed first.
        baselines: The pair, named in each line.
        manages: Whether a copy of the managed items brings a path.

    Returns:
        list[str]: One line per misplaced entry. Keys holding ` — ` are not
        paths and are never misplaced.
    """
    managed, portfolio = baselines.where()
    held, own = recorded
    return ([f"{key}: {managed} holds a path the bundle does not manage — move it to {portfolio}"
             for key in sorted(held) if " — " not in key and not manages(key)]
            + [f"{key}: {portfolio} holds a path the bundle manages — move it to {managed}"
               for key in sorted(own) if " — " not in key and manages(key)])


def against_baseline(counts: dict[str, int], sites: dict[str, list[str]],
                     recorded: Recorded, noun: str,
                     baselines: Baselines) -> list[str]:
    """What a ratchet has to say about the counts it found, against the counts it recorded.

    The comparison the Ratchet Discipline turns on: a baseline that may fall
    and may not rise, so a file is failed on either side of its number — over,
    because the debt grew; under, because a baseline nobody lowers has stopped
    being one. It lives here rather than beside either step that reads it, because a
    checker importing another checker for it would be an edge back up the
    gate's import graph (stereorepo's DR-150).

    Args:
        counts: Repository-relative path to the debt the tree holds.
        sites: Repository-relative path to the detail lines listed under a
            failing file, each already formatted.
        recorded: What each baseline allows, managed first, as
            `Baselines.recorded` reads it. A group key is left to
            `comments.against_repeats`.
        noun: What is being counted, as it reads in the failure sentence.
        baselines: The pair, so that a failure names the file to edit. Where
            its `owner()` is None no entry is misplaced and every failure
            names `managed`.

    Returns:
        list[str]: One line per entry held in the wrong file, then one line per
        file whose count is not its recorded number, naming the number to
        write and the file that owns the path, and then one line per site in
        that file. A file a baseline holds and the tree no longer has is a
        stale entry and says so instead, naming the file that holds it.
    """
    owns = baselines.owner()
    problems = misplaced(recorded, baselines, owns) if owns is not None else []
    allowed_by = summed(recorded, groups=False)
    managed, portfolio = baselines.where()
    for relative in sorted(set(counts) | set(allowed_by)):
        count, allowed = counts.get(relative, 0), allowed_by.get(relative, 0)
        if count == allowed:
            continue
        if not (ROOT / relative).is_file():
            holder = managed if relative in recorded[0] else portfolio
            problems.append(f"{relative}: {holder} holds a file that does not exist "
                            f"— delete the entry")
            continue
        owner = managed if owns is None or owns(relative) else portfolio
        direction = "over" if count > allowed else "under"
        problems.append(f"{relative}: {count} {noun}, {direction} its baseline of "
                        f"{allowed} — write {count} in {owner}")
        problems.extend(f"     {line}" for line in sites.get(relative, []))
    return problems


def tree_root(sv: Any) -> str | None:
    """Returns the class designated as tree_root in the schema view, or None."""
    for name, cls in sv.all_classes().items():
        if cls.tree_root:
            return str(name)
    return None


def view_for(data: dict[str, Any], views: Sequence[Any]) -> tuple[Any | None, str | None]:
    """The schema whose container accepts every top-level key in this document."""
    for sv in views:
        root = tree_root(sv)
        if root and set(data) <= set(sv.class_slots(root)):
            return sv, root
    return None, None


@dataclasses.dataclass
class Collected:
    """What one pass over the assertions gathers: the index, and every reference site."""

    index: Index
    refs: Refs


def walk(obj: Any, cls: str, sv: Any, found: Collected, where: str) -> None:
    """Collect identified objects into `found.index` and reference sites into `found.refs`."""
    if not isinstance(obj, dict):
        return
    ident = sv.get_identifier_slot(cls)
    if ident and ident.name in obj:
        found.index[obj[ident.name]] = (cls, obj, where)
    for key, val in obj.items():
        try:
            slot = sv.induced_slot(key, cls)
        except Exception:  # noqa: BLE001  # reason: LinkML raises its own hierarchy for a key no class induces, and a key this schema does not model is skipped rather than fatal
            continue
        if slot is None or slot.range not in sv.all_classes():
            continue
        target = slot.range
        values = val if isinstance(val, list) else [val]
        if sv.get_identifier_slot(target) and not (slot.inlined or slot.inlined_as_list):
            for v in values:
                if isinstance(v, str):
                    found.refs.append((v, target, f"{where}: {cls}.{key}"))
        else:
            for v in values:
                walk(v, target, sv, found, where)


def views() -> list[Any]:
    """Loads LinkML SchemaView instances for all schemas declared in SCHEMAS."""
    return [SchemaView(str(META / s)) for s in SCHEMAS]


def collect(views: Sequence[Any]) -> tuple[Index, Refs, list[str]]:
    """Scans all YAML assertions under .meta/assertions/ and bootstraps/*/assertions/, indexing entities and references."""
    found, skipped = Collected({}, []), []
    paths = sorted((META / "assertions").rglob("*.yaml"))
    bootstraps_dir = ROOT / "bootstraps"
    if bootstraps_dir.is_dir():
        paths.extend(sorted(bootstraps_dir.glob("*/assertions/*.yaml")))
    for path in paths:
        data = yaml.safe_load(path.read_text())
        if not data:
            continue
        sv, root = view_for(data, views)
        if sv is None:
            skipped.append(path.name)
            continue
        for key, val in data.items():
            slot = sv.induced_slot(key, root)
            for item in (val if isinstance(val, list) else [val]):
                walk(item, slot.range, sv, found, path.name)
    return found.index, found.refs, skipped

