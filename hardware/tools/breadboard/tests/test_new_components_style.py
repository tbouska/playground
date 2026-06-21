"""Style-sourcing tests for new components (crystal).

Each crystal drawer must read its colours and scalar dimensions from the passed
Style, not from inline literals. Overriding a style key must change the render;
if a drawer regresses to an inline literal, the override stops taking effect and
the matching test fails.

New components have no historical inline literal, so the wild-override-changes-
render assertion is the real signal. The same-value assertion rules out the
"any two renders differ" trap (volatile bits already scrubbed).
"""

import re
from pathlib import Path

import pytest

import render_layout
from breadboard.model import Component, Layout

_SENTINEL = "#017fae"

_CLIP_ID_RE = re.compile(r'(id="|url\(#)(p[0-9a-f]{9,})')


def _scrub(svg_text: str) -> str:
    text = re.sub(r"[ \t]*<dc:date>.*?</dc:date>\n?", "", svg_text)
    return _CLIP_ID_RE.sub(lambda m: m.group(1) + "CLIP_ID_PLACEHOLDER", text)


def _render_svg(component: Component, tmp_path: Path, style_inline: dict | None) -> str:
    layout = Layout(title="t", columns=10, components=(component,), style=style_inline)
    render_layout.render(layout, tmp_path / "o")
    return (tmp_path / "o.svg").read_text(encoding="utf-8")


_CRYSTAL = Component(kind="crystal", ref="X1", value="16MHz", legs=("A1", "A3"))

# (id, component, (section, key), default_value, wild_value)
_CRYSTAL_STYLE_CASES = [
    ("crystal-body-colour", _CRYSTAL, ("crystal", "body"), "#c8ccce", _SENTINEL),
    ("crystal-body-edge-colour", _CRYSTAL, ("crystal", "body_edge"), "#7f8589", _SENTINEL),
    ("crystal-body-edge-width", _CRYSTAL, ("crystal", "body_edge_width"), 1.0, 9.9),
]


@pytest.mark.parametrize(
    "label, component, key, default_value, wild_value",
    _CRYSTAL_STYLE_CASES,
    ids=[case[0] for case in _CRYSTAL_STYLE_CASES],
)
def test_crystal_style_key_read_from_style(
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
    # An explicit default-value override must produce the same render as no override.
    assert default_svg == same_svg, f"{label}: style default != render with no override"


_INDUCTOR = Component(kind="inductor", ref="L1", value="10uH", legs=("A1", "A3"))

# (id, component, (section, key), default_value, wild_value)
_INDUCTOR_STYLE_CASES = [
    ("inductor-coil-colour", _INDUCTOR, ("inductor", "coil"), "#6b5430", _SENTINEL),
    ("inductor-coil-width", _INDUCTOR, ("inductor", "coil_width"), 1.6, 9.9),
    ("inductor-body-colour", _INDUCTOR, ("inductor", "body"), "#efe7d6", _SENTINEL),
    ("inductor-body-edge-colour", _INDUCTOR, ("inductor", "body_edge"), "#9a8f78", _SENTINEL),
    ("inductor-body-edge-width", _INDUCTOR, ("inductor", "body_edge_width"), 1.0, 9.9),
]


@pytest.mark.parametrize(
    "label, component, key, default_value, wild_value",
    _INDUCTOR_STYLE_CASES,
    ids=[case[0] for case in _INDUCTOR_STYLE_CASES],
)
def test_inductor_style_key_read_from_style(
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
    # An explicit default-value override must produce the same render as no override.
    assert default_svg == same_svg, f"{label}: style default != render with no override"
