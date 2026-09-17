"""The bodies of the scripts under `.meta/`, one package per script (solorepo's DR-217).

A script at `.meta/<name>.py` stays where the justfile, the workflows and the
structure assertions invoke it, and delegates to `.meta/lib/<name>/`. The
package is what a reader opens; the script is what a shell runs.
"""
