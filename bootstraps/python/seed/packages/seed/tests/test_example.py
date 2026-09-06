"""The example module's tests, which are also what `example.history.md` cites."""

from seed.example import lines


def test_blank_lines_are_dropped() -> None:
    assert lines("a\n\n   \nb") == ["a", "b"]


def test_surrounding_whitespace_is_trimmed() -> None:
    assert lines("  a\t\n b ") == ["a", "b"]
