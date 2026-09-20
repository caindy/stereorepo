"""What the repository writes down about itself, held to the form its readers assume (solorepo's DR-209).

The knowledge Knowledge Management governs is one subject in three containers,
and each of these probes is over one of them: a history log parsed for its
entries and the Evidence they name (solorepo's DR-171), a withdrawn Decision of the
record asked for the reason its `WITHDRAWN` status owes under
`.meta/work/decisions.yaml`, and a wiki page held to closed-world wikilinks, a
MOS:LEAD lead, vocabulary parity and synonyms its concept does not forbid
(solorepo's DR-185, solorepo's DR-190, solorepo's DR-231) —
together with the authoring tool that scaffolds such a page, which is a probe
over the wiki's form and not over a tool beside the gate (solorepo's DR-187).
One further probe is over the form the prose in all three containers carries:
the possessive that marks a citation as solorepo's rather than a portfolio's
own (solorepo's DR-121, solorepo's DR-132).
Each check is run against strings and stand-in pages rather than the tree, so a
case is one fixture and one expectation, and a failure names the case. The
steps register here rather than beside the checks they exercise, because the
gate over assertions should not take its imports from a test suite
(solorepo's DR-150).
"""
import collections
import contextlib
import io
import types

from checks import citations, files, graph
from checks.collect import META, ROOT, check
from checks.probes.harness import FakeWikiPath, load_module

WithdrawnCase = collections.namedtuple("WithdrawnCase", "name number decision refused")
"""One Decision put to `graph.withdrawn_decisions`: `number`, the last segment of its id; `decision`, its fields; `refused`, whether the check must name it."""

REFUSAL = "status is WITHDRAWN but lacks 'withdrawn_because'"
"""What `graph.withdrawn_decisions` says of a withdrawal that gives no reason."""

WikiCase = collections.namedtuple("WikiCase", "name reads pages says")
"""One page or set of pages put to a wiki check: `reads`, the `files` check run; `pages`, the `(path, text)` pairs it is given as the tree; `says`, text one finding must carry, or `None` where the check must find nothing."""


@check("history probes", pre=True)
def history_probes() -> list[str]:
    """`files.history_entries_of` reads a history log's entries and the Evidence they name as `meta history evidence` needs them (solorepo's DR-171).

    Two logs, each a string. The first holds a live entry and, inside an HTML
    comment, a second whose Evidence names nothing: the comment is stripped
    before parsing, so one entry comes back, it is the live one, and its
    Evidence is what stood between the backticks. The second holds an entry
    with no `Evidence:` line, which parses to `None`, as an entry
    whose `Evidence:` line has no backticks does.
    """
    problems = []
    commented = (
        "### Live Entry\n\n"
        "Evidence: `.meta/check.py::main`\n\n"
        "<!--\n"
        "### Commented Entry\n\n"
        "Evidence: `.meta/checks/probes/knowledge.py::no_such_probe`\n"
        "-->"
    )
    entries = files.history_entries_of(commented)
    if len(entries) != 1:
        problems.append(f"history probes: an entry inside an HTML comment: expected 1 entry, got {len(entries)}")
    elif entries[0] != ("Live Entry", ".meta/check.py::main"):
        problems.append(f"history probes: an entry inside an HTML comment: unexpected entry {entries[0]}")
    no_evidence = files.history_entries_of("### Broken Entry\n\nNo Evidence line here\n")
    if len(no_evidence) != 1 or no_evidence[0][1] is not None:
        problems.append(f"history probes: an entry with no Evidence line: expected None, got {no_evidence}")
    return problems


@check("withdrawn decisions probes", pre=True)
def withdrawn_decisions_probes() -> list[str]:
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
def wiki_probes() -> list[str]:
    """Observed failure and concordance for wikilinks, MOS:LEAD lead paragraphs, vocabulary parity and forbidden synonyms (A2, solorepo's DR-185, solorepo's DR-190, solorepo's DR-231).

    One index stands for the record: a concept carrying an `avoid` list, a
    discipline and a Decision. Each case gives one of `files.wikilinks`,
    `files.wiki_lead_paragraphs`, `files.ubiquitous_language_wiki_parity` or
    `files.wiki_synonyms_are_not_avoided` that index and a tree of
    `FakeWikiPath` pages, and expects either a finding carrying a given text or
    no finding at all. A wikilink resolves against the index, the pages given,
    and the wiki on disk under `ROOT`; the case gives the scoped
    `[[solorepo/knowledge-management]]` its page so that it holds on a tree
    that lacks one; a code fence and inline backticks hide a wikilink from
    the check; `README.md` is exempt from the lead rule; frontmatter may stand
    ahead of the heading (solorepo's DR-187); a domain page with no minted
    concept fails parity where solorepo pages of a minted discipline and
    concept pass (solorepo's DR-190); and a page declaring an avoided word as a
    synonym fails where one declaring an unminted word passes, since parity is
    owed to the `avoid` list and not to `alt_labels` (solorepo's DR-231).
    """
    index = {
        "work:concept/ubiquitous-language": (
            "Concept",
            {"id": "work:concept/ubiquitous-language", "pref_label": "Ubiquitous Language",
             "avoid": ["Shared Glossary"]},
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
        WikiCase(
            "a synonym on the concept's own avoid list (solorepo's DR-231)",
            files.wiki_synonyms_are_not_avoided,
            (("wiki/solorepo/ubiquitous-language.md",
              "---\nslug: ubiquitous-language\ncontext: solorepo\nsynonyms:\n  - shared glossary\n"
              "minted: 2026-09-18\n---\n\n# Ubiquitous Language\n\n**Ubiquitous Language** is a concept.\n"),),
            "is on work:concept/ubiquitous-language's avoid list",
        ),
        WikiCase(
            "a synonym the vocabulary neither mints nor forbids (solorepo's DR-231)",
            files.wiki_synonyms_are_not_avoided,
            (("wiki/solorepo/ubiquitous-language.md",
              "---\nslug: ubiquitous-language\ncontext: solorepo\nsynonyms:\n  - domain dialect\n"
              "minted: 2026-09-18\n---\n\n# Ubiquitous Language\n\n**Ubiquitous Language** is a concept.\n"),
             ("wiki/solorepo/knowledge-management.md",
              "# Knowledge Management\n\n**Knowledge Management** is a discipline.\n")),
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
def wikisplain_probes() -> list[str]:
    """`.meta/wikisplain.py` slugifies a title, formats a MOS:LEAD lead, finds a duplicate, refuses a forbidden synonym, and scaffolds a page that passes its own verification (solorepo's DR-187, solorepo's DR-231).

    Eight of the tool's acts, each called directly or through `cli.main`:
    `slugify` on a two-word title; `format_lead_sentence` on a title and a
    definition, which must read as one bold copular sentence; `find_duplicates`
    on a discipline the wiki already holds a page for, which must be found
    among the wiki pages; `generate_page` followed by `verify_page` on a
    synthetic concept, which must raise no warning; `generate_page` on that
    concept filed under a slug its title does not produce, which must declare
    the slug it is filed under rather than the one its title implies; and
    `verify_page` on a page filed under that same custom slug with a
    self-referencing wikilink to it, which must raise no warning either —
    `verify_page` reads its own identity off `rel_path`'s stem rather than
    re-slugifying the title, so the two can diverge without false-positiving
    (solorepo's #617); and `cli.main`, which is where the tree the tool reads is
    resolved rather than passed: `--check-duplicate` on a concept the wiki and
    the vocabulary both hold, and a scaffold whose `--synonyms` name an avoided
    word. Each must exit 1, and the second is given `--force` and `--dry-run`,
    so it is refused for the avoid list rather than for the collision and
    nothing is written. Their output is captured, because the gate reads this
    process's stdout for A21's shapes. The tree-reading cases hold only while
    `wiki/solorepo/` holds the pages the tool links a new page to by default
    and the vocabulary holds `work:concept/challenge`.
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
    avoided = wikisplain.avoided_synonyms("challenge", ["Ticket", "unit of work"], root=ROOT)
    if [a["synonym"] for a in avoided] != ["Ticket"]:
        problems.append(f"avoided_synonyms: expected 'Ticket' alone to be refused, got {avoided!r}")
    content = wikisplain.generate_page(
        wikisplain.Page(title="Test Wiki Concept", context="solorepo",
                        definition="a synthetic concept for gate validation"),
        root=ROOT,
    )
    verif = wikisplain.verify_page(content, "wiki/solorepo/test-wiki-concept.md", root=ROOT)
    if verif:
        problems.append(f"verify_page: generated page produced validation warnings: {verif!r}")
    filed = wikisplain.generate_page(
        wikisplain.Page(title="Test Wiki Concept", slug="test-filed-elsewhere", context="solorepo",
                        definition="a synthetic concept for gate validation"),
        root=ROOT,
    )
    if "\nslug: test-filed-elsewhere\n" not in filed:
        problems.append(f"generate_page: a Page filed under its own slug declared another: {filed[:120]!r}")
    self_ref = wikisplain.generate_page(
        wikisplain.Page(title="Test Wiki Concept", slug="test-filed-elsewhere", context="solorepo",
                        definition="a synthetic concept for gate validation",
                        body="See [[test-filed-elsewhere]] for detail."),
        root=ROOT,
    )
    self_ref_verif = wikisplain.verify_page(self_ref, "wiki/solorepo/test-filed-elsewhere.md", root=ROOT)
    if self_ref_verif:
        problems.append(
            f"verify_page: self-reference under a custom --slug false-positived: {self_ref_verif!r}"
        )
    problems.extend(cli_probes(wikisplain))
    return problems


def cli_probes(wikisplain: types.ModuleType) -> list[str]:
    """`cli.main` refusing a collision and an avoided synonym, each read from its exit code with its output captured (solorepo's DR-187, solorepo's DR-231)."""
    problems = []
    for name, argv in (
        ("a concept the wiki and the vocabulary both hold",
         ["Knowledge Management", "--check-duplicate"]),
        ("a synonym on the concept's avoid list, past --force",
         ["Challenge", "--slug", "challenge", "--synonyms", "ticket", "--force", "--dry-run"]),
    ):
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            code = wikisplain.main(argv)
        if code != 1:
            problems.append(f"cli.main: {name}: expected exit 1, got {code} saying {said.getvalue()!r}")
    return problems


@check("wikisplain argv probes", pre=True)
def wikisplain_argv_probes() -> list[str]:
    """`wikisplain.main` joins shell-split concepts and scaffolds beneath its resolved repository root (solorepo's #483).

    A shell splits an unquoted `Test Wiki Concept Two` into four argv words;
    driven through `wikisplain.main` with `--dry-run`, the generated page's
    heading and MOS:LEAD lead must read the concept whole, not its first word
    alone. Losing `nargs="+"` regresses to argparse rejecting the trailing
    words as `unrecognized arguments`, which raises `SystemExit` rather than
    returning — caught here and reported as the case's own finding, since
    `check.py`'s precheck guard catches `Exception` and `SystemExit` is not
    one. A second invocation points `cli.ROOT` at a temporary repository and
    asserts that `main` writes its scaffold under that root's `wiki/` tree.
    """
    import contextlib
    import io
    import pathlib
    import tempfile
    wikisplain = load_module(META / "wikisplain.py", "wikisplain")
    problems = []
    argv = ["Test", "Wiki", "Concept", "Two", "--definition", "a synthetic concept for regression coverage",
            "--dry-run"]
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            rc = wikisplain.main(argv)
    except SystemExit as exc:
        problems.append(f"wikisplain argv: a shell-split concept raised SystemExit({exc.code}) "
                        "instead of joining the words")
        return problems
    content = out.getvalue()
    if rc != 0:
        problems.append(f"wikisplain argv: expected exit 0 for a shell-split concept, got {rc}")
    if "# Test Wiki Concept Two" not in content:
        problems.append(f"wikisplain argv: expected heading 'Test Wiki Concept Two', got {content!r}")
    if "**Test Wiki Concept Two** is a synthetic concept for regression coverage." not in content:
        problems.append(f"wikisplain argv: expected the joined MOS:LEAD lead, got {content!r}")

    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        old_root = wikisplain.cli.ROOT
        wikisplain.cli.ROOT = root
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                rc = wikisplain.main([
                    "Command Root Concept",
                    "--definition", "a synthetic concept for command-line root coverage",
                ])
        finally:
            wikisplain.cli.ROOT = old_root
        target = root / "wiki" / "solorepo" / "command-root-concept.md"
        if rc != 0:
            problems.append(f"wikisplain argv: expected a successful scaffold, got {rc}")
        if not target.is_file():
            problems.append(f"wikisplain argv: expected scaffold at {target}, but it was not written")
    return problems


@check("citation form probes", pre=True)
def citation_form_probes() -> list[str]:
    """`citations.FOREIGN` and `check_pr.FOREIGN` hold every citation character exact except its leading `S` or `s`.

    `citations.issue_citation()` loads the `(ISSUE, FOREIGN)` pair from
    `check_pr.py`. Two forms, each put through the same split `cited_decisions` and
    `inherited_citations` make between a citation the possessive marks as
    foreign and one left over for the bare scan: `foreign.sub("", text)`
    followed by the bare pattern's own `findall`. A sentence-initial
    possessive citation must leave nothing for the bare scan to find, and a
    genuinely bare one — no possessive at all — must still read as bare, so
    the widened pattern is pinned in both directions and not merely proved
    by the absence of a complaint. An all-uppercase possessive must remain
    bare, proving that only the leading letter is widened. The number is spelled from `count` rather
    than typed, because `DR-` or `#` immediately followed by digits in a file
    a portfolio copies is a citation as far as `cited decisions` and
    `inherited citations` are concerned, and this one is a fixture
    (solorepo's DR-124).
    """
    problems = []
    count = 999
    issue, issue_foreign = citations.issue_citation()
    cases = (
        ("Decision", citations.FOREIGN, citations.DR,
         f"Solorepo's DR-{count:03d} makes PR First a render target.",
         f"DR-{count:03d} makes PR First a render target."),
        ("Issue", issue_foreign, issue,
         f"Solorepo's #{count} tracks the same fix.",
         f"#{count} tracks the same fix."),
    )
    for name, foreign, pattern, capitalised, bare_text in cases:
        left_over = set(pattern.findall(foreign.sub("", capitalised)))
        if left_over:
            problems.append(f"citation form: a sentence-initial {name} citation "
                            f"read bare as {left_over!r}")
        still_bare = set(pattern.findall(foreign.sub("", bare_text)))
        if still_bare != {str(count)}:
            problems.append(f"citation form: a genuinely bare {name} citation "
                            f"read as {still_bare!r}, and the widened pattern "
                            "must still catch it")
        other_case = (
            f"SOLOREPO'S DR-{count:03d} makes PR First a render target."
            if name == "Decision"
            else f"SOLOREPO'S #{count} tracks the same fix."
        )
        still_bare = set(pattern.findall(foreign.sub("", other_case)))
        if still_bare != {str(count)}:
            problems.append(f"citation form: an all-uppercase {name} citation "
                            f"read as {still_bare!r}, but only the leading letter "
                            "may be case-insensitive")
    return problems
