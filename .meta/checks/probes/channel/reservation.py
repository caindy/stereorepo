"""The numbers `decision numbering` reads as reserved, from the tags GitHub holds (solorepo's DR-128).
"""


import graph
from collect import check


@check("reservation probes", pre=True)
def reservation_probes():
    """`decision numbering` over a hole GitHub reserves, a hole it does not, a
    hole a tag holds and a commit made, a remote that will not say, a history
    that is not there, a deletion with neither a remote nor a tag behind it,
    and a hole neither read can speak to (solorepo's DR-128).

    The record here is contiguous whenever this gate is green, so the branch
    that reads the reservations is the one branch a real run never takes: a
    collision is two sessions on one evening, and by the time one is happening
    is the wrong time to find out what this does. Both reads are stood in for
    by argument. Standing the remote in is also what keeps this probe from
    making the network call the check itself makes only once, and only when it
    is needed; the history is stood in for because the deletion it asks about
    is one this repository has not made.

    `advertised` is what `git ls-remote --tags` prints, verbatim: the object, a
    tab, the ref, and a second line per annotated tag dereferencing it to the
    commit. `graph.RESERVATION` is held to reading one reservation off it,
    since every other case here stands the read in and would not see a pattern
    that matched none of it: a branch is worth probing where its input comes
    from somewhere else. The hole's number is spelled from `hole` rather than
    typed, because `DR-` and three digits in a file a portfolio copies is a
    citation as far as `cited decisions` is concerned, and this one is a
    fixture (solorepo's DR-124).

    The tag is never deleted, so over a number the record once held it says as
    much about a deletion as about a reservation, and the history is what
    carries the difference. The deletion with no remote to ask is the install a
    portfolio with no `origin` is, permanently, and the one the history read is
    local for: the commits are read first, a hole they explain is one the
    remote is never asked about, and the stand-in for the remote reports being
    called at all. The hole neither read can speak to prints the one sentence
    of that function no other case here does, and is the only path on which
    the remote is asked over a hole the commits could never have explained —
    a clone with no history explains none, so every hole reaches the remote
    and both answers are red; the stand-in reports having been asked, since
    what a later reader needs from the case is whether that call is meant
    (solorepo's #152).
    """
    hole = 3
    index = {f"work:decision/{n}": ("Decision", {}, "a probe") for n in (1, 2, 4)}
    problems = []
    advertised = ("707ad55ec421eb46374520f6c4e7641d65f6afd9\trefs/tags/DR-{0:03d}\n"
                  "5f05eca90639651a8aadaf12fe98a30abaa39093\trefs/tags/DR-{0:03d}^{{}}\n")
    found = graph.RESERVATION.findall(advertised.format(hole))
    if found != [f"{hole:03d}"]:
        problems.append(f"decision numbering: the refs `git ls-remote` advertises read as {found!r}, "
                        "and one annotated tag is one reservation")
    if (said := graph.decision_numbering(index, reserved=lambda: {hole},
                                         deleted=lambda numbers: set())):
        problems.append(f"decision numbering: a hole GitHub reserves was reported as {said!r}")
    said = graph.decision_numbering(index, reserved=lambda: {hole},
                                    deleted=lambda numbers: {hole})
    if not said or f"DR-{hole:03d}" not in said[0] or "removed" not in said[0]:
        problems.append(f"decision numbering: a reserved number whose entry a commit removed "
                        f"was reported as {said!r}, and a tag does not explain a deletion")
    said = graph.decision_numbering(index, reserved=lambda: {5}, deleted=lambda numbers: set())
    if not said or f"DR-{hole:03d}" not in said[0]:
        problems.append(f"decision numbering: a hole nothing reserves was reported as {said!r}")
    said = graph.decision_numbering(index, reserved=lambda: None, deleted=lambda numbers: set())
    if not said or "would not say" not in said[0] or "tag" in said[0]:
        problems.append("decision numbering: a remote that would not answer was reported "
                        f"as {said!r}, and a run that read no tags says nothing about them")
    said = graph.decision_numbering(index, reserved=lambda: {hole}, deleted=lambda numbers: None)
    if not said or "no history" not in said[0]:
        problems.append("decision numbering: a hole under a history that cannot be read was "
                        f"reported as {said!r}, and an unexplained hole is a failure")

    def unreachable():
        """The remote over a hole the commits explain: never asked, and a call is itself a finding."""
        problems.append("decision numbering: the remote was asked about a hole a commit "
                        "here explains, and the tags decide only what the history leaves")
        return None

    said = graph.decision_numbering(index, reserved=unreachable, deleted=lambda numbers: {hole})
    if said != [f"the record held DR-{hole:03d} and a commit here removed it, tag or no tag; "
                "a number withdrawn stays in the record as a hole"]:
        problems.append("decision numbering: a deletion with no remote to ask was reported as "
                        f"{said!r}, and the read that can name it is the one every clone has")

    asked = []

    def unreadable():
        """The remote that will not say, over a hole no history explains.

        Records in `asked` that it was called, and answers `None`.
        """
        asked.append(True)
        return None

    said = graph.decision_numbering(index, reserved=unreadable, deleted=lambda numbers: None)
    if said != [f"no entry for DR-{hole:03d}; the remote would not say which numbers it "
                "reserves and this clone has no history to read, so nothing here tells a "
                "number in flight from a deletion"]:
        problems.append("decision numbering: a hole neither read could speak to was reported "
                        f"as {said!r}, and a sentence claims only what its run read")
    if not asked:
        problems.append("decision numbering: the remote was not asked over a hole no commit "
                        "here could explain, and a clone with no history explains none of them")
    return problems
