"""The question asked of each pair, and the model's answer.

stereorepo's DR-332.
"""

import shutil
import subprocess
from typing import Any

EXECUTABLE = "claude"
"""The harness CLI asked; whatever account it is logged in as answers."""

MODEL = "claude-sonnet-5"
"""The model asked unless `--model` names another."""


QUESTION = """You are checking one citation, the way a reviewer checks one.

Below is a sentence from `{path}` that cites {cite}, the span it sits in, and \
the whole of what {cite} says. Decide whether {cite} supports what the sentence \
says about it.

Answer with exactly one line, and nothing else:

  ok <the words of {cite} that support it>
  x <what the sentence claims that {cite} does not say>
  ? <what you would have to know to decide>

Rules. Judge only the claim the sentence makes about {cite}. A sentence that \
names {cite} as a pointer, asserting nothing about its content, is `ok`. A \
faithful paraphrase is `ok` even where no words match. A count, a date, a name \
or a derivation attributed to {cite} is `x` where {cite}'s own text gives a \
different one. Where the claim is about something outside {cite} — another \
entry, a file, the world — answer `?`, because that is not yours to decide from \
what you have. Prefer `?` to a guess.

THE SENTENCE
{sentence}

THE SPAN IT SITS IN
{context}

WHAT {cite} SAYS
{body}
"""


def available() -> bool:
    """Whether the harness CLI is on PATH."""
    return shutil.which(EXECUTABLE) is not None


def ask(pair: dict[str, Any], model: str = MODEL, seconds: int = 120) -> tuple[str, str]:
    """Ask the model about one pair and return its mark and detail.

    Everything the question turns on is in the prompt, so the model reads
    extracted text rather than searching. A timeout, a non-zero exit, or an
    answer outside the three marks is `?` with the reason.
    """
    try:
        out = subprocess.run(
            [EXECUTABLE, "-p", "--model", model],
            check=False,
            input=QUESTION.format(**pair),
            capture_output=True,
            text=True,
            timeout=seconds,
        )
    except subprocess.TimeoutExpired:
        return "?", f"{EXECUTABLE} did not answer within {seconds}s"
    if out.returncode:
        why = out.stdout.strip() or out.stderr.strip() or "the model could not be reached"
        return "?", f"{EXECUTABLE}: {why.splitlines()[-1][:160]}"
    line = next((s.strip() for s in out.stdout.splitlines() if s.strip()), "")
    for mark in ("ok", "x", "?"):
        if line == mark or line.startswith(mark + " "):
            return mark, line[len(mark) :].strip()
    return "?", f"{EXECUTABLE} answered outside the three-mark protocol: {line[:120]!r}"
