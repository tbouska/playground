"""Import a Wokwi diagram.json into a canonical interchange Circuit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dupont.canon.ids import mint_ids
from dupont.formats.wokwi.maps import (
    BOARD_TO_KIND,
    KIND_TO_PART_TYPE,
    wokwi_pin_to_canon,
)
from dupont.model.entities import Circuit, Component, Net, Pin, PinRef, Placement

_BREADBOARD_TYPE = "wokwi-breadboard"
_PART_TYPE_TO_KIND: dict[str, str] = {v: k for k, v in KIND_TO_PART_TYPE.items()}


def _load_diagram(source: str | Path | dict) -> dict[str, Any]:
    """Load a diagram.json from a dict, a Path, a filename string, or JSON text."""
    if isinstance(source, dict):
        return source
    if isinstance(source, Path):
        return json.loads(source.read_text())
    if "\n" not in source and Path(source).exists():
        return json.loads(Path(source).read_text())
    return json.loads(source)


def _pick_reference(parts: list[dict]) -> dict:
    """The re-origin reference: the wokwi-breadboard if present, else the sole board.

    :raises ValueError: when the reference is ambiguous (2+ boards, no breadboard)
        or absent (no breadboard and no board).
    """
    breadboards = [p for p in parts if p["type"] == _BREADBOARD_TYPE]
    boards = [p for p in parts if p["type"] in BOARD_TO_KIND]
    if len(breadboards) == 1:
        return breadboards[0]
    if not breadboards and len(boards) == 1:
        return boards[0]
    raise ValueError(
        f"ambiguous or absent re-origin reference: "
        f"{len(breadboards)} breadboard(s), {len(boards)} board(s)"
    )


def _kind_of(part: dict) -> str:
    """The model kind for a circuit part; raises ValueError on an unmapped part_type."""
    part_type = part["type"]
    if part_type not in _PART_TYPE_TO_KIND:
        raise ValueError(f"unmapped part_type: {part_type!r}")
    return _PART_TYPE_TO_KIND[part_type]


def _split_endpoint(endpoint: str) -> tuple[str, str]:
    part_id, _, pin = endpoint.partition(":")
    return part_id, pin


def _resolve_endpoint(
    endpoint: str,
    info: dict[str, tuple[str, str]],
    breadboard_id: str | None,
) -> str | None:
    """A connection endpoint as a canonical ``"instance_id:pin"`` key, or None.

    ``$``-virtual and breadboard-reference endpoints carry no circuit connectivity
    (None); an endpoint naming an unknown part raises ValueError (fail loud).
    """
    part_id, pin = _split_endpoint(endpoint)
    if part_id.startswith("$") or part_id == breadboard_id:
        return None
    if part_id not in info:
        raise ValueError(f"connection references unknown part: {part_id!r}")
    instance_id, kind = info[part_id]
    return f"{instance_id}:{wokwi_pin_to_canon(kind, pin)}"


def _closure(
    connections: list[list],
    info: dict[str, tuple[str, str]],
    breadboard_id: str | None,
) -> tuple[list[Net], dict[str, list[str]]]:
    """Transitive closure of the flat connection list into canonical nets.

    Returns the nets (>=2 distinct members) and, per canonical component id, the
    ordered distinct canonical pin names that participate in real connections.
    """
    # ponytail: local union-find; share it only if a third caller appears.
    parent: dict[str, str] = {}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for connection in connections:
        a = _resolve_endpoint(connection[0], info, breadboard_id)
        b = _resolve_endpoint(connection[1], info, breadboard_id)
        if a is None or b is None:
            continue
        for key in (a, b):
            parent.setdefault(key, key)
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_a] = root_b

    groups: dict[str, list[str]] = {}
    pins_by_id: dict[str, list[str]] = {}
    for key in parent:
        groups.setdefault(find(key), []).append(key)
        instance_id, canon = key.split(":", 1)
        pins_by_id.setdefault(instance_id, []).append(canon)

    nets: list[Net] = []
    for members in groups.values():
        if len(members) >= 2:
            refs = tuple(PinRef(*key.split(":", 1)) for key in members)
            nets.append(Net(f"_wokwi{len(nets) + 1}", refs, "wokwi/closure"))
    return nets, pins_by_id


def _build_components(
    circuit_parts: list[dict],
    info: dict[str, tuple[str, str]],
    pins_by_id: dict[str, list[str]],
) -> list[Component]:
    components = []
    for part in circuit_parts:
        instance_id, kind = info[part["id"]]
        pins = tuple(
            Pin(name, name, "passive", index)
            for index, name in enumerate(pins_by_id.get(instance_id, []))
        )
        value = part.get("attrs", {}).get("value") if kind == "resistor" else None
        components.append(
            Component(instance_id, kind, pins, part_type=part["type"], value=value)
        )
    return components


def _build_placements(
    circuit_parts: list[dict],
    info: dict[str, tuple[str, str]],
    ref_left: float,
    ref_top: float,
) -> list[Placement]:
    return [
        Placement(
            info[part["id"]][0],
            {"px": (float(part["left"]) - ref_left, float(part["top"]) - ref_top)},
            float(part.get("rotate", 0)),
            "wokwi",
            "wokwi/part",
        )
        for part in circuit_parts
    ]


def import_wokwi(source: str | Path | dict, title: str = "") -> Circuit:
    """Build a canonical Circuit from a Wokwi diagram.json.

    Nets come from the transitive closure of the flat ``connections`` list;
    placements are re-origined to the reference part's frame. See the A3 design doc
    (00009) for the full 9-step contract.
    """
    diagram = _load_diagram(source)
    parts: list[dict[str, Any]] = diagram["parts"]

    reference = _pick_reference(parts)
    ref_left, ref_top = float(reference["left"]), float(reference["top"])
    breadboard_id = reference["id"] if reference["type"] == _BREADBOARD_TYPE else None

    circuit_parts = [p for p in parts if p["type"] != _BREADBOARD_TYPE]
    kinds = [_kind_of(p) for p in circuit_parts]
    minted = mint_ids(kinds)
    info = {p["id"]: (mid, kind) for p, mid, kind in zip(circuit_parts, minted, kinds)}

    nets, pins_by_id = _closure(diagram["connections"], info, breadboard_id)
    components = _build_components(circuit_parts, info, pins_by_id)
    placements = _build_placements(circuit_parts, info, ref_left, ref_top)
    if breadboard_id is not None:
        placements.append(
            Placement(
                "__wokwi_breadboard__",
                {"px": (0.0, 0.0)},
                0.0,
                "wokwi",
                "wokwi/breadboard-origin",
            )
        )

    return Circuit(
        title=title,
        components=tuple(components),
        nets=tuple(nets),
        placements=tuple(placements),
    )
