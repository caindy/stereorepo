"""The channel under `.meta/say/`, run against the calls it exists to refuse (solorepo's DR-209).

Its parsers and the verb table they are read against, a Decision's status as
`move` reads it, `claim` at each level from a run and from a session, who the
Actor is, where a Role's signing key is, and the numbers `decision numbering`
reads as reserved. Not invariants over the record: each probe loads the channel
and runs it, which is why the probes are a package of their own rather than
steps beside the checks over assertions (solorepo's DR-150).
"""
import argparse
import collections
import os
import pathlib
import tempfile

import yaml

import graph
from collect import META, ROOT, Found, Passed, check
from probes.harness import (
    FakeGitHub,
    FakeIssue,
    environment,
    load_channel,
    load_module,
    outcome,
    run_verb,
    stood_in,
)


def _answered(call):
    """`call`'s return value beside how it ended, as `(value, code, exited)`; see `outcome`.

    `outcome` reads a call's exit as text and drops what it returned, and once
    an exit and a crash are both text nothing in the text tells them apart.
    Three probes here need both halves: a parser answers a namespace or exits
    with its usage, `channel.actor()` answers a session or refuses, and
    `role_signing_key()` answers a path or refuses. `value` is what the call
    returned, `None` where it did not return; `code` is `outcome(call).code`;
    `exited` is whether the call ended in `sys.exit`, read off the exception's
    class before `outcome` renders it, so that a case expecting a refusal is
    not satisfied by a crash. The `say:` prefix the channel puts on its
    refusals is not tested, since an exit carrying a number or nothing is as
    much a refusal as one carrying a sentence.
    """
    held, exits = [], []

    def attempt():
        """`call`, its value kept in `held` and an exit noted in `exits` on its way out to `outcome`."""
        try:
            held.append(call())
        except SystemExit:
            exits.append(True)
            raise

    code = outcome(attempt).code
    return (held[0] if held else None), code, bool(exits)


@check("channel parser probes", pre=True)
def channel_parser_probes():
    """Every verb of every program parses the flags its own branch in `main()`
    reads, refuses what is not typeable, and belongs to the program the table
    says (solorepo's DR-117).

    `accepted` is, per program, each line it parses and the attributes the line
    must set. `refused` is, per program, each line it rejects, grouped under the
    reason the report names: the withdrawn nouns are not verbs, and what they
    allowed is not typeable (solorepo's DR-116) — a Challenge without a
    difficulty, a difficulty that is not one, a layer with two bases; a verb is
    one program's (solorepo's DR-117), so what `post` says `move` does not, and
    the other way about; a close names what answered the Challenge, since the
    closing comment cites what `--by` names and PR First has no `close` verb
    (solorepo's DR-164); a dispatch says which pass, `review` or `rebase`, and
    no other: the two do opposite things to a branch, and `coder.yml` defaults
    its own input to `review`, so a dispatch that named none would be a review
    by the workflow's silence; and `mint` takes no number, since the number is
    GitHub's to issue and one a caller can name is the read of a shared value
    `mint` exists to replace (solorepo's DR-128). Argparse's usage text is
    captured rather than shown.
    """
    _, _, programs = load_channel()
    accepted = {
        "post": [
            ("review 1 --approve", {"verb": "review", "pr": "1", "verdict": "approve"}),
            ("review 1 --request-changes", {"verdict": "request-changes"}),
            ("review 1 --comment", {"verdict": "comment"}),
            ("--role reviewer review 1 --approve", {"role": "reviewer", "verdict": "approve"}),
            ("comment 93", {"verb": "comment", "number": "93"}),
            ("raise 13 .meta/say/post 12", {"verb": "raise", "pr": "13", "path": ".meta/say/post", "line": 12}),
            ("notice 13 .meta/say/post 12", {"verb": "notice", "pr": "13", "path": ".meta/say/post", "line": 12}),
            ("reply T_1", {"verb": "reply", "thread": "T_1"}),
            ("answer T_1", {"verb": "answer", "thread": "T_1"}),
            ("resolve T_1", {"verb": "resolve", "thread": "T_1"}),
            ("promote T_1 --title t --difficulty easy",
             {"verb": "promote", "thread": "T_1", "title": "t", "level": "easy", "no_resolve": False}),
            ("promote T_1 --title t --difficulty hard --no-resolve",
             {"verb": "promote", "thread": "T_1", "title": "t", "level": "hard", "no_resolve": True}),
            ("landed 13", {"verb": "landed", "pr": "13"}),
        ],
        "move": [
            ("claim 93", {"verb": "claim", "issue": "93"}),
            ("difficulty 93 human", {"verb": "difficulty", "issue": "93", "level": "human"}),
            ("triage 93 medium", {"verb": "triage", "issue": "93", "level": "medium"}),
            ("stop 93", {"verb": "stop", "issue": "93"}),
            ("file --title t --difficulty medium",
             {"verb": "file", "title": "t", "level": "medium", "roadmap": False}),
            ("file --title t --roadmap", {"verb": "file", "level": None, "roadmap": True}),
            ("open --title t", {"verb": "open", "title": "t", "base": "main", "on": None}),
            ("open --title t --on 12", {"verb": "open", "on": "12"}),
            ("layer 13 --on 12", {"verb": "layer", "pr": "13", "on": "12"}),
            ("revise 13 --title t", {"verb": "revise", "number": "13", "title": "t"}),
            ("revise 13", {"verb": "revise", "number": "13", "title": None}),
            ("merge 13 --auto", {"verb": "merge", "pr": "13", "auto": True, "stack": False}),
            ("merge 13 --stack", {"verb": "merge", "pr": "13", "auto": False, "stack": True}),
            ("supersede 13 --by 12", {"verb": "supersede", "pr": "13", "by": "12"}),
            ("supersede 13 --by DR-" + "152", {"verb": "supersede", "pr": "13", "by": "DR-" + "152"}),
            ("merge-manager", {"verb": "merge-manager", "dry_run": False}),
            ("merge-manager --dry-run", {"verb": "merge-manager", "dry_run": True}),
            ("advance", {"verb": "advance", "pr": None}),
            ("advance 13", {"verb": "advance", "pr": "13"}),
            ("dispatch 13 --task review", {"verb": "dispatch", "pr": "13", "task": "review"}),
            ("dispatch 13 --task rebase", {"verb": "dispatch", "pr": "13", "task": "rebase"}),
            ("request-review 13", {"verb": "request-review", "pr": "13", "to": "reviewer"}),
            ("mint", {"verb": "mint"}),
            ("--role reviewer merge 13 --auto", {"role": "reviewer", "verb": "merge"}),
            ("milestone 75 --set first-specialization",
             {"verb": "milestone", "issue": "75", "title": "first-specialization", "clear": False}),
            ("milestone 75 --clear", {"verb": "milestone", "issue": "75", "title": None, "clear": True}),
        ],
        "commit": [("-m subject", {"message": "subject"})],
        "whoami": [("", {"role": "coder"}), ("--role reviewer", {"role": "reviewer"})],
    }
    withdrawn = ("the withdrawn nouns are not verbs, and what they allowed is not typeable "
                 "(solorepo's DR-116)")
    elsewhere = "a verb is one program's (solorepo's DR-117)"
    refused = {
        "post": (
            (withdrawn, ["review 1", "comment 93 --approve", "promote T_1 --title t",
                         "issue-comment 93", "resolve", "pr-body 1"]),
            (elsewhere, ["claim 93", "open --title t", "merge 13", "stop 93", "commit -m x",
                         "mint", "supersede 13 --by 12"]),
        ),
        "move": (
            (withdrawn, ["milestone 75", "milestone 75 --set x --clear",
                         "file --title t", "file --title t --difficulty huge",
                         "file --title t --difficulty easy --roadmap",
                         "difficulty 93 huge", "triage 93", "triage 93 huge",
                         "open --title t --base b --on 12",
                         "issue --title t", "pr --title t", "pr-base 1 --base b",
                         "label 93 --add human", "stack 1 2"]),
            (elsewhere, ["comment 93", "answer T_1", "review 1 --approve", "landed 13"]),
            ("a close names what answered the Challenge, since the closing comment cites what "
             "`--by` names (solorepo's DR-164)",
             ["supersede 13", "close 13", "abandon 13"]),
            ("a dispatch says which pass and no other, since `coder.yml` would otherwise "
             "default it to `review`",
             ["dispatch 13", "dispatch 13 --task answer", "dispatch --task review"]),
            ("the number is GitHub's to issue, and `mint` takes none (solorepo's DR-128)",
             ["mint 127"]),
        ),
        "commit": (("the message is required and takes a value", ["", "comment 1", "-m"]),),
        "whoami": (("the program has no verbs, and `--role` takes a value", ["whoami", "--role"]),),
    }

    def parsed(name, line):
        """`.meta/say/<name> <line>` through the program's parser, as `(namespace, code, exited)`; see `_answered`.

        `namespace` is what the line parsed to, or `None`; `code` is `None`
        where it parsed and otherwise what the parser exited or crashed with,
        as text; `exited` is whether the parser ended in an exit, which is how
        argparse refuses a line, rather than a return or a crash.
        """
        return _answered(lambda: programs[name].build_parser().parse_args(line.split()))

    problems = []
    for name, lines in accepted.items():
        for line, expect in lines:
            args, code, _ = parsed(name, line)
            if code is not None:
                problems.append(f"`.meta/say/{name} {line}` did not parse")
                continue
            for key, value in expect.items():
                got = getattr(args, key, None)
                if got != value:
                    problems.append(f"`.meta/say/{name} {line}`: {key} was {got!r}, not {value!r}")
    for name, groups in refused.items():
        for reason, lines in groups:
            for line in lines:
                _, code, exited = parsed(name, line)
                if not exited:
                    problems.append(f"`.meta/say/{name} {line}` parsed or crashed ({code!r}), "
                                    f"and should have been rejected: {reason}")
    return problems


@check("channel status probes", pre=True)
def channel_status_probes():
    """`move`'s reading of the status a Decision's entry gives itself, against
    `yaml`'s, over every entry in the record (solorepo's DR-164).

    `supersede --by DR-nnn` asks whether the entry was adopted, because a
    listing cannot tell an answer from a hole: a number written back as
    WITHDRAWN is a file at that path like any other. The channel cannot import
    `yaml` — those programs run under plain `python3`, where this gate takes
    its own from a `uvx` shebang — so the status is matched in the entry's
    text, and what the match assumes about that text is checked here. Held
    against the whole record and not a fixture, because the assumption is about
    the entries that exist: the day one is written some other way, this is what
    says so, and the verb reads `None` and refuses rather than reading whichever
    line matched.

    Two shapes the match cannot speak to, and must read as `None`, are written
    out as fixtures because neither is in the record: two entries in one text,
    and an entry with no status at all. A refusal that fires only on a file
    nobody has written yet is one nothing has run.
    """
    _, _, programs = load_channel()
    move = programs["move"]
    problems = []
    for path in sorted((META / "assertions" / "decisions").glob("DR-*.yaml")):
        entries = (yaml.safe_load(path.read_text()) or {}).get("decisions") or []
        said = move.entry_status(path.read_text())
        if len(entries) != 1:
            if said is not None:
                problems.append(f"channel status: {path.name} holds {len(entries)} entries and "
                                f"the channel read {said!r} out of it, where a status is one "
                                "entry's own")
            continue
        want = entries[0].get("status")
        if said != want:
            problems.append(f"channel status: the channel reads {path.name} as {said!r} and "
                            f"`yaml` reads it as {want!r}")
    for shape, text in (("two entries", "decisions:\n  - id: a\n    status: ADOPTED\n"
                                        "  - id: b\n    status: WITHDRAWN\n"),
                        ("no status", "decisions:\n  - id: a\n    name: n\n")):
        if (said := move.entry_status(text)) is not None:
            problems.append(f"channel status: {shape} read as {said!r}, where nothing in that "
                            "text is the status of one entry")
    return problems


@check("channel table probes", pre=True)
def channel_table_probes():
    """The verb table is the parsers, and a Role's reading is the table (solorepo's DR-117).

    Every verb the table names parses in the program it names, every verb a
    program parses is in the table, every program the table names is where it
    says and executable, every `held_by` is a Role the authority assertions
    know or one of the two readers that are not Roles, and PR First's own
    steps type no command — the verbs are the steps, and a step that spelled
    one would be the second copy found drifting on solorepo's #117.

    The Roles are read from `imported/authority.yaml`, because they are the
    channel's and live with it under `imported/`; a portfolio's own
    `authority.yaml` holds the accounts they use (solorepo's DR-123). `solo` and
    `workflow` are the two readers of the table that are not Roles.
    """
    _, table, programs = load_channel()
    problems = []
    roles = {r["name"] for r in (yaml.safe_load(
        (META / "assertions" / "imported" / "authority.yaml").read_text()) or {}).get("roles") or []}
    readers = roles | {"solo", "workflow"}
    for program in table.get("programs") or []:
        name = program["name"]
        path = ROOT / program["path"]
        if path != META / "say" / name:
            problems.append(f"{name}: the table says {program['path']}, and the channel is .meta/say/{name}")
        if not path.is_file() or not os.access(path, os.X_OK):
            problems.append(f"{program['path']} is not an executable file")
        parser = programs[name].build_parser()
        subs = next((a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)
        parsed = set(subs.choices) if subs else {name}
        asserted = {v["name"] for v in program["verbs"]}
        for verb in sorted(asserted - parsed):
            problems.append(f"{name}: the table names `{verb}`, which the program does not parse")
        for verb in sorted(parsed - asserted):
            problems.append(f"{name}: the program parses `{verb}`, which the table does not name")
        for verb in program["verbs"]:
            for who in verb.get("held_by") or []:
                if who not in readers:
                    problems.append(f"{name} {verb['name']}: held by {who!r}, which is not a Role or a reader")
            if not verb.get("held_by"):
                problems.append(f"{name} {verb['name']}: held by nobody")
    disciplines = yaml.safe_load((META / "assertions" / "imported" / "disciplines.yaml").read_text()) or {}
    for d in disciplines.get("disciplines") or []:
        if d["name"] == table.get("discipline"):
            for i, step in enumerate(d.get("steps") or [], 1):
                if ".meta/say" in step:
                    problems.append(f"{d['name']} step {i} types a command; the verbs are the steps")
    return problems


@check("layer probes", pre=True)
def layer_probes():
    """`link` names the stack when the pull request below is a layer, and the pull request when it is not (solorepo's #496).

    `gh stack link` takes two pull requests, which starts a stack, or a stack's
    number and the layer to add, and refuses a call naming fewer pull requests
    than the stack already holds. So the one input the verb branches on is
    whether the pull request below carries a `stack` object, which is what
    GitHub is stood in for to answer, and what is read back is the argument
    vector the fake was handed for each case.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    fake = FakeGitHub({7: {"behind": 0, "armed": False},
                       8: {"behind": 0, "armed": False, "layer": True, "stack": 493}})
    problems = []
    for below in ("7", "8"):
        said = run_verb(channel, fake, lambda below=below: move.link(below, "9"))
        if said:
            problems.append(f"link({below!r}, '9') exited with {said!r}")
    if fake.linked != [("7", "9"), ("493", "9")]:
        problems.append(f"gh stack link was handed {fake.linked!r}; expected pull request 7 "
                        "named for itself, which is no layer, and stack 493 named for pull "
                        "request 8, which is one")
    if problems:
        return Found(problems)
    return Passed("a layer is linked by its stack's number, a first layer by the pull request below")


@check("claim probes", pre=True)
def claim_probes():
    """`move claim` at each level, from a run and from a session (solorepo's DR-148).

    The whole of the refusal is a branch taken on the environment, which is the
    one input a reader cannot see by reading the verb: "this is a session" holds
    on every machine except the one where it matters, or on none, and nothing
    says which. So `ACTOR_SESSION` is set and unset around each case rather than
    stood in for — the variable is the fact — and GitHub is stood in for by
    `FakeIssue`, so that all seven cases are cheap to state. `None` for the
    session is the variable unset, which is a session as much as an
    unrecognised value is.

    The cases: the two levels a loop takes, claimed from a session, are refused
    with nothing assigned, and the refusal names `move difficulty ... hard`, the
    move that takes the Challenge from the loop — a session told only that it
    may not claim is left with the collision and no act. An unrecognised
    `ACTOR_SESSION` is a session too: the mark is what a workflow writes, so
    anything else is nothing saying otherwise, and the unknown falls to the side
    that asks. The levels no loop takes are claimed as before, `human` above
    all, since it is where a loop puts what it could not finish and picking
    that up is what a session is for. A level with no `challenge` beside it
    starts no run (solorepo's #113), so it refuses nobody. And a run's own claim
    is refused by nothing and reads the labels zero times.

    A refusal's text is read, not just its presence: `run_verb` reports an
    exception as text rather than raising it, so a truthy answer alone cannot
    tell the refusal from the fake being asked something it has no answer for.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    problems = []

    def claimed(labels, session):
        """One claim of Issue 7 under `ACTOR_SESSION` set to `session`, as `(what it exited with, the fake)`."""
        fake = FakeIssue(labels)
        with environment(ACTOR_SESSION=session):
            return run_verb(channel, fake, lambda: move.claim("7")), fake

    for level in ("easy", "medium"):
        said, fake = claimed(["challenge", level], None)
        if fake.assignees:
            problems.append(f"claim: a session claiming a `{level}` Challenge was assigned it")
        if not said or "hard" not in said or "difficulty" not in said:
            problems.append(f"claim: a session claiming a `{level}` Challenge was told {said!r}")
    said, fake = claimed(["challenge", "medium"], "whatever-this-is")
    if not said or "hard" not in said or "difficulty" not in said or fake.assignees:
        problems.append(f"claim: an environment carrying no run mark was told {said!r} "
                        f"claiming a `medium` Challenge, and left it assigned to "
                        f"{fake.assignees!r}")
    for level in ("hard", "human"):
        said, fake = claimed(["challenge", level], None)
        if said or fake.assignees != ["o-r-coder"]:
            problems.append(f"claim: a session claiming a `{level}` Challenge said {said!r} "
                            f"and left it assigned to {fake.assignees!r}")
    said, fake = claimed(["medium"], None)
    if said or not fake.assignees:
        problems.append(f"claim: a session claiming a bare `medium` Issue said {said!r}")
    said, fake = claimed(["challenge", "medium"], "gha-1234")
    if said or fake.assignees != ["o-r-coder"]:
        problems.append(f"claim: a run claiming its own `medium` Challenge said {said!r} "
                        f"and left it assigned to {fake.assignees!r}")
    if fake.views:
        problems.append(f"claim: a run's claim read the labels {fake.views} time(s)")
    return problems


@check("actor probes", pre=True)
def actor_probes():
    """`channel.actor()` and `check_pr.mine()` agree on which session is
    speaking, over the precedence of the two variables and the fallback when
    neither is set (solorepo's #301).

    `ACTOR_SESSION` wins when it carries the run's mark, `gha-`, and
    `CLAUDE_CODE_SESSION_ID` wins otherwise: the mark winning, not mere
    presence, is the half of the rule the code does not say out loud. `mine()`
    reads a Trailer as its own exactly when it names the session `actor()`
    answers, so each case checks both, over one Trailer that is the session's
    own and one that is not. With neither variable set, `actor()` refuses and
    `mine()` answers `False` for any Trailer.

    A case is `(name, actor_session, claude_session, answer, own, not_own)`:
    the two variables, `None` for unset; `answer`, what `actor()` returns, or
    `None` where it refuses; `own`, the session a Trailer must read as mine, or
    `None` where none does; and `not_own`, a session a Trailer must not.
    """
    channel, _, _ = load_channel()
    check_pr = load_module(META / "check_pr.py", "check_pr")
    Case = collections.namedtuple("Case", "name actor_session claude_session answer own not_own")
    cases = (
        Case("both set, the run's mark beside the harness's uuid",
             "gha-7", "uuid-123", "gha-7", "gha-7", "uuid-123"),
        Case("`ACTOR_SESSION` unmarked beside the uuid",
             "not-marked-session", "uuid-456", "uuid-456", "uuid-456", "not-marked-session"),
        Case("neither set", None, None, None, None, "uuid-123"),
    )
    problems = []
    for case in cases:
        with environment(ACTOR_SESSION=case.actor_session, CLAUDE_CODE_SESSION_ID=case.claude_session):
            got, code, exited = _answered(channel.actor)
            if case.answer is None:
                if not exited:
                    problems.append(f"actor: {case.name}: expected a refusal, got {got!r} "
                                    f"returned and {code!r} exited")
            elif code is not None:
                problems.append(f"actor: {case.name}: exited with {code}")
            elif got != case.answer:
                problems.append(f"actor: {case.name}: expected {case.answer!r}, got {got!r}")
            if case.own is not None and not check_pr.mine(f"Actor: {case.own}\nAgent: cli"):
                problems.append(f"mine: {case.name}: expected True for the {case.own!r} Trailer")
            if check_pr.mine(f"Actor: {case.not_own}\nAgent: cli"):
                problems.append(f"mine: {case.name}: expected False for the {case.not_own!r} Trailer")
    return problems


@check("signing key probes", pre=True)
def signing_key_probes():
    """`channel.role_signing_key()` finds the Role's key, refuses one readable
    by others, and answers `None` for the solo (solorepo's DR-197).

    The cases, in the order the key is looked for, each later source taking
    precedence over the ones before: with no credential file at `ROLE_ENV`,
    the speaker is the solo and there is no key; with `coder.env` holding a
    token, the key is `<ROLE_DIR>/coder_signing.key`; that key with mode `0644`
    is refused, since a key readable by others is not a Role's; `GIT_SIGNING_KEY`
    in the credential file names the key instead; and `SOLOREPO_SIGNING_KEY` in
    the environment names it above both. Every file is written mode `0600` in a
    temporary directory stood in for `ROLE_DIR`, `ROLE_ENV` is stood in for
    beside it, and what the channel prints about the credential is captured.
    """
    channel, _, _ = load_channel()
    problems = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = pathlib.Path(tmpdir)
        with stood_in(channel, ROLE_ENV=tmppath / "empty.env"):
            key, code, _ = _answered(channel.role_signing_key)
            if key is not None or code is not None:
                problems.append(f"signing_key: the solo: expected None, got {key!r} returned "
                                f"and {code!r} exited")
        role_env = tmppath / "coder.env"
        role_env.write_text("GH_TOKEN=fake_token_for_test\n")
        role_env.chmod(0o600)
        key_file = tmppath / "coder_signing.key"
        key_file.write_text("dummy-key\n")
        key_file.chmod(0o600)
        with stood_in(channel, ROLE_ENV=role_env, ROLE_DIR=tmppath):
            got, code, _ = _answered(channel.role_signing_key)
            if code is not None or got != key_file:
                problems.append(f"signing_key: the Role's default key: expected {key_file}, "
                                f"got {got} returned and {code!r} exited")
            key_file.chmod(0o644)
            _, code, exited = _answered(channel.role_signing_key)
            if not exited:
                problems.append(f"signing_key: a key readable by others (mode 0644): expected a "
                                f"refusal, got {code!r}")
            key_file.chmod(0o600)
            custom_key = tmppath / "custom.key"
            custom_key.write_text("custom-dummy-key\n")
            custom_key.chmod(0o600)
            role_env.write_text(f"GH_TOKEN=fake_token_for_test\nGIT_SIGNING_KEY={custom_key}\n")
            got, code, _ = _answered(channel.role_signing_key)
            if code is not None or got != custom_key:
                problems.append(f"signing_key: GIT_SIGNING_KEY in the credential file: expected "
                                f"{custom_key}, got {got} returned and {code!r} exited")
            env_key = tmppath / "env.key"
            env_key.write_text("env-dummy-key\n")
            env_key.chmod(0o600)
            with environment(SOLOREPO_SIGNING_KEY=str(env_key)):
                got, code, _ = _answered(channel.role_signing_key)
                if code is not None or got != env_key:
                    problems.append(f"signing_key: SOLOREPO_SIGNING_KEY in the environment: "
                                    f"expected {env_key}, got {got} returned and {code!r} exited")
    return problems


@check("reservation probes", pre=True)
def reservation_probes():
    """`decision numbering` over a hole GitHub reserves, a hole it does not, a
    hole a tag holds and a commit made, a remote that will not say, a history
    that is not there, a deletion with neither a remote nor a tag behind it,
    and a hole neither read can speak to (solorepo's DR-128).

    The record here is contiguous whenever this gate is green, so the branch
    that reads the reservations is the one branch a real run never takes: a
    collision is two sessions on one evening, and by the time one is happening
    is the wrong time to find out what this does. Both reads are stood in for
    by argument. Standing the remote in is also what keeps this probe from
    making the network call the check itself makes only once, and only when it
    is needed; the history is stood in for because the deletion it asks about
    is one this repository has not made.

    `advertised` is what `git ls-remote --tags` prints, verbatim: the object, a
    tab, the ref, and a second line per annotated tag dereferencing it to the
    commit. `graph.RESERVATION` is held to reading one reservation off it,
    since every other case here stands the read in and would not see a pattern
    that matched none of it: a branch is worth probing where its input comes
    from somewhere else. The hole's number is spelled from `hole` rather than
    typed, because `DR-` and three digits in a file a portfolio copies is a
    citation as far as `cited decisions` is concerned, and this one is a
    fixture (solorepo's DR-124).

    The tag is never deleted, so over a number the record once held it says as
    much about a deletion as about a reservation, and the history is what
    carries the difference. The deletion with no remote to ask is the install a
    portfolio with no `origin` is, permanently, and the one the history read is
    local for: the commits are read first, a hole they explain is one the
    remote is never asked about, and the stand-in for the remote reports being
    called at all. The hole neither read can speak to prints the one sentence
    of that function no other case here does, and is the only path on which
    the remote is asked over a hole the commits could never have explained —
    a clone with no history explains none, so every hole reaches the remote
    and both answers are red; the stand-in reports having been asked, since
    what a later reader needs from the case is whether that call is meant
    (solorepo's #152).
    """
    hole = 3
    index = {f"work:decision/{n}": ("Decision", {}, "a probe") for n in (1, 2, 4)}
    problems = []
    advertised = ("707ad55ec421eb46374520f6c4e7641d65f6afd9\trefs/tags/DR-{0:03d}\n"
                  "5f05eca90639651a8aadaf12fe98a30abaa39093\trefs/tags/DR-{0:03d}^{{}}\n")
    found = graph.RESERVATION.findall(advertised.format(hole))
    if found != [f"{hole:03d}"]:
        problems.append(f"decision numbering: the refs `git ls-remote` advertises read as {found!r}, "
                        "and one annotated tag is one reservation")
    if (said := graph.decision_numbering(index, reserved=lambda: {hole},
                                         deleted=lambda numbers: set())):
        problems.append(f"decision numbering: a hole GitHub reserves was reported as {said!r}")
    said = graph.decision_numbering(index, reserved=lambda: {hole},
                                    deleted=lambda numbers: {hole})
    if not said or f"DR-{hole:03d}" not in said[0] or "removed" not in said[0]:
        problems.append(f"decision numbering: a reserved number whose entry a commit removed "
                        f"was reported as {said!r}, and a tag does not explain a deletion")
    said = graph.decision_numbering(index, reserved=lambda: {5}, deleted=lambda numbers: set())
    if not said or f"DR-{hole:03d}" not in said[0]:
        problems.append(f"decision numbering: a hole nothing reserves was reported as {said!r}")
    said = graph.decision_numbering(index, reserved=lambda: None, deleted=lambda numbers: set())
    if not said or "would not say" not in said[0] or "tag" in said[0]:
        problems.append("decision numbering: a remote that would not answer was reported "
                        f"as {said!r}, and a run that read no tags says nothing about them")
    said = graph.decision_numbering(index, reserved=lambda: {hole}, deleted=lambda numbers: None)
    if not said or "no history" not in said[0]:
        problems.append("decision numbering: a hole under a history that cannot be read was "
                        f"reported as {said!r}, and an unexplained hole is a failure")

    def unreachable():
        """The remote over a hole the commits explain: never asked, and a call is itself a finding."""
        problems.append("decision numbering: the remote was asked about a hole a commit "
                        "here explains, and the tags decide only what the history leaves")
        return None

    said = graph.decision_numbering(index, reserved=unreachable, deleted=lambda numbers: {hole})
    if said != [f"the record held DR-{hole:03d} and a commit here removed it, tag or no tag; "
                "a number withdrawn stays in the record as a hole"]:
        problems.append("decision numbering: a deletion with no remote to ask was reported as "
                        f"{said!r}, and the read that can name it is the one every clone has")

    asked = []

    def unreadable():
        """The remote that will not say, over a hole no history explains.

        Records in `asked` that it was called, and answers `None`.
        """
        asked.append(True)
        return None

    said = graph.decision_numbering(index, reserved=unreadable, deleted=lambda numbers: None)
    if said != [f"no entry for DR-{hole:03d}; the remote would not say which numbers it "
                "reserves and this clone has no history to read, so nothing here tells a "
                "number in flight from a deletion"]:
        problems.append("decision numbering: a hole neither read could speak to was reported "
                        f"as {said!r}, and a sentence claims only what its run read")
    if not asked:
        problems.append("decision numbering: the remote was not asked over a hole no commit "
                        "here could explain, and a clone with no history explains none of them")
    return problems
