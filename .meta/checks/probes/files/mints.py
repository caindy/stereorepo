"""`vocabulary mints` over a row reserved, a row that is not, and each read it
cannot make (solorepo's DR-276, solorepo's DR-282).

The step is run by the gate, so a wrong answer from it shows as a failure —
but only on a branch that adds a row, which is the branch a real run almost
never is. The cases drive it through its `added` and `reserved` seams instead,
so the refusal is observed on every run rather than on the one evening a Concept
is coined. The step registers here rather than beside the check it exercises,
because the gate over assertions should not take its imports from a test suite
(solorepo's DR-150).
"""

from checks.collect import CouldNotRun, Found, Passed, check
from checks.files import vocabulary

DOOR = "work:concept/door"

WHERE = ".meta/assertions/imported/vocabulary.yaml"

ADDED = {DOOR: (WHERE, "Door")}
"""One row added: the case every reservation answer is put to."""

ADVERTISED = ("707ad55ec421eb46374520f6c4e7641d65f6afd9\trefs/tags/concept/door\n"
              "5f05eca90639651a8aadaf12fe98a30abaa39093\trefs/tags/concept/door^{}\n")
"""What `git ls-remote --tags` prints for one annotated reservation, verbatim:
the ref, and the `^{}` line dereferencing it to the commit."""

DOCUMENT = """
concept_set:
  - id: work:concept/door
    pref_label: Door
  - definition: a row with no identifier, which names no Concept
"""

@check("vocabulary mint probes", pre=True)
def vocabulary_mint_probes() -> list[str]:
    """`vocabulary_mints` passes a reserved row, names an unreserved one, and
    asks the remote nothing where there is no row (solorepo's DR-276).

    A branch that adds no row must not reach the network, so the reservation
    read is stood in by a call that reports having been made: the step costs
    nothing on every branch that coins no word, and a call here is itself the
    finding. Both reads that can fail come to `CouldNotRun` rather than to a
    pass, since a row read against nothing is unchecked and not clean.

    `RESERVATION` is held to reading one reservation off what `git ls-remote`
    prints, because every other case stands that read in and would not see a
    pattern that counted the `^{}` line twice.
    """
    problems: list[str] = []

    found = vocabulary.RESERVATION.findall(ADVERTISED)
    if found != ["door"]:
        problems.append(f"vocabulary mints: the refs `git ls-remote` advertises read as "
                        f"{found!r}, and one annotated tag is one reservation")

    concepts = vocabulary.concepts_in(DOCUMENT)
    if concepts != {DOOR: "Door"}:
        problems.append(f"vocabulary mints: a vocabulary document read as {concepts!r}, and a "
                        "row with no identifier names no Concept")
    if vocabulary.concepts_in("- not a mapping") != {}:
        problems.append("vocabulary mints: a document with no concept_set read as a row")

    def unreachable() -> set[str] | None:
        """The remote where no row was added: never asked, and a call is itself a finding."""
        problems.append("vocabulary mints: the remote was asked which Concepts it reserves on a "
                        "branch that added no row")
        return None

    said = vocabulary.vocabulary_mints(added=lambda base: {}, reserved=unreachable)
    if not isinstance(said, Passed):
        problems.append(f"vocabulary mints: a branch adding no row came to {said!r}, not Passed")

    said = vocabulary.vocabulary_mints(added=lambda base: ADDED, reserved=lambda: {"door"})
    if not isinstance(said, Passed):
        problems.append(f"vocabulary mints: a reserved row came to {said!r}, not Passed")

    said = vocabulary.vocabulary_mints(added=lambda base: ADDED, reserved=lambda: set())
    if not isinstance(said, Found):
        problems.append(f"vocabulary mints: an unreserved row came to {said!r}, not Found")
    elif not any(DOOR in problem and "move mint --concept" in problem
                 for problem in said.problems):
        problems.append(f"vocabulary mints: an unreserved row was found as {list(said.problems)}, "
                        "which names neither the row nor the verb that reserves it")

    said = vocabulary.vocabulary_mints(added=lambda base: None, reserved=unreachable)
    if not isinstance(said, CouldNotRun):
        problems.append(f"vocabulary mints: a base this clone does not hold came to {said!r}, "
                        "not CouldNotRun")

    said = vocabulary.vocabulary_mints(added=lambda base: ADDED, reserved=lambda: None)
    if not isinstance(said, CouldNotRun):
        problems.append(f"vocabulary mints: a remote that would not say which Concepts it "
                        f"reserves came to {said!r}, not CouldNotRun")
    return problems
