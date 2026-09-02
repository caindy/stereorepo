## Schemas

_The ontologies, and how to exercise them._

_The ontologies, and how to exercise them._

| File | What it is |
|---|---|
| `work_ontology.yaml` | The umbrella: equations, load map, container. |
| `work/` | The work ontology in seven modules, each carrying its own reasoning. |
| `ddd_ontology.yaml` | The DDD umbrella: load map and container. |
| `ddd/` | DDD in four modules — core, skos, strategic, tactical. Restates the canon; never overrides it. |

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

### Assertions

The schemas are **TBox**: the terminology. `assertions/` is the **ABox**: what
solorepo actually states in that terminology — its Disciplines, its Ubiquitous
Language. Only the ABox compiles to APM primitives; the TBox is what validates it
before it does.

| File | Validates against |
|---|---|
| `assertions/disciplines.yaml` | `work_ontology.yaml` |
| `assertions/vocabulary.yaml` | `ddd_ontology.yaml` |

Fictional instances — a made-up portfolio, an invented persona — are fixtures,
not assertions, and do not belong here.
