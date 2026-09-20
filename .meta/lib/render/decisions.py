"""The record of decisions: its index, the form a new entry is written on, and what landed for a Challenge.
"""
import posixpath
from collections.abc import Sequence
from typing import Any

import yaml

from lib.render import META, record


def _decision_slots() -> dict[str, Any]:
    """The slot descriptions from the model, which is where the guidance lives.

    Read as plain YAML rather than through a SchemaView so the renderer keeps its
    one dependency, and from every module the class draws slots from — `falsifier`
    is `core`'s, shared with `Article`. The form and the record are two views of the same class, and
    a form whose headings were typed by hand would be the third copy of a shape
    the schema already states.
    """
    slots: dict[str, Any] = {}
    for module in ("work/core.yaml", "work/decisions.yaml"):
        slots.update((record.load(module) or {}).get("slots") or {})
    return slots


def landed(number: int | str) -> str:
    """What a Challenge got, rendered from the entries taken under it.

    The account of a finished piece of work is not new prose: every line of it is
    already a `consequence` on some Decision, and writing it again by hand is the
    copy that flatters. So it is generated, and it is **exactly as complete as the
    record** — a decision taken under another change's coat-tails is missing here,
    which is the point rather than a defect.

    Prints rather than writes. It is addressed to a pull request at merge, so it
    goes through the channel that signs: `.meta/say/post landed 15` runs this for
    every Challenge the body closes and posts each. By hand:

        uvx --with pyyaml python .meta/render.py --landed 11
    """
    challenges = {c["id"]: c for path in
                  sorted((META / "assertions" / "challenges").glob("*.yaml"))
                  for c in (yaml.safe_load(path.read_text()) or {}).get("challenges") or []}
    ident = f"work:challenge/{number}"
    if ident not in challenges:
        return f"No Challenge {ident} is asserted."
    ch = challenges[ident]
    rows = [d for d in record.record() if d.get("challenge") == ident]
    out = [f"## What landed for #{number} — {ch['name']}\n"]
    if not rows:
        out.append("No decision names this Challenge.\n")
        return "\n".join(out)
    out.append(f"{len(rows)} decisions, and what each of them changed. Generated from the\n"
               f"record: an entry missing here was taken without one.\n")
    for d in rows:
        num = d["id"].rsplit("/", 1)[-1]
        head = f"**[DR-{num}]({record.RECORD.format(num)}) · {d['name'].split(' · ', 1)[-1]}**"
        if d.get("status") != "ADOPTED":
            head += f" — {d['status'].lower()}"
        out.append(head + "\n")
        out += [f"- {c.strip()}" for c in (d.get("consequences") or
                                           ["No consequences recorded."])]
        out.append("")
    return "\n".join(out)


def decisions() -> str | None:
    """The index to the record, and the only thing rendered from it (solorepo's DR-082).

    An entry is its assertion file, so rendering one as markdown made a second
    copy and nothing else. What survives is what a directory listing cannot do:
    map a number to the question it settled, so a reader can choose an entry
    without opening any, and invert `enacted_in` into the **By artifact** table,
    which is the only answer to "which decisions account for this file".

    Deliberately insufficient to apply anything, per Progressive Disclosure. A
    withdrawn entry is listed under Holes rather than in the record, and keeps
    its number, because a citation to a hole must still resolve.
    """
    rows = record.record()
    if not rows:
        return None
    structure = record.load("assertions/structure.yaml") or {}
    levels = {u["id"]: u["name"] for key in ("products", "projects")
              for u in structure.get(key) or []}
    out = [record.BANNER.format(src="assertions/decisions/"),
           record.authored("decisions.md"),
           "| Entry | The question it settled | Status |",
           "| :-- | :-- | :-- |"]
    paths = record.artifacts()
    holes = [d for d in rows if d.get("status") == "WITHDRAWN"]
    out += [_row(rows, d, levels) for d in rows if d.get("status") != "WITHDRAWN"]
    out.append("")
    if holes:
        out.append("## Holes\n")
        out.append("Numbers that were issued and are not decisions. They are never reused, and\n"
                   "the prose is kept: a paragraph that was worth writing does not stop being\n"
                   "true because it turned out to foreclose nothing.\n")
        for d in holes:
            num = d["id"].rsplit("/", 1)[-1]
            why = " ".join(d["withdrawn_because"].strip().split())
            out.append(f"- [DR-{num}]({record.ENTRY.format(num)}) — withdrawn. "
                       + why.split(". ")[0].rstrip(".") + ".")
        out.append("")
    by_artifact: dict[str, list[str]] = {}
    for d in rows:
        for ref in (d.get("enacted_in") or []):
            by_artifact.setdefault(paths.get(ref, ref), []).append(
                d["id"].rsplit("/", 1)[-1])
    if by_artifact:
        out.append("## By artifact\n")
        out.append("Which entries account for a file. The other direction of `enacted_in`,\n"
                   "and the query a reader in a file actually has.\n")
        out.append("| Artifact | Entries |")
        out.append("| :-- | :-- |")
        for path in sorted(by_artifact):
            nums = ", ".join(f"[DR-{n}]({record.ENTRY.format(n)})"
                             for n in sorted(by_artifact[path]))
            out.append(f"| [`{path}`]({posixpath.relpath(path, '.meta')}) | {nums} |")
        out.append("")
    return "\n".join(out)


def _row(rows: Sequence[dict[str, Any]], d: dict[str, Any], levels: dict[str, str]) -> str:
    """One entry's line of the index: its number, the question it settled with its level where it is not the Portfolio's (solorepo's DR-093), and its status."""
    num = d["id"].rsplit("/", 1)[-1]
    status = (d.get("status") or "").capitalize()
    if d.get("status") == "SUPERSEDED":
        status = f"Superseded by {_link(rows, d['superseded_by'])}"
    title = d["name"].split(" · ", 1)[-1]
    for level in ("product", "project"):
        if d.get(level):
            title += f" · {levels.get(d[level], d[level])}"
    return f"| [DR-{num}]({record.ENTRY.format(num)}) | {title} | {status} |"


def _link(rows: Sequence[dict[str, Any]], ident: str) -> str:
    """A supersession, rendered as a link to the entry it names."""
    for d in rows:
        if d["id"] == ident:
            return f"[{d['name'].split(' · ')[0]}]({record.ENTRY.format(d['id'].rsplit('/', 1)[-1])})"
    return ident


def decision_form() -> str | None:
    """The form for an entry, rendered from the same class the record uses.

    One class at three levels — the Portfolio's, a Product's, a Project's —
    told apart by what the entry names (solorepo's DR-059, DR-093), so the form's headings
    are the model's slots and its guidance is their descriptions. Typing them
    here as well would be the copy that disagrees — and the copy that keeps a
    form asking for something the model stopped requiring.

    The chosen alternative asks for `reason` like the rejected one, because
    `reason`'s own description already says the chosen one's includes what it
    costs. It read `<As above, including what it costs.>` while that sentence
    sat in the model as well, which is the pair that drifts (solorepo's DR-152).
    What is left is woven: two blocks asserted on this page's Artifact, because
    no slot backs them.
    """
    slots = _decision_slots()
    if not slots:
        return None

    def guidance(name: str) -> str:
        return " ".join(slots[name]["description"].split())

    out = [record.BANNER.format(src="work/decisions.yaml"),
           record.authored("templates/decision.md"),
           "- **Status:** <" + " | ".join(
               (record.load("work/decisions.yaml") or {})["enums"]["DecisionStatus"]["permissible_values"]) + ">",
           "- **Level:** <Portfolio | Product: which | Project: which>\n",
           "## Context\n", "<" + guidance("context") + ">\n",
           "## Decision\n",
           "<" + record.woven("templates/decision.md", "decision") + ">\n",
           "## Alternatives considered\n",
           "<" + guidance("alternatives") + ">\n",
           "### A: <alternative> — rejected\n", "<" + guidance("reason") + ">\n",
           "<" + guidance("tried") + ">\n",
           "### B: <alternative> — chosen\n", "<" + guidance("reason") + ">\n",
           "## Consequences\n", "<" + guidance("consequences") + ">\n",
           "## What would falsify this\n", "<" + guidance("falsifier") + ">\n",
           "## Bearing on the Charter\n",
           record.woven("templates/decision.md", "bearing on the charter") + "\n",
           "- **Applies:** <" + guidance("applies") + ">",
           "- **Departs from:** <" + guidance("departs_from") + ">\n",
           "## Supersedes\n",
           "<" + guidance("supersedes") + " Omit the section if there is none.>\n",
           "## Withdrawn because\n",
           "<" + guidance("withdrawn_because") + " Omit the section if there is none.>\n",
           "## Rationale\n", "<" + guidance("rationale") + ">\n"]
    return "\n".join(out)
