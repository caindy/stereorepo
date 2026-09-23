#!/usr/bin/env python3
"""The channel: the credential and the Trailer, and nothing else.

Every comment an agent writes here is posted under its Role's account, so which
Job wrote it is carried by an `Actor:` Trailer and by nothing else. The channel
composes and appends the Trailer itself from the environment, ensuring signing
is an intrinsic property of the channel rather than a manual act that can be
omitted (solorepo's DR-069). History in channel.history.md.

Identity is derived directly from the environment; callers do not supply
identity arguments manually (solorepo's DR-175).

It is a module, not a verb surface. The programs beside it import it, and each
holds one concern (solorepo's DR-117): `post` says things — comments, threads, answers,
what landed, the reviewer's verdict; `move` changes what GitHub holds — claims,
levels, layers, merges, handoffs; `commit` is git's; `whoami` answers which
login this speaks as. None of them reads a credential or composes a Trailer:
each speaks through here, or not at all. Which Role holds which verb is asserted
once, in `.meta/say/verbs.yaml`, and a Role's reading of PR
First is compiled from it, so `/pr-first` lists the coder's verbs and
`/pr-first-reviewer` the reviewer's. A program's `--help` lists its own.

`--role` names which Role speaks, coder by default: its credential is
`~/.config/solorepo/<role>.env`, and its login is `<owner>-<repo>-<role>`, so a
Role is one word said once (solorepo's DR-107). `SOLOREPO_ROLE_ENV` names a file outright
and wins.

Bodies are read from stdin rather than command-line arguments to preserve
multiline text and quotes without shell escaping issues.
"""
import argparse
import json
import os
import pathlib
import re
import select
import subprocess
import sys
import time
import types
from collections.abc import Callable
from typing import Any, TypeVar

NO_SPEC = "no module spec for {path}"
"""What loading a sibling raises where `importlib` declines to describe the file as a module."""

HERE = pathlib.Path(__file__).resolve().parent

ROLE_DIR = pathlib.Path("~/.config/solorepo").expanduser()
"""Path to external role credential directory outside the working tree (solorepo's DR-073)."""

ROLE_ENV = pathlib.Path(os.environ.get("SOLOREPO_ROLE_ENV", ROLE_DIR / "coder.env")).expanduser()
"""Path to the active role credential file, overridable via SOLOREPO_ROLE_ENV."""

ENV_AGENT = ("AI_AGENT",)
"""Environment variable names carrying the local agent harness name verbatim."""

ENV_ANTIGRAVITY = ("ANTIGRAVITY_AGENT", "ANTIGRAVITY_CONVERSATION_ID")
"""Environment variable names identifying a local Antigravity session (solorepo's DR-245)."""

ANTIGRAVITY = "antigravity-cli"
"""The agent name Antigravity signs with, matching `on.HARNESSES` (solorepo's DR-245)."""

ENV_SESSION = ("CLAUDE_CODE_SESSION_ID", ENV_ANTIGRAVITY[1], "ACTOR_SESSION")
"""Environment variable names evaluated to detect local session identifiers."""

RUN_MARK = "gha-"
"""Workflow run identifier prefix for ACTOR_SESSION to distinguish CI runs from local sessions (solorepo's DR-148)."""

ENV_RUN_ID = "GITHUB_RUN_ID"
"""Environment variable containing the attested GitHub Actions run identifier (solorepo's DR-233)."""

ENV_RUN_AGENT = "ACTOR_AGENT"
"""Environment variable containing the workflow-attested agent name (solorepo's DR-233)."""

ENV_RUN_STEP = ("GITHUB_WORKFLOW", "GITHUB_ACTION")
"""Fallback workflow step environment variables identifying caller provenance."""

READING = ("`.meta/say/verbs.yaml` says what each verb does and which "
           "Role holds it; /pr-first is the coder's reading of PR First and "
           "/pr-first-reviewer the reviewer's. Every body arrives on stdin.")


def parser(doc: str) -> argparse.ArgumentParser:
    """Creates a base argument parser configured with shared channel options.

    Parameters:
        doc: Command description string.

    Returns:
        argparse.ArgumentParser: Parser initialized with standard `--role` option.
    """
    ap = argparse.ArgumentParser(description=doc, epilog=READING,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--role", default="coder",
                    help="which Role speaks: ~/.config/solorepo/<role>.env (default coder)")
    return ap


def speak_as(role: str) -> None:
    """Configures the active role credential file path unless overridden by environment.

    Parameters:
        role: Role name identifying the credential file (~/.config/solorepo/<role>.env).
    """
    global ROLE_ENV
    if not os.environ.get("SOLOREPO_ROLE_ENV"):
        ROLE_ENV = ROLE_DIR / f"{role}.env"


def sibling(name: str) -> types.ModuleType:
    """Imports and caches a neighbouring executable script under .meta/say/ as a module.

    Parameters:
        name: Filename of the sibling script to load.

    Returns:
        types.ModuleType: Loaded module instance.

    Raises:
        ImportError: If the module specification cannot be created.
    """
    import importlib.util
    from importlib.machinery import SourceFileLoader

    if name in _siblings:
        return _siblings[name]
    loader = SourceFileLoader(name, str(HERE / name))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise ImportError(NO_SPEC.format(path=loader.path))
    module = importlib.util.module_from_spec(spec)
    _siblings[name] = module
    loader.exec_module(module)
    return module


_siblings: dict[str, types.ModuleType] = {}
"""Cached sibling executable modules loaded by sibling()."""


def attested_run() -> str | None:
    """Returns the attested workflow run identity, or None outside a GitHub Actions run.

    Reads `GITHUB_RUN_ID` from the environment and prefixes it with `RUN_MARK`
    (solorepo's DR-233).

    Returns:
        Attested run identifier string (`gha-<run_id>`), or None if unset.
    """
    run = os.environ.get(ENV_RUN_ID)
    return f"{RUN_MARK}{run}" if run else None


def speaker() -> str | None:
    """Resolves the active session or run identifier from the environment (solorepo's #285).

    Evaluates attested run identity first, followed by `ACTOR_SESSION` prefixed
    with `RUN_MARK`, and finally session variables declared in `ENV_SESSION`.

    Returns:
        The resolved speaker identifier string, or None if no identifier is present.
    """
    run = attested_run()
    if run:
        return run
    declared = os.environ.get("ACTOR_SESSION") or ""
    if declared.startswith(RUN_MARK):
        return declared
    return next((os.environ[k] for k in ENV_SESSION if os.environ.get(k)), None)


def actor() -> str:
    """Returns the verified session identifier for the current Actor (solorepo's DR-086, solorepo's DR-233).

    In a workflow run, validates that `ACTOR_SESSION` matches `attested_run()`.
    Refuses execution if no valid speaker identifier is established.

    Returns:
        The verified Actor session identifier.

    Raises:
        SystemExit: If `ACTOR_SESSION` conflicts with the attested run ID or no
            speaker is found in the environment.
    """
    run, declared = attested_run(), os.environ.get("ACTOR_SESSION")
    if run and declared and declared != run:
        sys.exit(f"say: this is run {run} and `ACTOR_SESSION` says {declared}; "
                 "refusing to sign as a Job that is not this one")
    session = speaker()
    if not session:
        sys.exit("say: the environment does not say who is speaking "
                 f"(need one of {ENV_SESSION}); refusing to post")
    return session


def in_a_run() -> bool:
    """Returns True if execution occurs within a GitHub Actions workflow run.

    Detects workflow execution by verifying either the presence of an attested
    GITHUB_RUN_ID or an ACTOR_SESSION starting with the RUN_MARK prefix
    (solorepo's DR-148, solorepo's DR-233).

    Returns:
        bool: True if executing within a GitHub Actions workflow, False otherwise.
    """
    return bool(attested_run()) or (os.environ.get("ACTOR_SESSION") or "").startswith(RUN_MARK)


def agent() -> str:
    """Returns the identifier of the executing agent harness component (solorepo's DR-233).

    In a workflow run, reads `ENV_RUN_AGENT` (`ACTOR_AGENT`) or derives identity
    from workflow step metadata (`ENV_RUN_STEP`). Outside a run, returns
    `AI_AGENT`, falling back to `ANTIGRAVITY` where `AI_AGENT` is unset and
    either name in `ENV_ANTIGRAVITY` is set.

    Returns:
        The resolved agent harness component name.

    Raises:
        SystemExit: If the environment does not specify the executing agent.
    """
    if in_a_run():
        step = [os.environ.get(name) for name in ENV_RUN_STEP]
        run_agent = os.environ.get(ENV_RUN_AGENT) or "/".join(part for part in step if part)
        if not run_agent:
            sys.exit(f"say: this run does not say what is speaking "
                     f"(need {ENV_RUN_AGENT}, which the workflow writes); refusing to post")
        return run_agent
    who = next((os.environ[k] for k in ENV_AGENT if os.environ.get(k)), None)
    if not who:
        if any(os.environ.get(name) for name in ENV_ANTIGRAVITY):
            return ANTIGRAVITY
        sys.exit(f"say: the environment does not say what is speaking "
                 f"(need one of {ENV_AGENT + ENV_ANTIGRAVITY}); refusing to post")
    return who


def trailers() -> str:
    """Constructs the standard Actor and Agent attribution trailer block.

    Returns:
        Formatted multi-line attribution string.
    """
    return f"Actor: {actor()}\nAgent: {agent()}"


TRAILING_TRAILER = re.compile(
    r"(?:\n|^)(?:Actor:\s*\S+\s*\nAgent:\s*\S+|Agent:\s*\S+\s*\nActor:\s*\S+|Actor:\s*\S+|Agent:\s*\S+)\s*$"
)
"""Matches terminal hand-crafted or foreign trailer blocks in input bodies (solorepo's DR-260)."""


def signed(text: str) -> str:
    """Appends Actor and Agent attribution trailers to a comment or issue body.

    Refuses input bodies terminating in hand-crafted or foreign trailers that do not
    match the attested environment trailer (solorepo's DR-260).
    """
    body = text.rstrip("\n")
    block = trailers()
    if body.endswith(block):
        return body
    if TRAILING_TRAILER.search(body):
        sys.exit("say: body ends in a hand-crafted or foreign trailer; the channel signs "
                 "automatically from workflow attestations (solorepo's DR-260). "
                 "Omit the trailing trailer.")
    return f"{body}\n\n{block}\n"


def piped(timeout: float = 0.5) -> str:
    """Reads non-blocking piped content from standard input if available.

    Returns an empty string immediately when stdin is connected to a tty.
    Otherwise polls stdin via select up to the specified timeout to avoid
    hanging on open but unwritten pipes.

    Parameters:
        timeout: Maximum duration in seconds to wait for stdin readability.

    Returns:
        The stripped string content from standard input, or an empty string if
        no input is available within the timeout.
    """
    if sys.stdin.isatty():
        return ""
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    return sys.stdin.read().strip() if ready else ""


def stdin_body() -> str:
    """Reads non-empty body text from piped stdin or exits with an error."""
    text = piped()
    if not text:
        sys.exit("say: nothing on stdin — pipe the body in, or redirect a file")
    return text


def role_credential() -> dict[str, str]:
    """Retrieves authentication tokens for the active role from the external configuration file.

    Loads credentials from ~/.config/solorepo/<role>.env (solorepo's DR-073).
    Enforces mode 0600 file permissions and validates that GH_TOKEN is present and
    non-empty.

    Returns:
        Dictionary mapping 'GH_TOKEN' to token value, or empty dict if speaking as solo.

    Raises:
        SystemExit: If the credential file permissions are invalid or GH_TOKEN is missing.
    """
    if not ROLE_ENV.exists():
        print(f"say: no {ROLE_ENV}; speaking with ambient auth, which is the solo",
              file=sys.stderr)
        return {}
    mode = ROLE_ENV.stat().st_mode
    if mode & 0o077:
        sys.exit(f"say: {ROLE_ENV} is readable by others (mode {mode & 0o777:o}); "
                 f"refusing to use it. chmod 600 it.")
    found: dict[str, str] = {}
    for line in ROLE_ENV.read_text().splitlines():
        line = line.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        found[key.strip()] = value.strip().strip("\"'")
    if not found.get("GH_TOKEN"):
        sys.exit(f"say: {ROLE_ENV} has no GH_TOKEN")
    print(f"say: speaking with the credential in {ROLE_ENV}", file=sys.stderr)
    return {"GH_TOKEN": found["GH_TOKEN"]}


GH_TIMEOUT = 60
"""Seconds one `gh` invocation is given before it is abandoned as hung (solorepo's #738).

The bound is the default and not the rule. A verb that waits on `gh` for a
single API call is bounded by it, and a minute is far longer than one of those
takes. The `gh stack` invocations in `.meta/say/move` are the exception and
pass `timeout=None`: rebasing and force-pushing every layer of a stack, or
merging every layer up to one, can take longer than a minute with nothing
wrong, and abandoned at a bound they would report a half-rewritten stack or a
merge whose landing nothing reconciled as a hang.
"""

TIMEOUT_RETURNCODE = 124
"""The `returncode` a tolerated timeout's `CalledProcessError` carries, which is what `timeout(1)` reports one under.

It is not an exit status of anything here: where failure is not tolerated a
timeout leaves through `sys.exit`, whose status is 1, so a shell tells a hang
from a refusal by the prose on standard error and not by `$?`.
"""

UNSET = object()
"""No default was given, as a value no caller can pass, so that a caller wanting `None` back from a failed read is told apart from a caller that wants the process to exit."""

STACK_EXTENSION = "github/gh-stack"
"""The extension `gh stack` is, spelled as `gh extension install` takes it.

`gh stack` is not part of the CLI. On a machine that does not already hold the
extension, the first `gh stack` invocation installs it, prints `Successfully
installed github/gh-stack` on standard error, exits 0, and never runs the
subcommand it was given. A runner is such a machine every time it starts, so
that first invocation is whichever stack call the job makes — a merge, where
the merge manager is the job (solorepo's #797).

`gh extension list` prints this same spelling in the row it gives the
extension, which is what `_stack_extension` reads the listing for.
"""


def _stack_extension() -> None:
    """Puts the `gh stack` extension on this machine before a stack call is made.

    The listing read falls back to an empty listing, which holds no
    `STACK_EXTENSION` and so falls through to the install: a machine that will
    not say what it has installed is treated as a machine that has nothing,
    which is the right act for it and keeps a read from ending a run. The
    install has no such fallback, because an install that failed is a stack
    call that cannot work.

    Raises:
        SystemExit: If `gh` will not install the extension.
    """
    if STACK_EXTENSION in gh("extension", "list", parse=False, default=""):
        return
    gh("extension", "install", STACK_EXTENSION, parse=False)


def _relay(args: tuple[str, ...], out: subprocess.CompletedProcess[str]) -> None:
    """Prints `gh <args>: exit <status>` on standard error, and what the invocation said.

    The status line is followed by whatever the invocation printed on standard
    output and standard error, joined by a newline; or, where both streams were
    empty after stripping, by the suffix ` and said nothing` on the status line
    itself, so a call that printed nothing is reported as having printed
    nothing rather than not reported.

    Args:
        args: The arguments `gh` was invoked with.
        out: What `subprocess.run` answered.
    """
    said = "\n".join(part for part in (out.stdout.strip(), out.stderr.strip()) if part)
    print(f"gh {' '.join(args)}: exit {out.returncode}"
          + (f"\n{said}" if said else " and said nothing"), file=sys.stderr)


def _degrade(default: Any, why: str) -> Any:
    """Answers a failed read with the caller's fallback, or exits saying what went wrong.

    Args:
        default: The fallback the caller gave, or `UNSET` if it gave none.
        why: What failed, in `gh`'s words or `json`'s, which `gh`'s stderr may
            spread over several lines.

    Returns:
        Any: The caller's fallback.

    Raises:
        SystemExit: When the caller gave no fallback.
    """
    if default is not UNSET:
        return default
    sys.exit(f"gh: {why}")


def gh(*args: str, parse: bool = True, default: Any = UNSET,
       tolerate_fail: bool = False, timeout: float | None = GH_TIMEOUT,
       echo: bool = False) -> Any:
    """Executes a gh CLI command using the role credential and parses JSON output.

    A `gh stack` call is preceded by `_stack_extension`, which installs
    `STACK_EXTENSION` where the machine does not hold it, so that the CLI's own
    install-on-first-use cannot consume the call (solorepo's #797).

    Args:
        *args: Command arguments passed to gh.
        parse: Whether to read the output as JSON. False returns it as stripped text,
            which is what a write that prints nothing answers with.
        default: Fallback value returned if the command fails, or prints output
            that `parse` cannot read as JSON. If `default` is omitted, either
            exits the process.
        tolerate_fail: Whether to raise the failure rather than answer it, which
            is how `gh_with_retry` sees the attempt it has to repeat. It is read
            before `default` on both failures, so a caller that sets it handles
            a failed command and an unreadable body itself.
        timeout: Seconds to wait for the invocation, `GH_TIMEOUT` by default;
            `None` waits indefinitely, which is what the `gh stack` calls pass.
        echo: Whether to relay the invocation's exit status and both of its
            streams on standard error. A call whose success is read back from
            GitHub rather than from its return value discards the only account
            of what it did, and the failure that account names is a call that
            exits 0 having done nothing.

    Returns:
        Any: Parsed JSON data, the stripped output where `parse` is false or the
            command printed nothing, or the fallback.

    Raises:
        subprocess.CalledProcessError: If the command fails or times out under
            `tolerate_fail`; a timeout carries `TIMEOUT_RETURNCODE`, so
            `gh_with_retry` retries it as it retries any other failure.
        json.JSONDecodeError: If the output cannot be read as JSON under
            `tolerate_fail`.
        SystemExit: If the read fails or times out and no fallback was given.
    """
    if args[:1] == ("stack",):
        _stack_extension()
    try:
        out = subprocess.run(["gh", *args], check=False, capture_output=True, text=True,
                             env={**os.environ, **role_credential()}, timeout=timeout)
    except subprocess.TimeoutExpired as expired:
        hung = f"`gh {' '.join(args)}` answered nothing within {timeout}s"
        if tolerate_fail:
            raise subprocess.CalledProcessError(
                TIMEOUT_RETURNCODE, ["gh", *list(args)], output="", stderr=hung) from expired
        sys.exit(f"gh: {hung}")
    if echo:
        _relay(args, out)
    if out.returncode:
        if tolerate_fail:
            raise subprocess.CalledProcessError(out.returncode, ["gh", *list(args)], output=out.stdout, stderr=out.stderr)
        return _degrade(default, out.stderr.strip())
    text = out.stdout.strip()
    if not parse or not text:
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        if tolerate_fail:
            raise
        return _degrade(default, f"answered what is not JSON: {exc}")


def gh_with_retry(*args: str, parse: bool = True, tries: int = 3, delay: float = 2,
                  backoff: float = 2, tolerate_fail: bool = False) -> Any:
    """Run gh, retrying on subprocess/API failure with exponential backoff.

    A call that answers nothing within `GH_TIMEOUT` seconds is a failure like
    any other here, so a hung invocation is abandoned and retried rather than
    waited on (solorepo's #738).

    Args:
        *args: Command arguments passed to gh.
        parse: Whether to read the output as JSON, as `gh` takes it.
        tries: How many attempts to make before the failure is final.
        delay: Seconds to wait after the first failed attempt.
        backoff: What each further wait is multiplied by.
        tolerate_fail: Whether to raise the final failure rather than exit on it.

    Returns:
        Any: What `gh` answered on the first attempt that succeeded.

    Raises:
        subprocess.CalledProcessError: If every attempt fails under `tolerate_fail`.
        json.JSONDecodeError: If an attempt answers a body that is not JSON. That
            failure is not retried and reaches the caller whatever `tolerate_fail`
            was set to, since a body `gh` printed once it will print again.
        SystemExit: If every attempt fails and the failure is not tolerated.
    """
    import time
    current_delay = delay
    for attempt in range(tries):
        try:
            return gh(*args, parse=parse, tolerate_fail=True)
        except subprocess.CalledProcessError as exc:
            if attempt == tries - 1:
                if tolerate_fail:
                    raise
                sys.exit(f"gh: {exc.stderr.strip()}")
            print(f"warning: gh {' '.join(args)} failed (attempt {attempt + 1}/{tries}): {exc.stderr.strip()}. Retrying in {current_delay}s...", file=sys.stderr)
            time.sleep(current_delay)
            current_delay *= backoff
    sys.exit(f"gh: {' '.join(args)} was never attempted — `tries` is {tries}")


Read = TypeVar("Read")
"""What a read answers with, which is what `settled` and `shown` hand back."""

Written = TypeVar("Written")
"""What a write answers with, which is what `act` hands back beside the read."""

# How long to wait for GitHub to *show* an act it has accepted. A different
# question from `MERGEABILITY` below: this waits on work GitHub queues and
# performs, that one on a value GitHub computes when asked. `gh pr
# update-branch --rebase` returns when GitHub has taken the rebase, not when it
# has done it — measured on runs 34593386083 and 34594139086, where the branch
# heads were rewritten one to two seconds after the call and a `pr view` half
# a second later still answered with the head they had before. Half a minute,
# because an act GitHub has not shown by then is one the next run will ask
# about again.
SETTLES = (6, 5)
"""How many reads after the first a write is waited on for, and the seconds between them.

The first read costs no wait, so `(6, 5)` is seven reads over thirty seconds
where nothing is held, and six where the caller holds the first answer."""

# How long to wait for GitHub to say whether a branch still merges. `mergeable`
# is computed in the background when it is asked for, and GitHub's reference
# for it says to poll until the value is no longer null — which `gh` spells
# `UNKNOWN`. `advance` runs on the push that invalidated every cached answer,
# which is exactly the read the reference warns about: asked once, every
# waiting pull request would report `UNKNOWN` and nothing would ever be
# dispatched.
MERGEABILITY = (6, 5)
"""How many reads after the one in hand a computed value is waited on, and the seconds between."""


def settled(read: Callable[[], Read], shows: Callable[[Read], object],
            bound: tuple[int, float] | None = None, held: Read | None = None) -> Read:
    """What GitHub holds once it shows the act asked of it, or still holds when the wait runs out.

    The first answer is `held` where the caller has one in hand, and the one
    `read` gives otherwise; an act GitHub has already shown costs one question
    and no sleep, and only a read that is too early pays, in a wait rather
    than in a wrong answer. The predicate is the caller's because what counts
    as shown differs: a head that has moved, a label that is listed, a value
    that is no longer `UNKNOWN`. What the wait runs out on is the caller's to
    judge; `shown` is the caller that ends the process on it.

    Args:
        read: One read of GitHub, made until `shows` is satisfied or the bound
            is spent.
        shows: Whether an answer shows the act.
        bound: Reads after the first, and seconds between them; `SETTLES` by
            default. The first read, or `held`, costs no wait.
        held: An answer already in hand, read before any is asked for.

    Returns:
        Read: The first answer `shows` accepts, or the last one read.
    """
    tries, wait = bound or SETTLES
    answer = held if held is not None else read()
    for _ in range(tries):
        if shows(answer):
            break
        time.sleep(wait)
        answer = read()
    return answer


def shown(read: Callable[[], Read], shows: Callable[[Read], object],
          refused: Callable[[Read], str], bound: tuple[int, float] | None = None) -> Read:
    """`settled`, and the process ended with what `refused` says of the answer if the wait ran out.

    Args:
        read: One read of GitHub, as `settled` takes it.
        shows: Whether an answer shows the act, as `settled` takes it.
        refused: The exit's words, given the answer GitHub still holds.
        bound: Reads after the first, and seconds between them; `SETTLES` by default.

    Returns:
        Read: The answer that showed the act.

    Raises:
        SystemExit: When the wait ran out, with `refused`'s words.
    """
    answer = settled(read, shows, bound)
    if not shows(answer):
        sys.exit(refused(answer))
    return answer


def act(write: Callable[[], Written], read: Callable[[], Read], shows: Callable[[Read], object],
        refused: Callable[[Read], str],
        bound: tuple[int, float] | None = None) -> tuple[Written, Read]:
    """A write, then the read that shows it, settled or refused (solorepo's DR-264).

    Args:
        write: The act, as one call or several; what it answers is handed back.
        read: One read of GitHub, as `settled` takes it.
        shows: Whether an answer shows the act.
        refused: The exit's words, given the answer GitHub still holds.
        bound: Reads after the first, and seconds between them; `SETTLES` by default.

    Returns:
        tuple[Written, Read]: What the write answered, and the read that showed it.

    Raises:
        SystemExit: When the wait ran out, with `refused`'s words; the write
            has been made, and the exit says what GitHub shows in its place.
    """
    written = write()
    return written, shown(read, shows, refused, bound)


def graphql(query: str, **variables: object) -> Any:
    """Executes a GitHub GraphQL query with provided variables."""
    args = ["api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        args += ["-F", f"{key}={value}"]
    return gh(*args)


def repo() -> str:
    """Returns the nameWithOwner repository identifier for the current repo."""
    return str(gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"])


def login() -> str:
    """Queries GitHub API for the authenticated login name corresponding to the credential."""
    return str(gh("api", "user", "--jq", ".login", parse=False))


def role_login(role: str) -> str:
    """Derives the expected GitHub login name for a designated role (solorepo's DR-107).

    Parameters:
        role: The role name.

    Returns:
        The formatted login string `<owner>-<repo>-<role>`.
    """
    return f"{repo().replace('/', '-')}-{role}"


def role_identity() -> dict[str, str]:
    """Derives git author and committer environment variables for the active role.

    Returns:
        Dictionary of GIT_* environment variable bindings, or empty dict if speaking as solo.
    """
    if not role_credential():
        return {}
    who, ident = gh("api", "user", "--jq", ".login,.id", parse=False).split("\n")
    email = f"{ident}+{who}@users.noreply.github.com"
    return {"GIT_AUTHOR_NAME": who, "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": who, "GIT_COMMITTER_EMAIL": email}


def role_signing_key() -> pathlib.Path | None:
    """Resolves the SSH signing key path for the active role (solorepo's DR-073, solorepo's DR-197).

    Validates that the key file exists and has permissions not readable by others (mode 0600).

    Returns:
        Path to the signing key file, or None if speaking as solo or key is not configured.

    Raises:
        SystemExit: If the key file exists but has permissions readable by others.
    """
    if not role_credential():
        return None
    key_path: pathlib.Path | None = None
    if os.environ.get("SOLOREPO_SIGNING_KEY"):
        key_path = pathlib.Path(os.environ["SOLOREPO_SIGNING_KEY"]).expanduser()
    elif ROLE_ENV.exists():
        for line in ROLE_ENV.read_text().splitlines():
            line = line.strip().removeprefix("export ").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "GIT_SIGNING_KEY":
                key_path = pathlib.Path(value.strip().strip("\"'")).expanduser()
                break
    if not key_path:
        key_path = ROLE_DIR / f"{ROLE_ENV.stem}_signing.key"
    if not key_path.exists():
        return None
    mode = key_path.stat().st_mode
    if mode & 0o077:
        sys.exit(f"say: {key_path} is readable by others (mode {mode & 0o777:o}); "
                 f"refusing to use it. chmod 600 it.")
    return key_path
