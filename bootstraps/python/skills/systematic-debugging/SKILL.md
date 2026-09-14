---
name: systematic-debugging
description: >-
  Use when something is broken and the cause is not obvious - reproduce, isolate, locate the
  layer it actually died in, then fix. Use when a test fails mysteriously, behaviour differs
  between environments, or a change had an effect nobody predicted. Derived from
  obra/superpowers (MIT), extended with four rules that each cost real time.
---

# Systematic debugging

## The loop

1. **Reproduce it deterministically.** A bug you cannot reproduce on demand is a bug you
   cannot verify you fixed. If it is intermittent, find the ordering or state that triggers
   it and *plant* that, rather than re-running until it appears.
2. **Locate the layer it died in.** See below — this is where most time is lost.
3. **Form one hypothesis and a cheap test that could refute it.** If your test cannot come
   back negative, it is not a test.
4. **Fix the cause.** If you cannot explain why the fix works, you have not found the cause.
5. **Prove it.** Break it again and watch the failure return, then fix and watch it go. A
   fix you never saw fail is a coincidence you have adopted.
6. **Record it** if the conclusion outlives the fix — `docs/JOURNAL.md`.

## Four rules that each cost real time

**Locate the layer a failure DIED in before proposing machinery for another.** The
expensive mistake is designing a fix for a layer that was working. Trace where the value
actually became wrong; it is frequently earlier and duller than the interesting subsystem
you suspected.

**A warning seen while debugging X is not evidence about X.** Check which component emitted
it before writing it up. Two subsystems producing similar-looking output is enough to
mis-attribute a warning and chase the wrong one — this has been done, and written up
confidently, more than once.

**Check the label before believing a failure.** Repeatedly, a "wrong" result has turned out
to be a wrong expectation, or a probe reading the wrong input. Verify that the thing you are
comparing against is what you think it is *before* concluding the code is broken.

**Establish that the process stopped before diagnosing a hang.** An operation with no
completion record, followed seconds later by a restart, is a **shutdown artifact**, not a
stall. Confirm the process actually stopped producing output at that point; otherwise you
will debug a hang that never happened.

## Environment-shaped failures

Before assuming a code defect, rule these out — they are common and they mimic real bugs.
`docs/TRAPS.md` has the full list.

- Green in one checkout, red in another → a missing gitignored artifact (`.env`, `.venv`, a
  symlink). Compare **skip counts**, not pass/fail.
- A script importing a different copy of the package than you expect → check
  `module.__file__`.
- A test that passes alone and fails in the suite → shared state, or an assertion scoped to
  the whole store rather than the test's own data.
- A hang with no output → the watchdog is your friend; `faulthandler_exit_on_timeout` is on
  so a hung test is a red gate, not a busy one.

## The class that hides best

**Failures that produce no signal.** Correct types, clean lint, no exception at the failure
site, and no record. The **absence is the evidence** — so no amount of reading what the log
*says* will find them. Something has to notice what it does **not** say: a turn that opened
and never closed, a fallback that fired and recorded nothing, a task whose exception nobody
retrieved.
