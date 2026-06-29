"""Shared test config for the breadboard renderer suite.

`render_layout.py` is a single-file PEP-723 script (not a package) living one
directory up. Put that directory on `sys.path` so the tests can `import
render_layout`. The module forces matplotlib's Agg backend at import, so this is
headless-safe with no display configuration needed here.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
