---
difficulty: easy
---

# Render a scope note's paragraphs as paragraphs

`.meta/lib/render/pages.py` writes each scope note into `.meta/vocabulary.md`
as `**Label.** {scope_note}` (`f"**{c['pref_label']}.** {c['scope_note'].strip()}\n"`).
A folded (`>-`) scope note with a blank line between paragraphs reaches it
with a single newline there, so the second paragraph renders as a line break
inside the first rather than a paragraph of its own. The scope notes of
Ubiquitous Language, Claim and Evidence show it today;
`why-fork-inherited-terms` avoided it for Portfolio by keeping that note to
one paragraph.

## How to reproduce

Run `just render` and open `.meta/vocabulary.md` at `**Claim.**`: "The same
class continues…" follows the first paragraph on the next line with no blank
line between them.

## Wanted

Every paragraph of a scope note renders as its own Markdown paragraph in
`.meta/vocabulary.md`, the first still led by the bold label. A folded
scalar keeps a paragraph break as one newline, so each newline in the
loaded scope note becomes a blank line.

## Out of scope

- Definitions, and any other page's rendering.
- What Claim's scope note says (`claim-scope-note-channel-verb`).

## Done when

- In `.meta/vocabulary.md`, the second paragraph of Claim's scope note ("The
  same class continues…") is separated from the first by a blank line, and
  likewise for Ubiquitous Language and Evidence.
- A probe under `.meta/checks/probes/` renders a concept with a
  two-paragraph folded scope note and finds two paragraphs separated by a
  blank line, the first beginning with the bold label.
