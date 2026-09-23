"""A row added to the Ubiquitous Language stands on a reservation the solo made (solorepo's DR-276).
"""
import re
import subprocess
from collections.abc import Callable

import yaml

from checks.collect import (
    ROOT,
    CouldNotRun,
    Found,
    Passed,
    StepOutcome,
    check,
)

BASE = "origin/main"

VOCABULARIES = (".meta/assertions/imported/vocabulary.yaml",
                ".meta/assertions/domain_vocabulary.yaml")
"""The two files a Concept is declared in: the vocabulary a portfolio
inherits, and its own domain's. Read as one language, so a row moved between
them is not a row added to either."""

# One line of `git ls-remote --tags origin 'concept/*'`: the object, a tab, the
# ref. `[\w.-]` rather than `\S`, so the `^{}` line that dereferences an
# annotated tag to its commit is not counted as a second reservation.
RESERVATION = re.compile(r"\trefs/tags/concept/([\w.-]+)$", re.M)

UNRESERVED = ("{where}: '{label}' ({ident}) is a new row in the Ubiquitous Language and nothing "
              "reserves `concept/{slug}`. A Concept is the solo's word to mint — "
              "`.meta/say/move mint --concept '{ident}'` — and a row a Job adds without it is a "
              "mint nobody asked for (solorepo's DR-276)")

NO_BASE = "{base} is not in this clone, so there is no diff to read a new row out of"

NO_REMOTE = ("the remote would not say which Concepts it reserves, and a row cannot be read "
             "against nothing")


def concepts_in(text: str) -> dict[str, str]:
    """Map every Concept identifier a vocabulary document declares to its preferred label.

    Parameters:
        text (str): The YAML of one vocabulary file.

    Returns:
        dict[str, str]: Identifier to preferred label, empty where the document
            parses to no `concept_set`.
    """
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError:
        return {}
    if not isinstance(document, dict):
        return {}
    return {concept["id"]: concept.get("pref_label") or concept["id"]
            for concept in (document.get("concept_set") or []) if concept.get("id")}


def added_concepts(base: str = BASE) -> dict[str, tuple[str, str]] | None:
    """The Concepts this branch adds to the vocabularies, read against `base`.

    Parameters:
        base (str): The ref the working tree is read against.

    Returns:
        dict[str, tuple[str, str]] or None: Identifier to `(file, label)` for
            every Concept the working tree declares and `base` does not,
            differenced across both vocabularies at once; None where `base` is
            not in this clone, which is a question that cannot be asked rather
            than an answer of none.

    A path `base` does not hold is a vocabulary this branch introduced, and
    `git show` fails on it: every row in such a file is then a new one.
    """
    known = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet",
                            f"{base}^{{commit}}"], check=False, capture_output=True, text=True)
    if known.returncode:
        return None
    here: dict[str, tuple[str, str]] = {}
    there: set[str] = set()
    for where in VOCABULARIES:
        path = ROOT / where
        declared = concepts_in(path.read_text(encoding="utf-8")) if path.is_file() else {}
        for ident, label in declared.items():
            here.setdefault(ident, (where, label))
        was = subprocess.run(["git", "-C", str(ROOT), "show", f"{base}:{where}"],
                             check=False, capture_output=True, text=True)
        there.update(concepts_in(was.stdout) if not was.returncode else {})
    return {ident: found for ident, found in here.items() if ident not in there}


def reserved_concepts() -> set[str] | None:
    """The Concept slugs GitHub holds a reservation tag for, or None when it will not say.

    Asked of the remote rather than of this clone, as `reserved_decision_numbers`
    asks it: CI checks out one commit with no tags at all.

    Returns:
        set[str] or None: The slugs reserved under `refs/tags/concept/`, or None
            where the remote could not be read.
    """
    try:
        found = subprocess.run(["git", "-C", str(ROOT), "ls-remote", "--tags", "origin",
                                "concept/*"],
                               check=False, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if found.returncode:
        return None
    return set(RESERVATION.findall(found.stdout))


@check("vocabulary mints")
def vocabulary_mints(
    base: str = BASE,
    added: Callable[[str], dict[str, tuple[str, str]] | None] = added_concepts,
    reserved: Callable[[], set[str] | None] = reserved_concepts,
) -> StepOutcome:
    """Every Concept this branch adds to a vocabulary stands on a `concept/<slug>`
    reservation (solorepo's DR-276).

    The slug is the tail of the identifier, so `work:concept/seed-commit` is
    reserved as `concept/seed-commit`, which is the name
    `.meta/say/move mint --concept` reserves from the same identifier. A branch
    that adds no row asks the remote nothing.

    Parameters:
        base (str): The ref the working tree is read against.
        added (Callable): The Concepts this branch adds, by identifier.
        reserved (Callable): The slugs the remote holds a reservation for.

    Returns:
        StepOutcome: `Passed` where this branch adds no Concept or every one it
        adds is reserved, `Found` naming each unreserved row, and `CouldNotRun`
        where the base ref or the remote could not be read.
    """
    new = added(base)
    if new is None:
        return CouldNotRun(NO_BASE.format(base=base))
    if not new:
        return Passed(f"no row added to {len(VOCABULARIES)} vocabularies against {base}")
    standing = reserved()
    if standing is None:
        return CouldNotRun(NO_REMOTE)
    problems = [UNRESERVED.format(where=where, label=label, ident=ident,
                                  slug=ident.rsplit("/", 1)[-1])
                for ident, (where, label) in sorted(new.items())
                if ident.rsplit("/", 1)[-1] not in standing]
    if problems:
        return Found(problems)
    return Passed(f"{len(new)} row(s) added against {base}, each on a reservation of its own")
