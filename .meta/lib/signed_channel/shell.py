"""The shell reading: a command line taken apart into segments behind its quotes, heredocs and interpreters, and the program each segment runs once its prefix of assignments and options is past.
"""
import os
from collections.abc import Iterator

from lib.signed_channel import tables


def bodies_after(command: str, index: int,
                 pending: list[tuple[str, bool, bool, int]]
                 ) -> tuple[int, list[tuple[int, bool, str]]]:
    """Collect the heredoc bodies that begin at an offset, one per opener awaiting one.

    Parameters:
        command: Raw command string from tool input.
        index: Offset of the first character after the newline ending the line
            the openers were written on.
        pending: Each opener awaiting a body, as `(delimiter, dashed, expands,
            offset)`, in the order the openers were written.

    Returns:
        tuple[int, list[tuple[int, bool, str]]]: The offset the shell text
        resumes at, and each body paired with whether the shell expands it and
        with the offset of the `<<` that opened it.

    A body runs to a line holding its delimiter alone, leading tabs ignored where
    the opener was written `<<-`. A delimiter that never arrives takes the rest of
    the command with it.
    """
    taken = []
    for word, dashed, expands, offset in pending:
        start = index
        while index < len(command):
            stop = command.find("\n", index)
            line = command[index:] if stop < 0 else command[index:stop]
            index = len(command) if stop < 0 else stop + 1
            if (line.lstrip("\t") if dashed else line).rstrip("\r") == word:
                break
        taken.append((offset, expands, command[start:index]))
    return index, taken


def without_heredocs(command: str) -> tuple[str, list[tuple[int, bool, str]]] | None:
    """Lift every heredoc body out of a command line, keeping each body's opener.

    Parameters:
        command: Raw command string from tool input.

    Returns:
        tuple[str, list[tuple[int, bool, str]]] | None: The shell text with every
        heredoc body removed, and each body paired with whether the shell expands
        it and with the offset in that text of the `<<` that opened it; None
        where the command holds an unclosed quote or a `<<` whose delimiter this
        hook cannot parse.

    A heredoc body is data the segment before it carries, so lifting it out keeps
    its lines from being read as commands of their own. `<<<` is a here-string,
    whose word is on the line already, and is left where it stands.
    """
    text, bodies, pending = "", [], []
    quote, index = "", 0
    while index < len(command):
        char = command[index]
        if char == "\\" and quote != "'" and index + 1 < len(command):
            text, index = text + command[index:index + 2], index + 2
            continue
        if quote:
            text, index = text + char, index + 1
            quote = "" if char == quote else quote
            continue
        if char in tables.QUOTES:
            text, quote, index = text + char, char, index + 1
            continue
        if command.startswith("<<<", index):
            text, index = text + "<<<", index + 3
            continue
        if command.startswith("<<", index):
            opener = tables.HEREDOC.match(command, index)
            if opener is None:
                return None
            pending.append((opener["word"], opener[0].startswith("<<-"),
                            opener["quote"] == "", len(text)))
            text, index = text + opener[0], opener.end()
            continue
        text, index = text + char, index + 1
        if char == "\n" and pending:
            index, taken = bodies_after(command, index, pending)
            bodies.extend(taken)
            pending = []
    return None if quote else (text, bodies)


def segments(text: str) -> Iterator[tuple[int, int, str]]:
    """Split shell text into the commands it runs, keeping each one's offsets.

    Parameters:
        text: Shell text with its heredoc bodies already lifted out.

    Yields:
        tuple[int, int, str]: The start offset, the end offset, and the text of
        each command the line runs, separated at unquoted `tables.SEPARATORS`.
    """
    start, quote, index = 0, "", 0
    while index < len(text):
        char = text[index]
        if char == "\\" and quote != "'":
            index += 2
            continue
        if quote:
            quote = "" if char == quote else quote
            index += 1
            continue
        if char in tables.QUOTES:
            quote, index = char, index + 1
            continue
        if char in tables.SEPARATORS:
            yield start, index, text[start:index]
            while index < len(text) and text[index] in tables.SEPARATORS:
                index += 1
            start = index
            continue
        index += 1
    yield start, len(text), text[start:]


def past_prefix(prefix: tuple[frozenset[str], int], words: list[str], at: int) -> int:
    """Walk a transparent prefix's own words to the one naming the command it runs.

    Parameters:
        prefix: The prefix, as `tables.TRANSPARENT` pairs it: the options whose value is
            the word after them, and how many arguments of its own it takes.
        words: One segment's words, as `shlex` lexed them.
        at: The offset of the first word after the prefix.

    Returns:
        int: The offset of the word naming the program the prefix runs, or the
        end of the words where every one of them was consumed — which `env -S
        <line>` does, its option's value being the command line itself. An
        option this pairing does not name as taking a value is read as taking
        none, so a prefix written with one hides the command behind it the way
        an unlisted prefix does.
    """
    values, mine = prefix
    while at < len(words):
        word = words[at]
        if len(word) > 1 and word[0] in "-+":
            at += 2 if word in values else 1
            continue
        if mine:
            mine, at = mine - 1, at + 1
            continue
        return at
    return at


def program(words: list[str]) -> tuple[str | None, list[str]]:
    """Name the program a segment runs, and the arguments it runs it with.

    Parameters:
        words: One segment's words, as `shlex` lexed them.

    Returns:
        tuple[str | None, list[str]]: The word naming the program, after
        `os.path.expandvars`, and the words following it. A prefix of
        `tables.TRANSPARENT` execs the rest of its words rather than doing the work
        itself, so the walk carries on behind one, and behind any run of them.
        The name is None where no word of the segment names a program: either
        it runs none, or a prefix consumed every word behind it, which
        `runs_nothing` tells apart.
    """
    at = 0
    while at < len(words):
        if tables.ASSIGNMENT.match(words[at]):
            at += 1
            continue
        name = os.path.expandvars(words[at])
        prefix = tables.TRANSPARENT.get(name.rsplit("/", 1)[-1])
        if prefix is None:
            return name, words[at + 1:]
        at = past_prefix(prefix, words, at + 1)
    return None, []


def runs_nothing(words: list[str]) -> bool:
    """Judge whether a segment names no program because there is none to name.

    Parameters:
        words: One segment's words, as `shlex` lexed them.

    Returns:
        bool: True where the segment is empty or environment assignments alone,
        which are the two ways `program` names nothing because nothing runs.
        It also names nothing where a transparent prefix consumed every word
        behind it — `env -S <line>` hands `env` the command line as the value of
        an option, and `env --split-string=<line>` as part of one — and that is
        a command this hook failed to find rather than one that was never there.
    """
    return all(tables.ASSIGNMENT.match(word) for word in words)


def run_by(wrapper: str, arguments: list[str]) -> str | None:
    """The script an interpreter was given to run, which is its first argument naming one.

    Parameters:
        wrapper: The interpreter, named as `tables.WRAPPERS` spells it.
        arguments: The words following it.

    Returns:
        str | None: The first argument that is neither an option nor `uv`'s own
        `run` subcommand, or None where the interpreter was given none. Only
        that position names the program being run, so an argument written
        elsewhere on the line is a mention of a path rather than a call to it.
    """
    for at, word in enumerate(arguments):
        if word.startswith("-"):
            continue
        if at == 0 and word == "run" and wrapper in ("uv", "uvx"):
            continue
        return word
    return None


def shell_code(arguments: list[str]) -> str | None:
    """The command line a shell interpreter was handed to run.

    Parameters:
        arguments: The words following the interpreter.

    Returns:
        str | None: The first argument that is not an option, where an option
        before it held `c`; None where the interpreter was given no command line
        to run. Bash reads the command from the first non-option argument rather
        than from the word after `-c`, so an option written between the two — as
        `bash -c -x <command>` does — does not hide the command line from this
        hook. `c` is looked for in any run of short options, `-lc` and `-cx`
        alike, and `tables.OPTION_VALUES` names the short options whose own value
        follows them as a word.
    """
    taking, skip = False, False
    for word in arguments:
        if skip:
            skip = False
            continue
        if word.startswith("--"):
            continue
        if len(word) > 1 and word[0] in "-+":
            if word in tables.OPTION_VALUES:
                skip = True
            elif "c" in word[1:]:
                taking = True
            continue
        return word if taking else None
    return None
