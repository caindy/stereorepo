#!/usr/bin/env python3
"""The channel: the credential and the Trailer, and nothing else.

Every comment an agent writes here is posted under its Role's account, so which
Job wrote it is carried by an `Actor:` Trailer and by nothing else. A Trailer
that the writer types is a Trailer the writer can forget — and one was forgotten
on this repository's own pull request, where it read as the solo and
manufactured the second party A16 asks for. That defect is not an oversight to
remember harder about; it is what happens when signing is an act rather than a
property of the channel.

So this is the channel (solorepo's DR-069). It appends the Trailer itself, from the
environment, and refuses to speak when the environment does not say who is
speaking. There is no argument for the identity, deliberately: what a caller can
pass, a caller can pass wrongly.

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

Bodies come from stdin rather than the command line: the text is usually long,
often has quotes in it, and a shell is the wrong place to keep an artifact.
"""
import argparse
import json
import os
import pathlib
import select
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent

# Outside the tree, per role and per machine (solorepo's DR-073). `speak_as` points
# ROLE_ENV at the Role named by --role; the environment variable names a file
# and wins.
ROLE_DIR = pathlib.Path("~/.config/solorepo").expanduser()
ROLE_ENV = pathlib.Path(os.environ.get("SOLOREPO_ROLE_ENV", ROLE_DIR / "coder.env")).expanduser()

ENV_AGENT = ("AI_AGENT",)
ENV_SESSION = ("CLAUDE_CODE_SESSION_ID", "ACTOR_SESSION")

# What a workflow writes into `ACTOR_SESSION` and nothing else does, so that a
# verb can tell a run from a session beside it (`in_a_run`, solorepo's DR-148).
RUN_MARK = "gha-"

READING = ("`.meta/say/verbs.yaml` says what each verb does and which "
           "Role holds it; /pr-first is the coder's reading of PR First and "
           "/pr-first-reviewer the reviewer's. Every body arrives on stdin.")


def parser(doc):
    """A program's parser: its docstring, and `--role`, the one option every
    program shares. The verbs are the caller's to add."""
    ap = argparse.ArgumentParser(description=doc, epilog=READING,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--role", default="coder",
                    help="which Role speaks: ~/.config/solorepo/<role>.env (default coder)")
    return ap


def speak_as(role):
    """Point the credential at a Role, unless the environment named a file."""
    global ROLE_ENV
    if not os.environ.get("SOLOREPO_ROLE_ENV"):
        ROLE_ENV = ROLE_DIR / f"{role}.env"


def sibling(name):
    """A program beside this one, as a module.

    The programs have no `.py` and are programs rather than libraries, so the
    loader is named explicitly. Importing runs nothing: everything each does is
    under `main()`, and `main()` is under `__name__`. Loaded once and kept
    here, so two programs that import each other — `move stop` posts a
    comment, `post promote` files an Issue — share one copy.
    """
    from importlib.machinery import SourceFileLoader
    import importlib.util

    if name in _siblings:
        return _siblings[name]
    loader = SourceFileLoader(name, str(HERE / name))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    _siblings[name] = module
    loader.exec_module(module)
    return module


# Kept on this module and not in `sys.modules`, so a probe that loads the
# channel afresh gets programs bound to that copy and not to an earlier one.
_siblings = {}


def actor():
    """**Who** is speaking: the session, and nothing else.

    A workload identity, attested for one run (solorepo's DR-086). A Role account will hold
    the principal identity and say which Role acted; it cannot say which run did
    the work, because one account serves many sessions. The key reads `Actor:`
    because it names the entity, not the identity it carries.

    One Job is one thread, and the session is what identifies it. The harness
    build used to be part of this and was doing a different job badly — it
    changes at every upgrade, so one Actor across an update read as two, while
    the part that actually distinguishes never moved.

    `ACTOR_SESSION` wins over `ENV_SESSION`'s declared order when it carries
    `RUN_MARK`: inside a container run the harness also sets
    `CLAUDE_CODE_SESSION_ID`, a uuid that says nothing about the workflow, and
    would otherwise shadow the workload identity `coder.yml` wrote — the run's
    Trailer reading a session indistinguishable from a laptop's.

    Fail closed. An unsigned comment should be unrepresentable, not discouraged.
    """
    run_session = os.environ.get("ACTOR_SESSION", "")
    if run_session.startswith(RUN_MARK):
        return run_session
    session = next((os.environ[k] for k in ENV_SESSION if os.environ.get(k)), None)
    if not session:
        sys.exit("say: the environment does not say who is speaking "
                 f"(need one of {ENV_SESSION}); refusing to post")
    return session


def in_a_run():
    """**Where** it is speaking from: a workflow run, or a session beside it.

    A third question, and the one a verb asks when what it does depends on
    whether a loop is standing on the work (solorepo's DR-148). `coder.yml` and `review.yml`
    write `gha-<run id>` into `ACTOR_SESSION`, so that prefix is the run's mark
    under solorepo's DR-086 — a workload identity, attested for one run.

    Not `actor()`, which answers a different question: it says which session
    is speaking, and a caller that only needs to know whether one is standing
    on a run would have to compare its answer against `RUN_MARK` itself. The
    mark is on `ACTOR_SESSION` itself, which nothing but a workflow here writes.

    That the mark reaches the agent's shell at all is a fact about the action,
    so it is a probe: run 34554434032 read `ACTOR_SESSION=gha-34554434032`
    beside `GITHUB_RUN_ID=34554434032` inside it, with `actor()` answering the
    harness's uuid in the same shell. The credential in that same `env:` block
    was not there, which is solorepo's DR-134's finding and is the
    credential's alone.

    A session is the answer wherever nothing says otherwise — unset, or a shape
    no workflow writes. That is the side that asks rather than the side that
    acts, which is where an unknown belongs when the refusal it feeds costs one
    act to escape and the collision it prevents costs a Job.
    """
    return (os.environ.get("ACTOR_SESSION") or "").startswith(RUN_MARK)


def agent():
    """**What** is speaking: the harness build, verbatim.

    A different question from `actor`, and a different class — this is a
    Component of a Bill of Materials, which is *supposed* to change when the
    build changes. It is recorded exactly as the environment gives it, because
    `AI_AGENT`'s format is undocumented and prettifying it would be inventing
    structure that nothing attests.

    The model is not here, and not because it was forgotten. Nothing in this
    environment attests it, and configuring it would put a confident falsehood
    in the record the first time a session switches models. A missing identity
    is recoverable; a wrong one is not.
    """
    who = next((os.environ[k] for k in ENV_AGENT if os.environ.get(k)), None)
    if not who:
        sys.exit(f"say: the environment does not say what is speaking "
                 f"(need one of {ENV_AGENT}); refusing to post")
    return who


def trailers():
    """The block this channel signs with, defined once because two readers need
    it: the one that writes it, and the one that recognises it."""
    return f"Actor: {actor()}\nAgent: {agent()}"


def signed(text):
    body = text.rstrip("\n")
    block = trailers()
    return body if body.endswith(block) else f"{body}\n\n{block}\n"


def piped(timeout=0.5):
    """Whatever was piped in, or nothing — but never a wait for input that will
    not come.

    A plain `sys.stdin.read()` hangs forever when this is run by a tool harness:
    stdin is neither a terminal nor closed, so `isatty()` says pipe and the read
    blocks on a pipe nobody is writing to. Five minutes of a session went that
    way. Ask whether anything is actually readable first.
    """
    if sys.stdin.isatty():
        return ""
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    return sys.stdin.read().strip() if ready else ""


def stdin_body():
    text = piped()
    if not text:
        sys.exit("say: nothing on stdin — pipe the body in, or redirect a file")
    return text


def role_credential():
    """The token for the Role this machine holds, from outside the working tree.

    Outside because a token in the tree is one `git add -A` from being published,
    and per role and per machine because that is what the credential is: a Remit
    bound where the work happens. It is read here and handed to one child
    process, so nothing exports it into the environment of every other command.

    It is not a boundary on this machine. Anything with a shell can read this
    file, so the wrapper is the only path by convention until an agent runs
    somewhere it cannot reach the solo's credentials at all. What it does buy is
    that GitHub can tell the Role from the solo, and that the fallback is
    visible rather than silent.
    """
    if not ROLE_ENV.exists():
        print(f"say: no {ROLE_ENV}; speaking with ambient auth, which is the solo",
              file=sys.stderr)
        return {}
    mode = ROLE_ENV.stat().st_mode
    if mode & 0o077:
        sys.exit(f"say: {ROLE_ENV} is readable by others (mode {mode & 0o777:o}); "
                 f"refusing to use it. chmod 600 it.")
    found = {}
    for line in ROLE_ENV.read_text().splitlines():
        line = line.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        found[key.strip()] = value.strip().strip("\"'")
    if not found.get("GH_TOKEN"):
        # Empty counts as missing. A secret that was never set arrives as an
        # empty string, and the first run of review.yml (solorepo's #84) passed this
        # check with one and failed further down, in gh's words rather than
        # this file's.
        sys.exit(f"say: {ROLE_ENV} has no GH_TOKEN")
    print(f"say: speaking with the credential in {ROLE_ENV}", file=sys.stderr)
    return {"GH_TOKEN": found["GH_TOKEN"]}


def gh(*args, parse=True):
    out = subprocess.run(["gh", *args], capture_output=True, text=True,
                         env={**os.environ, **role_credential()})
    if out.returncode:
        sys.exit(f"gh: {out.stderr.strip()}")
    return json.loads(out.stdout) if parse and out.stdout.strip() else out.stdout.strip()


def graphql(query, **variables):
    args = ["api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        args += ["-F", f"{key}={value}"]
    return gh(*args)


def repo():
    return gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]


def login():
    """The account this credential is, asked of GitHub."""
    return gh("api", "user", "--jq", ".login", parse=False)


def role_login(role):
    """The account a Role holds, by name and not by reading anything.

    `<owner>-<repo>-<role>` is the convention solorepo's DR-107 set, and it is what lets the
    coder name the reviewer without touching the reviewer's token — which on
    this machine it could read, and must not.
    """
    return f"{repo().replace('/', '-')}-{role}"


def role_identity():
    """The Role's git identity, or nothing at all.

    Only when a Role credential is in use. Without one the channel is speaking
    as the solo, and overriding his configured identity to say so would be the
    channel asserting something it was not given.
    """
    if not role_credential():
        return {}
    who, ident = gh("api", "user", "--jq", ".login,.id", parse=False).split("\n")
    email = f"{ident}+{who}@users.noreply.github.com"
    return {"GIT_AUTHOR_NAME": who, "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": who, "GIT_COMMITTER_EMAIL": email}
