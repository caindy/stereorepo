"""The body of `.meta/hooks/signed_channel.py`: the one path to GitHub is the channel's, and the hook refuses every other (solorepo's DR-069).

In dependency order. `tables` names what the hook knows and draws on nothing
in the package; `shell` takes a command line apart and draws on `tables`;
`reach` judges a command line, segment by segment, and draws on both; `verdict`
is the entry that reads the event and exits with the judgement.
"""
