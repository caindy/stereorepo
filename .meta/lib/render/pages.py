"""The Portfolio's pages: the Disciplines, the vocabulary, the Charter, and the Specialization steps.
"""

from collections.abc import Sequence
from typing import Any

from lib.render import record


def disciplines() -> str:
    """Renders the disciplines catalog markdown from declared and imported disciplines."""
    tbox = record.load("work/disciplines.yaml") or {}
    abox: dict[str, list[dict[str, Any]]] = {"disciplines": []}
    for rel in ("assertions/disciplines.yaml", "assertions/imported/disciplines.yaml"):
        abox["disciplines"].extend((record.load(rel) or {}).get("disciplines") or [])
    out = [record.BANNER.format(src="assertions/disciplines.yaml + assertions/imported/disciplines.yaml"),
           record.authored("disciplines.md"),
           str(tbox.get("description", "")).strip() + "\n"]
    for d in abox["disciplines"]:
        out.append(f"### {d['name']}\n")
        if d.get("description"):
            out.append(d["description"].strip() + "\n")
        if d.get("judgement"):
            out.append(f"**Where the judgement is.** {d['judgement'].strip()}\n")
        if d.get("steps"):
            out.append("\n".join(
                f"{i}. **{s['name'].rstrip('.')}.** {s['statement'].strip()}"
                for i, s in enumerate(d["steps"], 1)
            ) + "\n")
        if d.get("produces"):
            out.append("_Produces: " + "; ".join(d["produces"]).rstrip(".") + "._\n")
    return "\n".join(out) + record.accounted_by("disciplines.md")


def _term_table(rows: Sequence[dict[str, Any]]) -> list[str]:
    """The `Term | Means | Do not say` table over `rows`, and a blank line after it."""
    out = ["| Term | Means | Do not say |\n|---|---|---|"]
    for c in rows:
        avoid = ", ".join(c.get("avoid", [])) or "—"
        out.append(f"| **{c['pref_label']}** | {c['definition'].strip()} | {avoid} |")
    out.append("")
    return out


def _scheme(scheme: dict[str, Any], members: Sequence[dict[str, Any]],
            concepts: Sequence[dict[str, Any]]) -> list[str]:
    """One scheme's section: its authority, the loose terms, a table under each hub, and every scope note."""
    out = [f"### {scheme['name']}\n", f"_Authority: {scheme.get('authority', 'unstated')}._\n"]
    hubs = [c for c in members if any(m.get("broader") == c["id"] for m in concepts)]
    grouped: dict[str, list[dict[str, Any]]] = {h["id"]: [] for h in hubs}
    loose: list[dict[str, Any]] = []
    for c in members:
        if c in hubs:
            continue
        (grouped[c["broader"]] if c.get("broader") in grouped else loose).append(c)
    if loose:
        out += _term_table(loose)
    for h in hubs:
        if grouped[h["id"]]:
            out += [f"#### {h['pref_label']}\n", f"_{h['definition'].strip()}_\n", *_term_table(grouped[h["id"]])]
    out += [f"**{c['pref_label']}.** {c['scope_note'].strip()}\n" for c in members if c.get("scope_note")]
    return out


def _confusables(concepts: Sequence[dict[str, Any]]) -> list[str]:
    """The `Confusables` section, one row per concept with `confusable_with`, or nothing."""
    collisions = [c for c in concepts if c.get("confusable_with")]
    if not collisions:
        return []
    by_label = {c["id"]: c["pref_label"] for c in concepts}
    out = ["### Confusables\n",
           "One word, more than one meaning. The hazard a vocabulary "
           "guards against is\nmore often a collision than a gap.\n",
           "| This | Is not | \n|---|---|"]
    for c in collisions:
        others = ", ".join(by_label.get(o, o) for o in c["confusable_with"])
        out.append(f"| **{c['pref_label']}** | {others} |")
    out.append("")
    return out


def vocabulary() -> str:
    """Imported and domain terms render as one language, which is what a reader
    needs. They are separate files because sync treats them differently, not
    because they are separate vocabularies."""
    abox: dict[str, list[dict[str, Any]]] = {"concept_schemes": [], "concept_set": []}
    for rel in ("assertions/imported/vocabulary.yaml", "assertions/vocabulary.yaml",
                "assertions/domain_vocabulary.yaml"):
        part = record.load(rel) or {}
        for key in abox:
            abox[key].extend(part.get(key) or [])
    concepts = abox["concept_set"]
    out = [record.BANNER.format(src="assertions/*vocabulary.yaml"),
           record.authored("vocabulary.md")]
    for sid, scheme in {s["id"]: s for s in abox["concept_schemes"]}.items():
        members = [c for c in concepts if c.get("in_scheme") == sid]
        if members:
            out += _scheme(scheme, members, concepts)
    out += _confusables(concepts)
    return "\n".join(out) + record.accounted_by("vocabulary.md")


def charter() -> str | None:
    """The Charter, numbered, which is the form that makes an Article citable.

    Rendered flat and in order rather than grouped by Discipline: the number is
    the identifier, and a reader arriving from a citation wants to find it by
    counting, not by guessing which Discipline it belongs to.

    A retired number sits in that sequence, one line reading `Retired.` and no
    more. A reader scanning the Charter needs to know the gap is a gap; why it
    is one belongs to the retiring entry, and reaching it costs a grep, which
    is the point.
    """
    abox = record.load("assertions/imported/charter.yaml") or {}
    rows = abox.get("articles") or []
    if not rows:
        return None
    disciplines = {d["id"]: d["name"] for rel in
                   ("assertions/disciplines.yaml", "assertions/imported/disciplines.yaml")
                   for d in ((record.load(rel) or {}).get("disciplines") or [])}
    out = [record.BANNER.format(src="assertions/imported/charter.yaml"),
           record.authored("charter.md")]
    holes = {h["number"]: h for h in abox.get("retired_articles") or []}
    live = {int(a["id"].rsplit("/", 1)[-1]): a for a in rows}
    for num in sorted(live | holes):
        if num in holes:
            out.append(f"### A{num}. Retired.\n")
            continue
        inv = live[num]
        out.append(f"### A{num}. {inv['statement'].strip()}\n")
        held = disciplines.get(inv.get("enforces"))
        bits = []
        if held:
            bits.append(f"**Enforces** {held}.")
        if inv.get("checked_by"):
            bits.append(f"**Checked by** {inv['checked_by'].strip().rstrip('.')}.")
        if bits:
            out.append(" ".join(bits) + "\n")
        if inv.get("example"):
            out.append(f"_In practice:_ {inv['example'].strip()}\n")
        if inv.get("falsifier"):
            out.append(f"_Retired when:_ {inv['falsifier'].strip()}\n")
    return "\n".join(out) + record.accounted_by("charter.md")


def _procedure(name: str, target: str) -> str | None:
    """The root-level page for the Discipline called `name`.

    Reads only `assertions/disciplines.yaml`, the scaffold's own Disciplines,
    which a portfolio does not inherit.

    Args:
        name: The Discipline's `name`.
        target: The page's render target, whose Artifact carries its preamble
            and postamble.

    Returns:
        str | None: The page, or `None` when the assertions hold no such
        Discipline.
    """
    abox = record.load("assertions/disciplines.yaml") or {}
    d = next((x for x in abox.get("disciplines", []) if x["name"] == name), None)
    if d is None:
        return None
    out = [record.BANNER.format(src="assertions/disciplines.yaml"),
           record.authored(target),
           d["description"].strip() + "\n",
           f"**Where the judgement is.** {d['judgement'].strip()}\n",
           "## Steps\n",
           "\n".join(
               f"{i}. **{s['name'].rstrip('.')}.** {s['statement'].strip()}"
               for i, s in enumerate(d["steps"], 1)
           ) + "\n",
           "_Produces: " + "; ".join(d["produces"]).rstrip(".") + "._\n",
           record.authored(target, "postamble")]
    return "\n".join(out) + record.accounted_by(target)


def specialize() -> str | None:
    """The root-level instruction an agent arriving at the repo is pointed to.

    Generated from the Specialization Discipline, so the steps exist once. A
    procedure copied into a second file is a procedure that will disagree with
    itself.

    Answers `None` where the assertions hold no Specialization Discipline,
    which is every portfolio: a portfolio specializes nothing, so it has no
    such page.
    """
    return _procedure("Specialization", "../SPECIALIZE.md")


def adopt() -> str | None:
    """The root-level instruction for bringing an existing repository under stereorepo.

    Generated from the Adoption Discipline, as `specialize()` is generated
    from Specialization. Answers `None` where the assertions hold no Adoption
    Discipline, which is every portfolio: a portfolio adopts nothing.
    """
    return _procedure("Adoption", "../ADOPT.md")
