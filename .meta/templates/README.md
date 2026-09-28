# .meta/templates

Forms filled in repeatedly, once per thing recorded. Inherited by a portfolio and
maintained here.

Distinct from stereorepo's root `template/`, which is the seed Specialization
copies **once**. Both are seeds and both answer to A9 and A10 — a seed is data,
and it does not violate the rules it seeds — but they are filled at different
moments and by different hands.

They use different placeholder markers, and the difference is load-bearing:

| | Marker | Filled by | Left unfilled |
|---|---|---|---|
| stereorepo's `template/` | double-underscore tokens | Specialization, once | fails the gate |
| `.meta/templates/` | `<angle brackets>` | an author, every time | expected — the form keeps them forever |

A form that used the first marker would fail the gate for the crime of being a
form.

## The one form here

`decision.md` is the form a Decision is written on. `render.py` generates it
from the `Decision` class, so its headings are the schema's slots and cannot
drift from them. **Edit the class, never the form.**
