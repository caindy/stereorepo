"""What the repository writes down about itself, held to the form its readers assume (solorepo's DR-209).

The knowledge Knowledge Management governs is one subject in three containers,
and each of these probes is over one of them: a history log parsed for its
entries and their receipts (solorepo's DR-171), a withdrawn Decision of the
record asked for the reason its `WITHDRAWN` status owes under
`.meta/work/decisions.yaml`, and a wiki page held to closed-world wikilinks, a
MOS:LEAD lead and vocabulary parity (solorepo's DR-185, solorepo's DR-190) —
together with the authoring tool that scaffolds such a page, which is a probe
over the wiki's form and not over a tool beside the gate (solorepo's DR-187).
Each check is run against strings and stand-in pages rather than the tree, so a
case is one fixture and one expectation, and a failure names the case. The
steps register here rather than beside the checks they exercise, because the
gate over assertions should not take its imports from a test suite
(solorepo's DR-150).
"""
import collections

import files
import graph
from collect import META, ROOT, check
from probes.harness import FakeWikiPath, load_module

WithdrawnCase = collections.namedtuple("WithdrawnCase", "name number decision refused")
"""One Decision put to `graph.withdrawn_decisions`: `number`, the last segment of its id; `decision`, its fields; `refused`, whether the check must name it."""

REFUSAL = "status is WITHDRAWN but lacks 'withdrawn_because'"
"""What `graph.withdrawn_decisions` says of a withdrawal that gives no reason."""

WikiCase = collections.namedtuple("WikiCase", "name reads pages says")
"""One page or set of pages put to a wiki check: `reads`, the `files` check run; `pages`, the `(path, text)` pairs it is given as the tree; `says`, text one finding must carry, or `None` where the check must find nothing."""


@check("history probes", pre=True)
def history_probes():
    """`files.history_entries_of` reads a history log's entries and receipts as `meta history receipts` needs them (solorepo's DR-171).

    Two logs, each a string. The first holds a live entry and, inside an HTML
    comment, a second whose receipt names nothing: the comment is stripped
    before parsing, so one entry comes back, it is the live one, and its
    receipt is what stood between the backticks. The second holds an entry
    with no `Receipt:` line, which parses to a `None` receipt, as an entry
    whose receipt line has no backticks does.
    """
    problems = []
    commented = (
        "### Live Entry\n\n"
        "Receipt: `.meta/check.py::main`\n\n"
        "<!--\n"
        "### Commented Entry\n\n"
        "Receipt: `.meta/checks/probes/knowledge.py::no_such_probe`\n"
        "-->"
    )
    entries = files.history_entries_of(commented)
    if len(entries) != 1:
        problems.append(f"history probes: an entry inside an HTML comment: expected 1 entry, got {len(entries)}")
    elif entries[0] != ("Live Entry", ".meta/check.py::main"):
        problems.append(f"history probes: an entry inside an HTML comment: unexpected entry {entries[0]}")
    no_receipt = files.history_entries_of("### Broken Entry\n\nNo receipt line here\n")
    if len(no_receipt) != 1 or no_receipt[0][1] is not None:
        problems.append(f"history probes: an entry with no receipt line: expected None receipt, got {no_receipt}")
    return problems


@check("withdrawn decisions probes", pre=True)
def withdrawn_decisions_probes():
    """`graph.withdrawn_decisions` names a WITHDRAWN Decision that gives no `withdrawn_because`, and nothing else, as the `Decision` rule in `.meta/work/decisions.yaml` requires when `status` is `WITHDRAWN`.

    Three Decisions, each indexed alone under `work:decision/<number>`:
    WITHDRAWN with no reason, which the check names; WITHDRAWN with a reason,
    which passes; and ADOPTED with no reason, which passes, since only a
    withdrawal owes one.
    """
    cases = (
        WithdrawnCase("WITHDRAWN lacking withdrawn_because", "001", {"status": "WITHDRAWN"}, True),
        WithdrawnCase("WITHDRAWN with withdrawn_because", "002",
                      {"status": "WITHDRAWN", "withdrawn_because": "Some reason"}, False),
        WithdrawnCase("ADOPTED lacking withdrawn_because", "003", {"status": "ADOPTED"}, False),
    )
    problems = []
    for case in cases:
        index = {f"work:decision/{case.number}": ("Decision", case.decision, "a probe")}
        said = graph.withdrawn_decisions(index)
        if case.refused and not any(REFUSAL in s for s in said):
            problems.append(f"withdrawn decisions: {case.name}: expected a finding saying {REFUSAL!r}, got {said!r}")
        elif not case.refused and said:
            problems.append(f"withdrawn decisions: {case.name}: expected no finding, got {said!r}")
    return problems


@check("wiki probes", pre=True)
def wiki_probes():
    """Observed failure and concordance for wikilinks, MOS:LEAD lead paragraphs and vocabulary parity (A2, solorepo's DR-185, solorepo's DR-190).

    One index stands for the record: a concept, a discipline and a Decision.
    Each case gives one of `files.wikilinks`, `files.wiki_lead_paragraphs` or
    `files.ubiquitous_language_wiki_parity` that index and a tree of
    `FakeWikiPath` pages, and expects either a finding carrying a given text or
    no finding at all. A wikilink resolves against the index, the pages given,
    and the wiki on disk under `ROOT`; the case gives the scoped
    `[[solorepo/knowledge-management]]` its page so that it holds on a tree
    that lacks one; a code fence and inline backticks hide a wikilink from
    the check; `README.md` is exempt from the lead rule; frontmatter may stand
    ahead of the heading (solorepo's DR-187); and a domain page with no minted
    concept fails parity where solorepo pages of a minted discipline and
    concept pass (solorepo's DR-190).
    """
    index = {
        "work:concept/ubiquitous-language": (
            "Concept",
            {"id": "work:concept/ubiquitous-language", "pref_label": "Ubiquitous Language"},
            "vocabulary.yaml",
        ),
        "work:discipline/knowledge-management": (
            "Discipline",
            {"id": "work:discipline/knowledge-management", "name": "Knowledge Management"},
            "disciplines.yaml",
        ),
        "work:decision/185": (
            "Decision",
            {"id": "work:decision/185", "number": 185, "name": "DR-" + "185 · Wikipedia conventions"},
            "DR-" + "185.yaml",
        ),
    }
    cases = (
        WikiCase(
            "an unregistered wikilink",
            files.wikilinks,
            (("wiki/solorepo/test.md",
              "# Test\n\n**Test** is a probe referencing [[unregistered-floating-term]].\n"),),
            "[[unregistered-floating-term]] resolves to nothing",
        ),
        WikiCase(
            "wikilinks to a concept, a discipline, a Decision and a scoped wiki page",
            files.wikilinks,
            (("wiki/solorepo/knowledge-management.md",
              "# Knowledge Management\n\n**Knowledge Management** is a discipline.\n"),
             ("wiki/solorepo/test.md",
              "# Test\n\n**Test** is a test referencing [[knowledge-management]], "
              "[[solorepo/knowledge-management]], [[Ubiquitous Language]], and [[" + "DR-" + "185]].\n")),
            None,
        ),
        WikiCase(
            "wikilinks inside a code fence and inline backticks",
            files.wikilinks,
            (("wiki/solorepo/test.md",
              "# Test\n\n**Test** is a test showing `[[unregistered-inline]]` and:\n```\n[[unregistered-block]]\n```\n"),),
            None,
        ),
        WikiCase(
            "a page with no top-level heading",
            files.wiki_lead_paragraphs,
            (("wiki/solorepo/test.md", "## Subheading\n\n**Test** is a test page.\n"),),
            "must begin with a top-level heading",
        ),
        WikiCase(
            "a lead with no bold copula",
            files.wiki_lead_paragraphs,
            (("wiki/solorepo/test.md", "# Test\n\nTest is a test page without bold formatting.\n"),),
            "first paragraph must open with bold copular definition",
        ),
        WikiCase(
            "a bold subject that is not the title",
            files.wiki_lead_paragraphs,
            (("wiki/solorepo/test.md", "# Test\n\n**Different Subject** is a test page.\n"),),
            "does not match title",
        ),
        WikiCase(
            "a subject that disagrees with the minted label",
            files.wiki_lead_paragraphs,
            (("wiki/solorepo/ubiquitous-language.md",
              "# Ubiquitous Language Alternate\n\n**Ubiquitous Language Alternate** is a discipline.\n"),),
            "disagrees with minted label",
        ),
        WikiCase(
            "a README.md, exempt from MOS:LEAD",
            files.wiki_lead_paragraphs,
            (("wiki/solorepo/README.md", "# Context Index\n\nAn index of pages without bold copular lead.\n"),),
            None,
        ),
        WikiCase(
            "frontmatter ahead of a MOS:LEAD lead (solorepo's DR-187)",
            files.wiki_lead_paragraphs,
            (("wiki/solorepo/test-frontmatter.md",
              "---\nslug: test-frontmatter\ncontext: solorepo\nminted: 2026-09-12\n---\n\n"
              "# Test Frontmatter\n\n**Test Frontmatter** is a test page.\n"),),
            None,
        ),
        WikiCase(
            "a domain page with no minted concept (solorepo's DR-190)",
            files.ubiquitous_language_wiki_parity,
            (("wiki/billing/unminted-term.md", "# Unminted Term\n\n**Unminted Term** is a term.\n"),),
            "has no corresponding concept in vocabulary schema",
        ),
        WikiCase(
            "solorepo pages of a minted discipline and concept (solorepo's DR-190)",
            files.ubiquitous_language_wiki_parity,
            (("wiki/solorepo/knowledge-management.md",
              "# Knowledge Management\n\n**Knowledge Management** is a discipline.\n"),
             ("wiki/solorepo/ubiquitous-language.md",
              "# Ubiquitous Language\n\n**Ubiquitous Language** is a concept.\n")),
            None,
        ),
    )
    problems = []
    for case in cases:
        said = case.reads(index, md_files=[FakeWikiPath(path, text) for path, text in case.pages])
        if case.says is None and said:
            problems.append(f"{case.reads.__name__}: {case.name}: expected no finding, got {said!r}")
        elif case.says is not None and not any(case.says in p for p in said):
            problems.append(
                f"{case.reads.__name__}: {case.name}: expected a finding saying {case.says!r}, got {said!r}"
            )
    return problems


@check("wikisplain probes", pre=True)
def wikisplain_probes():
    """`.meta/wikisplain.py` slugifies a title, formats a MOS:LEAD lead, finds a duplicate, and scaffolds a page that passes its own verification (solorepo's DR-187).

    Four of the tool's acts, each called directly:
    `slugify` on a two-word title; `format_lead_sentence` on a title and a
    definition, which must read as one bold copular sentence; `find_duplicates`
    on a discipline the wiki already holds a page for, which must be found
    among the wiki pages; and `generate_page` followed by `verify_page` on a
    synthetic concept, which must raise no warning. The last two read the tree
    at `ROOT`, so they hold only while `wiki/solorepo/` holds the pages the
    tool links a new page to by default.
    """
    wikisplain = load_module(META / "wikisplain.py", "wikisplain")
    problems = []
    slug = wikisplain.slugify("Domain Storytelling")
    if slug != "domain-storytelling":
        problems.append(f"slugify: expected 'domain-storytelling', got {slug!r}")
    lead = wikisplain.format_lead_sentence("Domain Storytelling", "a visual modeling method")
    if lead != "**Domain Storytelling** is a visual modeling method.":
        problems.append(f"format_lead_sentence: unexpected result {lead!r}")
    dups = wikisplain.find_duplicates("Knowledge Management", root=ROOT)
    if not any(d["source"] == "wiki" for d in dups):
        problems.append(f"find_duplicates: expected wiki duplicate for 'Knowledge Management', got {dups!r}")
    content = wikisplain.generate_page(
        title="Test Wiki Concept",
        context="solorepo",
        definition="a synthetic concept for gate validation",
        root=ROOT,
    )
    verif = wikisplain.verify_page(content, "wiki/solorepo/test-wiki-concept.md", root=ROOT)
    if verif:
        problems.append(f"verify_page: generated page produced validation warnings: {verif!r}")
    return problems
