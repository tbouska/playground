"""Smoke render tests for new components (crystal).

Verifies that rendering a layout containing a crystal component completes
without raising and produces a non-empty SVG file.
"""

from pathlib import Path

import render_layout
from breadboard.model import Component, Layout


def test_crystal_renders_without_error(tmp_path: Path) -> None:
    crystal = Component(kind="crystal", ref="X1", value="16MHz", legs=("A1", "A3"))
    layout = Layout(title="t", columns=10, components=(crystal,), style=None)
    render_layout.render(layout, tmp_path / "o")
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")
    assert svg, "crystal render produced an empty SVG"
