"""The shell's view of a command line: what it would expand, substitute, escape or chain before the program saw it, and the words that survive.

The grammar in `grammar` reads words, and a word is only what the shell would
hand the program unchanged. So the characters the shell acts on, the ones that
still act inside double quotes, and the ones that chain two commands are named
here as sets, and a command line is walked with its quoting tracked, so that a
`;` inside a quoted heredoc is text and one outside it is a second command.
"""
import re
from collections.abc import Iterator

# Characters the shell acts on. None of them may appear unquoted; inside quotes
# bash acts on almost nothing, and `EXPANDS` is the almost.
SHELL = set(';&|<>$`*?[]{}()~!#\\"\n')


QUOTES = {"'", '"'}

# Characters that still expand inside double quotes per bash reference.
# Double quotes preserve literal character values except for $, `, \, and !.
EXPANDS = set("$`\\!")


# Characters representing command or variable substitutions ($ and `).
# Substitutions produce dynamic output and cannot be derived into literal single quotes.
SUBSTITUTES = set("$`")


# Characters escaped by backslash inside double quotes per bash reference.
ESCAPES = set('$`"\\\n')


# Shell operators that separate commands or perform redirection.
# Truncation at chain operators preserves the leading command for nearest-form derivation.
CHAINS = set(";&|<>\n")


# Matches trailing file descriptor digits preceding redirection operators.
DESCRIPTOR = re.compile(r"(?:^|\s)\d+$")


class Lexer:
    """The state of a walk over one command line: the words so far, the word being built, the quote open, whether the current word was quoted, and whether a backslash is pending."""

    def __init__(self, literal: bool) -> None:
        self.literal = literal
        self.words: list[str] = []
        self.word: list[str] = []
        self.quote = ""
        self.seen = False
        self.escaped = False

    def escape(self, ch: str) -> None:
        """The character after a backslash inside double quotes: one of `ESCAPES` stands alone, a newline is dropped, anything else keeps its backslash."""
        self.escaped = False
        if ch not in ESCAPES:
            self.word.append("\\")
        if ch != "\n":
            self.word.append(ch)

    def quoted(self, ch: str) -> str | None:
        """A character inside quotes: the closing quote, a character double quotes still expand, or text; the refusal where an expansion is not `literal`."""
        if ch == self.quote:
            self.quote = ""
        elif self.quote == '"' and ch in EXPANDS:
            if not self.literal or ch in SUBSTITUTES:
                return f"`{ch}`"
            if ch == "\\":
                self.escaped = True
            else:
                self.word.append(ch)
        else:
            self.word.append(ch)
        return None

    def bare(self, ch: str) -> str | None:
        """A character outside quotes: a quote opens, whitespace ends a word, one of `SHELL` is refused, and anything else is text."""
        if ch in QUOTES:
            self.quote, self.seen = ch, True
        elif ch in SHELL:
            return f"`{ch!r}`" if ch == "\n" else f"`{ch}`"
        elif ch.isspace():
            self.end_word()
        else:
            self.word.append(ch)
        return None

    def end_word(self) -> None:
        """Close the word being built, keeping an empty one that was quoted."""
        if self.word or self.seen:
            self.words.append("".join(self.word))
        self.word, self.seen = [], False


def words_of(text: str, literal: bool = False) -> list[str] | str:
    """Tokenize a single shell command on whitespace respecting quoting rules.

    Parameters:
        text: Command string to tokenize.
        literal: When True, preserves escape sequences and literal characters
            within double quotes for derivation rather than refusing expansion triggers.

    Returns:
        list[str] | str: List of tokenized string arguments if parsing succeeds;
        otherwise an explanatory string indicating which active shell expansion
        character or unclosed quote triggered refusal.

    A backslash inside a double quote escapes one of `ESCAPES` and is dropped,
    taking a newline with it; before anything else it stands for itself, which
    is what `\\s` and `\\b` want of it.
    """
    lexer = Lexer(literal)
    for ch in text:
        if lexer.escaped:
            lexer.escape(ch)
            continue
        refused = lexer.quoted(ch) if lexer.quote else lexer.bare(ch)
        if refused:
            return refused
    if lexer.quote:
        return "an unclosed quote"
    lexer.end_word()
    return lexer.words


def unquoted(text: str) -> Iterator[tuple[int, str]]:
    """Iterate through unquoted characters and their positions in a shell command.

    Yields indices and characters that appear outside single or double quote boundaries.

    Parameters:
        text: Shell command text to scan.

    Yields:
        tuple[int, str]: Zero-indexed position and character for unquoted tokens.
    """
    quote = ""
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in QUOTES:
            quote = ch
        else:
            yield i, ch


def partition_unquoted(text: str, marker: str) -> tuple[str, str, str]:
    """Partition a command string on the first unquoted occurrence of a marker.

    Parameters:
        text: Shell command text to partition.
        marker: Substring marker to locate outside quoted spans.

    Returns:
        tuple[str, str, str]: Three-tuple of `(head, marker, tail)`. If marker is
        not found unquoted, returns `(text, "", "")`.
    """
    for i, _ in unquoted(text):
        if text.startswith(marker, i):
            return text[:i], marker, text[i + len(marker):]
    return text, "", ""


def before_operator(text: str) -> str:
    """Extract command text preceding the first unquoted chain or redirection operator.

    Trailing file descriptor digits directly attached to redirection operators (e.g. `2>`)
    are stripped to avoid corrupting the trailing argument of the preceding command.

    Parameters:
        text: Raw shell command string.

    Returns:
        str: Truncated command text prior to operators, or original text if no operator is present.
    """
    for i, ch in unquoted(text):
        if ch in CHAINS:
            head = text[:i]
            if ch in "<>":
                descriptor = DESCRIPTOR.search(head)
                if descriptor:
                    head = head[:descriptor.start()]
            return head
    return text


def requote(word: str) -> str:
    """Enclose a command token in single quotes unless already safe without quotes.

    Parameters:
        word: Command token to format.

    Returns:
        str: Quoted or unquoted representation of the token for bash interpretation.
    """
    return word if word and not (set(word) & SHELL) and not any(c.isspace() for c in word) else f"'{word}'"
