"""Shared test config for the consolidated dupont package suite.

The distribution root (this file's grandparent directory) holds the importable
top-level packages `dupont` and `breadboard` plus the single-file `render_layout`
PEP-723 script. Put that root on `sys.path` so the whole test tree can `import
dupont`, `import breadboard`, and `import render_layout`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
