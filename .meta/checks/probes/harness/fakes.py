"""A wiki page answered from a string.
"""
import pathlib

from checks.collect import ROOT


class FakeWikiPath:
    """A wiki page as the wiki checks read one: a repository-relative path whose text is given rather than read from disk.

    Answers the `pathlib.Path` surface `files.wikilinks`,
    `files.wiki_lead_paragraphs` and `files.ubiquitous_language_wiki_parity`
    use — name, stem, suffix, parts, parent, `relative_to`, `read_text` — and
    nothing else, so a case is one string and one path rather than a file.
    """

    def __init__(self, rel_str: str | pathlib.Path, text: str) -> None:
        self._path = ROOT / rel_str
        self._text = text

    @property
    def suffix(self) -> str:
        """The path's suffix, `.md` for a page."""
        return self._path.suffix

    @property
    def name(self) -> str:
        """The file name."""
        return self._path.name

    @property
    def stem(self) -> str:
        """The file name without its suffix, which is the page's slug."""
        return self._path.stem

    @property
    def parts(self) -> tuple[str, ...]:
        """The path's components."""
        return self._path.parts

    @property
    def parent(self) -> pathlib.Path:
        """The directory the page is in, which names its context."""
        return self._path.parent

    def is_symlink(self) -> bool:
        """Never a symlink."""
        return False

    def is_file(self) -> bool:
        """Always a file."""
        return True

    def read_text(self, encoding: str = "utf-8") -> str:
        """The page's text, as given."""
        return self._text

    def relative_to(self, other: pathlib.Path | str) -> pathlib.Path:
        """The path relative to `other`, as `pathlib.Path.relative_to` answers it."""
        return self._path.relative_to(other)

    def __str__(self) -> str:
        return str(self._path)
