"""Probes for schema slot citations in durable prose against LinkML declarations.

Validates that `cited_schema_slots` correctly identifies invalid qualified slot citations,
explicit slot phrases, and document-scoped former slot names, while verifying git diff
parsing of deleted schema slots and CouldNotRun fallback behaviour. Probes sit in
their own module under `.meta/checks/probes/` by subject under test (solorepo's DR-209,
organizing probes into per-subject modules). Verifies the citation subject's slot checks
under the gate's per-subject decomposition (solorepo's DR-150).

History in citations.history.md (solorepo's DR-171).
"""
import pathlib
import tempfile
from typing import Any

from checks.citations import slots
from checks.collect import ROOT, CouldNotRun, check


class _FakeClass:
    """Stand-in class definition carrying tree_root state for SchemaView probes."""

    def __init__(self, tree_root: bool = False) -> None:
        self.tree_root = tree_root


class _FakeSlot:
    """Stand-in induced slot definition carrying class range for SchemaView probes."""

    range = "Article"


class _FakeSchemaView:
    """Minimal LinkML SchemaView stand-in resolving Article container slots."""

    def all_classes(self) -> dict[str, Any]:
        """Return declared probe classes keyed by identifier."""
        return {"Ontology": _FakeClass(tree_root=True), "Article": _FakeClass()}

    def class_slots(self, cls: str) -> list[str]:
        """Return container slots for root ontology."""
        if cls == "Ontology":
            return ["articles"]
        return []

    def induced_slot(self, key: str, root: str) -> Any:
        """Resolve slot range for container slot key."""
        if key == "articles" and root == "Ontology":
            return _FakeSlot()
        return None


def _probe_qualified_and_former(indices: slots.SlotIndices, rel: str) -> list[str]:
    """Test qualified slot citations and document-scoped former slot name checks."""
    problems: list[str] = []

    violating_qualified = ["Check Article.origin before proceeding."]
    res = slots.check_prose_spans(violating_qualified, rel, indices, {"Article"})
    if not any("Article.origin" in p and "not declared on class Article" in p for p in res):
        problems.append(
            f"qualified slot: expected invalid slot error for 'Article.origin', got {res!r}"
        )

    passing_qualified = ["Check Article.falsifier before proceeding."]
    res = slots.check_prose_spans(passing_qualified, rel, indices, {"Article"})
    if res:
        problems.append(
            f"qualified slot: expected no errors for 'Article.falsifier', got {res!r}"
        )

    with_yaml_filename = ["In work/disciplines.yaml, Article.origin was changed."]
    res = slots.check_prose_spans(with_yaml_filename, rel, indices, {"Article"})
    if not any("Article.origin" in p for p in res):
        problems.append(
            f"qualified slot: dot in 'disciplines.yaml' destroyed citation span, got {res!r}"
        )

    hedged_qualified = ["In solorepo's DR-087, Article.origin was removed from schema."]
    res = slots.check_prose_spans(hedged_qualified, rel, indices, {"Article"})
    if res:
        problems.append(f"qualified slot: hedged citation should be ignored, got {res!r}")

    violating_former = ["The Charter held an Article whose prose referred to `origin`."]
    res = slots.check_prose_spans(violating_former, rel, indices, {"Article", "Discipline"})
    if (
        len(res) != 1
        or "removed from Article" not in res[0]
        or "declared on no current schema class" not in res[0]
        or "Discipline" in res[0]
    ):
        problems.append(
            f"former slot: expected single finding naming Article for '`origin`', got {res!r}"
        )

    unrelated_class = ["A discipline assertion mentions `origin`."]
    res = slots.check_prose_spans(unrelated_class, rel, indices, {"Discipline"})
    if res:
        problems.append(
            f"former slot: unasserted class should not flag '`origin`', got {res!r}"
        )

    repeated_former = ["Both `origin` and `origin` appear in this clause."]
    res = slots.check_prose_spans(repeated_former, rel, indices, {"Article"})
    if len(res) != 1:
        problems.append(
            f"former slot: expected deduplication for multiple '`origin`', got {res!r}"
        )

    unscoped_former = ["A markdown file mentions `origin` as plain prose."]
    res = slots.check_prose_spans(unscoped_former, rel, indices, set())
    if res:
        problems.append(f"former slot: unscoped file should not flag '`origin`', got {res!r}")

    return problems


def _probe_phrases_and_seams(indices: slots.SlotIndices, rel: str) -> list[str]:
    """Test explicit slot phrases and CouldNotRun attribution under seam inputs."""
    problems: list[str] = []

    violating_phrase = ["Check `origin` on Article."]
    res = slots.check_prose_spans(violating_phrase, rel, indices, set())
    if not any("`origin` on Article" in p for p in res):
        problems.append(
            f"explicit phrase: expected error for '`origin` on Article', got {res!r}"
        )

    violating_unqualified = ["Check the `nonsense_xyz` slot."]
    res = slots.check_prose_spans(violating_unqualified, rel, indices, set())
    if not any("`nonsense_xyz` slot" in p and "not declared in schemas" in p for p in res):
        problems.append(f"explicit phrase: expected error for undeclared slot, got {res!r}")

    hedged_subclause = [
        "It has a `statement` slot, a line naming a test that would fail, "
        "and `origin` on Article."
    ]
    res = slots.check_prose_spans(hedged_subclause, rel, indices, {"Article"})
    if not any("`origin` on Article" in p for p in res):
        problems.append(
            f"hedged subclause: comma-delimited clause should isolate hedge, got {res!r}"
        )

    custom_outcome = slots.cited_schema_slots(
        views=[], deleted=lambda: (None, "custom failure cause from seam")
    )
    if (
        not isinstance(custom_outcome, CouldNotRun)
        or custom_outcome.why != "custom failure cause from seam"
    ):
        problems.append(
            f"could not run: expected passthrough reason, got {custom_outcome!r}"
        )

    fallback_outcome = slots.cited_schema_slots(
        views=[], deleted=lambda: (None, None)
    )
    expected_fallback = "git history could not be read to derive former schema slots"
    if (
        not isinstance(fallback_outcome, CouldNotRun)
        or fallback_outcome.why != expected_fallback
    ):
        problems.append(
            f"could not run: expected fallback reason, got {fallback_outcome!r}"
        )

    raw_deleted_sample = {"Article": {"statement", "origin"}}
    all_slots_sample = {"statement"}
    class_slots_sample: dict[str, set[str]] = {"Article": set()}
    filtered_former = slots._former_slots(
        raw_deleted_sample, class_slots_sample, all_slots_sample
    )
    if filtered_former != {"Article": {"origin"}}:
        problems.append(
            f"former slot filter: expected 'statement' filtered out, got {filtered_former!r}"
        )

    cross_class_deleted = {"Actor": {"persona", "origin"}}
    cross_class_slots = {"Actor": set(), "Personality": {"persona"}}
    cross_all_slots = {"persona"}
    cross_filtered = slots._former_slots(
        cross_class_deleted, cross_class_slots, cross_all_slots
    )
    if cross_filtered != {"Actor": {"origin"}}:
        problems.append(
            "former slot cross-class filter: expected 'persona' filtered out, "
            f"got {cross_filtered!r}"
        )

    return problems


def _probe_diff_parsing() -> list[str]:
    """Test parsing of git diff hunks with function context into class-scoped deleted slots."""
    diff_fixture = (
        "commit 06dcfa8e1234567890abcdef1234567890abcdef\n"
        "diff --git a/.meta/work/disciplines.yaml b/.meta/work/disciplines.yaml\n"
        "@@ -130,24 +124,56 @@ classes:\n"
        "   Article:\n"
        "     is_a: WorkEntity\n"
        "     slots:\n"
        "       - statement\n"
        "       - enforces\n"
        "       - checked_by\n"
        "-      - origin\n"
        "+      - example\n"
        "+      - falsifier\n"
        "@@ -200,10 +200,10 @@ classes:\n"
        "-  DeletedClass:\n"
        "-    slots:\n"
        "-      - retired_slot\n"
    )
    parsed = slots._parse_deleted_slots(diff_fixture)
    expected = {"Article": {"origin"}, "DeletedClass": {"retired_slot"}}
    if parsed != expected:
        return [f"_parse_deleted_slots: expected {expected!r}, got {parsed!r}"]
    return []


def _probe_yaml_comment_scanning(indices: slots.SlotIndices) -> list[str]:
    """Test that _scan_durable_file inspects YAML comment blocks as prose."""
    problems: list[str] = []
    fake_views = [_FakeSchemaView()]
    with tempfile.TemporaryDirectory(dir=ROOT) as tmpdir:
        fixture_path = pathlib.Path(tmpdir) / "fixture.yaml"
        fixture_path.write_text(
            "articles:\n"
            "  - statement: Valid scalar prose.\n"
            "# `origin` is the receipt\n",
            encoding="utf-8",
        )
        res = slots._scan_durable_file(fixture_path, fake_views, indices)
        if (
            len(res) != 1
            or "removed from Article" not in res[0]
            or "declared on no current schema class" not in res[0]
        ):
            problems.append(
                "_scan_durable_file comment scan: expected error for '`origin`' in comment, "
                f"got {res!r}"
            )
    return problems


@check("cited schema slot probes", pre=True)
def cited_schema_slot_probes() -> list[str]:
    """Verify that schema slot citation checking resolves valid and invalid forms correctly.

    Pins qualified `Class.slot` citations, explicit slot phrases, former slot scoping,
    YAML comment scanning in durable files, and `CouldNotRun` cause attribution.

    Returns:
        list[str]: Findings naming cases whose outcome did not match expectations.
    """
    class_slots = {
        "Article": {"statement", "enforces", "checked_by", "example", "falsifier"},
        "Discipline": {"name", "statement", "judgement"},
    }
    all_slots = {
        "statement", "enforces", "checked_by", "example", "falsifier",
        "name", "judgement", "description",
    }
    former_slots = {"Article": {"origin"}}
    indices = slots.SlotIndices(
        class_slots=class_slots, all_slots=all_slots, former_slots=former_slots
    )
    rel = "test.md"

    return (
        _probe_qualified_and_former(indices, rel)
        + _probe_phrases_and_seams(indices, rel)
        + _probe_diff_parsing()
        + _probe_yaml_comment_scanning(indices)
    )

