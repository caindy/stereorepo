"""What the repository writes down about itself, held to its readers' form (stereorepo's DR-209).

The knowledge Knowledge Management governs is one subject in three containers,
and each of these probes is over one of them: a history log parsed for its
entries and the Evidence they name (stereorepo's DR-171), a withdrawn Decision of the
record asked for the reason its `WITHDRAWN` status owes under
`.meta/work/decisions.yaml`, and the authoring tool that scaffolds a wiki page,
which is a probe over the wiki's form and not over a tool beside the gate
(stereorepo's DR-187). The wiki checks themselves are probed in
`checks/probes/wiki.py`.
One further probe is over the form the prose in all three containers carries:
the possessive that marks a citation as stereorepo's rather than a portfolio's
own (stereorepo's DR-121, stereorepo's DR-132).
Each check is run against strings and stand-in pages rather than the tree, so a
case is one fixture and one expectation, and a failure names the case. The
steps register here rather than beside the checks they exercise, because the
gate over assertions should not take its imports from a test suite
(stereorepo's DR-150).
"""
import collections
import contextlib
import io
import types

from checks import citations, files, graph
from checks.collect import META, ROOT, check
from checks.probes.harness import load_module

WithdrawnCase = collections.namedtuple("WithdrawnCase", "name number decision refused")
"""One Decision put to `graph.withdrawn_decisions`: `number`, the last segment of its id; `decision`, its fields; `refused`, whether the check must name it."""

REFUSAL = "status is WITHDRAWN but lacks 'withdrawn_because'"
"""What `graph.withdrawn_decisions` says of a withdrawal that gives no reason."""


@check("history probes", pre=True)
def history_probes() -> list[str]:
    """`files.history_entries_of` reads a history log's entries and the Evidence they name as `meta history evidence` needs them (stereorepo's DR-171).

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


@check("wikisplain probes", pre=True)
def wikisplain_probes() -> list[str]:
    """`.meta/wikisplain.py` slugifies a title, formats a MOS:LEAD lead, finds a duplicate, refuses a forbidden synonym, and scaffolds a page that passes its own verification (stereorepo's DR-187, stereorepo's DR-231).

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
    re-slugifying the title, so the two can diverge without false-positiving;
    and `cli.main`, which is where the tree the tool reads is
    resolved rather than passed: `--check-duplicate` on a concept the wiki and
    the vocabulary both hold, and a scaffold whose `--synonyms` name an avoided
    word. Each must exit 1, and the second is given `--force` and `--dry-run`,
    so it is refused for the avoid list rather than for the collision and
    nothing is written. Their output is captured, because the gate reads this
    process's stdout for A21's shapes. The tree-reading cases hold only while
    `wiki/stereorepo/` holds the pages the tool links a new page to by default
    and the vocabulary holds `work:concept/issue`.
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
    avoided = wikisplain.avoided_synonyms("issue", ["Ticket", "unit of work"], root=ROOT)
    if [a["synonym"] for a in avoided] != ["Ticket"]:
        problems.append(f"avoided_synonyms: expected 'Ticket' alone to be refused, got {avoided!r}")
    content = wikisplain.generate_page(
        wikisplain.Page(title="Test Wiki Concept", context="stereorepo",
                        definition="a synthetic concept for gate validation"),
        root=ROOT,
    )
    verif = wikisplain.verify_page(content, "wiki/stereorepo/test-wiki-concept.md", root=ROOT)
    if verif:
        problems.append(f"verify_page: generated page produced validation warnings: {verif!r}")
    filed = wikisplain.generate_page(
        wikisplain.Page(title="Test Wiki Concept", slug="test-filed-elsewhere", context="stereorepo",
                        definition="a synthetic concept for gate validation"),
        root=ROOT,
    )
    if "\nslug: test-filed-elsewhere\n" not in filed:
        problems.append(f"generate_page: a Page filed under its own slug declared another: {filed[:120]!r}")
    self_ref = wikisplain.generate_page(
        wikisplain.Page(title="Test Wiki Concept", slug="test-filed-elsewhere", context="stereorepo",
                        definition="a synthetic concept for gate validation",
                        body="See [[test-filed-elsewhere]] for detail."),
        root=ROOT,
    )
    found = wikisplain.verify_page(self_ref, "wiki/stereorepo/test-filed-elsewhere.md", root=ROOT)
    if found:
        problems.append(
            f"verify_page: self-reference under a custom --slug false-positived: {found!r}"
        )
    problems.extend(cli_probes(wikisplain))
    return problems


def cli_probes(wikisplain: types.ModuleType) -> list[str]:
    """`cli.main` refusing a collision and an avoided synonym, each read from its exit code with its output captured (stereorepo's DR-187, stereorepo's DR-231)."""
    problems = []
    for name, argv in (
        ("a concept the wiki and the vocabulary both hold",
         ["Knowledge Management", "--check-duplicate"]),
        ("a synonym on the concept's avoid list, past --force",
         ["Issue", "--slug", "issue", "--synonyms", "ticket", "--force", "--dry-run"]),
    ):
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            code = wikisplain.main(argv)
        if code != 1:
            problems.append(f"cli.main: {name}: expected exit 1, got {code} saying {said.getvalue()!r}")
    return problems


@check("wikisplain argv probes", pre=True)
def wikisplain_argv_probes() -> list[str]:
    """`wikisplain.main` joins shell-split concepts and scaffolds beneath its resolved repository root.

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
        target = root / "wiki" / "stereorepo" / "command-root-concept.md"
        if rc != 0:
            problems.append(f"wikisplain argv: expected a successful scaffold, got {rc}")
        if not target.is_file():
            problems.append(f"wikisplain argv: expected scaffold at {target}, but it was not written")
    return problems


@check("wikisplain default root probes", pre=True)
def wikisplain_default_root_probes() -> list[str]:
    """`find_duplicates`, `extract_known_concepts` and `cli.main`, called with
    no `root`, read this repository.

    Every other probe over these functions passes `root=ROOT` explicitly, or
    points `cli.ROOT` at a temporary directory before calling, so the default
    `lib.wikisplain.ROOT` the command line actually relies on is exercised by
    nothing else in the gate — the gap that let a package
    split leave the default wrong, silently, until a later change corrected
    it. Called with no `root` at all, `find_duplicates` must still find the
    wiki's own Knowledge Management page and `extract_known_concepts` must
    still know its slug; `cli.main` takes no `root` parameter at all, so
    `--check-duplicate` on the same concept exercises the same default by
    construction. None of the three would pass were the default one directory
    off, since neither the wiki nor the vocabulary exists under
    `.meta/lib/wikisplain` or above the repository. The cheapest of the four,
    holding independently of whether the calls above still exist to make: the
    default itself is a directory holding `wiki/` and `.meta/assertions/`,
    true of the repository and of nothing above or below it.
    """
    wikisplain = load_module(META / "wikisplain.py", "wikisplain")
    problems = []
    default_root = wikisplain.cli.ROOT
    if not (default_root / "wiki").is_dir() or not (default_root / ".meta" / "assertions").is_dir():
        problems.append(
            f"wikisplain default root: expected a directory holding wiki/ and "
            f".meta/assertions/, got {default_root}"
        )
    dups = wikisplain.find_duplicates("Knowledge Management")
    if not any(d["source"] == "wiki" for d in dups):
        problems.append(
            f"find_duplicates: no root given: expected a wiki duplicate for "
            f"'Knowledge Management', got {dups!r}"
        )
    known = wikisplain.extract_known_concepts()
    if known.get("knowledge-management") != "knowledge-management":
        problems.append(
            f"extract_known_concepts: no root given: expected 'knowledge-management' "
            f"known, got {known.get('knowledge-management')!r}"
        )
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        code = wikisplain.main(["Knowledge Management", "--check-duplicate"])
    if code != 1:
        problems.append(
            f"cli.main: no root given: expected exit 1 for 'Knowledge Management', "
            f"got {code} saying {said.getvalue()!r}"
        )
    return problems


@check("citation form probes", pre=True)
def citation_form_probes() -> list[str]:
    """`citations.FOREIGN` holds every character exact but a leading `S` or `s`.

    `cited_decisions` splits a citation the possessive marks as foreign from one
    left over for the bare scan: `FOREIGN.sub("", text)` followed by `DR`'s own
    `findall`. A sentence-initial possessive citation must leave nothing for the
    bare scan to find, a genuinely bare one must still read as bare, and an
    all-uppercase possessive must remain bare, proving that only the leading
    letter is widened. The number is spelled from `count` rather than typed,
    because `DR-` followed by digits in a file a portfolio copies is a citation
    as far as `cited decisions` is concerned, and this one is a fixture
    (stereorepo's DR-124).
    """
    problems = []
    count = 999
    for label, text, want in (
        ("a sentence-initial possessive", f"Stereorepo's DR-{count:03d} is a target.", set()),
        ("a genuinely bare citation", f"DR-{count:03d} is a render target.", {str(count)}),
        ("an all-uppercase possessive", f"STEREOREPO'S DR-{count:03d} is a render target.",
         {str(count)}),
    ):
        found = set(citations.DR.findall(citations.FOREIGN.sub("", text)))
        if found != want:
            problems.append(f"citation form: {label} read bare as {found!r}, not {want!r}")
    return problems


@check("concept duplicate id probes", pre=True)
def concept_duplicate_id_probes() -> list[str]:
    """`files.duplicate_concept_ids` detects duplicate concept IDs in a concept_set with exact line numbers (stereorepo's DR-190)."""
    import pathlib
    import tempfile

    problems = []
    with tempfile.TemporaryDirectory() as tmpdir:
        test_yaml = pathlib.Path(tmpdir) / "vocab.yaml"
        test_yaml.write_text(
            "concept_set:\n"
            "  - id: work:concept/first\n"
            "    pref_label: First\n"
            "  - id: work:concept/second\n"
            "    pref_label: Second\n"
            "  - id: work:concept/first\n"
            "    pref_label: First Duplicate\n",
            encoding="utf-8",
        )
        findings = files.duplicate_concept_ids([test_yaml])
        if len(findings) != 1:
            problems.append(f"concept duplicate id probes: expected 1 finding, got {len(findings)}: {findings}")
        elif "concept 'work:concept/first' declared twice in concept_set (first at line 2)" not in findings[0]:
            problems.append(f"concept duplicate id probes: unexpected finding text {findings[0]}")

        clean_yaml = pathlib.Path(tmpdir) / "clean.yaml"
        clean_yaml.write_text(
            "concept_set:\n"
            "  - id: work:concept/alpha\n"
            "    pref_label: Alpha\n"
            "  - id: work:concept/beta\n"
            "    pref_label: Beta\n",
            encoding="utf-8",
        )
        clean_findings = files.duplicate_concept_ids([clean_yaml])
        if clean_findings:
            problems.append(f"concept duplicate id probes: expected 0 findings on clean file, got {clean_findings}")
    return problems


@check("operational artifact probes", pre=True)
def operational_artifact_probes() -> list[str]:
    """`graph.operational_artifacts` enforces completeness of .meta/ operational files."""
    import pathlib
    import tempfile

    problems = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmproot = pathlib.Path(tmpdir)
        meta_dir = tmproot / ".meta"
        lib_dir = meta_dir / "lib" / "sub"
        checks_dir = meta_dir / "checks" / "sub"
        for d in (meta_dir, lib_dir, checks_dir):
            d.mkdir(parents=True, exist_ok=True)

        (meta_dir / "tool.py").write_text("# tool\n", encoding="utf-8")
        (lib_dir / "util.py").write_text("# util\n", encoding="utf-8")
        (checks_dir / "check_step.py").write_text("# check\n", encoding="utf-8")
        (lib_dir / "generated.py").write_text("# generated\n", encoding="utf-8")
        (checks_dir / "fixture.py").write_text("# fixture\n", encoding="utf-8")

        structure_file = tmproot / "structure.yaml"
        structure_file.write_text(
            "excluded_paths:\n"
            "  - .meta/lib/sub/generated.py\n",
            encoding="utf-8",
        )

        index = {
            "work:artifact/tool": (
                "Artifact",
                {"path": ".meta/tool.py"},
                "structure.yaml",
            ),
            "work:artifact/util": (
                "Artifact",
                {"path": ".meta/lib/sub/util.py"},
                "structure.yaml",
            ),
        }

        findings = graph.operational_artifacts(
            index, structure_path=structure_file, root=tmproot
        )
        suffix = ": operational file is neither asserted as an Artifact nor excluded"
        expected = [
            f".meta/checks/sub/check_step.py{suffix}",
            f".meta/checks/sub/fixture.py{suffix}",
        ]
        if findings != expected:
            problems.append(
                f"operational artifact probes: expected {expected!r}, got {findings!r}"
            )

        index["work:artifact/check"] = (
            "Artifact",
            {"path": ".meta/checks/sub/check_step.py"},
            "structure.yaml",
        )
        index["work:artifact/fixture"] = (
            "Artifact",
            {"path": ".meta/checks/sub/fixture.py"},
            "structure.yaml",
        )
        clean_findings = graph.operational_artifacts(
            index, structure_path=structure_file, root=tmproot
        )
        if clean_findings:
            problems.append(
                f"operational artifact probes: expected clean run, got {clean_findings!r}"
            )

    return problems



