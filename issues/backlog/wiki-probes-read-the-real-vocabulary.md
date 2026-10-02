# Keep the wiki parity probes off the portfolio's real vocabulary

The `wiki probes` step fails in every portfolio that mints a domain concept.
Its case "stereorepo pages of a minted discipline and concept"
(`.meta/checks/probes/knowledge.py`) hands `ubiquitous_language_wiki_parity`
a synthetic set of wiki pages and expects no finding. But
`_domain_vocabulary_problems` in `.meta/checks/files/wiki.py` reads the
repository's real `.meta/assertions/domain_vocabulary.yaml` whatever pages it
is given. stereorepo's own domain vocabulary has no concepts, so the probe
passes here. fitch-mvp minted 24 concepts, each with its page in
`wiki/fitch/`, and the probe fails there, reporting each concept as having no
wiki page because the synthetic set holds none of them.

This is the same class of defect as `_probe_adopt`: a check that is right in
stereorepo and wrong in every portfolio (`portfolio-gate-before-landing`).

## Wanted

A probe of the parity check reads the vocabulary its case supplies, or none,
and never the repository's own. The check itself, run on the real tree, still
reads the real vocabulary.

## How anyone will know it is done

- A probe over a temporary portfolio whose `domain_vocabulary.yaml` holds a
  concept with its page passes, and the same portfolio without the page
  fails the real check.
- stereorepo's `wiki probes` step passes as before.

## Out of scope

- Running a portfolio's gate before landing, which
  `portfolio-gate-before-landing` covers.
