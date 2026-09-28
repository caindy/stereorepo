"""The bodies of the scripts under `.meta/`, one package per script (stereorepo's DR-217).

A script at `.meta/<name>.py`, or a hook at `.meta/hooks/<name>.py`, stays
where the justfile, the workflows, the harness settings and the structure
assertions invoke it, and delegates to `.meta/lib/<name>/`. The package is what
a reader opens; the script is what a shell runs. A script's own directory is
`.meta/`, so its package imports as `lib.<name>` with nothing added; a hook one
directory down puts `.meta/` on the path first. `.meta/lib/gh.py` is the single
shared base GitHub CLI runner, shared across read-only tools and mutation
channels without being the body of a single script (solorepo's #748).
"""
