"""The body of `.meta/search.py`: retrieval over the assertions, the record and the wiki by meaning (stereorepo's DR-337).

`bm25` is the index; `build` fills it from the assertions and the wiki;
`benchmark` asks it the queries it must answer; `cli` is the command line the
script delegates to. `.meta/` goes on the path here, so `build` can import the
gate's collector as `checks.collect`.
"""
import sys
from pathlib import Path

META = Path(__file__).resolve().parents[2]
"""The `.meta/` directory, two levels above this package."""
ROOT = META.parent
"""The repository root."""
if str(META) not in sys.path:
    sys.path.insert(0, str(META))
