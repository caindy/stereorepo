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

Someone onboarding a second repository need not read `bundle.yaml` to follow
the step.

## Out of scope

- A tool that copies the template items or fills the placeholders.
