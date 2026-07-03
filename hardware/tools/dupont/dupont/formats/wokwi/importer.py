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
from dupont.model.entities import (
    Circuit,
    Component,
    Net,
    Pin,
    PinRef,
    Placement,
)


def import_wokwi(
    source: str | Path | dict,
    title: str = "",
) -> Circuit:
    # 1. Load the diagram dict
    if isinstance(source, dict):
        diagram: dict[str, Any] = source
    elif isinstance(source, Path):
        diagram = json.loads(source.read_text())
    else:
        if "\n" not in source and Path(source).exists():
            diagram = json.loads(Path(source).read_text())
        else:
            diagram = json.loads(source)

    parts: list[dict[str, Any]] = diagram["parts"]
    connections: list[list] = diagram["connections"]

    # 2. RE-ORIGIN REFERENCE
    breadboard_parts = [p for p in parts if p["type"] == "wokwi-breadboard"]
    board_parts = [p for p in parts if p["type"] in BOARD_TO_KIND]

    if len(breadboard_parts) == 1:
        ref = breadboard_parts[0]
    elif len(breadboard_parts) == 0 and len(board_parts) == 1:
        ref = board_parts[0]
    else:
        raise ValueError(
            "ambiguous or absent reference: "
            f"{len(breadboard_parts)} breadboard(s), {len(board_parts)} board(s)"
        )

    ref_left = float(ref["left"])
    ref_top = float(ref["top"])

    part_positions: dict[str, tuple[float, float]] = {}
    for p in parts:
        part_positions[p["id"]] = (
            float(p["left"]) - ref_left,
            float(p["top"]) - ref_top,
        )

    # 3. Virtual endpoints
    def _is_virtual(part_id: str) -> bool:
        return part_id.startswith("$")

    # 4. CIRCUIT PARTS + IDS
    circuit_parts = [p for p in parts if p["type"] != "wokwi-breadboard"]

    part_type_to_kind: dict[str, str] = {v: k for k, v in KIND_TO_PART_TYPE.items()}

    ordered_parts: list[dict[str, Any]] = circuit_parts

    kinds: list[str] = []
    for p in ordered_parts:
        if p["type"] in BOARD_TO_KIND:
            kinds.append(BOARD_TO_KIND[p["type"]])
        else:
            if p["type"] not in part_type_to_kind:
                raise ValueError(f"unmapped part_type: {p['type']!r}")
            kinds.append(part_type_to_kind[p["type"]])

    minted_ids = mint_ids(kinds)

    # raw_id -> (minted_id, kind)
    raw_to_info: dict[str, tuple[str, str]] = {}
    for p, mid, kind in zip(ordered_parts, minted_ids, kinds):
        raw_to_info[p["id"]] = (mid, kind)

    # 5 & 6. CANONICAL PIN MAP + TRANSITIVE CLOSURE
    parent: dict[str, str] = {}

    def _find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(a: str, b: str) -> None:
        ra, rb = _find(a), _find(b)
        if ra != rb:
            parent[ra] = rb

    def _split_endpoint(ep: str) -> tuple[str, str]:
        idx = ep.index(":")
        return ep[:idx], ep[idx + 1:]

    for conn in connections:
        src_ep, dst_ep = conn[0], conn[1]
        src_id, src_pin = _split_endpoint(src_ep)
        dst_id, dst_pin = _split_endpoint(dst_ep)

        if _is_virtual(src_id) or _is_virtual(dst_id):
            continue

        if src_id not in raw_to_info or dst_id not in raw_to_info:
            continue

        src_mid, src_kind = raw_to_info[src_id]
        dst_mid, dst_kind = raw_to_info[dst_id]

        src_canonical = wokwi_pin_to_canon(src_kind, src_pin)
        dst_canonical = wokwi_pin_to_canon(dst_kind, dst_pin)

        src_key = f"{src_mid}:{src_canonical}"
        dst_key = f"{dst_mid}:{dst_canonical}"

        if src_key not in parent:
            parent[src_key] = src_key
        if dst_key not in parent:
            parent[dst_key] = dst_key
        _union(src_key, dst_key)

    groups: dict[str, list[str]] = {}
    for key in parent:
        root = _find(key)
        groups.setdefault(root, []).append(key)

    nets: list[Net] = []
    for i, keys in enumerate(groups.values(), start=1):
        if len(keys) < 2:
            continue
        # Deduplicate while preserving first-seen order
        seen: set[str] = set()
        distinct: list[str] = []
        for k in keys:
            if k not in seen:
                seen.add(k)
                distinct.append(k)
        if len(distinct) < 2:
            continue
        pin_refs = tuple(
            PinRef(k.split(":", 1)[0], k.split(":", 1)[1]) for k in distinct
        )
        nets.append(Net(f"_wokwi{i}", pin_refs, "wokwi/closure"))

    # 8. PLACEMENTS
    placements: list[Placement] = []
    for p in ordered_parts:
        mid = raw_to_info[p["id"]][0]
        px = part_positions[p["id"]]
        rotation = float(p.get("rotate", 0))
        placements.append(Placement(
            component_ref=mid,
            coords={"px": px},
            rotation=rotation,
            source="wokwi",
            provenance="wokwi/part",
        ))

    # 9. BREADBOARD SENTINEL
    if ref["type"] == "wokwi-breadboard":
        placements.append(Placement(
            component_ref="__wokwi_breadboard__",
            coords={"px": (0.0, 0.0)},
            rotation=0.0,
            source="wokwi",
            provenance="wokwi/breadboard-origin",
        ))

    # COMPONENTS
    # For each circuit part, collect distinct canonical pins in first-seen order
    part_canonical_pins: dict[str, list[str]] = {}
    for conn in connections:
        src_ep, dst_ep = conn[0], conn[1]
        src_id, src_pin = _split_endpoint(src_ep)
        dst_id, dst_pin = _split_endpoint(dst_ep)

        for raw_id, raw_pin in [(src_id, src_pin), (dst_id, dst_pin)]:
            if _is_virtual(raw_id):
                continue
            if raw_id not in raw_to_info:
                continue
            mid, kind = raw_to_info[raw_id]
            canon = wokwi_pin_to_canon(kind, raw_pin)
            part_canonical_pins.setdefault(mid, []).append(canon)

    components: list[Component] = []
    for p in ordered_parts:
        mid = raw_to_info[p["id"]][0]
        kind = raw_to_info[p["id"]][1]
        pins = part_canonical_pins.get(mid, [])
        # Deduplicate canonical pin names in first-seen order
        seen_pins: set[str] = set()
        distinct_pins: list[str] = []
        for canon in pins:
            if canon not in seen_pins:
                seen_pins.add(canon)
                distinct_pins.append(canon)

        pin_objects = tuple(
            Pin(name, name, "passive", i) for i, name in enumerate(distinct_pins)
        )

        # Value: for resistors, use attrs.value; otherwise None
        value = None
        if p["type"] == "wokwi-resistor":
            value = p.get("attrs", {}).get("value")

        components.append(Component(
            instance_id=mid,
            kind=kind,
            pins=pin_objects,
            part_type=p["type"],
            value=value,
        ))

    return Circuit(
        title=title,
        components=tuple(components),
        nets=tuple(nets),
        placements=tuple(placements),
    )
