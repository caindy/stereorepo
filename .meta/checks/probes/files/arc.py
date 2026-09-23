"""The runner image read for what it installs, against a Dockerfile whose every
install form is known (solorepo's DR-209).

`files.arc.installed_commands` is read by the `guarded tools installed` step
rather than run beside it, and its wrong answer is a pass: a reader that
over-reports finds every guarded tool installed whatever the image does, so the
step goes green forever and the drift solorepo's DR-156 names as its falsifier
escapes again. The cases are one Dockerfile text per install form, each with the
commands it does and does not put on a runner's `PATH`, and a failure names the
case. The step registers here rather than beside the check it exercises, because
the gate over assertions should not take its imports from a test suite
(solorepo's DR-150).
"""
import collections

from checks.collect import check
from checks.files import arc

ImageCase = collections.namedtuple("ImageCase", "name text installs absent")
"""One Dockerfile put to `installed_commands`.

Attributes:
    name: What the case is about, as a failure names it.
    text: The Dockerfile, as a whole file rather than a fragment.
    installs: Every command the answer must hold.
    absent: Every command the answer must not hold.
"""


IMAGE_CASES = (
    ImageCase(
        "an apt package list behind a chain",
        "FROM base\nRUN apt-get update -qq && \\\n"
        "    apt-get install -y --no-install-recommends curl jq && \\\n"
        "    apt-get clean\n",
        ("curl", "jq"),
        ("update", "clean", "-y", "--no-install-recommends"),
    ),
    ImageCase(
        "a COPY into a bin directory",
        "FROM base\nCOPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /uvx /usr/local/bin/\n",
        ("uv", "uvx"),
        ("bin", "ghcr.io/astral-sh/uv:0.6.14"),
    ),
    ImageCase(
        "a COPY into a directory that is not on PATH",
        "FROM base\nCOPY /kubectl /opt/tools/\n",
        (),
        ("kubectl",),
    ),
    ImageCase(
        "a symlink under a bin directory",
        "FROM base\nRUN ln -s /usr/local/lib/apm/apm /usr/local/bin/apm\n",
        ("apm",),
        (),
    ),
    ImageCase(
        "a tar extraction into a bin directory, behind a pipe",
        "FROM base\nRUN curl -fsSL https://example.invalid/cli.tar.gz | \\\n"
        "    tar -xz -C /usr/local/bin antigravity\n",
        ("antigravity",),
        ("cli.tar.gz", "curl"),
    ),
    ImageCase(
        "a tar extraction into a prefix rather than a bin directory",
        "FROM base\nRUN curl -fsSL https://example.invalid/node.tar.xz | \\\n"
        "    tar -xJ -C /usr/local --strip-components=1\n",
        (),
        ("node", "npm"),
    ),
    ImageCase(
        "an installer that names no command it lands",
        "FROM base\nRUN curl -sSf https://just.systems/install.sh | \\\n"
        "    bash -s -- --tag 1.58.0 --to /usr/local/bin\n",
        (),
        ("just", "install.sh"),
    ),
    ImageCase(
        "a comment naming a tool the file does not install",
        "FROM base\n# Install the GitHub CLI (gh), jq and just\nRUN apt-get install -y jq\n",
        ("jq",),
        ("gh", "just"),
    ),
)
"""Every Dockerfile the reader is asked about, one per install form. The text is
the case rather than a quotation of `.meta/arc/Dockerfile`, which moves, and each
carries what must be absent as well as what must be present, since the answer
that fails this step silently is the one that reports too much."""


GUARD_CASES = (
    ("type -p gh >/dev/null || install_gh", ("gh",)),
    ("command -v jq || apt-get install -y jq", ("jq",)),
    ("# on an image that already carries it this is a `type -p gh`", ("gh",)),
)
"""A script line against the tools `GUARD` reads out of it. The third is a shell
comment and is read like any other line, which is why `guarded_tools` drops the
comments before asking rather than leaving `GUARD` to tell prose from a guard."""


@check("runner image probes", pre=True)
def runner_image_probes() -> list[str]:
    """`installed_commands` reads what a Dockerfile installs, and `GUARD` what a script guards.

    Four install forms are recognised and everything else is not, so the cases
    run both ways: a package list, a `COPY` into a `bin` directory, a symlink
    under one and a `tar` into one are read, while a `COPY` or `tar` into a prefix
    that is not on `PATH`, an installer that names no command it lands, and a
    comment naming a tool are not. The comment case is the one the Dockerfile
    makes likely: its install lines are each introduced by a sentence listing
    what they install, so a reader that took prose for an install would find
    every tool named installed whatever the line below it did.
    """
    problems = []
    for case in IMAGE_CASES:
        found = arc.installed_commands(case.text)
        for command in case.installs:
            if command not in found:
                problems.append(f"runner image: {case.name} installs '{command}', "
                                "which is not read out of it")
        for command in case.absent:
            if command in found:
                problems.append(f"runner image: {case.name} installs no '{command}', "
                                "which is read out of it anyway")
    for line, expected in GUARD_CASES:
        read = tuple(arc.GUARD.findall(line))
        if read != expected:
            problems.append(f"runner image: {line!r} guards {expected}, read as {read}")
    return problems
