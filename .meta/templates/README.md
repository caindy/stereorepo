# .meta/templates

Forms filled in repeatedly, once per thing recorded. Inherited by a portfolio and
maintained here.

Distinct from solorepo's root `template/`, which is the seed Specialization
copies **once**. Both are seeds and both answer to A9 and A10 — a seed is data,
and it does not violate the rules it seeds — but they are filled at different
moments and by different hands.

They use different placeholder markers, and the difference is load-bearing:

| | Marker | Filled by | Left unfilled |
|---|---|---|---|
| solorepo's `template/` | double-underscore tokens | Specialization, once | fails the gate |
| `.meta/templates/` | `<angle brackets>` | an author, every time | expected — the form keeps them forever |

A form that used the first marker would fail the gate for the crime of being a
form.

## One of them is filled by a program

`constraints.md` is what bounds every agent on a review, and the review door
(`.meta/say/on`, solorepo's DR-264) fills it under `.review/` before the
reviewer's session starts: the pull request, the repository, the head, and the
trunk paths the run restored, counted and enumerated from `depth.CONTROL_PLANE`.
The door fills five of its angle brackets, `<number>`, `<repository>`, `<head>`,
`<count>` and `<paths>`, and a probe holds what it writes; every other angle
bracket in the form, such as the `<path>` in a command it shows, is the
reviewer's to read as written.

## Three of them are the source for `.github/`

`pull-request.md`, `issue.md` and `roadmap.md` each hold their form in a
```` ```markdown ```` fence, and `render.py` extracts the fence into
`.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/challenge.md` and
`.github/ISSUE_TEMPLATE/roadmap.md`.
**Edit the form here, never the generated file** — `check.py` fails on the
staleness either way, but only one of the two edits survives.

They carry no generated-by banner, unlike the prose satellites. The issue
template's front matter has to be the first thing in the file or GitHub will not
parse it, and a banner in the pull request form would ride along in the body of
every pull request thereafter.

`check_pr.py` reads the same fence to decide what a submitted body must contain,
which is what makes the angle brackets do double duty: they live in the form
forever, and one surviving into a submitted body is the form showing through.
