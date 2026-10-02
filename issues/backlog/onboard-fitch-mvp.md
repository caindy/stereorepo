---
difficulty: hard
---

# Onboard fitch-mvp, the first existing repository

Specialization turns an empty repository into a portfolio. Nothing yet takes a
repository that already has code, history and conventions of its own, and
`just adapt plan` only plans that adoption: nothing applies the plan, no
procedure covers the judgement it leaves, and no existing Product has been
brought under a gate. This Flight onboards one real repository,
`/Users/christopher/fitch-mvp`, and fixes each gap the attempt finds in the
tool that caused it, so that the second onboarding has less to find.

fitch-mvp is a Python decision-modelling framework (LinkML schemas, a Neo4j
loader, pytest). Its tests run through `./build.py`, which starts a Neo4j
Docker container. It is colocated with Jujutsu (`.jj/`), and it keeps its own
`ROADMAP.md`, `DOGFOODING.md` and a design-decision graph in
`data/fitch_design_graph.yaml`.

## Settled by the developer

- **Jujutsu goes.** fitch-mvp stops using Jujutsu with this adoption, and
  `.jj/` is removed. Nothing is lost: both of its heads are empty, and its
  `main` is an ancestor of git's.
- **Two decision regimes, split by subject.** fitch-mvp is a decision
  management product, so it keeps dogfooding its *product* decisions in its
  own model, `data/fitch_design_graph.yaml`. Its *coding* decisions (how the
  repository is built, tested and delivered) are Decision Records under
  stereorepo's discipline, in `.meta/assertions/decisions/`. Its `AGENTS.md`
  is integrated to state the split, and `ROADMAP.md`'s work items move to the
  board.
- **The gate splits around Neo4j.** `./build.py` starts a Neo4j Docker
  container, and the seats' sandbox does not run Docker. fitch-mvp's gate
  therefore has a fast part that needs no database, which seats run while
  they work, and a full part with Neo4j, which runs before an Issue lands.

Once fitch-mvp holds its assertions, both of these become its first Decision
Records.

## How anyone will know it is delivered

The Flight is delivered in two repositories, and each is checked by whoever
can see it.

**The Flight check, in stereorepo.** The pair confirms that:

- every part of this Flight is in `done/`, and each one's change is in
  `main`;
- each finding under "Findings for the adoption procedure" names a part that
  addresses it, or says it waits for the procedure.

The Flight check writes no part for the state of fitch-mvp. That repository
is outside this tree, and the seats can neither read it nor change it. Where
the pair finds that fitch-mvp is not yet onboarded, it says so in the
desk-check brief and leaves the call to the developer.

**The desk check, in fitch-mvp.** The developer confirms that:

- fitch-mvp holds the adopted bundle and its own assertions in place of the
  scaffold's, and its `README.md`, `AGENTS.md` and `.gitignore` keep their
  own content beside the stereorepo conventions;
- a seat working in fitch-mvp runs the tests that need no database without
  Docker, and an Issue that lands there has first passed the tests that need
  Neo4j;
- one Issue in fitch-mvp's `issues/backlog/` has landed on its `main` through
  `uv run --script <stereorepo>/pair/pair.py run`.

## How parts are found

The parts are not known in advance. Each is written when the onboarding finds
it, and the developer adds the next ones as desk-check notes on this Flight.

A part changes stereorepo: its tools, bundle or disciplines. The adoption
itself changes fitch-mvp, which is outside this repository's tree, so the
developer does it with an agent session in fitch-mvp rather than through this
loop, and records what it found here.

## Findings for the adoption procedure

What the procedure written after this Flight must cover, as the onboarding
finds it:

- A repository may keep its own decision log or roadmap. The procedure asks
  which subjects each one keeps, rather than assuming Decision Records and the
  board replace them.
- A repository may use another version-control layer over git. The procedure
  checks that layer holds nothing git lacks before removing it.
