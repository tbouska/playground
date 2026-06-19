"""Entry shim for the breadboard layout renderer.

Reads a hole-placement layout YAML (components addressed to breadboard holes
such as ``F12`` or rail holes such as ``B-28``) and writes a realistic
breadboard SVG + PNG, matching the schematic renderer so both views build the
same way.

The renderer itself lives in the :mod:`breadboard` package; this file stays a
single-file PEP-723 script so ``uv run --script render_layout.py <layout>`` and
``bin/render`` keep working. It forces matplotlib's headless ``Agg`` backend,
puts its own directory on ``sys.path``, then delegates to the package.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "matplotlib>=3.8",
#     "pyyaml>=6.0",
# ]
# ///

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from breadboard.parse import load_layout
from breadboard.render import render


def main() -> None:
    """Parse the YAML path from the command line and render the layout.

    :returns: None. The function writes the rendered image files to disk.
    :rtype: None
    """
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("layout.yaml")
    render(load_layout(source), source.with_suffix(""))


if __name__ == "__main__":
    main()
