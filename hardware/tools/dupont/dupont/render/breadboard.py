"""Render a breadboard layout from the interchange :class:`Circuit` model.

Imports:
    dupont.formats.breadboard.exporter -- :func:`collapse_to_layout` collapses
        the :class:`Circuit` model back to the :class:`breadboard.model.Layout`
        draw structures.
    breadboard.render -- :func:`render` draws a :class:`Layout` and saves it as
        SVG and PNG.
    dupont.model.entities -- the canonical :class:`Circuit` interchange model
        the draw path now reads.
"""

from pathlib import Path

from breadboard.render import render
from dupont.formats.breadboard.exporter import collapse_to_layout
from dupont.model.entities import Circuit


def render_breadboard(circuit: Circuit, out_stem: Path) -> None:
    """Render a breadboard FROM THE INTERCHANGE MODEL to ``<stem>.svg`` + ``.png``.

    Collapses the :class:`Circuit` model to its :class:`breadboard.model.Layout`
    draw structures and saves the images. :func:`collapse_to_layout` is the only
    model-to-draw bridge, so no layout parsing happens in this draw path.

    :param circuit: The interchange model to render.
    :type circuit: Circuit
    :param out_stem: The output path without extension.
    :type out_stem: Path
    :returns: None. The function writes the two image files to disk.
    :rtype: None
    """
    render(collapse_to_layout(circuit), out_stem)
