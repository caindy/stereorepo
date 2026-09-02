## Schemas

_The ontologies, and how to exercise them._

_The ontologies, and how to exercise them._

| File | What it is |
|---|---|
| `work_ontology.yaml` | The umbrella: equations, load map, container. |
| `work/` | The work ontology in seven modules, each carrying its own reasoning. |
| `ddd_ontology.yaml` | DDD reified, republished per DR-016. Restates the canon; never overrides it. |

Start from `work_ontology.yaml`'s load map, then read the module that covers
what you are touching. A module explains itself.

### Exercising them

No toolchain is checked in; the schema is exercised with `uvx`:

```bash
uvx --from linkml gen-json-schema .meta/work_ontology.yaml   # compiles?
uvx --from linkml linkml-validate -s .meta/work_ontology.yaml <instance.yaml>
uvx --from linkml linkml-lint .meta/work_ontology.yaml       # style only
```

`linkml-lint` reports warnings for uppercase enum values. That is the common
LinkML convention and they are left as they are.

There is **no instance data in the repo**. Every change so far was validated
against a throwaway example covering all classes, including negative cases for
each rule, but that example was never committed.
