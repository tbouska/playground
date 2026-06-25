"""Render a microcontroller-to-load schematic from a declarative YAML file.

This module reads a circuit description (a microcontroller driving N channels,
each through a series resistor into a multi-pin load such as an RGB LED) and
renders it to SVG and PNG with :mod:`schemdraw`. The YAML file is the source of
truth that lives in version control; the images are reproducible build outputs.

Imports:
    dataclasses -- provide the frozen value objects (:class:`Resistor`,
        :class:`Channel`, :class:`PowerPin`, :class:`TerminalPin`, :class:`Mcu`,
        :class:`Load`, :class:`Circuit`) that model the parsed description.
    pathlib -- resolve the input and output file paths.
    sys -- read the optional YAML path from the command line.
    typing -- supply :class:`Any` for the untyped parsed YAML mapping.
    matplotlib -- force the non-interactive ``Agg`` backend before schemdraw
        imports it, so rendering works headless in CI.
    yaml -- parse the description with :func:`yaml.safe_load`.
    schemdraw -- build and save the drawing via :class:`schemdraw.Drawing` and
        the elements in :mod:`schemdraw.elements`.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "schemdraw>=0.19",
#     "matplotlib>=3.8",
#     "pyyaml>=6.0",
# ]
# ///

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import schemdraw
import schemdraw.elements as elm

PIN_SPACING = 2.4
UNIT = 2.4
FONT_SIZE = 12
RESISTOR_FONT_SIZE = 10
RENDER_DPI = 200


@dataclass(frozen=True)
class Resistor:
    """Describe a series resistor on one channel.

    :ivar ref: The reference designator, e.g. ``"R1"``.
    :vartype ref: str
    :ivar value: The displayed value, e.g. ``"330"``.
    :vartype value: str
    """

    ref: str
    value: str


@dataclass(frozen=True)
class Channel:
    """Describe one GPIO-to-load channel through a resistor.

    :ivar gpio: The microcontroller pin name driving the channel.
    :vartype gpio: str
    :ivar load_pin: The load pin name the channel feeds.
    :vartype load_pin: str
    :ivar resistor: The series resistor on the channel.
    :vartype resistor: Resistor
    """

    gpio: str
    load_pin: str
    resistor: Resistor


@dataclass(frozen=True)
class Button:
    """Describe a momentary push switch tapping one MCU pin to a net.

    :ivar ref: The reference designator, e.g. ``"SW1"``.
    :vartype ref: str
    :ivar gpio: The microcontroller pin the switch reads.
    :vartype gpio: str
    :ivar net: The net the far side of the switch ties to, e.g. ``"GND"``.
    :vartype net: str
    """

    ref: str
    gpio: str
    net: str


@dataclass(frozen=True)
class PowerPin:
    """Describe a microcontroller power pin and the net it ties to.

    :ivar pin: The pin name, e.g. ``"3V3"``.
    :vartype pin: str
    :ivar net: The net name, e.g. ``"+3V3"`` or ``"GND"``.
    :vartype net: str
    """

    pin: str
    net: str


@dataclass(frozen=True)
class TerminalPin:
    """Describe the load common pin and the net it ties to.

    :ivar pin: The pin name, e.g. ``"K"``.
    :vartype pin: str
    :ivar net: The net name, e.g. ``"GND"``.
    :vartype net: str
    """

    pin: str
    net: str


@dataclass(frozen=True)
class Mcu:
    """Describe the microcontroller block.

    :ivar label: The block label.
    :vartype label: str
    :ivar power: The power pins, ordered top to bottom on the left edge.
    :vartype power: tuple[PowerPin, ...]
    """

    label: str
    power: tuple[PowerPin, ...]


@dataclass(frozen=True)
class Load:
    """Describe the load block.

    :ivar label: The block label.
    :vartype label: str
    :ivar common: The shared common pin (anode or cathode).
    :vartype common: TerminalPin
    """

    label: str
    common: TerminalPin


@dataclass(frozen=True)
class Circuit:
    """Describe the whole circuit parsed from YAML.

    :ivar title: The schematic title.
    :vartype title: str
    :ivar mcu: The microcontroller block.
    :vartype mcu: Mcu
    :ivar load: The load block.
    :vartype load: Load
    :ivar channels: The driver channels, ordered top to bottom.
    :vartype channels: tuple[Channel, ...]
    :ivar buttons: The momentary switches read by the MCU.
    :vartype buttons: tuple[Button, ...]
    """

    title: str
    mcu: Mcu
    load: Load
    channels: tuple[Channel, ...]
    buttons: tuple[Button, ...]


def load_circuit(path: Path) -> Circuit:
    """Parse a YAML circuit description into a :class:`Circuit`.

    :param path: The path to the YAML description.
    :type path: Path
    :returns: The parsed circuit.
    :rtype: Circuit
    :raises KeyError: If a required key is missing from the description.
    """
    import yaml

    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    mcu_data: dict[str, Any] = data["mcu"]
    load_data: dict[str, Any] = data["load"]
    mcu = Mcu(
        label=mcu_data["label"],
        power=tuple(
            PowerPin(pin=item["pin"], net=item["net"]) for item in mcu_data["power"]
        ),
    )
    load = Load(
        label=load_data["label"],
        common=TerminalPin(
            pin=load_data["common"]["pin"], net=load_data["common"]["net"]
        ),
    )
    channels = tuple(
        Channel(
            gpio=item["gpio"],
            load_pin=item["load_pin"],
            resistor=Resistor(
                ref=item["resistor"]["ref"], value=item["resistor"]["value"]
            ),
        )
        for item in data["channels"]
    )
    buttons = tuple(
        Button(ref=item["ref"], gpio=item["gpio"], net=item["net"])
        for item in data.get("buttons", [])
    )
    return Circuit(
        title=data["title"], mcu=mcu, load=load, channels=channels, buttons=buttons
    )


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


def build_drawing(circuit: Circuit) -> schemdraw.Drawing:
    """Build the schemdraw drawing for a parsed circuit.

    :param circuit: The circuit to render.
    :type circuit: Circuit
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


def render(circuit: Circuit, out_stem: Path) -> None:
    """Render a circuit to ``<stem>.svg`` and ``<stem>.png``.

    :param circuit: The circuit to render.
    :type circuit: Circuit
    :param out_stem: The output path without extension.
    :type out_stem: Path
    :returns: None. The function writes the two image files to disk.
    :rtype: None
    """
    drawing = build_drawing(circuit)
    drawing.save(str(out_stem.with_suffix(".svg")))
    drawing.save(str(out_stem.with_suffix(".png")), dpi=RENDER_DPI)


def main() -> None:
    """Parse the YAML path from the command line and render the circuit.

    :returns: None. The function writes the rendered image files to disk.
    :rtype: None
    """
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("circuit.yaml")
    circuit = load_circuit(source)
    render(circuit, source.with_suffix(""))


if __name__ == "__main__":
    main()
