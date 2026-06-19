import math

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from breadboard.components import register
from breadboard.components.base import (
    _body_quad,
    _draw_leads,
    _leg_dots,
    _leg_frame,
    _part_label,
)
from breadboard.geometry import Geometry
from breadboard.model import Component
from breadboard.style import (
    BODY_COLOR,
    RESISTOR_DIGIT_COLORS,
    RESISTOR_MULTIPLIER_EXTRA,
    RESISTOR_TOLERANCE,
)


def _parse_ohms(value: str) -> float | None:
    """Parse a resistor value like ``220``, ``4.7k`` or ``1M`` into ohms."""
    text = value.strip().lower().replace("ω", "").replace("ohm", "").replace(" ", "")
    if not text:
        return None
    multiplier = 1.0
    if text[-1] == "k":
        multiplier, text = 1e3, text[:-1]
    elif text[-1] == "m":
        multiplier, text = 1e6, text[:-1]
    elif text[-1] == "r":
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def _format_ohms(value: str) -> str:
    """Format a resistor value with the ohm symbol (``220 Ω``, ``4.7 kΩ``)."""
    ohms = _parse_ohms(value)
    if ohms is None:
        return value
    if ohms >= 1e6:
        return f"{ohms / 1e6:g} MΩ"
    if ohms >= 1e3:
        return f"{ohms / 1e3:g} kΩ"
    return f"{ohms:g} Ω"


def _resistor_bands(value: str) -> list[str] | None:
    """Five-band colour code (three digits, multiplier, tolerance) for a value."""
    ohms = _parse_ohms(value)
    if ohms is None or ohms <= 0:
        return None
    exponent = math.floor(math.log10(ohms))
    mantissa = round(ohms / 10 ** (exponent - 2))
    if mantissa >= 1000:
        mantissa //= 10
        exponent += 1
    digits = (mantissa // 100, (mantissa // 10) % 10, mantissa % 10)
    multiplier = exponent - 2
    if 0 <= multiplier <= 9:
        multiplier_color = RESISTOR_DIGIT_COLORS[multiplier]
    elif multiplier in RESISTOR_MULTIPLIER_EXTRA:
        multiplier_color = RESISTOR_MULTIPLIER_EXTRA[multiplier]
    else:
        return None
    return [RESISTOR_DIGIT_COLORS[d] for d in digits] + [
        multiplier_color,
        RESISTOR_TOLERANCE,
    ]


@register("resistor")
def _resistor(axes: plt.Axes, geo: Geometry, component: Component) -> None:
    """Draw a resistor: leads, tan body, colour-code bands and labels."""
    p1, p2 = geo.hole(component.legs[0]), geo.hole(component.legs[1])
    ux, uy, nx, ny, mx, my, length = _leg_frame(p1, p2)
    body_half = min(0.32 * length, 0.55)
    width = 0.22
    e1, e2 = _draw_leads(axes, p1, p2, ux, uy, body_half)
    axes.add_patch(
        Polygon(
            _body_quad(e1, e2, nx, ny, width),
            closed=True,
            facecolor=BODY_COLOR,
            edgecolor="#7a7466",
            linewidth=1.0,
            zorder=4,
        )
    )
    bands = _resistor_bands(component.value)
    if bands:
        band_w = body_half * 0.12
        for index, color in enumerate(bands):
            frac = (index + 1) / (len(bands) + 1)
            bx = e1[0] + (e2[0] - e1[0]) * frac
            by = e1[1] + (e2[1] - e1[1]) * frac
            stripe = (bx - ux * band_w, by - uy * band_w)
            stripe2 = (bx + ux * band_w, by + uy * band_w)
            axes.add_patch(
                Polygon(
                    _body_quad(stripe, stripe2, nx, ny, width),
                    closed=True,
                    facecolor=color,
                    edgecolor="none",
                    zorder=4.5,
                )
            )
    _leg_dots(axes, p1, p2)
    _part_label(axes, mx, my, nx, ny, component.ref, _format_ohms(component.value))
