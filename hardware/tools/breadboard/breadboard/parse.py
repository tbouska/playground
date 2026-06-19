"""Parse breadboard layouts from YAML.

This module contains functions to parse YAML hole-placement descriptions
into Layout objects.
"""

from pathlib import Path
from typing import Any

from breadboard.model import Component, Layout, Pin


def _component_from_dict(data: dict[str, Any]) -> Component:
    """Build a :class:`Component` from one parsed YAML mapping."""
    kind: str = data["kind"]
    pins = tuple(
        Pin(name=str(item["name"]), hole=str(item["hole"]))
        for item in data.get("pins", [])
    )
    named_legs: dict[str, str] = (
        {str(key): str(value) for key, value in data.get("legs", {}).items()}
        if isinstance(data.get("legs"), dict)
        else {}
    )
    legs: tuple[str, ...] = (
        tuple(str(item) for item in data["legs"])
        if isinstance(data.get("legs"), list)
        else ()
    )
    span_raw = data.get("span", [0, 0])
    return Component(
        kind=kind,
        ref=str(data.get("ref", "")),
        label=str(data.get("label", "")),
        value=str(data.get("value", "")),
        legs=legs,
        named_legs=named_legs,
        common=str(data.get("common", "cathode")),
        color=str(data.get("color", "black")),
        endpoints=(str(data.get("from", "")), str(data.get("to", ""))),
        span=(int(span_raw[0]), int(span_raw[1])),
        pins=pins,
    )


def load_layout(path: Path) -> Layout:
    """Parse a YAML hole-placement description into a :class:`Layout`.

    :param path: The path to the YAML description.
    :type path: Path
    :returns: The parsed layout.
    :rtype: Layout
    :raises KeyError: If a required key is missing from the description.
    """
    import yaml

    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    components = tuple(_component_from_dict(item) for item in data["components"])
    return Layout(
        title=str(data.get("title", "Breadboard layout")),
        columns=int(data["breadboard"]["columns"]),
        components=components,
        style=data.get("style"),
    )