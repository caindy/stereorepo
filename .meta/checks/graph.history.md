# History

<!--
### Missing check allowed language seeds to diverge silently from project Disciplines

LinkML validated schema conformance of Bootstrap assertions, but no check verified
that registered language standards comprehensively covered or exempted all
project-binding Disciplines. A newly adopted project Discipline could leave
language seed gates non-conforming without notice. Established:
`graph.bootstrap_discipline_coverage` guarantees that every Bootstrap in
the assertions explicitly maps each project-binding Discipline to implementing
gate steps or provides an explicit exemption reason (Article 7).

Evidence: `.meta/checks/probes/structure.py::bootstrap_discipline_coverage_probes`

