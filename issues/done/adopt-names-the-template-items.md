---
difficulty: easy
parent: onboard-fitch-mvp
---

# ADOPT.md says where the template items come from

Step 5 of `ADOPT.md`, "Integrate the template items", says `.meta/assertions/`
"takes the template's files with the placeholders filled". The sync of step 4
copies only managed items, and step 5 names neither where the template items
are nor which placeholders they carry. In fitch-mvp the first round copied
them with `lib.bundle`'s `template_items()`, which takes reading
`.meta/bundle.yaml` to know of.

## Wanted

Step 5, in the Adoption Discipline that renders `ADOPT.md`, says:

- where the template items are: the entries `ownership: template` in the
  checkout's `.meta/bundle.yaml`, whose sources are under the checkout's
  `template/` (`template/.meta/assertions/` for the assertions);
- which of them a repository that already has its own `README.md` and
  `AGENTS.md` integrates rather than copies;
- the four placeholders to fill, each an upper-case name between double
  underscores: the portfolio's name, slug and description, and why it exists.
  This Issue does not spell them out, because the `surviving placeholders`
  gate step fails on any of them outside the template. No one template file
  carries all four: `template/.meta/assertions/structure.yaml` and
  `domain_vocabulary.yaml` beside it carry the name, slug and description,
  `decisions/DR-001.yaml` the name and why it exists, and
  `template/README.md` and `template/AGENTS.md` the name and description.
  The step should say which file needs which.
- that `decisions/DR-001.yaml` is taken from the template only as the shape
  of DR-001: the later step "Record the adoption" rewrites it as the decision
  to adopt, so step 5 points there instead of having it filled in twice.

Someone onboarding a second repository need not read `bundle.yaml` to follow
the step.

## Out of scope

- A tool that copies the template items or fills the placeholders.

## Done when

- Step 5 of the rendered `ADOPT.md` names every `ownership: template` entry
  in `.meta/bundle.yaml` by its target path (today `.meta/README.md`, the
  four files under `.meta/assertions/`, `issues/README.md`, `README.md` and
  `AGENTS.md`), says each is copied from `template/<path>`, and says which
  are integrated rather than copied.
- For each template file that carries a placeholder, the step names which of
  the four it carries, as in Wanted, by description and never by the
  placeholder's literal spelling.
- Step 5 says DR-001 is finished in "Record the adoption", and that step
  does not contradict it.
- A test reads the `ownership: template` entries from `.meta/bundle.yaml`
  and fails when the Adoption Discipline's step 5 omits one, so a template
  item added later cannot go unmentioned.

## The plan

1. **Rewrite step 5's statement** in `.meta/assertions/disciplines.yaml`
   (`work:discipline-step/adoption/integrate-the-template-items`). Keep the
   opening sentence about the plan's integrate and conflict entries and the
   closing symlink sentence. Between them, list the template items, each
   copied from the checkout's `template/<path>`: `.meta/README.md`,
   `.meta/assertions/structure.yaml`,
   `.meta/assertions/domain_vocabulary.yaml`,
   `.meta/assertions/personas.yaml`,
   `.meta/assertions/decisions/DR-001.yaml`, `issues/README.md`,
   `README.md` and `AGENTS.md`. Then say:
   - `README.md` and `AGENTS.md` are integrated (the product's content kept
     beside the conventions) where the repository already has them, and the
     rest are copied;
   - the placeholders by description, "the portfolio's name", "slug",
     "description" and "why it exists", never spelled out, because the
     `surviving placeholders` check in `.meta/checks/files/templates.py`
     scans every file outside `template/`. `structure.yaml` and
     `domain_vocabulary.yaml` take the name, slug and description, and
     `README.md` and `AGENTS.md` take the name and description;
   - `DR-001.yaml` carries the name and why it exists, but is copied for its
     shape only: "Record the adoption" (step 7), which stays as it is, writes
     it, and those two are filled there. Done when requires the placeholders
     of every file that carries one, DR-001 included.
   Read each template file's tokens again before writing, so the file-to-
   placeholder mapping matches what the files carry today.
2. **Re-render** with `just render`, so that `ADOPT.md` and
   `.meta/decisions.md` (if it changes) come from the assertion. Do not edit
   `ADOPT.md` itself.
3. **Add the test** as a tenth case in
   `.meta/checks/probes/tools/test_brownfield.py`. That probe is
   scaffold-only like `ADOPT.md` (DR-305), so it never runs in a portfolio
   that lacks `template/`. A new `_check_template_items_named(scaffold_dir)`
   loads `scaffold_dir/.meta/bundle.yaml` with `load_bundle`, reads the
   integrate-the-template-items statement out of
   `.meta/assertions/disciplines.yaml` with `yaml.safe_load`, and returns one
   problem per `template_items()` entry whose `dest_path()` does not appear
   in that statement, as a backticked full path. Step 1 therefore writes
   every target path in full (`.meta/assertions/domain_vocabulary.yaml`,
   not `domain_vocabulary.yaml`), as Done when asks. Wire it into
   `test_brownfield_probes`, update the docstring list, and make the pass
   message read "10 adoption cases".
4. **Check the test fails** when it should by removing one item name from the
   statement and running the probe, then putting the name back.

Risks:
- A literal placeholder in the statement, in `ADOPT.md` or in this Issue
  fails the `surviving placeholders` check. Describe them; never spell them.
- The statement is folded YAML (`>-`). A backtick path that breaks across
  lines still renders correctly, but keep each path on one line so the test's
  substring match finds it.
- A bare substring check would let `.meta/README.md` satisfy `README.md`.
  Match each path with its backticks, `` `README.md` ``, so only the exact
  target counts.

## Notes

- Step 5 is rewritten in `.meta/assertions/disciplines.yaml`, and `ADOPT.md`
  and `.meta/disciplines.md` were re-rendered from it. The file-to-placeholder
  mapping was read again from `template/` and matches Wanted.
- The test is `_check_template_items_named`, the tenth case of the
  brownfield adoption probes. It reads step 5 by its id. Removing
  `.meta/assertions/personas.yaml` from the statement made it fail with that
  path named. `disciplines.yaml` is scaffold-only, like this probe, so the
  case never runs in a portfolio.
- Departure from the plan: the new case took `test_brownfield.py` past its
  500-line ceiling. Rather than raise the baseline, the
  "planned X, expected Y" comparisons of the retains, conflicts and
  portfolio-items cases now share one helper, `_misplanned`. Their failure
  messages now read "<path> was planned <got>, expected <want>".
- `just render` in the seat's sandbox wrote `ADOPT.md` and
  `.meta/disciplines.md`, then stopped on a write under `.claude/skills/`,
  which the sandbox denies. No skill changed here, so nothing is missing.
- Step 5 no longer calls the template items "the files the sync does not
  copy", since the sync also skips the product's own files and every
  scaffold-only path. It now says the sync leaves the template items out, and
  that the template's `README.md` or `AGENTS.md` is integrated into the
  repository's own.
