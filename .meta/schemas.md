## Schemas

_The ontologies, and how to exercise them._

| File | What it is |
|---|---|
| `work_ontology.yaml` | The umbrella: equations, load map, container. |
| `work/` | The work ontology in seven modules, each carrying its own reasoning. |
| `ddd_ontology.yaml` | The DDD umbrella: load map and container. |
| `ddd/` | DDD in four modules — core, skos, strategic, tactical. Restates the canon; never overrides it. |

Start from `work_ontology.yaml`'s load map, then read the module that covers
what you are touching. A module explains itself, in LinkML rather than in prose
(stereorepo's DR-323).

### Exercising them

No toolchain is checked in; the schema is exercised with `uvx`:

```bash
uvx --from linkml gen-json-schema .meta/work_ontology.yaml   # compiles?
uvx --from linkml linkml-validate -s .meta/work_ontology.yaml <instance.yaml>
uvx --from linkml linkml-lint .meta/work_ontology.yaml       # style only
```

`linkml-lint` reports warnings for uppercase enum values. That is the common
LinkML convention and they are left as they are.

The repository's instance data is the **ABox** in `assertions/` (stereorepo's DR-183).
Every assertion file is an instance document validated against the TBox schemas
before compiling to APM primitives or generating derived prose.

### Assertions

The schemas are **TBox**: the terminology. `assertions/` is the **ABox**: what
this repo actually states in that terminology — its Disciplines, its Ubiquitous
Language. Only the ABox compiles to APM primitives; the TBox is what validates it
before it does.

Assertions are split by **ownership**, because sync treats the halves
differently: it pulls `imported/` forward and never touches anything beside it.

| File | Owner | Validates against |
|---|---|---|
| `assertions/imported/authority.yaml` | stereorepo | `work_ontology.yaml` |
| `assertions/imported/charter.yaml` | stereorepo | `work_ontology.yaml` |
| `assertions/imported/disciplines.yaml` | stereorepo | `work_ontology.yaml` |
| `assertions/imported/structure.yaml` | stereorepo | `work_ontology.yaml` |
| `assertions/imported/vocabulary.yaml` | stereorepo | `ddd_ontology.yaml` |
| `assertions/decisions/` | this portfolio, one file per entry | `work_ontology.yaml` |
| `assertions/disciplines.yaml` | this portfolio | `work_ontology.yaml` |
| `assertions/domain_vocabulary.yaml` | this portfolio | `ddd_ontology.yaml` |
| `assertions/personas.yaml` | this portfolio | `work_ontology.yaml` |
| `assertions/structure.yaml` | this portfolio | `work_ontology.yaml` |
| `assertions/vocabulary.yaml` | this portfolio | `ddd_ontology.yaml` |

Fictional instances — a made-up portfolio, an invented persona — are fixtures,
not assertions, and do not belong here.

### The gate

`linkml-validate` checks what the schemas can express. `.meta/check.py` checks
what they cannot: four invariants crossing paths LinkML will not traverse, and
reference resolution, which crosses a file boundary because two tree roots are
two documents. Run both; the second assumes the first has passed.

Which slots hold references is read off the schema — a slot is a reference when
its range is a class with an identifier and it is not inlined — so the checker
cannot drift from the schemas the way a hand-kept list would.
