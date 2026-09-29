# History

### A verdict that moved between runs read as a cold-start defect

`just dereference` was reported finding `x` on the first run after a change
and passing on the run that followed, four times in one session, each first run
printing `Installed 84 packages` from a cold `uvx` cache (#804). No
cold-start mechanism exists. Probed on `--sample 6`, whose rotation is keyed to
the commit count and so holds the same six pairs across runs: `--pairs`, which
asks nothing, printed identical pairs from a cold cache and from a warm one, so
the deterministic half does not move; five askings of those same six pairs — one
cold, four warm — returned five different sets of failing citations (`DR-050`
and `DR-052`; `DR-050`; `A8` and `DR-052`; `DR-052`; `A8`, `DR-050` and
`DR-052`), so the verdict moves warm to warm at the rate it moves cold to warm.
The install correlates because it falls on the run a coder then re-runs, not
because the reading reads anything differently while the environment is being
built. Established: an `x` report closes by saying its marks are a model's
reading, to be answered rather than asked again, which is the re-run habit
DR-134 names as the cost of a provisional red.

Evidence: `.meta/checks/probes/tools/dereference.py::dereference_probes`
