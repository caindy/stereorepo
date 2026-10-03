"""What a citation goes on to claim: an Article that resolves, a quotation that appears where it is attributed, and a relation that is the slot it claims to be (A12); and no citation of a line (stereorepo's DR-355).
"""
import re
from typing import Any

import yaml

from checks.citations import loaders, prose
from checks.collect import META, ROOT, check


@check("cited articles")
def cited_articles() -> list[str]:
    """Validate that every Article number cited in prose resolves in the Charter.

    Ensures `An` references outside code spans match live or reserved articles in `charter.yaml`.

    Returns:
        list[str]: Validation problem messages for unresolved Article citations.
    """
    charter = yaml.safe_load(
        (META / "assertions" / "imported" / "charter.yaml").read_text()) or {}
    live = {int(a["id"].rsplit("/", 1)[-1]) for a in charter.get("articles") or []}
    reserved = {r["number"] for r in charter.get("retired_articles") or []}
    if not live:
        return []
    problems = []
    for path in loaders.durable(loaders.copied_files()):
        cited = {int(m.group(1)) for span in prose.prose(path)
                 for m in prose.ARTICLE.finditer(prose.SPAN.sub(" ", span))}
        for num in sorted(cited - live - reserved):
            problems.append(f"{path.relative_to(ROOT)}: A{num} is cited and is no Article, "
                            "live or reserved")
    return problems


# What may stand between a citation and the words attributed to it: almost
# nothing. `DR-043's step read "..."` puts a noun in the gap and thereby
# attributes the words to a step that entry changed rather than to the entry,
# and a reader who opens that entry is right not to find them there — the shape
# stereorepo's DR-044 uses of its predecessor. The claim is un-dereferenceable
# too, and it is not this check's: a check that tests something other than what
# it says it tests is worse than one that is narrow.
SUBJECT = r",?(?:\s+(?:which|itself|already|also|still|then|only|here|now|"
SUBJECT += r"explicitly|expressly|plainly)){0,2}\s*"


# A quotation and the entry it is attributed to, in the two orders prose puts
# them: the citation first and the quotation after it, or the quotation first
# and the attribution behind it. Twelve characters at least, because a quoted
# word is a term being used and not a claim being sourced.
QUOTED = (re.compile(rf"(?P<cite>{prose.CITE}){SUBJECT}\b(?:{prose.SAYS})\b[^\"\n]{{0,20}}"
                     rf"\"(?P<quote>[^\"\n]{{12,}})\""),
          re.compile(rf"\"(?P<quote>[^\"\n]{{12,}})\"[^\"\n]{{0,20}}?\b(?:{prose.SAYS})\b"
                     rf"{SUBJECT}(?P<cite>{prose.CITE})\b"))


ELISION = re.compile(r"…|\.\.\.|\[[^\]]*\]")


@check("quoted claims")
def quoted_claims() -> list[str]:
    """Validate that quotations attributed to an Article or Decision appear in that entry.

    Matches attributed quotations in prose against the normalized text of cited entries,
    accounting for elisions and bracketed interpolations.

    Returns:
        list[str]: Validation problem messages for unattributed or mismatched quotations.

    A quotation attributed to an entry that does not exist is passed over
    rather than reported: `cited decisions` and `cited articles` own the
    citation that names nothing, and reporting it twice reports it twice.
    """
    charter = {int(a["id"].rsplit("/", 1)[-1]): a for a in (yaml.safe_load(
        (META / "assertions" / "imported" / "charter.yaml").read_text()) or {}
    ).get("articles") or []}
    problems = []
    for path in loaders.durable(loaders.copied_files()):
        for span in prose.prose(path):
            for pattern in QUOTED:
                for m in pattern.finditer(span):
                    entry = prose.entry_text(m["cite"], charter)
                    if entry is None:
                        continue
                    claimed = [part.strip(" ,.;:—-")
                               for part in ELISION.split(prose.normalise(m["quote"]))]
                    missing = [part for part in claimed
                               if len(part) >= 8 and part not in entry]
                    if missing:
                        problems.append(
                            f"{path.relative_to(ROOT)}: \"{missing[0]}\" is attributed to "
                            f"{m['cite']}, which does not contain it")
    return problems


# A relation between two entries, and the slot that is the only place it is
# recorded. `superseded_by` is checked from either end: where a later entry
# killed part of an earlier one the schema puts the link on the successor's
# `supersedes` and leaves `superseded_by` empty, so a prose sentence in the
# passive is answered by either slot.
RELATIONS = {
    "supersedes": ("supersedes", "Decision", False),
    "supersede": ("supersedes", "Decision", False),
    "superseding": ("supersedes", "Decision", False),
    "superseded by": ("superseded_by", "Decision", True),
    "applies": ("applies", "Article", False),
    "apply": ("applies", "Article", False),
    "departs from": ("departs_from", "Article", False),
    "depart from": ("departs_from", "Article", False),
    "departing from": ("departs_from", "Article", False),
}


STATED = re.compile(rf"(?P<subject>{prose.CITE})(?P<before>{prose.NEAREST})"
                    rf"\b(?P<word>{'|'.join(sorted(RELATIONS, key=len, reverse=True))})\b"
                    rf"(?P<after>{prose.GAP})(?P<object>{prose.CITE})\b", re.I)


@check("stated relations")
def stated_relations(index: dict[str, Any]) -> list[str]:
    """Validate that semantic relationships between entries stated in prose match assertion slots.

    Checks indicative statements using relational verbs (`supersedes`, `applies`, `departs_from`)
    against explicit relation slots in Decision Record definitions (stereorepo's DR-334).

    Parameters:
        index (dict): LinkML model index mapping URI identifiers to entity tuples.

    Returns:
        list[str]: Validation problem messages for relations stated in prose but unset in the model.
    """
    problems = []
    decisions = {ident.rsplit("/", 1)[-1]: obj
                 for ident, (cls, obj, _) in index.items() if cls == "Decision"}
    if not decisions:
        return []
    for path in loaders.durable(loaders.copied_files()):
        for span in prose.prose(path):
            for m in STATED.finditer(span.replace("`", "")):
                slot, wants, either = RELATIONS[m["word"].lower()]
                entry = decisions.get(m["subject"].removeprefix("DR-"))
                target_ref = ("work:decision/" + m["object"].removeprefix("DR-") if wants == "Decision"
                              else "work:article/" + m["object"].removeprefix("A"))
                if entry is None or not m["object"].startswith("DR-" if wants == "Decision" else "A"):
                    continue
                if prose.HEDGED.search(m["before"]) or prose.HEDGED.search(m["after"]):
                    continue
                held = [entry.get(slot)] if slot == "superseded_by" else list(entry.get(slot) or [])
                targets = [target_ref]
                if either:
                    other = decisions.get(m["object"].removeprefix("DR-")) or {}
                    held += list(other.get("supersedes") or [])
                    targets.append("work:decision/" + m["subject"].removeprefix("DR-"))
                if not set(held) & set(targets):
                    problems.append(
                        f"{path.relative_to(ROOT)}: \"{prose.flat(m.group(0))}\" is a relation stated in "
                        f"prose, and {m['subject']}'s `{slot}` does not name it; a relation here "
                        "is a slot")
    return problems


# A path and a line, cited as one code span. Anchored to the span so that
# `see foo.py:1` is prose about a file rather than a citation of a line.
PATH_LINE = re.compile(r"`(?P<path>[^`\s:]*[./][^`\s:]*):(?P<line>\d+)`")


@check("no line citations")
def no_line_citations() -> list[str]:
    """Refuse every `path:line` code span in durable prose (stereorepo's DR-355).

    A line number moves whenever the file above it changes, so a citation of
    one fails on edits to a file the citing prose never touched. Prose cites
    the path and the thing in it instead: a function, class, constant, test,
    heading or step. Fenced code blocks are not prose, so tool output there
    is not read.

    Returns:
        list[str]: One message per `path:line` code span, naming the file that
        holds it.
    """
    return [f"{path.relative_to(ROOT)}: {m.group(0)} cites a line; "
            "name the path and the thing in it instead"
            for path in loaders.durable(loaders.copied_files())
            for span in prose.prose(path)
            for m in PATH_LINE.finditer(span)]


# A Discipline step is an identified entity with a semantic slug CURIE, cited
# in prose by its human name, and ordinal step citations are refused (stereorepo's DR-270).
ORDINAL_WORDS = (
    r"first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
    r"eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|"
    r"seventeenth|eighteenth|nineteenth|twentieth|"
    r"opening|initial|final|closing|\d+(?:st|nd|rd|th)"
)
CARDINAL_WORDS = (
    r"\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty"
)


def _disciplines(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index declared Disciplines by human name, mapping to their declared steps."""
    return {obj["name"]: {s["name"]: s for s in obj.get("steps") or []}
            for _, (cls, obj, _) in index.items() if cls == "Discipline"}


def _step_patterns(
    disciplines: dict[str, dict[str, Any]],
) -> tuple[re.Pattern[str], re.Pattern[str]]:
    """Build shared regex patterns for ordinal step refusals and step name citations."""
    disc_pattern = "|".join(re.escape(d) for d in sorted(disciplines.keys(), key=len, reverse=True))
    ordinal_step = re.compile(
        rf"\b(?P<disc>{disc_pattern})(?:'s\s+(?P<ord>{ORDINAL_WORDS})\s+step|"
        rf"'s\s+step\s+(?P<card>{CARDINAL_WORDS})|\s+step\s+(?P<card2>{CARDINAL_WORDS})(?!\s+[a-z]+s\b))\b",
        re.I,
    )
    any_step_cite = re.compile(
        rf"\b(?P<disc>{disc_pattern})'s\s+(?:\*(?P<step_emp>[^*]+)\*|(?P<step_bare>[A-Z][^\n.;:?!]{{1,60}}?))\s+step\b"
    )
    return ordinal_step, any_step_cite


@check("refused ordinal step citations")
def refused_ordinal_step_citations(index: dict[str, Any]) -> list[str]:
    """Validate that durable prose cites Discipline steps by name rather than ordinal numbers.

    Enforces that references to Discipline steps use `<Discipline>'s *<Step Name>* step`
    rather than positional ordinals to prevent silent citation drift (stereorepo's DR-270).
    Code spans (enclosed in backticks) are exempt as legitimate quotation/mention syntax.

    Parameters:
        index (dict): LinkML model index mapping URI identifiers to entity tuples.

    Returns:
        list[str]: Validation problem messages for refused ordinal step citations.
    """
    disciplines = _disciplines(index)
    if not disciplines:
        return []
    ordinal_step, _ = _step_patterns(disciplines)
    problems = []
    for path in loaders.durable(loaders.copied_files()):
        rel = path.relative_to(ROOT)
        for span in prose.prose(path):
            unquoted = prose.SPAN.sub(" ", span)
            for m in ordinal_step.finditer(unquoted):
                problems.append(
                    f"{rel}: {m.group(0)} is an ordinal step citation; "
                    "cite steps by name under stereorepo's DR-270"
                )
    return problems


@check("cited discipline steps")
def cited_discipline_steps(index: dict[str, Any]) -> list[str]:
    """Validate that `<Discipline>'s *<Step Name>* step` citations resolve against declared steps.

    Ensures that step citations in durable prose match declared step names in LinkML
    discipline assertions, preventing misattribution across disciplines or casing errors
    (stereorepo's DR-270).

    Parameters:
        index (dict): LinkML model index mapping URI identifiers to entity tuples.

    Returns:
        list[str]: Validation problem messages for unresolved discipline step citations.
    """
    disciplines = _disciplines(index)
    if not disciplines:
        return []
    ordinal_step, any_step_cite = _step_patterns(disciplines)

    problems = []
    for path in loaders.durable(loaders.copied_files()):
        rel = path.relative_to(ROOT)
        for span in prose.prose(path):
            unquoted = prose.SPAN.sub(" ", span)
            for m in any_step_cite.finditer(unquoted):
                if ordinal_step.search(m.group(0)):
                    continue
                disc = m.group("disc")
                step = (m.group("step_emp") or m.group("step_bare") or "").strip()
                declared = disciplines.get(disc, {})
                if step not in declared:
                    declared_lower = {s.lower(): s for s in declared}
                    if step.lower() in declared_lower:
                        problems.append(
                            f"{rel}: '{step}' is cited with incorrect casing for "
                            f"{disc}'s '{declared_lower[step.lower()]}'"
                        )
                    else:
                        problems.append(
                            f"{rel}: '{step}' is cited as a step of {disc}, and is no declared step"
                        )
    return problems

