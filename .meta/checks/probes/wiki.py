"""The wiki checks, run against stand-in pages rather than the tree (stereorepo's DR-209).

A wiki page is held to closed-world wikilinks, a MOS:LEAD lead, vocabulary
parity and synonyms its concept does not forbid (stereorepo's DR-185,
stereorepo's DR-190, stereorepo's DR-231). Each case gives one check an index,
a tree of `FakeWikiPath` pages and, for parity, a domain concept set, so that
a case reads nothing of the repository it runs in: the same probe passes in
stereorepo, whose domain vocabulary mints no concept, and in a portfolio that
mints many. The step registers here rather than beside the checks, because
the gate over assertions should not take its imports from a test suite
(stereorepo's DR-150).
"""
import collections
from collections.abc import Callable

import yaml

from checks import files
from checks.collect import Index, check
from checks.files import wiki
from checks.probes.harness import FakeWikiPath

WikiCase = collections.namedtuple("WikiCase", "name reads pages says concepts", defaults=((),))
"""One page or set of pages put to a wiki check.

`reads` is the `files` check run; `pages`, the `(path, text)` pairs it is
given as the tree; `says`, text one finding must carry, or `None` where the
check must find nothing; `concepts`, the domain `concept_set` the parity check
is given in place of `domain_vocabulary.yaml`, and which no other check takes.
"""

INDEX: Index = {
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
        {"id": "work:decision/185", "number": 185,
         "name": "DR-" + "185 · Wikipedia conventions"},
        "DR-" + "185.yaml",
    ),
    "ddd:concept/ledger": (
        "Concept",
        {"id": "ddd:concept/ledger", "pref_label": "Ledger"},
        "domain_vocabulary.yaml",
    ),
}
"""The record: a concept with an `avoid` list, a Discipline, a Decision and a domain concept."""

KNOWLEDGE_MANAGEMENT = (
    "wiki/stereorepo/knowledge-management.md",
    "# Knowledge Management\n\n**Knowledge Management** is a discipline.\n",
)
"""The scaffold's page of a minted Discipline."""

UBIQUITOUS_LANGUAGE = "\n# Ubiquitous Language\n\n**Ubiquitous Language** is a concept.\n"
"""The heading and lead of the scaffold's page of a minted concept."""

LEDGER = ({"id": "ddd:concept/ledger"},)
"""A domain concept set minting one concept."""

CASES = (
    WikiCase(
        "an unregistered wikilink",
        files.wikilinks,
        (("wiki/stereorepo/test.md",
          "# Test\n\n**Test** is a probe referencing [[unregistered-floating-term]].\n"),),
        "[[unregistered-floating-term]] resolves to nothing",
    ),
    WikiCase(
        "wikilinks to a concept, a discipline, a Decision and a scoped wiki page",
        files.wikilinks,
        (KNOWLEDGE_MANAGEMENT,
         ("wiki/stereorepo/test.md",
          "# Test\n\n**Test** is a test referencing [[knowledge-management]], "
          "[[stereorepo/knowledge-management]], [[Ubiquitous Language]], and "
          "[[" + "DR-" + "185]].\n")),
        None,
    ),
    WikiCase(
        "wikilinks inside a code fence and inline backticks",
        files.wikilinks,
        (("wiki/stereorepo/test.md",
          "# Test\n\n**Test** is a test showing `[[unregistered-inline]]` and:\n"
          "```\n[[unregistered-block]]\n```\n"),),
        None,
    ),
    WikiCase(
        "a page with no top-level heading",
        files.wiki_lead_paragraphs,
        (("wiki/stereorepo/test.md", "## Subheading\n\n**Test** is a test page.\n"),),
        "must begin with a top-level heading",
    ),
    WikiCase(
        "a lead with no bold copula",
        files.wiki_lead_paragraphs,
        (("wiki/stereorepo/test.md",
          "# Test\n\nTest is a test page without bold formatting.\n"),),
        "first paragraph must open with bold copular definition",
    ),
    WikiCase(
        "a bold subject that is not the title",
        files.wiki_lead_paragraphs,
        (("wiki/stereorepo/test.md", "# Test\n\n**Different Subject** is a test page.\n"),),
        "does not match title",
    ),
    WikiCase(
        "a subject that disagrees with the minted label",
        files.wiki_lead_paragraphs,
        (("wiki/stereorepo/ubiquitous-language.md",
          "# Ubiquitous Language Alternate\n\n"
          "**Ubiquitous Language Alternate** is a discipline.\n"),),
        "disagrees with minted label",
    ),
    WikiCase(
        "a README.md, exempt from MOS:LEAD",
        files.wiki_lead_paragraphs,
        (("wiki/stereorepo/README.md",
          "# Context Index\n\nAn index of pages without bold copular lead.\n"),),
        None,
    ),
    WikiCase(
        "frontmatter ahead of a MOS:LEAD lead (stereorepo's DR-187)",
        files.wiki_lead_paragraphs,
        (("wiki/stereorepo/test-frontmatter.md",
          "---\nslug: test-frontmatter\ncontext: stereorepo\nminted: 2026-09-12\n---\n\n"
          "# Test Frontmatter\n\n**Test Frontmatter** is a test page.\n"),),
        None,
    ),
    WikiCase(
        "a domain page with no minted concept (stereorepo's DR-190)",
        files.ubiquitous_language_wiki_parity,
        (("wiki/billing/unminted-term.md", "# Unminted Term\n\n**Unminted Term** is a term.\n"),),
        "has no corresponding concept in vocabulary schema",
    ),
    WikiCase(
        "stereorepo pages of a minted discipline and concept (stereorepo's DR-190)",
        files.ubiquitous_language_wiki_parity,
        (KNOWLEDGE_MANAGEMENT, ("wiki/stereorepo/ubiquitous-language.md", UBIQUITOUS_LANGUAGE)),
        None,
    ),
    WikiCase(
        "a domain concept with its page (stereorepo's DR-190)",
        files.ubiquitous_language_wiki_parity,
        (("wiki/billing/ledger.md", "# Ledger\n\n**Ledger** is a concept.\n"),),
        None,
        LEDGER,
    ),
    WikiCase(
        "a domain concept with no page (stereorepo's DR-190)",
        files.ubiquitous_language_wiki_parity,
        (),
        "concept 'ddd:concept/ledger' has no corresponding wiki page",
        LEDGER,
    ),
    WikiCase(
        "a synonym on the concept's own avoid list (stereorepo's DR-231)",
        files.wiki_synonyms_are_not_avoided,
        (("wiki/stereorepo/ubiquitous-language.md",
          "---\nslug: ubiquitous-language\ncontext: stereorepo\nsynonyms:\n  - shared glossary\n"
          "minted: 2026-09-18\n---\n" + UBIQUITOUS_LANGUAGE),),
        "is on work:concept/ubiquitous-language's avoid list",
    ),
    WikiCase(
        "a synonym the vocabulary neither mints nor forbids (stereorepo's DR-231)",
        files.wiki_synonyms_are_not_avoided,
        (("wiki/stereorepo/ubiquitous-language.md",
          "---\nslug: ubiquitous-language\ncontext: stereorepo\nsynonyms:\n  - domain dialect\n"
          "minted: 2026-09-18\n---\n" + UBIQUITOUS_LANGUAGE),
         KNOWLEDGE_MANAGEMENT),
        None,
    ),
)
"""Each wiki check's observed failure and its concordance."""

PORTFOLIO_CONCEPTS: list[dict[str, object]] = [{"id": "ddd:concept/fitch-term"}]
"""A portfolio's domain `concept_set`, minting one concept whose page no case gives."""


@check("wiki probes", pre=True)
def wiki_probes() -> list[str]:
    """Observed failure and concordance for every wiki check (A2, stereorepo's DR-190).

    Each case gives one of `files.wikilinks`, `files.wiki_lead_paragraphs`,
    `files.ubiquitous_language_wiki_parity` or
    `files.wiki_synonyms_are_not_avoided` the shared `INDEX` and a tree of
    `FakeWikiPath` pages, and expects either a finding carrying a given text or
    no finding at all. A wikilink resolves against the index, the pages given,
    and the wiki on disk under `ROOT`; the case gives the scoped
    `[[stereorepo/knowledge-management]]` its page so that it holds on a tree
    that lacks one; a code fence and inline backticks hide a wikilink from
    the check; `README.md` is exempt from the lead rule; frontmatter may stand
    ahead of the heading (stereorepo's DR-187); a domain page with no minted
    concept, and a domain concept with no page, fail parity where a domain
    concept with its page and stereorepo pages of a minted discipline and
    concept pass (stereorepo's DR-190); and a page declaring an avoided word as
    a synonym fails where one declaring an unminted word passes, since parity
    is owed to the `avoid` list and not to `alt_labels` (stereorepo's DR-231).

    The cases are run twice: once as the repository holds its domain
    vocabulary, and once with `wiki.domain_concepts` answering a portfolio's,
    so that a case reading the vocabulary on disk fails here, in stereorepo,
    rather than only in a portfolio that mints a concept. The gate's own call,
    which gives no `concepts`, is probed apart in `_vocabulary_on_disk`.
    """
    problems = _run_cases()
    problems.extend(f"in a portfolio minting a concept: {problem}"
                    for problem in _with_domain_concepts(lambda: PORTFOLIO_CONCEPTS, _run_cases))
    problems.extend(_vocabulary_on_disk())
    return problems


def _vocabulary_on_disk() -> list[str]:
    """The parity check given no `concepts`, as the gate gives none, reads `wiki.domain_concepts`.

    A concept read so with no page is reported, and a vocabulary that will not
    parse is one finding rather than an exception.
    """
    def unparseable() -> list[dict[str, object]]:
        raise yaml.YAMLError("stand-in")

    expectations = (
        ("a portfolio's concept with no page", lambda: PORTFOLIO_CONCEPTS,
         "concept 'ddd:concept/fitch-term' has no corresponding wiki page"),
        ("a vocabulary that will not parse", unparseable, "failed to parse for parity check"),
    )
    problems = []
    for name, answer, says in expectations:
        said = _with_domain_concepts(
            answer, lambda: files.ubiquitous_language_wiki_parity(INDEX, md_files=[]))
        if not any(says in p for p in said):
            problems.append(f"ubiquitous_language_wiki_parity: given no concepts, {name}: "
                            f"expected a finding saying {says!r}, got {said!r}")
    return problems


def _run_cases() -> list[str]:
    """Every case of `CASES` whose check answered other than it expects."""
    problems = []
    for case in CASES:
        pages = [FakeWikiPath(path, text) for path, text in case.pages]
        parity = case.reads is files.ubiquitous_language_wiki_parity
        said = case.reads(INDEX, md_files=pages, **({"concepts": case.concepts} if parity else {}))
        if case.says is None and said:
            problems.append(f"{case.reads.__name__}: {case.name}: "
                            f"expected no finding, got {said!r}")
        elif case.says is not None and not any(case.says in p for p in said):
            problems.append(f"{case.reads.__name__}: {case.name}: "
                            f"expected a finding saying {case.says!r}, got {said!r}")
    return problems


def _with_domain_concepts[T](
        answer: Callable[[], list[dict[str, object]]], fn: Callable[[], T]) -> T:
    """`fn()` with `answer` standing for `wiki.domain_concepts`, the module restored after."""
    saved = wiki.domain_concepts
    wiki.domain_concepts = answer
    try:
        return fn()
    finally:
        wiki.domain_concepts = saved
