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

## The prompts are filled by a program too

`prompts/` holds the prompt each Role's pass runs with, one form per pass
and one more where a harness takes a form of its own (`reviewer-review-jules.md`),
and the door fills it for the rung about to run (solorepo's DR-281). Each pass
has its own fields, which are what its door writes and all a form may ask for:

| Form | Fields the door fills |
|---|---|
| `coder-take.md` | `<number>`, `<repository>`, `<level>`, `<branch_prefix>`, `<resume>` |
| `coder-rebase.md` | `<number>`, `<repository>`, `<branch>`, `<base>`, `<issue>` |
| `coder-answer.md` | those five and `<stop>` |
| `reviewer-review.md` | `<number>`, `<repository>`, `<head>`, `<login>`, `<agents>` |
| `reviewer-read.md` | `<number>`, `<repository>`, `<login>` |

Every form may also use `<effort>`, `<turns>`, `<minutes>` and `<budget>`, which
come from the rung rather than the door, the last a sentence naming the caps the
rung's harness binds. The reading form's `<level>` is not a field: it is the
verdict the session is there to decide, shown in the command it will type, and
the probe names it as the one angle bracket that survives on purpose. A block
between `<!-- claude -->` and `<!-- /claude -->`, or
`gemini`, is kept where its name is the rung's harness and dropped otherwise,
which is how one form says the one thing that differs by harness. Every other
angle bracket, such as the `<thread-id>` in a command the prompt shows, is the
session's to read as written. The rendered prompt is written to
`.review/prompt.md`, where the attempt step reads it, and `.review/routing.json`
beside it holds the chain and the fields, for the phase between two rungs to
render the next rung's prompt from.

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
