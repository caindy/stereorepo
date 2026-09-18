# History

No entry yet. The first defect fixed in this module writes one in the form
below, and `uv run gate evidence` holds every entry to it: an entry says what
failed and what the change established, never what changed, and it names the
test that would fail if the change were undone. When that test is gone the
entry is stale and goes with it.

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Evidence: `tests/test_example.py::<the test that fails if this is undone>`
-->
