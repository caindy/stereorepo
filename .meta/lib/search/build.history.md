# History

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Evidence: `<path>::<symbol>`
-->

### Every frontmatter list item was indexed at title weight, not the declared synonyms

The wiki half of the index scraped every `- ` item out of a page's frontmatter
block with a regular expression and folded the lot into the title field, which
is the highest weight the index carries. It held while `synonyms` was the only
list-valued key any page declared, so the name and the behaviour agreed by
accident; the next key anybody added — `see_also`, a list of contexts, a list
of authors — would have made the page answer searches for words nobody declared
findable. The `wiki synonyms` gate step reads `synonyms` by name out of the
parsed block, so a forbidden word arriving through another key would have been
indexed at title weight with the step blind to it, and the two readers of the
same block would have disagreed about what the title field holds. Established:
the block is parsed as YAML and only a list-valued `synonyms` reaches the title
field.

Evidence: `.meta/checks/probes/tools/search.py::search frontmatter`
