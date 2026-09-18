"""What an Artifact owes the record: a path that exists, an Article number that is reserved, and a Decision that names what enacts it.
"""

import yaml

from citations import FOREIGN
from collect import META, ROOT, check

# The record itself: naming it under `enacted_in` satisfies the letter of A20 and
# defeats the point, so it does not count. `.meta/work/decisions.yaml` is the
# schema and is a legitimate target, which is why this is a prefix and not a word.
RECORD = (".meta/assertions/decisions/", ".meta/decisions.md")


@check("artifact paths")
def artifact_paths(index):
    """Every Artifact is a file that exists.

    The reference to an Artifact is resolved by the references check, like any
    other; what no schema can know is whether the path on the far side still
    names something. One check per Artifact rather than one per citation, which
    is the whole reason for making it an entity.
    """
    return [f"{ident}: {obj['path']} does not exist"
            for ident, (cls, obj, _) in sorted(index.items())
            if cls == "Artifact" and not (ROOT / obj["path"]).is_file()]


@check("reserved article numbers")
def reserved_article_numbers(index):
    """A retired Article's number is never issued again.

    The reservation is the only thing a retirement leaves behind, and it exists
    so that a citation written years ago cannot silently come to mean something
    new. Nothing else defends it: the Charter is hand-numbered, and a hole is an
    absence, which nothing notices on its own.
    """
    charter = yaml.safe_load(
        (META / "assertions" / "imported" / "charter.yaml").read_text()) or {}
    holes = charter.get("retired_articles") or []
    retired = {r["number"] for r in holes}
    live = {int(a["id"].rsplit("/", 1)[-1]) for a in charter.get("articles") or []}
    problems = [f"A{n} is retired and issued again; a retired number is reserved forever"
                for n in sorted(retired & live)]
    # The pointer to the account is prose, `solorepo's DR-085`, since the entry
    # is solorepo's and the Charter goes to every portfolio (solorepo's DR-121). A string
    # slot is a slot nothing resolves, so the form is held here and the number
    # by `cited decisions`, which together are what the reference check was.
    problems += [f"A{r['number']}: retired_by is {r.get('retired_by')!r}, and the account "
                 "of a retirement is cited as solorepo's DR-nnn"
                 for r in holes if not FOREIGN.fullmatch(str(r.get("retired_by", "")))]
    return problems


@check("enacted decisions")
def enacted_decisions(index):
    """A20. An adopted decision names an Artifact that carries its rule (solorepo's DR-078).

    Whether the Artifact exists is a reference, resolved with every other. What
    is left here is the arithmetic no schema states: ADOPTED means in force, and
    in force with nowhere to be read from is in force over nobody.

    Naming the record itself would satisfy the letter and defeat the point, so
    it does not count.
    """
    record = {ident for ident, (cls, obj, _) in index.items()
              if cls == "Artifact" and obj["path"].startswith(RECORD)}
    return [f"DR-{ident.rsplit('/', 1)[-1]} is adopted and names no artifact "
            "carrying its rule"
            for ident, (cls, obj, _) in sorted(index.items())
            if cls == "Decision" and obj.get("status") == "ADOPTED"
            and not [a for a in (obj.get("enacted_in") or []) if a not in record]]
