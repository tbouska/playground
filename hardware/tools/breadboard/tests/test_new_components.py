"""Smoke render tests for new components (crystal, inductor, buzzer).

Verifies that rendering a layout containing each component completes
without raising and produces a non-empty SVG file.
"""

import logging
import re
from pathlib import Path

import render_layout
from breadboard.model import Component, Layout, Pin

_CLIP_ID_RE = re.compile(r'(id="|url\(#)(p[0-9a-f]{9,})')


def _scrub(svg_text: str) -> str:
    text = re.sub(r"[ \t]*<dc:date>.*?</dc:date>\n?", "", svg_text)
    return _CLIP_ID_RE.sub(lambda m: m.group(1) + "CLIP_ID_PLACEHOLDER", text)


def test_crystal_renders_without_error(tmp_path: Path) -> None:
    crystal = Component(kind="crystal", ref="X1", value="16MHz", legs=("A1", "A3"))
    layout = Layout(title="t", columns=10, components=(crystal,), style=None)
    render_layout.render(layout, tmp_path / "o")
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")
    assert svg, "crystal render produced an empty SVG"


def test_inductor_renders_without_error(tmp_path: Path) -> None:
    inductor = Component(kind="inductor", ref="L1", value="10uH", legs=("A1", "A3"))
    layout = Layout(title="t", columns=10, components=(inductor,), style=None)
    render_layout.render(layout, tmp_path / "o")
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")
    assert svg, "inductor render produced an empty SVG"


def test_buzzer_renders_without_error(tmp_path: Path) -> None:
    buzzer = Component(kind="buzzer", ref="BZ1", legs=("A1", "A3"))
    layout = Layout(title="t", columns=10, components=(buzzer,), style=None)
    render_layout.render(layout, tmp_path / "o")
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")
    assert svg, "buzzer render produced an empty SVG"


def test_buzzer_polarity_follows_leg_order(tmp_path: Path) -> None:
    """The + mark is placed on legs[0] side; reversing leg order must move it."""
    buzzer_fwd = Component(kind="buzzer", ref="BZ1", legs=("A1", "A3"))
    buzzer_rev = Component(kind="buzzer", ref="BZ1", legs=("A3", "A1"))

    layout_fwd = Layout(title="t", columns=10, components=(buzzer_fwd,), style=None)
    render_layout.render(layout_fwd, tmp_path / "fwd")
    svg_fwd = _scrub((tmp_path / "fwd.svg").read_text(encoding="utf-8"))

    layout_rev = Layout(title="t", columns=10, components=(buzzer_rev,), style=None)
    render_layout.render(layout_rev, tmp_path / "rev")
    svg_rev = _scrub((tmp_path / "rev.svg").read_text(encoding="utf-8"))

    assert svg_fwd != svg_rev, (
        "buzzer polarity not enforced: reversing legs[0]/legs[1] produced identical SVG"
    )


def test_potentiometer_renders_without_error(tmp_path: Path) -> None:
    pot = Component(kind="potentiometer", ref="RV1", value="10k", legs=("D1", "D2", "D3"))
    layout = Layout(title="t", columns=10, components=(pot,), style=None)
    render_layout.render(layout, tmp_path / "o")
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")
    assert svg, "potentiometer render produced an empty SVG"


def test_potentiometer_wiper_follows_middle_leg(tmp_path: Path) -> None:
    """The wiper tick points toward legs[1]; swapping which leg is the middle must move it."""
    pot_d2_wiper = Component(kind="potentiometer", ref="RV1", value="10k", legs=("D1", "D2", "D3"))
    pot_d1_wiper = Component(kind="potentiometer", ref="RV1", value="10k", legs=("D2", "D1", "D3"))

    layout_d2 = Layout(title="t", columns=10, components=(pot_d2_wiper,), style=None)
    render_layout.render(layout_d2, tmp_path / "d2wiper")
    svg_d2 = _scrub((tmp_path / "d2wiper.svg").read_text(encoding="utf-8"))

    layout_d1 = Layout(title="t", columns=10, components=(pot_d1_wiper,), style=None)
    render_layout.render(layout_d1, tmp_path / "d1wiper")
    svg_d1 = _scrub((tmp_path / "d1wiper.svg").read_text(encoding="utf-8"))

    assert svg_d2 != svg_d1, (
        "potentiometer wiper not enforced: changing legs[1] (wiper leg) produced identical SVG"
    )


def test_relay_renders_without_error(tmp_path: Path) -> None:
    relay = Component(
        kind="relay",
        ref="K1",
        label="RELAY",
        span=(1, 3),
        pins=(Pin(name="VCC", hole="A1"), Pin(name="NO", hole="A3")),
    )
    layout = Layout(title="t", columns=10, components=(relay,), style=None)
    render_layout.render(layout, tmp_path / "o")
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")
    assert svg, "relay render produced an empty SVG"


def test_seven_segment_renders_without_error(tmp_path: Path) -> None:
    seg = Component(
        kind="7segment",
        ref="DS1",
        common="cathode",
        span=(1, 4),
        pins=(Pin(name="a", hole="A1"), Pin(name="b", hole="A4")),
    )
    layout = Layout(title="t", columns=10, components=(seg,), style=None)
    render_layout.render(layout, tmp_path / "o")
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")
    assert svg, "7segment render produced an empty SVG"


def test_seven_segment_empty_pins_warns_and_does_not_crash(tmp_path: Path, caplog) -> None:
    seg = Component(
        kind="7segment",
        ref="DS1",
        common="cathode",
        span=(1, 4),
        pins=(),
    )
    layout = Layout(title="t", columns=10, components=(seg,), style=None)
    out_stem = tmp_path / "no_pins"

    with caplog.at_level(logging.WARNING, logger="breadboard"):
        render_layout.render(layout, out_stem)

    svg_path = out_stem.with_suffix(".svg")
    assert svg_path.exists(), f"render() did not write {svg_path}"
    assert svg_path.stat().st_size > 0

    pin_warnings = [
        r.getMessage()
        for r in caplog.records
        if r.levelno >= logging.WARNING and "pin" in r.getMessage().lower()
    ]
    assert pin_warnings, (
        "expected at least one WARNING referencing pins when 7segment has no pins; got none"
    )
    # The warning must come from the drawer, not the generic dispatch loop.
    assert not any("unknown component kind" in w for w in pin_warnings), (
        "7segment IS a registered kind; the pin warning must not be the generic "
        "'unknown component kind' message from the dispatch loop"
    )


def test_seven_segment_empty_pins_and_empty_span_skips_without_crash(tmp_path: Path, caplog) -> None:
    seg = Component(
        kind="7segment",
        ref="DS1",
        common="cathode",
        span=(0, 0),
        pins=(),
    )
    layout = Layout(title="t", columns=10, components=(seg,), style=None)
    out_stem = tmp_path / "no_pins_no_span"

    with caplog.at_level(logging.WARNING, logger="breadboard"):
        render_layout.render(layout, out_stem)

    svg_path = out_stem.with_suffix(".svg")
    assert svg_path.exists(), f"render() did not write {svg_path}"
    assert svg_path.stat().st_size > 0

    pin_warnings = [
        r.getMessage()
        for r in caplog.records
        if r.levelno >= logging.WARNING and "pin" in r.getMessage().lower()
    ]
    assert pin_warnings, (
        "expected at least one WARNING referencing pins when 7segment has no pins and no span; got none"
    )
