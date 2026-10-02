# Render a scope note's paragraphs as paragraphs

`.meta/lib/render/pages.py` writes each scope note into `.meta/vocabulary.md`
as `**Label.** {scope_note}`. A folded (`>-`) scope note with a blank line
between paragraphs reaches it with a single newline there, so the second
paragraph renders as a line break inside the first rather than a paragraph
of its own. The scope notes of Ubiquitous Language, Claim and Evidence show
it today; `why-fork-inherited-terms` avoided it for Portfolio by keeping that
note to one paragraph.

## Wanted

Every paragraph of a scope note renders as its own Markdown paragraph in
`.meta/vocabulary.md`, the first still led by the bold label.

## Done when

In `.meta/vocabulary.md`, the second paragraph of Claim's scope note ("The
same class continues…") is separated from the first by a blank line, and a
test of the renderer shows a two-paragraph scope note rendering as two
paragraphs.
