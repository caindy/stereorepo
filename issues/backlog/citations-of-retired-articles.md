# Stop citing retired Articles as though they were in force

Article 15, Article 16, Article 18 and Article 19 are retired (`.meta/charter.md`
shows each as "Retired."), but live prose still cites two of them for a rule:

- `.meta/assertions/imported/vocabulary.yaml`, the Concept's `scope_note`,
  avoids "Article" to protect "the Charter's empirical clauses
  (stereorepo's Article 1, stereorepo's Article 15)".
- `bootstraps/python/skills/py-quality-setup/SKILL.md` (the source;
  `.meta/lib/apm_compile/bootstrap.py` reads `bootstraps/python/skills/` and
  `just render` writes the copy under `bootstraps/python/.apm/skills/`) says "A19 says a
  commit that does not name its Actor is …", and cites A19 again further
  down. Both passages also send commits through `.meta/say/commit` and its
  Actor Trailer; `.meta/say/` and the Actor class are gone too.

Found while trimming DR-179 to DR-217 (`trim-decision-records-179-217`).

## Wanted

Each citation of a retired Article either names a current Article or
Decision that carries the rule, or goes, with the sentence restated so it
does not lean on it. The probe case in
`.meta/checks/probes/tools/comments.py` that quotes A19 is a test string
for comment shapes and can stay.

## Done when

Outside the decision log, the Issues, the history logs and the probe's test
string, a grep for Article 15, 16, 18 and 19 (and A15, A16, A18, A19) finds
only the charter's "Retired." headings.
