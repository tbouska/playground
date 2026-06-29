from __future__ import annotations

import dataclasses
from pathlib import Path

import yaml

from dupont.model.entities import Circuit, Component, Net, Pin, Placement, PinRef, Role


def dump_model(circuit: Circuit) -> str:
    return yaml.safe_dump(
        dataclasses.asdict(circuit),
        sort_keys=False,
        allow_unicode=True,
    )


def load_model(source: str | Path) -> Circuit:
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8")
    else:
        text = source
    d = yaml.safe_load(text)
    return Circuit(
        title=d["title"],
        components=tuple(
            Component(
                instance_id=c["instance_id"],
                kind=c["kind"],
                pins=tuple(Pin(**p) for p in c["pins"]),
                part_type=c.get("part_type"),
                variant=c.get("variant"),
                label=c.get("label", ""),
                value=c.get("value"),
            )
            for c in d["components"]
        ),
        nets=tuple(
            Net(
                net_id=n["net_id"],
                member_pin_refs=tuple(
                    PinRef(instance_id=r["instance_id"], pin=r["pin"])
                    for r in n["member_pin_refs"]
                ),
                provenance=n["provenance"],
            )
            for n in d["nets"]
        ),
        placements=tuple(
            Placement(
                component_ref=p["component_ref"],
                coords=p["coords"],
                rotation=p["rotation"],
                source=p["source"],
                provenance=p["provenance"],
            )
            for p in d.get("placements", [])
        ),
        roles=tuple(
            Role(target=r["target"], tag=r["tag"], source=r["source"])
            for r in d.get("roles", [])
        ),
    )
