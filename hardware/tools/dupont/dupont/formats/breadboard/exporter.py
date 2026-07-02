from __future__ import annotations

from breadboard.model import Component, Layout, Pin
from dupont.model.entities import Circuit


def collapse_to_layout(circuit: Circuit) -> Layout:
    board = next((p for p in circuit.placements if p.component_ref == "__board__"), None)
    if board is None:
        raise ValueError("circuit has no '__board__' placement")

    columns = int(board.coords["columns"])
    style = board.coords["style"]

    components = tuple(
        Component(
            kind=p.coords["kind"],
            ref=p.coords["ref"],
            label=p.coords["label"],
            value=p.coords["value"],
            legs=tuple(p.coords["legs"]),
            named_legs=dict(p.coords["named_legs"]),
            common=p.coords["common"],
            color=p.coords["color"],
            endpoints=tuple(p.coords["endpoints"]),
            span=tuple(p.coords["span"]),
            pins=tuple(Pin(pin["name"], pin["hole"]) for pin in p.coords["pins"]),
            digits=p.coords["digits"],
        )
        for p in circuit.placements
        if p.component_ref != "__board__"
    )

    return Layout(title=circuit.title, columns=columns, components=components, style=style)
