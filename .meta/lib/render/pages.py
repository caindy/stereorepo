"""The Portfolio's pages: the Disciplines, the vocabulary, the Charter, the Specialization steps, and the three GitHub forms.
"""

from lib.render import META, record, skills


def disciplines():
    """Renders the disciplines catalog markdown from declared and imported disciplines."""
    tbox = record.load("work/disciplines.yaml")
    abox = {"disciplines": []}
    for rel in ("assertions/disciplines.yaml", "assertions/imported/disciplines.yaml"):
        abox["disciplines"].extend((record.load(rel) or {}).get("disciplines") or [])
    out = [record.BANNER.format(src="assertions/disciplines.yaml + assertions/imported/disciplines.yaml"),
           record.authored("disciplines.md"),
           tbox["description"].strip() + "\n"]
    for d in abox["disciplines"]:
        out.append(f"### {d['name']}\n")
        if d.get("description"):
            out.append(d["description"].strip() + "\n")
        if d.get("judgement"):
            out.append(f"**Where the judgement is.** {d['judgement'].strip()}\n")
        if d.get("steps"):
            out.append("\n".join(f"{i}. {s}" for i, s in enumerate(d["steps"], 1)) + "\n")
        if d["name"] == (skills.channel() or {}).get("discipline"):
            out.append("The verbs are the steps, and each refuses its own misuse (solorepo's DR-116). Every act\n"
                       "on GitHub goes through the channel, `.meta/say/`, which names the Actor in\n"
                       "every commit and every comment; which Role holds each verb is\n"
                       "`.meta/say/verbs.yaml`'s to say, and a Role's reading lists\n"
                       "only its own (solorepo's DR-117).\n")
            for program in skills.channel()["programs"]:
                out.append(f"**`.meta/say/{program['name']}`** — {program['concern'].strip()}\n")
                out.append("\n".join(f"- `{skills.verb_line(program, v)}` — {v['does']} *({', '.join(v['held_by'])})*"
                                      for v in program["verbs"]) + "\n")
        if d.get("produces"):
            out.append("_Produces: " + "; ".join(d["produces"]).rstrip(".") + "._\n")
    return "\n".join(out) + record.accounted_by("disciplines.md")


def vocabulary():
    """Imported and domain terms render as one language, which is what a reader
    needs. They are separate files because sync treats them differently, not
    because they are separate vocabularies."""
    abox = {"concept_schemes": [], "concept_set": []}
    for rel in ("assertions/imported/vocabulary.yaml", "assertions/vocabulary.yaml",
                "assertions/domain_vocabulary.yaml"):
        part = record.load(rel) or {}
        for key in abox:
            abox[key].extend(part.get(key) or [])
    schemes = {s["id"]: s for s in abox["concept_schemes"]}
    out = [record.BANNER.format(src="assertions/*vocabulary.yaml"),
           record.authored("vocabulary.md")]
    for sid, scheme in schemes.items():
        members = [c for c in abox["concept_set"] if c.get("in_scheme") == sid]
        if not members:
            continue
        out.append(f"### {scheme['name']}\n")
        out.append(f"_Authority: {scheme.get('authority', 'unstated')}._\n")
        hubs = [c for c in members
                if any(m.get("broader") == c["id"] for m in abox["concept_set"])]
        grouped = {h["id"]: [] for h in hubs}
        loose = []
        for c in members:
            if c in hubs:
                continue
            (grouped[c["broader"]] if c.get("broader") in grouped else loose).append(c)

        def table(rows):
            out.append("| Term | Means | Do not say |\n|---|---|---|")
            for c in rows:
                avoid = ", ".join(c.get("avoid", [])) or "—"
                out.append(f"| **{c['pref_label']}** | {c['definition'].strip()} | {avoid} |")
            out.append("")

        if loose:
            table(loose)
        for h in hubs:
            if grouped[h["id"]]:
                out.append(f"#### {h['pref_label']}\n")
                out.append(f"_{h['definition'].strip()}_\n")
                table(grouped[h["id"]])
        for c in members:
            if c.get("scope_note"):
                out.append(f"**{c['pref_label']}.** {c['scope_note'].strip()}\n")
    collisions = [c for c in abox["concept_set"] if c.get("confusable_with")]
    if collisions:
        by_label = {c["id"]: c["pref_label"] for c in abox["concept_set"]}
        out.append("### Confusables\n")
        out.append("One word, more than one meaning. The hazard a vocabulary "
                   "guards against is\nmore often a collision than a gap.\n")
        out.append("| This | Is not | \n|---|---|")
        for c in collisions:
            others = ", ".join(by_label.get(o, o) for o in c["confusable_with"])
            out.append(f"| **{c['pref_label']}** | {others} |")
        out.append("")
    return "\n".join(out) + record.accounted_by("vocabulary.md")


def charter():
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


def specialize():
    """The root-level instruction an agent arriving at the repo is pointed to.

    Generated from the Specialization Discipline, so the steps exist once. A
    procedure copied into a second file is a procedure that will disagree with
    itself.

    Answers `None` where the assertions hold no Specialization Discipline,
    which is every portfolio: a portfolio specializes nothing, so it has no
    such page.
    """
    abox = record.load("assertions/disciplines.yaml") or {}
    d = next((x for x in abox.get("disciplines", []) if x["name"] == "Specialization"), None)
    if d is None:
        return None
    out = [record.BANNER.format(src="assertions/disciplines.yaml"),
           record.authored("../SPECIALIZE.md"),
           d["description"].strip() + "\n",
           f"**Where the judgement is.** {d['judgement'].strip()}\n",
           "## Steps\n",
           "\n".join(f"{i}. {s}" for i, s in enumerate(d["steps"], 1)) + "\n",
           "_Produces: " + "; ".join(d["produces"]).rstrip(".") + "._\n",
           record.authored("../SPECIALIZE.md", "postamble")]
    return "\n".join(out) + record.accounted_by("../SPECIALIZE.md")


def form(name):
    """The fenced block of a form in `.meta/templates/`, which is the form itself.

    The prose around it explains the form to whoever fills it in; the fence is
    what GitHub hands them. One copy, and this is the generator reading it —
    Literate Programming's rule applied to a template rather than to a schema.
    """
    text = (META / "templates" / name).read_text()
    fence = text.split("```markdown\n", 1)[1].split("\n```", 1)[0]
    return fence.rstrip("\n") + "\n"


def pull_request_template():
    """Renders the GitHub pull request markdown template form."""
    return form("pull-request.md")


def issue_template():
    """Renders the GitHub issue markdown template form."""
    return form("issue.md")


def roadmap_template():
    """Renders the GitHub roadmap item markdown template form."""
    return form("roadmap.md")
