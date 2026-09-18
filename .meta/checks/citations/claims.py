"""What a citation goes on to claim: an Article that resolves, a quotation that appears where it is attributed, a relation that is the slot it claims to be, and a line that reads what it is cited for (A12).
"""
import re

import yaml

from citations import loaders, prose
from collect import META, ROOT, check


@check("cited articles")
def cited_articles():
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
# solorepo's DR-044 uses of its predecessor. The claim is un-dereferenceable
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
def quoted_claims():
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
def stated_relations(index):
    """Validate that semantic relationships between entries stated in prose match assertion slots.

    Checks indicative statements using relational verbs (`supersedes`, `applies`, `departs_from`)
    against explicit relation slots in Decision Record definitions (solorepo's DR-175).

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
                target = ("work:decision/" + m["object"].removeprefix("DR-") if wants == "Decision"
                          else "work:article/" + m["object"].removeprefix("A"))
                if entry is None or not m["object"].startswith("DR-" if wants == "Decision" else "A"):
                    continue
                if prose.HEDGED.search(m["before"]) or prose.HEDGED.search(m["after"]):
                    continue
                held = [entry.get(slot)] if slot == "superseded_by" else list(entry.get(slot) or [])
                if either:
                    other = decisions.get(m["object"].removeprefix("DR-")) or {}
                    held += list(other.get("supersedes") or [])
                    target = [target, "work:decision/" + m["subject"].removeprefix("DR-")]
                if not set(held) & set(target if either else [target]):
                    problems.append(
                        f"{path.relative_to(ROOT)}: \"{prose.flat(m.group(0))}\" is a relation stated in "
                        f"prose, and {m['subject']}'s `{slot}` does not name it; a relation here "
                        "is a slot")
    return problems


# A path and a line, cited as one code span, which is the form a reviewer writes
# a precedent in. Anchored to the span so that `see foo.py:1` is prose about a
# file rather than a claim about a line.
PATH_LINE = re.compile(r"`(?P<path>[^`\s:]*[./][^`\s:]*):(?P<line>\d+)`")


@check("path and line claims")
def path_and_line_claims():
    """Validate that `path:line` citations point to existing lines containing adjacent code spans.

    Ensures that file line references cited beside code snippets in prose exist and contain
    the referenced tokens.

    Returns:
        list[str]: Validation problem messages for nonexistent paths, out-of-range lines,
        or mismatched line contents.
    """
    problems = []
    for path in loaders.durable(loaders.copied_files()):
        rel = path.relative_to(ROOT)
        for span in prose.prose(path):
            for m in PATH_LINE.finditer(span):
                target = ROOT / m["path"]
                if not target.is_file():
                    problems.append(f"{rel}: {m.group(0)} names no file")
                    continue
                try:
                    lines = target.read_text().splitlines()
                except (UnicodeDecodeError, OSError):
                    continue
                number = int(m["line"])
                if not 1 <= number <= len(lines):
                    problems.append(f"{rel}: {m.group(0)} cites a line of a file "
                                    f"with {len(lines)}")
                    continue
                after = prose.SPAN.findall(span[m.end():m.end() + 60].split(". ")[0])[:1]
                back = span[max(0, m.start() - 60):m.start()].rsplit(". ")[-1]
                if span[:m.start() - len(back)].count("`") % 2:
                    back = back.partition("`")[2]
                before = prose.SPAN.findall(back)[-1:]
                near = [s for s in (s.strip("` ") for s in after + before) if s]
                if near and not any(s in lines[number - 1] for s in near):
                    problems.append(
                        f"{rel}: {m.group(0)} is cited beside "
                        + ", ".join(f"`{s}`" for s in near)
                        + f", and line {number} reads `{lines[number - 1].strip()}`")
    return problems
