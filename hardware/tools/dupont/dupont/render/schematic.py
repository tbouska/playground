"""Render a microcontroller-to-load schematic from a declarative YAML file.

This module reads a circuit description (a microcontroller driving N channels,
each through a series resistor into a multi-pin load such as an RGB LED) and
renders it to SVG and PNG with :mod:`schemdraw`. The YAML file is the source of
truth that lives in version control; the images are reproducible build outputs.

Imports:
    dupont.model.entities -- the canonical :class:`Circuit` interchange model
        the draw path now reads.
    dupont.formats.circuit.importer -- :func:`import_circuit` parses a
        ``circuit.yaml`` file into the :class:`Circuit` model.
    dupont.formats.circuit.exporter -- :func:`collapse_to_schematic` collapses
        the :class:`Circuit` model back to the :class:`Schematic` draw structures.
    dupont.formats.circuit.schema -- provides :class:`Schematic`, the draw-side
        value object :func:`build_drawing` consumes.
    pathlib -- resolve the input and output file paths.
    sys -- read the optional YAML path from the command line.
    matplotlib -- force the non-interactive ``Agg`` backend before schemdraw
        imports it, so rendering works headless in CI.
    schemdraw -- build and save the drawing via :class:`schemdraw.Drawing` and
        the elements in :mod:`schemdraw.elements`.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import schemdraw
import schemdraw.elements as elm

from dupont.formats.circuit.exporter import collapse_to_schematic
from dupont.formats.circuit.importer import import_circuit
from dupont.formats.circuit.schema import Schematic
from dupont.model.entities import Circuit

PIN_SPACING = 2.4
UNIT = 2.4
FONT_SIZE = 12
RESISTOR_FONT_SIZE = 10
RENDER_DPI = 200


def load_circuit(path: Path) -> Schematic:
    """Load a ``circuit.yaml`` into a :class:`Schematic` via the interchange model.

    The draw path no longer parses channels directly: the file is imported into
    the canonical :class:`Circuit` model and collapsed back to the
    :class:`Schematic` draw structures, so the rendered SVG is byte-identical to
    the pre-migration direct-parse path.

    :param path: The path to the YAML description.
    :type path: Path
    :returns: The schematic collapsed from the interchange model.
    :rtype: Schematic
    :raises ValueError: If a required key is missing from the description.
    """
    return collapse_to_schematic(import_circuit(path))


def _terminate_net(drawing: schemdraw.Drawing, net: str) -> None:
    """Attach a ground or supply symbol for a net at the current point.

    :param drawing: The drawing to add the terminating symbol to.
    :type drawing: schemdraw.Drawing
    :param net: The net name that selects the symbol (``"GND"`` or ``"+..."``).
    :type net: str
    :returns: None. The function modifies the drawing in place.
    :rtype: None
    """
    if net == "GND":
        drawing += elm.Ground()
    else:
        drawing += elm.Vdd().label(net)


def build_drawing(circuit: Schematic) -> schemdraw.Drawing:
    """Build the schemdraw drawing for a parsed circuit.

    :param circuit: The circuit to render.
    :type circuit: Schematic
    :returns: The assembled drawing, ready to save.
    :rtype: schemdraw.Drawing
    """
    drawing = schemdraw.Drawing(show=False)
    drawing.config(unit=UNIT, fontsize=FONT_SIZE)

    channel_count = len(circuit.channels)
    # Power pins and button GPIOs share the left edge, ordered top to bottom.
    left_names = [power.pin for power in circuit.mcu.power] + [
        button.gpio for button in circuit.buttons
    ]
    left_count = len(left_names)
    mcu_pins = [
        elm.IcPin(
            name=channel.gpio, side="right", slot=f"{channel_count - i}/{channel_count}"
        )
        for i, channel in enumerate(circuit.channels)
    ] + [
        elm.IcPin(name=name, side="left", slot=f"{left_count - i}/{left_count}")
        for i, name in enumerate(left_names)
    ]
    mcu = elm.Ic(pins=mcu_pins, pinspacing=PIN_SPACING, edgepadW=2.4, edgepadH=0.7)
    mcu.label(circuit.mcu.label, loc="top", ofst=0.3)
    drawing += mcu

    resistors: list[elm.Resistor] = []
    for channel in circuit.channels:
        resistor = (
            elm.Resistor()
            .right()
            .at(mcu.absanchors[channel.gpio])
            .label(
                f"{channel.resistor.ref}\n{channel.resistor.value}",
                fontsize=RESISTOR_FONT_SIZE,
            )
        )
        drawing += resistor
        resistors.append(resistor)

    load_pins = [
        elm.IcPin(
            name=channel.load_pin,
            side="left",
            slot=f"{channel_count - i}/{channel_count}",
        )
        for i, channel in enumerate(circuit.channels)
    ] + [elm.IcPin(name=circuit.load.common.pin, side="bottom", slot="1/1")]
    load = (
        elm.Ic(pins=load_pins, pinspacing=PIN_SPACING, edgepadW=1.8, edgepadH=0.7)
        .anchor(circuit.channels[0].load_pin)
        .at(resistors[0].end)
    )
    load.label(circuit.load.label, loc="top", ofst=0.3)
    drawing += load

    for index in range(1, channel_count):
        drawing += (
            elm.Line()
            .at(resistors[index].end)
            .to(load.absanchors[circuit.channels[index].load_pin])
        )

    for power in circuit.mcu.power:
        drawing += elm.Line().left().at(mcu.absanchors[power.pin]).length(1.4)
        _terminate_net(drawing, power.net)

    for button in circuit.buttons:
        drawing += elm.Line().left().at(mcu.absanchors[button.gpio]).length(0.7)
        drawing += elm.Button().left().label(button.ref, fontsize=RESISTOR_FONT_SIZE)
        drawing += elm.Line().left().length(0.5)
        _terminate_net(drawing, button.net)

    drawing += (
        elm.Line().down().at(load.absanchors[circuit.load.common.pin]).length(1.2)
    )
    _terminate_net(drawing, circuit.load.common.net)

    return drawing


def render(circuit: Schematic, out_stem: Path) -> None:
    """Render a circuit to ``<stem>.svg`` and ``<stem>.png``.

    :param circuit: The circuit to render.
    :type circuit: Schematic
    :param out_stem: The output path without extension.
    :type out_stem: Path
    :returns: None. The function writes the two image files to disk.
    :rtype: None
    """
    drawing = build_drawing(circuit)
    drawing.save(str(out_stem.with_suffix(".svg")))
    drawing.save(str(out_stem.with_suffix(".png")), dpi=RENDER_DPI)


def render_schematic(circuit: Circuit, out_stem: Path) -> None:
    """Render a schematic FROM THE INTERCHANGE MODEL to ``<stem>.svg`` + ``.png``.

    Collapses the :class:`Circuit` model to its :class:`Schematic` draw
    structures and saves the images. :func:`collapse_to_schematic` is the only
    model-to-draw bridge, so no channel parsing happens in this draw path.

    :param circuit: The interchange model to render.
    :type circuit: Circuit
    :param out_stem: The output path without extension.
    :type out_stem: Path
    :returns: None. The function writes the two image files to disk.
    :rtype: None
    """
    render(collapse_to_schematic(circuit), out_stem)


def main() -> None:
    """Parse the YAML path from the command line and render the circuit.

    :returns: None. The function writes the rendered image files to disk.
    :rtype: None
    """
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("circuit.yaml")
    circuit = import_circuit(source)
    render_schematic(circuit, source.with_suffix(""))


if __name__ == "__main__":
    main()
