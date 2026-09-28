"""The body of `.meta/wikisplain.py`: authoring a wiki concept page the Knowledge Management way (stereorepo's DR-187).

`lead` writes the definition a page opens with; `duplicates` looks for the
concept already on a page; `links` embeds closed-world wikilinks; `pages`
scaffolds and verifies a page; `cli` is the command line the script delegates
to.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
"""The repository root, resolved once by the package so its modules agree on the wiki and assertions they read."""
