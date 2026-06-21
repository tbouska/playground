"""Per-component style-sourcing tests.

Each drawer must read its colours and scalar dimensions (component line widths,
the LED lead width, the label-halo pad) from the passed Style, not from inline
literals. Overriding a style key must change the render; if a drawer regresses to
an inline literal, the override stops taking effect and the matching test fails.
The default style value must equal the historical inline literal so default
output stays byte-identical (the render-parity suite is the hard gate).
"""

import re
from pathlib import Path

import pytest

import render_layout
from breadboard.model import Component, Layout, Pin
from breadboard.style import load_style

_SENTINEL = "#017fae"

# Volatile matplotlib-SVG bits (per test_render_parity._normalize): a per-render
# timestamp and a per-render clip-path id. Scrub them so two renders of identical
# geometry compare equal, and a real drawing difference (e.g. lead width) does not.
_CLIP_ID_RE = re.compile(r'(id="|url\(#)(p[0-9a-f]{9,})')


def _scrub(svg_text: str) -> str:
    text = re.sub(r"[ \t]*<dc:date>.*?</dc:date>\n?", "", svg_text)
    return _CLIP_ID_RE.sub(lambda m: m.group(1) + "CLIP_ID_PLACEHOLDER", text)


def _render_svg(component: Component, tmp_path: Path, style_inline: dict | None) -> str:
    layout = Layout(title="t", columns=10, components=(component,), style=style_inline)
    render_layout.render(layout, tmp_path / "o")
    return (tmp_path / "o.svg").read_text(encoding="utf-8")


# (id, component, (section, key), default hex the drawer bakes in today)
_BODY_COLOUR_CASES = [
    (
        "capacitor-polar-body",
        Component(kind="capacitor", ref="C1", common="polar", legs=("A1", "A3")),
        ("capacitor", "polar_body"),
        "#2c3e6b",
    ),
    (
        "capacitor-ceramic-body",
        Component(kind="capacitor", ref="C2", legs=("B1", "B3")),
        ("capacitor", "ceramic_body"),
        "#d9a441",
    ),
    (
        "diode-body",
        Component(kind="diode", ref="D1", legs=("C1", "C3")),
        ("diode", "body"),
        "#2b2b2b",
    ),
    (
        "transistor-body",
        Component(kind="transistor", ref="Q1", legs=("D1", "D2", "D3")),
        ("transistor", "body"),
        "#23282d",
    ),
    (
        "button-housing",
        Component(kind="button", ref="SW1", legs=("E1", "E3")),
        ("button", "housing"),
        "#3a3f44",
    ),
    (
        "block-body",
        Component(kind="module", label="U1", span=(1, 3)),
        ("block", "body"),
        "#5b6770",
    ),
    (
        "led-rgb-lens",
        Component(kind="led-rgb", ref="L1", named_legs={"R": "F1", "G": "F2", "B": "F3"}),
        ("led", "rgb_lens"),
        "#f6d9d2",
    ),
]


@pytest.mark.parametrize(
    "label, component, key, default_hex",
    _BODY_COLOUR_CASES,
    ids=[case[0] for case in _BODY_COLOUR_CASES],
)
def test_component_body_colour_read_from_style(
    label: str,
    component: Component,
    key: tuple[str, str],
    default_hex: str,
    tmp_path: Path,
) -> None:
    section, name = key
    svg = _render_svg(component, tmp_path, {section: {name: _SENTINEL}})
    assert _SENTINEL in svg, f"{label}: override ignored — colour still inline?"
    assert default_hex not in svg, f"{label}: default hex still emitted despite override"


def test_led_lead_width_default_unchanged() -> None:
    # Parity lock: the externalized LED lead width must equal the value that was
    # inline (1.6) so default output stays byte-identical.
    assert load_style().dim("led.lead_width") == 1.6


def test_led_lead_width_read_from_style(tmp_path: Path) -> None:
    led = Component(kind="led-rgb", ref="L1", named_legs={"R": "F1", "G": "F2", "B": "F3"})
    default_svg = _scrub(_render_svg(led, tmp_path, None))
    thick_svg = _scrub(_render_svg(led, tmp_path, {"led": {"lead_width": 9.9}}))
    same_svg = _scrub(_render_svg(led, tmp_path, {"led": {"lead_width": 1.6}}))
    # Scrubbed renders are byte-identical for identical geometry, so the only way
    # the 9.9 override can differ is if the drawer sources the lead width from
    # Style. Re-asserting that an explicit 1.6 override equals the default rules
    # out the "any two renders differ" trap (volatile bits already scrubbed).
    assert default_svg != thick_svg
    assert default_svg == same_svg


_BLOCK = Component(kind="module", label="U1", span=(1, 3))
_BLOCK_PINNED = Component(
    kind="module", ref="U1", label="U1", span=(1, 3),
    pins=(Pin(name="P1", hole="A1"), Pin(name="P2", hole="A3")),
)
_DIODE = Component(kind="diode", ref="D1", legs=("C1", "C3"))
_CAP_POLAR = Component(kind="capacitor", ref="C1", common="polar", legs=("A1", "A3"))
_CAP_CERAMIC = Component(kind="capacitor", ref="C2", legs=("B1", "B3"))
_TRANSISTOR = Component(kind="transistor", ref="Q1", legs=("D1", "D2", "D3"))
_BUTTON = Component(kind="button", ref="SW1", legs=("E1", "E3"))
_LED = Component(kind="led-rgb", ref="L1", named_legs={"R": "F1", "G": "F2", "B": "F3"})

# (id, component, (section, key), default value baked in today, a wild override)
_STYLE_SOURCING_CASES = [
    ("diode-body-edge-width", _DIODE, ("diode", "body_edge_width"), 1.0, 9.9),
    ("block-body-edge-width", _BLOCK, ("block", "body_edge_width"), 1.0, 9.9),
    ("block-top-edge-width", _BLOCK, ("block", "top_edge_width"), 1.6, 9.9),
    ("block-pin-edge-width", _BLOCK_PINNED, ("block", "pin_edge_width"), 0.6, 9.9),
    ("led-lens-edge-width", _LED, ("led", "lens_edge_width"), 1.2, 9.9),
    ("cap-polar-edge-width", _CAP_POLAR, ("capacitor", "polar_body_edge_width"), 1.0, 9.9),
    ("cap-ceramic-edge-width", _CAP_CERAMIC, ("capacitor", "ceramic_body_edge_width"), 1.0, 9.9),
    ("transistor-body-edge-width", _TRANSISTOR, ("transistor", "body_edge_width"), 1.0, 9.9),
    ("button-housing-edge-width", _BUTTON, ("button", "housing_edge_width"), 1.0, 9.9),
    ("button-plunger-edge-width", _BUTTON, ("button", "plunger_edge_width"), 1.0, 9.9),
    ("block-label-colour", _BLOCK, ("block", "label"), "white", _SENTINEL),
    ("block-pin-label-colour", _BLOCK_PINNED, ("block", "pin_label"), "white", _SENTINEL),
    ("led-highlight-colour", _LED, ("led", "highlight"), "white", _SENTINEL),
    ("label-halo-pad", _LED, ("label", "halo_pad"), 0.18, 0.99),
]


@pytest.mark.parametrize(
    "label, component, key, default_value, wild_value",
    _STYLE_SOURCING_CASES,
    ids=[case[0] for case in _STYLE_SOURCING_CASES],
)
def test_component_style_key_read_from_style(
    label: str,
    component: Component,
    key: tuple[str, str],
    default_value: object,
    wild_value: object,
    tmp_path: Path,
) -> None:
    section, name = key
    default_svg = _scrub(_render_svg(component, tmp_path, None))
    wild_svg = _scrub(_render_svg(component, tmp_path, {section: {name: wild_value}}))
    same_svg = _scrub(_render_svg(component, tmp_path, {section: {name: default_value}}))
    # A wild override must change the render -> the drawer reads it from Style.
    assert default_svg != wild_svg, f"{label}: override ignored — value still inline?"
    # The style default must equal the historical inline literal -> parity holds.
    assert default_svg == same_svg, f"{label}: style default != historical inline literal"
