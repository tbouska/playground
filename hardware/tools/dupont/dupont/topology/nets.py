"""Breadboard net extraction.

Collapses placed components into electrical nets by union-find over the
breadboard base nodes returned by :func:`dupont.grid.holes.node_key`. Column
continuity and rail continuity are implicit in ``node_key``; wires add the only
explicit unions. Multi-leg parts bridge distinct nodes but never merge them.
"""

from breadboard.model import Component, Layout
from dupont.grid.holes import node_key
from dupont.model.entities import Net, PinRef


def component_pins(component: Component) -> list[tuple[str, str]]:
    """Map a component to its ``(pin_name, hole)`` pairs.

    :param component: The placed breadboard component.
    :type component: Component
    :returns: The geometry-native pin list, empty for wires and power.
    :rtype: list[tuple[str, str]]
    :raises ValueError: If the component kind carries no pin mapping.
    """
    kind = component.kind
    if kind in ("resistor", "led"):
        return [(str(index), hole) for index, hole in enumerate(component.legs, start=1)]
    if kind == "led-rgb":
        return list(component.named_legs.items())
    if kind == "module":
        return [(pin.name, pin.hole) for pin in component.pins]
    if kind in ("wire", "power"):
        return []
    raise ValueError(f"component kind has no pin mapping: {kind!r}")


def extract_nets(layout: Layout) -> tuple[Net, ...]:
    """Extract the electrical nets from a breadboard layout.

    :param layout: The placed breadboard layout.
    :type layout: Layout
    :returns: The nets, numbered ``bb_net1..`` by ascending minimum node key.
    :rtype: tuple[Net, ...]
    """
    parent: dict[tuple, tuple] = {}

    def find(node: tuple) -> tuple:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: tuple, b: tuple) -> None:
        parent[find(a)] = find(b)

    node_pins: dict[tuple, list[PinRef]] = {}
    for component in layout.components:
        for pin_name, hole in component_pins(component):
            node = find(node_key(hole))
            node_pins.setdefault(node, []).append(PinRef(component.ref, pin_name))

    wires: list[tuple[str, str]] = []
    for component in layout.components:
        if component.kind == "wire":
            union(node_key(component.endpoints[0]), node_key(component.endpoints[1]))
            wires.append(component.endpoints)

    groups: dict[tuple, set] = {}
    for node in list(parent):
        groups.setdefault(find(node), set()).add(node)

    wires_by_root: dict[tuple, list[tuple[str, str]]] = {}
    for endpoints in wires:
        wires_by_root.setdefault(find(node_key(endpoints[0])), []).append(endpoints)

    pending: list[tuple[tuple, tuple[PinRef, ...], str]] = []
    for root, nodes in groups.items():
        members = [ref for node in nodes for ref in node_pins.get(node, [])]
        if not members:
            continue
        members.sort(key=lambda ref: (ref.instance_id, ref.pin))
        group_wires = wires_by_root.get(root)
        if group_wires:
            first, second = sorted(min(group_wires, key=sorted))
            provenance = f"breadboard/jumper {first}-{second}"
        else:
            key = min(nodes)
            if key[0] == "rail":
                provenance = f"breadboard/rail {key[1]}"
            else:
                provenance = f"breadboard/column-merge col{key[2]}"
        pending.append((min(nodes), tuple(members), provenance))

    pending.sort(key=lambda item: item[0])
    return tuple(
        Net(f"bb_net{index}", members, provenance)
        for index, (_, members, provenance) in enumerate(pending, start=1)
    )
