"""`--handoff`'s reading of an adopted decision against the Artifacts it names (solorepo's DR-204).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import sys
from typing import Any

from checks import citations
from checks.collect import META, CouldNotRun, check
from checks.probes.harness import (
    outcome,
    stood_in,
)


@check("enacted probes", pre=True)
def enacted_probes() -> CouldNotRun | list[str]:
    """`--handoff`'s reading of a decision against the artifacts the branch edits.

    Three parts, and they fail differently. The judgement, which edited
    artifacts a settled decision leaves unnamed, is run against a branch stood
    in for, because the real one is whatever this session happens to be doing
    and a check cannot be written against that: a branch settling no decision,
    one settling the first decision on disk beside a declared non-record
    Artifact, and that decision read as adopted and naming nothing. Then the
    ordering the step depends on: it reads the record's rendered index, so it
    is skipped, and says so rather than answering, wherever that page's
    freshness is not established — a render that could not run leaves it
    unknown, and `ok` over an unknown is the reading the ordering exists to
    refuse. The render answers under two prefixes, `stale` and `unrendered`,
    and a page nothing renders is as unestablished as a stale one, since
    `just render` writes nothing for it; so the index arriving under either
    word skips the step, a page that is not the index under either word does
    not, and each finding names its page, which is the repair the coder
    needs. The step's own unknown is a base git cannot resolve: `git diff`
    against it exits non-zero, and read as an empty diff that would be a
    branch reported to settle no decision, `ok` over a diff nobody read.
    Last, the readers under all of it are run against the tree itself,
    because their failure is silence: both are regexes over text
    `check_pr.py` has no YAML reader for, and a reformat of either file would
    leave them matching nothing and every question answered green. What is
    held is that they still find something and still agree, every file the
    record's rendered table names being a declared Artifact, which is the
    claim a drift in either shape breaks first.
    """
    check_pr = citations.load_check_pr()
    decisions = sorted((META / "assertions" / "decisions").glob("DR-*.yaml"))
    if not decisions:
        return CouldNotRun("no decision files found in assertions/decisions/")
    return (_unenacted_cases(check_pr, decisions[0]) + _handoff_cases(check_pr)
            + _unresolvable_base(check_pr) + _readers_agree(check_pr))


def _unenacted_cases(check_pr: Any, sample: Any) -> list[str]:
    """`unenacted` over a branch that settles nothing, one that settles `sample` and names an artifact, and one whose decision names none."""
    problems = []

    def read(changed: list[str]) -> tuple[Any, Any]:
        """`unenacted("origin/main")` with the branch's diff stood in for by `changed`."""
        with stood_in(check_pr.branch, touched=lambda base: changed):
            res: tuple[Any, Any] = check_pr.branch.unenacted("origin/main")
            return res

    found, note = read([".meta/arc/deploy", ".meta/say/move"])
    if found or "settles no decision" not in note:
        problems.append(f"unenacted: a branch settling no decision reported {found!r}, {note!r}")

    number = int(sample.stem.removeprefix("DR-"))
    entry = f".meta/assertions/decisions/{sample.name}"
    artifact = next((p for p in check_pr.branch.artifact_map().values()
                     if not any(p.startswith(r) for r in check_pr.branch.RECORD)), "AGENTS.md")
    found, note = read([entry, artifact])
    if found:
        problems.append(f"unenacted: DR-{number:03d} (valid) reported problems {found!r}")

    with stood_in(check_pr.branch, parse_decision_yaml=lambda path: ("ADOPTED", [])):
        found, note = read([entry])
    if not found or f"DR-{number:03d}" not in found[0]:
        problems.append(f"unenacted: DR-{number:03d} with no artifacts did not report expected problem, got {found!r}")
    return problems


def _handoff_cases(check_pr: Any) -> list[str]:
    """`handoff` with the render unrunnable, and with it answering each of the four pages it can name stale or unrendered."""
    problems = []

    def handed_off(render: list[str]) -> tuple[list[str], list[str]]:
        """What `handoff("origin/main")` printed with `RENDER` stood in for by the command `render`, and the bases the enacted step was asked about, the step itself answering nothing."""
        asked: list[str] = []

        def mock_unenacted(base: str) -> tuple[list[str], str]:
            asked.append(base)
            return ([], "")

        with stood_in(check_pr.branch, RENDER=render,
                      unenacted=mock_unenacted):
            said = outcome(lambda: check_pr.branch.handoff("origin/main")).out
        return asked, said.splitlines()

    asked, lines = handed_off(["no-such-program-here"])
    enacted = [line for line in lines if "enacted" in line]
    if asked or not enacted or not all(line.startswith("?") for line in enacted):
        problems.append(f"handoff: with the render unrunnable it said {enacted!r} and asked "
                        f"{len(asked)} question(s) of an index whose freshness is unknown")

    index = check_pr.branch.INDEX.split("/")[-1]
    for answer, run in ((f"unrendered: {index}", False),
                        (f"stale: {index}", False),
                        ("unrendered: justfile", True),
                        ("stale: justfile", True)):
        asked, lines = handed_off([sys.executable, "-c",
                                   f"import sys; print({answer!r}); sys.exit(1)"])
        enacted = [line for line in lines if " enacted" in line]
        if bool(asked) is not run or not enacted or any(
                line.startswith("?") is run for line in enacted):
            problems.append(f"handoff: the render answering {answer!r} left the enacted step "
                            f"saying {enacted!r}, which is not the "
                            + ("reading" if run else "skip") + " that page calls for")
        page = answer.split(": ", 1)[1]
        if not any(line.startswith("x ") and page in line for line in lines):
            problems.append(f"handoff: the render answering {answer!r} produced no finding "
                            "naming the page, so the repair the coder needs is unsaid")
    return problems


def _unresolvable_base(check_pr: Any) -> list[str]:
    """`unenacted` against a ref no checkout has says the diff went unread."""
    found, note = check_pr.branch.unenacted("no-such-ref-on-any-checkout")
    if found is not None:
        return [f"unenacted: an unresolvable base answered {found!r}, {note!r}, "
                "rather than saying the diff went unread"]
    return []


def _readers_agree(check_pr: Any) -> list[str]:
    """The two readers of the record find something and agree: every path the rendered table names is a declared Artifact."""
    problems = []
    declared, named = check_pr.branch.artifacts(), check_pr.branch.accounted()
    if not declared or not named:
        problems.append(f"the handoff's readers found {len(declared)} declared artifact(s) and "
                        f"{len(named)} accounted for; a regex over a file that has been "
                        "reformatted matches nothing and answers every question green")
    stray = sorted(set(named) - declared)
    if stray:
        problems.append(f"the record's table names {stray}, which no `artifacts:` list "
                        "declares; the two readers disagree about what a path is")
    return problems
