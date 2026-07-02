"""Entry shim for the schematic renderer.

The renderer itself lives in the :mod:`dupont` package; this file stays a
standalone PEP-723 script so ``uv run --script render_schematic.py <circuit>``
and ``bin/render`` keep working.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "matplotlib==3.11.0",
#     "schemdraw==0.19",
#     "pyyaml==6.0.3",
# ]
# ///

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dupont.render.schematic import main

if __name__ == "__main__":
    main()
