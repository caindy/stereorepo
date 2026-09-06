#![doc = include_str!("example.overview.md")]
#![doc = include_str!("example.rationale.md")]
#![doc = include_str!("example.history.md")]

/// The non-empty lines of `text`, each trimmed.
///
/// ```
/// use seed::example::lines;
///
/// assert_eq!(lines(" a \n\n b "), ["a", "b"]);
/// ```
#[must_use]
pub fn lines(text: &str) -> Vec<&str> {
    text.lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::lines;

    #[test]
    fn blank_lines_are_dropped() {
        assert_eq!(lines("a\n\n   \nb"), ["a", "b"]);
    }

    #[test]
    fn surrounding_whitespace_is_trimmed() {
        assert_eq!(lines("  a\t\n b "), ["a", "b"]);
    }
}
