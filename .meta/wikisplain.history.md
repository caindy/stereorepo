# History

### The tool read a repository three directories above the one it was run in

`cli.main` resolved the tree it reads as `pathlib.Path(__file__).parent.parent`,
which was the repository root while the command line lived in
`.meta/wikisplain.py` and became `.meta/lib` when it moved to
`.meta/lib/wikisplain/cli.py`. Every read was then relative to a directory with
no `wiki/` and no `.meta/assertions/`, so `find_duplicates` found nothing and
`--check-duplicate "Knowledge Management"` answered `Clear` over a concept the
wiki, the vocabulary and the disciplines all hold, while a scaffold would have
been written to `.meta/lib/wiki/` (DR-231). The
probes did not see it because each called the library functions with `root=ROOT`
and none went through the command line. Established: `ROOT` is module-level in
`cli.py`, named from `parents[3]`, and two probes go through `cli.main` itself —
a collision and a forbidden synonym, each read from its exit code.

Evidence: `.meta/checks/probes/knowledge.py::cli_probes`

### A synonym scaffolded from a word the concept's `avoid` list forbids

`--synonyms` was documented as "synonyms or alternate labels" and took a word on
the concept's `avoid` list without complaint. It wrote that word
into the frontmatter that `.meta/lib/search/build.py` folds into the title field of the BM25 index
(DR-231). Established: `avoided_synonyms` reads the
proposed synonyms against the `avoid` list of the concept minted at the page's
slug, matched on the slugified word, and `cli.main` refuses before the page is
generated, naming the word, the concept and the vocabulary file that forbids it.
`--force` does not pass it: that flag overwrites a duplicate page, and this
refusal is not about a collision.

Evidence: `.meta/lib/wikisplain/duplicates.py::avoided_synonyms`
