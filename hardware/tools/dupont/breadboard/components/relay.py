import matplotlib.pyplot as plt

from breadboard.components import register
from breadboard.components.block import _block
from breadboard.geometry import Geometry
from breadboard.model import Component
from breadboard.style import Style


@register("relay")
def draw_relay(axes: plt.Axes, geo: Geometry, component: Component, style: Style) -> None:
    _block(axes, geo, component, style, section="relay", label=component.label or component.ref)
