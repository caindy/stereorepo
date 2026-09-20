"""`link` names the stack when the pull request below is a layer, and the pull request when it is not (solorepo's #496).
"""


import functools

from checks.collect import Found, Passed, check
from checks.probes.harness import (
    FakeGitHub,
    load_channel,
    run_verb,
)


@check("layer probes", pre=True)
def layer_probes() -> Found | Passed:
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
        said = run_verb(channel, fake, functools.partial(move.link, below, "9"))
        if said:
            problems.append(f"link({below!r}, '9') exited with {said!r}")
    if fake.linked != [("7", "9"), ("493", "9")]:
        problems.append(f"gh stack link was handed {fake.linked!r}; expected pull request 7 "
                        "named for itself, which is no layer, and stack 493 named for pull "
                        "request 8, which is one")
    if problems:
        return Found(problems)
    return Passed("a layer is linked by its stack's number, a first layer by the pull request below")
