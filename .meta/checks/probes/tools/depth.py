"""`depth.py`'s four layers, each answered by the paths a change touches (solorepo's DR-188).
"""

from typing import Any

from checks.collect import META, ROOT, check
from checks.probes.harness import load_module, written


@check("depth probes", pre=True)
def depth_probes() -> list[str]:
    """`depth.evaluate` answers from the first of its four layers that speaks, one case per layer and one per precedence between them (solorepo's DR-188).

    Layer 1 is the scaffold boundary: each of the four boundary files alone
    takes the deep tier, and the reason says so. Layer 4 is the standard path
    that files matching nothing take, with the real `structure.yaml` and no
    hook. Layer 2 is read from a `structure.yaml` written for the case, whose
    one project declares two `critical_paths` globs: a file under one takes
    the deep tier with the declared reason, and a file under neither falls
    through to standard. Layer 3 is read from a hook written for the case,
    which answers a two-agent, ninety-turn configuration for a file whose
    name holds `custom_trigger` and `None` for any other; a boundary file
    beside that name still takes layer 1, because the layers answer in order
    and a hook cannot talk a boundary out of deep review. Last,
    `.meta/hooks/depth.py.example` must exist and, run as the hook, must put
    a migration on the deep tier and a README on the standard one.
    """
    depth = load_module(META / "depth.py", "depth_module")
    problems = []
    opus, sonnet = "claude-opus-5", "claude-sonnet-5"

    def expect(case: str, cfg: Any, **want: Any) -> None:
        """One problem naming `case` when any field of `cfg` differs from `want`; `reason_has` asks that the reason contain a phrase rather than equal one."""
        phrase = want.pop("reason_has", None)
        if any(getattr(cfg, field) != value for field, value in want.items()) or (
                phrase is not None and phrase not in cfg.reason):
            asked = [f"{field}={value!r}" for field, value in want.items()]
            if phrase is not None:
                asked.append(f"reason containing {phrase!r}")
            problems.append(f"depth: {case} expected {', '.join(asked)}, got {cfg}")

    for boundary in (".meta/say/post", ".meta/hooks/worktree_only.py",
                     ".claude/settings.json", ".github/workflows/gate.yml"):
        cfg = depth.evaluate([boundary])
        expect(f"scaffold boundary {boundary}", cfg, model=opus, agents=3)
        expect(f"scaffold boundary {boundary}", cfg, reason_has="scaffold boundary")
    standard = depth.evaluate(["src/main.rs", "docs/guide.md"])
    expect("standard files", standard, model=sonnet, agents=1)
    expect("standard files", standard, reason="standard path")

    structure = (
        "projects:\n"
        "  - id: work:project/billing\n"
        "    critical_paths:\n"
        "      - 'services/billing/**'\n"
        "      - 'migrations/*.sql'\n"
    )
    with written(".yaml", structure) as declared:
        critical = depth.evaluate(["services/billing/ledger.rs"], structure_file=declared)
        expect("declared critical path", critical, model=opus, agents=3)
        expect("declared critical path", critical, reason_has="declared critical path")
        other = depth.evaluate(["services/auth/token.rs"], structure_file=declared)
        expect("a file matching no declared critical path", other, model=sonnet, agents=1)

    hook = (
        "def evaluate_depth(pr_meta, files, diff):\n"
        "    if any('custom_trigger' in f for f in files):\n"
        "        return {'model': 'claude-opus-5', 'gemini_model': 'gemini-3.8-flash', "
        "'effort': 'high', 'turns': 90, 'minutes': 30, 'agents': 2, 'reason': 'custom rule'}\n"
        "    return None\n"
    )
    with written(".py", hook) as programmatic:
        hooked = depth.evaluate(["apps/custom_trigger.py"], hook_file=programmatic)
        expect("programmatic hook", hooked, agents=2, turns=90, reason="custom rule")
        overridden = depth.evaluate([".meta/say/post", "apps/custom_trigger.py"], hook_file=programmatic)
        expect("scaffold boundary over the programmatic hook", overridden,
               agents=3, reason_has="scaffold boundary")

    example = ROOT / ".meta" / "hooks" / "depth.py.example"
    if not example.is_file():
        problems.append("depth: .meta/hooks/depth.py.example is missing")
    else:
        expect("the example hook on a migration",
               depth.evaluate(["migrations/001_initial.sql"], hook_file=example), model=opus, agents=3)
        expect("the example hook on a README",
               depth.evaluate(["README.md"], hook_file=example), model=sonnet, agents=1)
    return problems
