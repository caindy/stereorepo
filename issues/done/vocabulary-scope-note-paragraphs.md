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
- A probe beside the existing render probes in
  `.meta/checks/probes/tools/render.py` renders a concept with a
  two-paragraph folded scope note and finds two paragraphs separated by a
  blank line, the first beginning with the bold label. The same probe finds
  a one-paragraph scope note rendered exactly as before, as one line led by
  the label. That module's docstring is about writes the sandbox denies, so
  it is widened to cover what the new probe checks.
- Every other scope note in `.meta/vocabulary.md` is unchanged: none of
  them holds a paragraph break today.

## The plan

1. **Renderer.** In `_scheme` in `.meta/lib/render/pages.py`, write each
   scope note as `c['scope_note'].strip().replace("\n", "\n\n")` after the
   bold label. `vocabulary()` joins the entries with `"\n"` and each already
   ends in `"\n"`, so the notes stay separated from each other as they are.
   A one-paragraph note holds no newline and comes out byte-for-byte the same.
2. **Probe.** Add a `@check("render scope note probes", pre=True)` to
   `.meta/checks/probes/tools/render.py`. It loads two concepts with
   `yaml.safe_load`, one with a two-paragraph `>-` scope note and one with a
   one-paragraph note, so the input is what the real loader produces. It then
   calls `pages._scheme({"name": "S"}, members, members)` and checks two things:
   - the two-paragraph note's entry is `**A.** first\n\nsecond\n`;
   - the one-paragraph note's entry is `**B.** only\n`.

   Each concept needs `id`, `pref_label` and `definition`, because `_scheme`
   puts the concepts that are not hubs into a term table, and that table
   reads `definition`.

   Widen the module docstring so that it also covers how a scope note's
   paragraphs render.
3. **Re-render.** Run `just render` and commit `.meta/vocabulary.md`. The
   diff should add one blank line at each paragraph break in the scope notes
   of Ubiquitous Language (one break), Claim (two) and Evidence (three), and
   change nothing else.

**Tests:** the new probe, plus the vocabulary diff from step 3 read by eye.

**Risk:** small. The `replace` would also double a newline inside an
indented, literal-style line, but no scope note has one today, as my partner
confirmed in the backlog turn. `_scheme` is private, so the probe depends on
its signature. That is acceptable: `vocabulary()` reads the real assertion
files, so testing through it would test the repository's data rather than
the rule.

The scope-note line was one of the five lines in `pages.py` longer than the
100-character `line-length`, and `.meta/checks/lines.baseline.yaml`
records `pages.py: 5`. The `meta lines` step fails a file whose count moves
in either direction. If the step stays on one line, the baseline stays at 5.
If it is split so that every line fits, lower the baseline to 4 in the same
commit. `.meta/checks/probes/tools/render.py` has no entry in the baseline, so
it may hold no line over 100 characters. Every line of the new probe has to
fit, including its `@check` line and its docstrings.

## Implementation notes

- The step is split over two lines, so `pages.py` now holds four lines over
  the limit and its baseline is lowered to 4.
- The lines this adds to `pages.py` moved a citation in
  `issues/done/adopt-probe-passes-in-a-portfolio.md`, which now cites line
  199. The plan's own citations of the renderer and the baseline lost their
  line numbers, since their line content changed.
- The probe's YAML is in block style: a `>-` scalar cannot sit inside a
  flow mapping.
- `.meta/vocabulary.md` gained six blank lines and nothing else, one at
  each paragraph break of the three notes.

## Pair notes

> **primary, backlog turn 1**
>
> I made one small change. The Issue was already precise enough to plan, so I left `difficulty: easy` as it was.
>
> I checked what the Issue claims against the code:
> - `.meta/lib/render/pages.py` writes each scope note as `**Label.** {scope_note}` and does nothing to the paragraph breaks.
> - In `.meta/vocabulary.md`, the scope notes of Ubiquitous Language, Claim and Evidence each continue on the very next line, with no blank line between paragraphs. So the bug is there as described.
>
> **The change:** the "Done when" section asked for a probe somewhere under `.meta/checks/probes/`. It now names the file: `.meta/checks/probes/tools/render.py`, where the existing render probes already are.
>
> The other sections are already clear and stay as they were: what is wanted, what is out of scope (definitions, other pages, and what Claim's note says), and the visible result in `vocabulary.md`.

> **secondary, backlog turn 2**
>
> I made two small additions to the "Done when" section of the Issue and left `difficulty: easy` as it was.
>
> I checked the Issue against the code first, and it is accurate:
> - **Where the bug is:** `_scheme` in `.meta/lib/render/pages.py` writes each scope note on one line after its bold label and keeps the paragraph breaks as single newlines.
> - **Which notes show it:** in `.meta/assertions/imported/vocabulary.yaml`, the only scope notes with paragraph breaks are those of Ubiquitous Language, Claim and Evidence. All three are plain folded text with no extra-indented lines. So the fix the Issue asks for, turning each newline into a blank line, can't damage anything else.
>
> What I added:
> - **Single-paragraph notes:** the new probe must also check that a scope note with one paragraph still renders exactly as before. Every other note in `.meta/vocabulary.md` must come out unchanged.
> - **The probe file's description:** `.meta/checks/probes/tools/render.py` is described only as checking writes the sandbox blocks. The Issue now says that description should be widened to cover the new probe.

> **primary, backlog turn 3**
>
> I changed nothing this turn. My partner's two additions to "Done when" hold up against the code, and `difficulty: easy` still fits.
>
> - **The probe file's description:** the opening docstring of `.meta/checks/probes/tools/render.py` really does cover only writes the sandbox blocks. It needs widening once the scope-note probe goes into that file, so it is right for the Issue to ask for that.
> - **Single-paragraph notes:** requiring that a one-paragraph scope note renders exactly as before guards against the fix changing the notes that are fine today. My partner confirmed that only the scope notes of Ubiquitous Language, Claim and Evidence contain paragraph breaks, so that check can't clash with the fix.

> **primary, todo turn 1**
>
> I added a `## The plan` section to the Issue file and changed no code. The fix is three small steps:
>
> 1. **The renderer:** in `_scheme` in `.meta/lib/render/pages.py`, turn each newline in a scope note into a blank line, so each paragraph becomes its own Markdown paragraph. A one-paragraph note has no newline in it, so it comes out exactly as it does now.
> 2. **The probe:** add a new check to `.meta/checks/probes/tools/render.py` that builds two concepts from YAML, one with a two-paragraph scope note and one with a single paragraph. It renders them through the same function `.meta/vocabulary.md` uses and compares the output for each exactly. The file's opening docstring gets widened to cover this new check.
> 3. **Re-render:** run `just render` and commit `.meta/vocabulary.md`. The only change should be one new blank line inside each of the scope notes of Ubiquitous Language, Claim and Evidence.
>
> The plan records two small risks:
> - A scope note with an indented, literal-style line would get an extra blank line too, but none has one today.
> - The probe calls `_scheme`, a private function. That is acceptable because the probe sits next to the code it checks.

> **secondary, todo turn 2**
>
> I made three small corrections to the plan's text and changed no code. The plan itself is sound: the fix belongs in `_scheme` in `.meta/lib/render/pages.py`, and a one-paragraph scope note has no newline, so it comes out unchanged.
>
> - **The probe's test data:** each test concept must carry `id`, `pref_label` and `definition`. `_scheme` puts concepts without narrower terms into a term table, and that table reads `definition`. A probe built without it would crash.
> - **Why the probe calls the private function:** the plan said this was fine because the probe sits beside the code it checks. It doesn't: the probe is under `.meta/checks/`, not next to `pages.py`. The plan now gives the real reason: `vocabulary()` reads the real assertion files, so testing through it would test the repository's data rather than the rendering rule.
> - **A new risk, about line length:** line 61 is already one of the five lines in `pages.py` longer than the 100-character limit. `.meta/checks/lines.baseline.yaml` records exactly 5 such lines for this file, and the line-length check fails if that count goes up or down.
>   - If line 61 stays one long line, the count stays at 5.
>   - If it gets split so every line fits, the baseline must drop to 4 in the same commit.

> **primary, todo turn 3**
>
> I kept all three of my partner's corrections and added one sentence to the plan's line-length risk. I changed no code.
>
> **What I checked:**
> - **`pages.py`:** it has exactly five lines over 100 characters (lines 1, 16, 47, 60 and 61), and `.meta/checks/lines.baseline.yaml` records 5 for it. So my partner's line-length note is right. Line 61 gets longer with the fix but is still one line, so the count stays at 5.
> - **The probe file:** `.meta/checks/probes/tools/render.py` has no entry in that baseline. The baseline file's header says a file with no entry may hold no line over 100 characters.
>
> **What I added:** every line of the new probe, including its `@check` line and its docstrings, must fit within 100 characters. Otherwise the line-length check fails that file.

> **secondary, todo turn 4**
>
> I changed nothing this turn. My partner added one sentence: every line of the new probe must fit within 100 characters. That's right. `.meta/checks/probes/tools/render.py` has no entry in the line-length baseline, so it may hold no line over 100 characters. The file is also only 135 lines long, so adding a probe won't take it past its file-size ceiling. The plan covers what's needed to implement it.

> **primary, in-progress turn 1**
>
> Each paragraph of a scope note now shows as its own paragraph in `.meta/vocabulary.md`, and `just gate meta` passes. I ran no other gate, because the change touches nothing under `pair/` or `bootstraps/`.
>
> - **The fix:** in `.meta/lib/render/pages.py`, each newline in a scope note now becomes a blank line, and a short docstring says why. I split that line in two so it fits the 100-character limit. That leaves four over-long lines in `pages.py`, so I lowered its entry in `.meta/checks/lines.baseline.yaml` from 5 to 4.
> - **The new check:** "render scope note probes" in `.meta/checks/probes/tools/render.py` builds two concepts from YAML, one with a two-paragraph scope note and one with a single paragraph. It checks that the first comes out as `**A.** first\n\nsecond\n` and the second as `**B.** only\n`. It passes, and I widened the file's opening docstring to cover it.
> - **The re-render:** `just render` added six blank lines to `.meta/vocabulary.md` and changed nothing else. That is one line at each paragraph break: one in Ubiquitous Language, two in Claim and three in Evidence. The plan expected one per note, so I corrected it.
> - **Line citations:** the lines I added shifted code that other files cite by line number, and the gate's citation check failed on that.
>   - `issues/done/adopt-probe-passes-in-a-portfolio.md` now cites line 199 of `pages.py` instead of 194.
>   - Two of the plan's citations whose lines changed content now give the file without a line number.
>
> I recorded these points under "Implementation notes" in the Issue file and committed the work as `f1f8a3d`.

> **secondary, in-progress turn 2**
>
> My partner's implementation was correct, and I made one small style fix. The new probe in `.meta/checks/probes/tools/render.py` had three blank lines before it. I cut that to the usual two, and `just gate meta` passes.
>
> What I checked:
> - **The fix:** `.meta/lib/render/pages.py` now turns each newline in a scope note into a blank line. A one-paragraph note has no newline, so it renders exactly as before.
> - **The new probe:** it would have failed on the old code, which produced `**A.** first\nsecond\n` where the probe wants `**A.** first\n\nsecond\n`. So it really guards the fix.
> - **`.meta/vocabulary.md`:** it gained six blank lines, one at each paragraph break in Ubiquitous Language, Claim and Evidence, and nothing else changed.
> - **Line-length baseline:** splitting the scope-note line in `pages.py` leaves four lines over 100 characters, so the baseline entry correctly drops from 5 to 4.
> - **Citation fixes:** the moved line-number citations in the Issue and in `issues/done/adopt-probe-passes-in-a-portfolio.md` are right.
>
> The fix is committed as `b2f8ced`.

> **primary, in-progress turn 3**
>
> I changed nothing this turn, and `just gate meta` still passes.
>
> My partner's one change was to remove an extra blank line before the new check in `.meta/checks/probes/tools/render.py`. That brings it to the usual two blank lines, so it is right. The work the plan asked for is done:
> - **The fix:** each paragraph of a scope note now renders as its own paragraph in `.meta/vocabulary.md`.
> - **The new check:** it compares the rendered output exactly for a two-paragraph note and a one-paragraph note.
> - **The line-length baseline:** the entry for `pages.py` is lowered from 5 to 4.
> - **Line citations:** the citations my added lines had moved are corrected.
