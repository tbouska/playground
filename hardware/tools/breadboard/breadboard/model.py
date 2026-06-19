from dataclasses import dataclass, field


@dataclass(frozen=True)
class Pin:
    """Describe a named module pin placed on a hole.

    :ivar name: The pin label, e.g. ``"GPIO0"``.
    :vartype name: str
    :ivar hole: The hole address the pin sits on, e.g. ``"J3"``.
    :vartype hole: str
    """

    name: str
    hole: str


@dataclass(frozen=True)
class Component:
    """Describe one placed component on the breadboard.

    :ivar kind: The component kind: ``module``, ``resistor``, ``led-rgb``,
        ``wire`` or ``power``.
    :vartype kind: str
    :ivar ref: The reference designator, or an empty string for wires.
    :vartype ref: str
    :ivar label: The display label, where applicable.
    :vartype label: str
    :ivar value: The component value, where applicable.
    :vartype value: str
    :ivar legs: The hole addresses for a two-leg part, in order.
    :vartype legs: tuple[str, ...]
    :ivar named_legs: The named-leg to hole mapping for an RGB LED.
    :vartype named_legs: dict[str, str]
    :ivar common: The RGB common type, ``cathode`` or ``anode``.
    :vartype common: str
    :ivar color: The wire color name.
    :vartype color: str
    :ivar endpoints: The two hole addresses of a wire, in order.
    :vartype endpoints: tuple[str, str]
    :ivar span: The inclusive column span ``(first, last)`` of a block.
    :vartype span: tuple[int, int]
    :ivar pins: The named pins of a module.
    :vartype pins: tuple[Pin, ...]
    """

    kind: str
    ref: str = ""
    label: str = ""
    value: str = ""
    legs: tuple[str, ...] = ()
    named_legs: dict[str, str] = field(default_factory=dict)
    common: str = "cathode"
    color: str = "black"
    endpoints: tuple[str, str] = ("", "")
    span: tuple[int, int] = (0, 0)
    pins: tuple[Pin, ...] = ()


@dataclass(frozen=True)
class Layout:
    """Describe a whole breadboard layout parsed from YAML.

    :ivar title: The layout title.
    :vartype title: str
    :ivar columns: The number of numbered columns on the board.
    :vartype columns: int
    :ivar components: The placed components.
    :vartype components: tuple[Component, ...]
    :ivar style: Inline style overrides from the layout YAML ``style:`` key, or None.
    :vartype style: dict | None
    """

    title: str
    columns: int
    components: tuple[Component, ...]
    style: dict | None = None
