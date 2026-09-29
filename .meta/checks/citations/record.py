"""A citation resolved against the record: a Decision that exists, an Artifact named by the Decision it cites, and the citations inherited material carries as stereorepo's (stereorepo's DR-132).
"""


from typing import Any

from checks.citations import loaders
from checks.collect import ROOT, TEMPLATE, check
from checks.files import FENCED


@check("cited decisions")
def cited_decisions(index: dict[str, Any]) -> list[str]:
    """Validate that every Decision Record cited in durable prose resolves in the index.

    Ensures that Decision citations (`DR-nnn`) in durable files resolve to known Decision
    records in `index` (or the template seed), and enforces that files inherited by
    specialized portfolios use the qualified `stereorepo's DR-nnn` form
    (stereorepo's DR-121, stereorepo's DR-124).

    Parameters:
        index (dict): LinkML model index mapping URI identifiers to entity tuples.

    Returns:
        list[str]: Validation problem messages for dangling or unqualified DR citations.
    """
    known = {d.rsplit("/", 1)[-1] for d, (cls, _, _) in index.items() if cls == "Decision"}
    if not known:
        return []
    home = loaders.SCAFFOLD in index
    seed = {m.group(1) for path in (TEMPLATE / ".meta" / "assertions" / "decisions").glob("DR-*.yaml")
            if (m := loaders.DR.search(path.name))}
    copied = loaders.copied_files()
    problems = []
    for path in loaders.durable(copied):
        seeded = TEMPLATE in path.parents
        try:
            text = FENCED.sub("", path.read_text())
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(ROOT)
        foreign = {num for m in loaders.FOREIGN.finditer(text) for num in loaders.DR.findall(m.group())}
        bare = set(loaders.DR.findall(loaders.FOREIGN.sub("", text)))
        if home:
            for num in sorted(foreign - known):
                problems.append(f"{rel}: stereorepo's DR-{num} is cited and does not exist")
        outmoded = {n for n in bare if home and int(n) < loaders.OUTMODED_BELOW}
        for num in sorted(bare - (seed if seeded else known) - outmoded):
            problems.append(f"{rel}: DR-{num} is cited and does not exist")
        if home and path in copied:
            for num in sorted(bare - seed):
                problems.append(f"{rel}: DR-{num} is cited bare in a file a portfolio inherits, "
                                "where it will come to mean the portfolio's; cite it as stereorepo's")
    return problems


@check("enacting citations")
def enacting_citations(index: dict[str, Any]) -> list[str]:
    """Validate that files named in Decision `enacted_in` slots cite at least one enacting entry.

    Enforces bidirectional consistency between Decision enactment metadata and the citations
    carried in durable file prose (stereorepo's DR-131).

    Parameters:
        index (dict): LinkML model index mapping URI identifiers to entity tuples.

    Returns:
        list[str]: Validation problem messages for files where citations disagree with enactment slots.

    Only an `enacted_in` slot resolving to an Artifact contributes a path. A
    slot naming nothing is `unresolved references`' finding, and one resolving
    to something other than an Artifact is the schema's; either way there is no
    path here for a citation to be held against.
    """
    known = {d.rsplit("/", 1)[-1] for d, (cls, _, _) in index.items() if cls == "Decision"}
    if not known:
        return []
    home = loaders.SCAFFOLD in index
    named: dict[str, set[str]] = {}
    for ident, (cls, obj, _) in index.items():
        if cls != "Decision":
            continue
        for ref in obj.get("enacted_in") or []:
            target = index.get(ref)
            if target and target[0] == "Artifact":
                named.setdefault(target[1]["path"], set()).add(ident.rsplit("/", 1)[-1])

    def listed(numbers: set[str]) -> str:
        shown = sorted(numbers)
        return ", ".join(f"DR-{n}" for n in shown[:6]) + (
            f" and {len(shown) - 6} more" if len(shown) > 6 else "")

    problems = []
    for path in loaders.durable(loaders.copied_files()):
        rel = str(path.relative_to(ROOT))
        if rel not in named:
            continue
        try:
            text = FENCED.sub("", path.read_text())
        except (UnicodeDecodeError, OSError):
            continue
        foreign = {num for m in loaders.FOREIGN.finditer(text) for num in loaders.DR.findall(m.group())}
        bare = set() if TEMPLATE in path.parents else set(loaders.DR.findall(loaders.FOREIGN.sub("", text)))
        cited = (bare | (foreign if home else set())) & known
        if cited and not cited & named[rel]:
            problems.append(f"{rel}: cites {listed(cited)}, and the record names it in "
                            f"{listed(named[rel])}; a file the record names cites an entry "
                            "that names it, or the entry that does names the file")
    return problems
