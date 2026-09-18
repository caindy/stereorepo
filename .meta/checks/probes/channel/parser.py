"""The channel's parsers: every verb of every program parses the flags its own branch in `main()` reads, refuses what is not typeable, and belongs to the program the table says (solorepo's DR-117).
"""
from collect import check
from probes.harness import (
    answered,
    load_channel,
)


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
        """`.meta/say/<name> <line>` through the program's parser, as `(namespace, code, exited)`; see `answered`.

        `namespace` is what the line parsed to, or `None`; `code` is `None`
        where it parsed and otherwise what the parser exited or crashed with,
        as text; `exited` is whether the parser ended in an exit, which is how
        argparse refuses a line, rather than a return or a crash.
        """
        return answered(lambda: programs[name].build_parser().parse_args(line.split()))

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
