from dataclasses import dataclass


@dataclass(frozen=True)
class Pin:
    pin_id: str
    name: str
    type: str
    physical_index: int


@dataclass(frozen=True)
class Component:
    instance_id: str
    kind: str
    pins: tuple[Pin, ...]
    part_type: str | None = None
    variant: str | None = None
    label: str = ""
    value: str | None = None


@dataclass(frozen=True)
class PinRef:
    instance_id: str
    pin: str


@dataclass(frozen=True)
class Net:
    net_id: str
    member_pin_refs: tuple[PinRef, ...]
    provenance: str


@dataclass(frozen=True)
class Placement:
    component_ref: str
    coords: dict
    rotation: float
    source: str
    provenance: str


@dataclass(frozen=True)
class Role:
    target: str
    tag: str
    source: str


@dataclass(frozen=True)
class Circuit:
    title: str
    components: tuple[Component, ...]
    nets: tuple[Net, ...]
    placements: tuple[Placement, ...] = ()
    roles: tuple[Role, ...] = ()
