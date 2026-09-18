"""The body of `.meta/timing.py`: what the workflows cost in time, read from GitHub (solorepo's DR-157).

`github` reads the runs and jobs; `arithmetic` turns them into spans and
percentiles and the critical path; `routing` says what each run was routed to
and why; `screen` prints the rows; `cli` is the command line the script
delegates to.
"""
