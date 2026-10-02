---
difficulty: medium
parent: onboard-fitch-mvp
---

# Resolve cited schema slots against the portfolio's own schemas

The `cited schema slots` step (`.meta/checks/citations/slots.py`) reads prose
across the repository and resolves each `Class.slot` it finds against
stereorepo's LinkML schemas (`SCHEMA_PATHS`). A product that has LinkML
schemas of its own fails the step wherever its documentation cites them.
fitch-mvp is a decision management product, and its `README.md` and
`ROADMAP.md` cite 27 slots of its own `Decision` class, such as its
outcomes and its posits. Each one fails against stereorepo's `Decision` (a Decision Record),
which has a class of the same name and different slots.

## How to reproduce it

In a temporary portfolio, add a LinkML schema outside `.meta/` that declares
a class `Decision` with a slot that stereorepo's `Decision` lacks, and a
`README.md` that cites that slot in the qualified `Class.slot` form. Run the
`meta` gate. `cited schema slots` fails, saying the slot is not declared on
class `Decision`.

## Wanted

- A Project in `.meta/assertions/structure.yaml` can name the LinkML schemas
  it owns, as repository-relative paths in a new multivalued slot on
  `Project` (`schemas`, or a better name the work finds). This is where a
  portfolio declares its product's schemas: a schema belongs to a build unit,
  and the Project is already asserted there.
- `cited schema slots` loads every schema the Projects name beside
  stereorepo's own, and prose that cites a slot one of them declares passes.
- Where a class name is in both a product schema and stereorepo's schemas,
  a citation passes when either one declares the slot. Telling which class a
  sentence means is out of reach.
- A named schema that is missing or does not load fails the step, naming the
  path and the Project, rather than being skipped.
- With no Project naming a schema, the step behaves as it does today.
- The new slot is settled in a Decision Record.

## How anyone will know it is done

Probes of `cited_schema_slots`, beside its existing ones in
`.meta/checks/probes/citations.py`, over a temporary portfolio whose Project
names a product schema declaring a class `Decision` with a slot stereorepo's
`Decision` lacks:

- a `README.md` citing that slot in the qualified `Class.slot` form passes;
- a citation of a slot neither `Decision` declares still fails;
- a citation of a slot only stereorepo's `Decision` declares still passes;
- a Project naming a schema path that does not exist, or a file that is not
  a loadable LinkML schema, fails the step with a message naming that path
  and the Project.

## Out of scope

- Renaming either `Decision`. fitch-mvp's domain term and stereorepo's
  Decision Record are a confusable pair, which fitch-mvp's domain vocabulary
  records.
- Former slots of product schemas. The check derives slots removed in git
  history from stereorepo's schemas only (`SCHEMA_PATHS`), and keeps doing so.
- Validating assertions against product schemas. Only the slot citation check
  reads them; the schema views the rest of the gate uses are unchanged.
- Declaring fitch-mvp's schemas in fitch-mvp, which its onboarding does.

## The plan

The step already receives the assertion index as a gate source (`index` in
`SOURCES`, `.meta/checks/collect.py`), and every Project in
`.meta/assertions/structure.yaml` is in it as `(class, object, file)`. So the
step reads the declared schemas off the index, and nothing new is threaded
through `check.py`.

1. **The slot.** In `.meta/work/structure.yaml`, add a slot `schemas`
   (`range: string`, `multivalued: true`) described as the repository-relative
   paths of the LinkML schemas a Project owns, read by the slot citation
   check, and list it under the `slots` of `Project`. No Project in stereorepo names one.
2. **Loading them.** In `.meta/checks/citations/slots.py`, add
   `product_views(index, load=SchemaView) -> tuple[list[Any], list[str]]`:
   for each `Project` entry in the index, for each path in `schemas`, resolve
   it against `ROOT`, and call `load(path)` and then `all_classes()` on the
   result inside a `try`. `SchemaView` parses lazily, so the `all_classes()`
   call is what makes a file that is not LinkML fail here rather than later.
   A missing file, or any exception from loading, becomes a problem line
   naming the path and the Project's id. The `load` seam exists for the
   probes.
3. **The step.** `cited_schema_slots(views, index, deleted=...)`: call
   `product_views`, return `Found` with its problems if there are any, and
   otherwise compile `_compile_schema_indices(list(views) + product)`. That
   function already unions slots per class name with `setdefault(...).update`,
   so a citation passes when either `Decision` declares the slot with no
   further change. `file_asserted_classes` keeps receiving stereorepo's
   `views` only, and `deleted_schema_slots` keeps `SCHEMA_PATHS`, which
   keeps the former-slot derivation and the other steps out of it. The
   `Passed` scope line says how many product schemas were read.
4. **Probes**, in `.meta/checks/probes/citations.py`. They write a minimal
   LinkML schema into a `tempfile` directory, declaring `Decision` with
   `posit_kind`, a slot of its own. They then build a fake index holding one
   `Project` whose `schemas` names its absolute path, which `ROOT / path`
   leaves absolute. A new function `_probe_product_schemas` then checks:
   - indices compiled from a fake stereorepo view (a `Decision` with
     `rationale`) plus the product view: `check_prose_spans` over a
     `README.md` span citing the product slot in the qualified form finds
     nothing; one qualifying an invented slot on the class is found; one
     qualifying `rationale` on it finds nothing. The step skips
     `checks/probes/`, so the probe writes these spans whole;
   - `product_views` on a Project naming a path that does not exist, and on
     one naming a file holding plain YAML that is not a schema, each returns
     one problem naming the path and the Project id;
   - an index with no Project naming `schemas` gives no views and no
     problems, which is today's behaviour;
   - `cited_schema_slots(views=[], index=..., deleted=lambda: ({}, None))`
     with an index whose Project names the missing path returns `Found`
     naming it, so the step itself, not only `product_views`, is pinned to
     fail on a schema that does not load. It returns before scanning any file,
     so the probe does not walk the repository.

   The probe step is `pre=True`, so it loads the temporary schema itself
   through `SchemaView` rather than taking `views`. Plain YAML with no
   `classes` key may load as an empty schema, not raise. If so, the plan
   counts a schema that declares no class as not loadable and says so in
   the message, and the probe pins that.
5. **Record.** Write `.meta/assertions/decisions/DR-304.yaml` (the record ends
   at DR-303). It settles that a portfolio declares its product schemas on
   its Projects and that only the slot citation check reads them, with
   `enacted_in` naming `work:artifact/meta-work-structure` and
   `work:artifact/meta-checks-citations-slots`. Cite it from the slot's
   description and from the step's docstring, and re-render.

### Risky

- **The new step source.** Adding `index` to the step's signature changes
  how `check.py` calls it. That is what `SOURCES` is for. The existing
  probes call `cited_schema_slots(views=[], deleted=...)` and must pass
  `index={}`.
- **Self-citation.** The new docstrings, the DR and this Issue are themselves
  scanned by the step. Write any example citation of a product slot in a
  hedged clause, or not in the qualified `Class.slot` form, as the backlog
  version of this Issue had to (commit `d7cd924`).
- **Load cost.** One `SchemaView` a declared schema, each gate run. That is
  nothing in stereorepo, which names none.

## What the work found

- Built as planned: the `schemas` slot on `Project` in
  `.meta/work/structure.yaml`, `product_views` and the `index` source in
  `.meta/checks/citations/slots.py`, `_probe_product_schemas` and
  `_probe_product_citations` in `.meta/checks/probes/citations.py`, and
  DR-304.
- The step reads the product schemas only after it has derived former slots,
  so a shallow clone still says `CouldNotRun` before it says anything about a
  product schema.
- The step's own prose check caught this Issue: the plan named the product
  slot in the "a slot `x`" phrase form, which the step resolves even when it
  is not qualified. Any Issue or record that names a slot of a product's
  schema has the same trap until that schema is declared.
- `just render` cannot write `.claude/skills/` from inside a seat's sandbox
  and stops there. `render.py --check` reported every page current, so
  nothing was left unrendered by this change.
