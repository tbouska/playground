"""Per-component colour + LED lead-width style-sourcing tests.

Blind review (PRD 00003) C1/C2: the component body/decorative colours and the
LED lead width were hardcoded literals in the drawers, violating Phase 1's "no
palette/dimension hex or magic number remains inline". These tests lock the
fix — each drawer must source its colour (and the LED its lead width) from the
passed Style. Overriding a new style key must change the render; if a drawer
ever regresses to an inline literal, the override stops taking effect and the
matching test fails.
"""

import re
from pathlib import Path

import pytest

import render_layout
from breadboard.model import Component, Layout
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
