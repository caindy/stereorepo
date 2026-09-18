"""The decision for one command line, each segment judged on its own: whether it reaches GitHub through a CLI verb that writes, through the endpoint by name, or through code an interpreter is handed to the nesting the tables allow, and whether what runs is the channel's own program (solorepo's DR-117).
"""
import os
import shlex

from lib.signed_channel import shell, tables


def runs_channel(name: str, arguments: list[str]) -> bool:
    """Judge whether a segment runs a program of the channel.

    Parameters:
        name: The program the segment runs, as `shell.program` resolved it.
        arguments: The words following it.

    Returns:
        bool: True where the program is one of `.meta/say/` or
        `.meta/check_pr.py`, either named directly or named as the script an
        interpreter of `tables.WRAPPERS` is given to run, which is the one argument
        position that runs it. An interpreter handed code on its command line
        runs that code rather than a script, so any argument beginning with one
        of `tables.RUNS_CODE` — attached to its own value, as `-cimport os` is, or
        written apart from it — sanctions nothing.
    """
    if tables.SANCTIONED.search(name):
        return True
    if name.rsplit("/", 1)[-1] not in tables.WRAPPERS:
        return False
    if any(word.startswith(tuple(tables.RUNS_CODE)) for word in arguments):
        return False
    script = shell.run_by(name.rsplit("/", 1)[-1], arguments)
    return script is not None and bool(tables.SANCTIONED.search(os.path.expandvars(script)))


def writes(words: list[str]) -> bool:
    """Judge whether a segment's words run `gh` carrying one of the writing verbs.

    Parameters:
        words: One segment's words, as `shlex` lexed them.

    Returns:
        bool: True where a word naming `gh` is followed by the words of one of
        `tables.GH_WRITES`, in order and next to one another. A verb spelled inside a
        single word is an argument rather than an invocation, so a pattern
        searched for with these words in it is not one.
    """
    for at, word in enumerate(words):
        if word.rsplit("/", 1)[-1] != "gh":
            continue
        after = words[at + 1:]
        if any(tuple(after[start:start + len(form)]) == form
               for form in tables.GH_WRITES
               for start in range(len(after))):
            return True
    return False


def reaches(segment: str, data: str, depth: int) -> str | None:
    """Judge whether one command of a line reaches GitHub outside the signed channel.

    Parameters:
        segment: One command's text, as `shell.segments` cut it.
        data: The heredoc bodies the command carries, joined.
        depth: How many shell interpreters this command is already nested under.

    Returns:
        str | None: The refusal to show the agent, or None where this command
        posts nothing unsigned.
    """
    try:
        words = shlex.split(segment)
    except ValueError:
        return tables.UNREADABLE
    if tables.SUBSTITUTION.search(segment):
        return tables.UNREADABLE
    name, arguments = shell.program(words)
    if name is None:
        return None if shell.runs_nothing(words) else tables.UNREADABLE
    if runs_channel(name, arguments):
        return None
    if "$" in name:
        return tables.UNREADABLE
    called = name.rsplit("/", 1)[-1]
    if called in tables.READING or (called, arguments[0] if arguments else "") in tables.READING_PAIRS:
        return None
    if called in tables.SHELLS:
        code = shell.shell_code(arguments)
        if code is None:
            return tables.UNREADABLE
        if (problem := blocked(code, depth + 1)) is not None:
            return problem
    if writes(words):
        return tables.WHY
    if tables.ENDPOINT.search(" ".join(words)) or tables.ENDPOINT.search(data):
        return tables.WHY
    return None


def blocked(command: str, depth: int = 0) -> str | None:
    """The predicate: does this command reach GitHub outside the signed channel?

    Parameters:
        command: Raw command string from tool input.
        depth: How many shell interpreters this command line is nested under; a
            line nested past `tables.NESTING` is refused rather than read further.

    Returns:
        str | None: The refusal to show the agent, naming what to use instead;
        None where every command on the line posts nothing unsigned.
    """
    try:
        if depth > tables.NESTING:
            return tables.UNREADABLE
        read = shell.without_heredocs(command)
        if read is None:
            return tables.UNREADABLE
        text, bodies = read
        for start, end, segment in shell.segments(text):
            carried = [(expands, body) for offset, expands, body in bodies
                       if start <= offset < end]
            if any(expands and tables.SUBSTITUTION.search(body) for expands, body in carried):
                return tables.UNREADABLE
            problem = reaches(segment, "".join(body for _, body in carried), depth)
            if problem:
                return problem
        return None
    except Exception as exc:
        return f"{tables.UNREADABLE} ({type(exc).__name__}: {exc})"

