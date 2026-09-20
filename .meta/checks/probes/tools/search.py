"""`search.py`'s index and its benchmark (solorepo's DR-103).
"""
import contextlib
import dataclasses
import io
import pathlib
import tempfile

from checks.collect import META, ROOT, check
from checks.probes.harness import load_module

COMMENTED_PAGE = """---
slug: probe
# Rendered By A Comment
synonyms:
  - Beacon
---

# Probe

**Probe** is the page a commented frontmatter block used to rename.
"""


@check("search probes", pre=True)
def search_probes() -> list[str]:
    """`search.py` indexes the assertions and the wiki, ranks by Okapi BM25F over three fields, and meets the retrieval benchmark (solorepo's DR-103, solorepo's DR-194, solorepo's DR-195).

    The index built over `.meta/assertions/` and `wiki/` holds at least a
    hundred documents. Asked who is allowed to push to trunk, the top five
    hold Article 18, solorepo's DR-100 or solorepo's DR-072; asked for
    leftover work, they hold the Concept noticed-and-not-done or
    solorepo's DR-195, the Decision that minted that ingress alias. The
    eighteen-query benchmark passes at hit@5 of fifteen or better; its
    printing is silenced, because its return value is the verdict. And a
    result's dictionary carries `id`, `score` and `source_file`.

    A wiki page whose frontmatter carries a YAML comment is indexed under its
    Markdown heading rather than under that comment, and its summary is the
    lead definition sentence rather than the heading repeated.
    """
    search = load_module(META / "search.py", "search", register=False)
    problems = []
    index = search.build_index(META, ROOT)
    if len(index.docs) < 100:
        problems.append(f"search: index populated too few documents ({len(index.docs)})")

    results = index.search("who is allowed to push to trunk", top_k=5)
    ranked = [res.identifier for res in results]
    if not any(ident in ranked for ident in ("work:article/18", "work:decision/100", "work:decision/072")):
        problems.append("search: 'who is allowed to push to trunk' expected solorepo's Article 18, "
                        f"solorepo's DR-100, or solorepo's DR-072 in top 5, got {ranked}")
    leftover = [res.identifier for res in index.search("leftover work", top_k=5)]
    if "work:concept/noticed-and-not-done" not in leftover and "work:decision/195" not in leftover:
        problems.append(f"search: 'leftover work' expected noticed-and-not-done in top 5, got {leftover}")

    with contextlib.redirect_stdout(io.StringIO()):
        failed = search.run_benchmark(index)
    if failed != 0:
        problems.append(f"search: solorepo's DR-103 benchmark failed {failed} queries "
                        "below threshold (hit@5 >= 15/18)")

    if results:
        shown = results[0].to_dict()
        if not ("id" in shown and "score" in shown and "source_file" in shown):
            problems.append(f"search: SearchResult dictionary missing expected fields: {shown}")

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "wiki").mkdir()
        (root / "wiki" / "probe.md").write_text(COMMENTED_PAGE, encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()):
            _, payload, _ = search.build_index(root / ".meta", root).docs["wiki:probe"]
    if payload.get("name") != "Probe":
        problems.append("search: a commented frontmatter block renamed the page, expected "
                        f"'Probe', got {payload.get('name')!r}")
    if not payload.get("description", "").startswith("**Probe** is"):
        problems.append("search: expected the lead definition sentence as the summary, got "
                        f"{payload.get('description')!r}")
    return problems


@dataclasses.dataclass(frozen=True)
class FrontmatterCase:
    """One wiki page, and what the title field it is indexed under must and must not hold.

    Attributes:
        name: The case, as a failure names it.
        page: The whole Markdown of the page, written to `wiki/solorepo/probe.md`.
        indexed: Words the title field must hold, each tokenized before it is read.
        ignored: Words the title field must not hold, tokenized the same way.
        body: A word the body field must hold, or None where the case does not say.
    """

    name: str
    page: str
    indexed: tuple[str, ...] = ()
    ignored: tuple[str, ...] = ()
    body: str | None = None


LEAD = "# Probe\n\n**Probe** is a page a probe wrote.\n\nA paragraph the body holds.\n"
"""The Markdown every `FrontmatterCase` page carries below its frontmatter, so that only the block varies."""

FRONTMATTER_CASES = (
    FrontmatterCase(
        "a declared synonym beside a second list key",
        "---\nslug: probe\nsynonyms:\n  - Beacon\nsee_also:\n  - Lighthouse\n---\n\n" + LEAD,
        indexed=("Beacon",),
        ignored=("Lighthouse",),
        body="paragraph",
    ),
    FrontmatterCase(
        "synonyms that is not a list",
        "---\nslug: probe\nsynonyms: Beacon\n---\n\n" + LEAD,
        ignored=("Beacon",),
    ),
    FrontmatterCase(
        "a block that will not parse as YAML",
        "---\nslug: probe\nsynonyms: [Beacon\n---\n\n" + LEAD,
        ignored=("Beacon",),
        body="paragraph",
    ),
    FrontmatterCase(
        "no frontmatter at all",
        LEAD,
        body="paragraph",
    ),
)


@check("search frontmatter", pre=True)
def search_frontmatter_probes() -> list[str]:
    """A wiki page's title field takes the `synonyms` it declares and no other frontmatter list (solorepo's DR-103).

    Each case writes one page into a tree of its own and reads back the tokens
    `search.py` indexed it under. A declared synonym is in the title field,
    which is the highest weight the index carries; an item of a list under any
    other key is not, and neither is a `synonyms` that is not a list. That is
    the shape the gate reads out of the same block, and a word either reader
    counts alone is a word the two disagree about. A block that will not parse
    is dropped whole, and the page below it is indexed either way.
    """
    search = load_module(META / "search.py", "search", register=False)
    problems: list[str] = []
    for case in FRONTMATTER_CASES:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            page = root / "wiki" / "solorepo" / "probe.md"
            page.parent.mkdir(parents=True)
            page.write_text(case.page, encoding="utf-8")
            index = search.build_index(root / ".meta", root)
        fields = index.doc_field_tokens.get("wiki:probe")
        if fields is None:
            problems.append(f"search frontmatter: {case.name}: the page was not indexed")
            continue
        title = set(fields["title"])
        for word in case.indexed:
            if not set(search.tokenize(word)) <= title:
                problems.append(f"search frontmatter: {case.name}: expected '{word}' in the "
                                f"title field, got {fields['title']}")
        for word in case.ignored:
            if set(search.tokenize(word)) & title:
                problems.append(f"search frontmatter: {case.name}: '{word}' reached the title "
                                f"field, which only a declared synonym does, got {fields['title']}")
        if case.body and not set(search.tokenize(case.body)) <= set(fields["body"]):
            problems.append(f"search frontmatter: {case.name}: expected '{case.body}' in the "
                            f"body field, got {fields['body']}")
    return problems
