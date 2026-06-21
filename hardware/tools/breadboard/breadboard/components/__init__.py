from typing import Callable
from matplotlib.axes import Axes
from breadboard.geometry import Geometry
from breadboard.model import Component
from breadboard.style import Style

Drawer = Callable[[Axes, Geometry, Component, Style], None]

_REGISTRY: dict[str, Drawer] = {}

def register(*kinds: str) -> Callable[[Drawer], Drawer]:
    """Register a drawer under one or more kind strings. Returns the drawer
    unchanged so it can stack as a decorator."""
    def _decorate(drawer: Drawer) -> Drawer:
        for kind in kinds:
            _REGISTRY[kind] = drawer
        return drawer
    return _decorate

def get_drawer(kind: str) -> Drawer | None:
    """Return the drawer for ``kind``, or None if no kind is registered."""
    return _REGISTRY.get(kind)


from breadboard.components import (
    resistor, led, capacitor, diode, transistor, button, block, crystal, inductor, buzzer,
    potentiometer,
)

# kept referenced so the registration side effect is explicit; importing each
# module runs its @register(...) decorator.
_KIND_MODULES = (resistor, led, capacitor, diode, transistor, button, block, crystal, inductor, buzzer, potentiometer)
