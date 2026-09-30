# Is the pair worth its second seat?

The pair loop runs two seats on every Issue, which roughly doubles what an
Issue costs to read, since both seats read the same code. Its first day (11
units of work, 88 turns, about 110 minutes of turns and about $28 of
API-equivalent usage) showed that it converges, runs without the developer,
and lands work that passes the gate. It did not show that the second seat
catches enough to be worth the cost, against one careful seat and the gate.

Effectiveness is judged on four things, each measured from what the loop
records:

| Criterion | Measure |
|---|---|
| Quality | defects found after landing that trace to an Issue; desk-check rejections; how many of the secondary seat's changes are substantive |
| Autonomy | the developer's interventions per Issue — pauses, send-backs, takeovers, `Needs elaboration` sections — by difficulty |
| Time | wall-clock per Issue by difficulty, gate included; turns per stage |
| Tokens | API-equivalent cost per landed Issue, reads and writes apart |

The question is answered by running comparable Issues with the secondary seat
disabled and comparing the four, and the answer is a Decision Record. It needs
the loop's instruments (`flight-instruments`) first, and Issues outside the
loop's own code: a product repository, a UI, a vague bug report, a
`developer` Issue.
