"""The form half of the pull request gate: what a body must contain, derived from the template.

The headings come out of the fence in `.meta/templates/pull-request.md`, so a
heading added to the form is required by that act alone (A15, solorepo's DR-089).
"""

import re

from lib.check_pr import META

FORM = META / "templates" / "pull-request.md"

HEADING = re.compile(r"^\*\*(.+?)\.\*\*", re.M)

PLACEHOLDER = re.compile(r"<[^<>\n]*\s[^<>\n]*>")

LINK = re.compile(r"(#\d+|https?://\S+)")

BULLET = re.compile(r"^\s*[-*]\s+(.*)$", re.M)

NONE = re.compile(r"^\s*(none|nothing)\b", re.I)

DEFERRED = "What was noticed and not done"

CLOSES = "What it closes"

# GitHub's closing keywords, followed by the reference GitHub accepts — a bare
# number, owner/repo#n, or the Issue's URL. Anything else under this heading
# names an Issue the merge will leave open.
KEYWORD = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+"
                     r"(?:#\d+|[\w.-]+/[\w.-]+#\d+|https://github\.com/[\w.-]+/[\w.-]+/issues/\d+)", re.I)


def fence(path):
    """Extracts markdown body content from the first code block fence in a template file."""
    return path.read_text().split("```markdown\n", 1)[1].split("\n```", 1)[0]


def uncoded(text):
    """Strip code fences and inline backtick spans from text.

    Parameters:
        text (str): Raw markdown text.

    Returns:
        str: Text with markdown code blocks and inline code spans removed.
    """
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def sections(body):
    """Splits pull request markdown body text at bold section headings.

    Args:
        body: Raw markdown body string.

    Returns:
        dict[str, str]: Mapping of heading names to their corresponding body text.
    """
    marks = list(HEADING.finditer(body))
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        out[m.group(1)] = body[m.end():end].strip()
    return out


def unfilled(title, body):
    """Every placeholder the form spells in angle brackets that survives into `title` or `body`, as one problem each."""
    form = fence(FORM)
    literal = set(PLACEHOLDER.findall(form)) | set(re.findall(r"<[^<>\s]+>", form))
    problems = []
    for where, raw in (("title", title), ("body", body)):
        text = uncoded(raw)
        seen = set(PLACEHOLDER.findall(text)) | (literal & set(re.findall(r"<[^<>\s]+>", text)))
        problems += [f"unfilled placeholder in {where}: {m}" for m in sorted(seen)]
    return problems


def listed(section, heading, takes, carries, otherwise):
    """The problems with one list section: prose where items were wanted, or an item without what `carries` looks for, said as `otherwise`; nothing where the section is empty or an explicit 'None.'."""
    if not section or NONE.match(section):
        return []
    items = [m.group(1).strip() for m in BULLET.finditer(section)]
    if not items:
        return [f"**{heading}.** is prose. It takes {takes}, or an explicit 'None.'"]
    return [f"{otherwise}: {item}" for item in items if not carries.search(item)]


def check(title, body):
    """Validates pull request title and body against template requirements.

    Args:
        title: Pull request title string.
        body: Pull request markdown body string.

    Returns:
        list[str]: Validation error messages.

    Four things are asked of a body, in order. Every heading the form declares
    is present and not blank. No placeholder the form spells in angle brackets
    survives into the title or the body. Each item under **What it closes**
    carries a closing keyword, so the merge closes the Issue and nobody has to
    remember to (solorepo's DR-089). And each item under **What was noticed and
    not done** is a link, which is Article 15 itself: everything before it is
    the form being present, and this is the rule the form exists to carry.
    """
    required = [m.group(1) for m in HEADING.finditer(fence(FORM))]
    found = sections(body)
    problems = []
    for heading in required:
        if heading not in found:
            problems.append(f"missing section: **{heading}.**")
        elif not found[heading]:
            problems.append(f"empty section: **{heading}.** — the form was submitted blank")
    problems += unfilled(title, body)
    problems += listed(found.get(CLOSES, ""), CLOSES, "one `Closes #n` per item", KEYWORD,
                       "no closing keyword, so the merge leaves it open")
    problems += listed(found.get(DEFERRED, ""), DEFERRED, "one link per item", LINK,
                       "not a link, so it closes with this pull request")
    return problems
