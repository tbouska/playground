"""Frozen value objects modelling a parsed circuit description.

These dataclasses are the in-memory shape produced by parsing a ``circuit.yaml``
file: a microcontroller driving N channels, each through a series resistor into
a multi-pin load such as an RGB LED.
"""

from dataclasses import dataclass


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
class Schematic:
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
