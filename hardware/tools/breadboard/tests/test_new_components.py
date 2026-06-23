"""Render tests for the new components.

Each component test renders a single-component layout and asserts the drawer
added geometry beyond the bare board. A no-op drawer (one that registers but
draws nothing) would still leave the board SVG non-empty, so a plain "is the
SVG non-empty" check could never catch it; comparing the drawn <path> count
against an empty board can.
"""

import logging
import re
from pathlib import Path

import pytest

import render_layout
from breadboard.model import Component, Layout, Pin
from breadboard.parse import _component_from_dict

_CLIP_ID_RE = re.compile(r'(id="|url\(#)(p[0-9a-f]{9,})')


def _scrub(svg_text: str) -> str:
    text = re.sub(r"[ \t]*<dc:date>.*?</dc:date>\n?", "", svg_text)
    return _CLIP_ID_RE.sub(lambda m: m.group(1) + "CLIP_ID_PLACEHOLDER", text)


def _path_count(svg_text: str) -> int:
    """Number of drawn <path> elements; a proxy for rendered geometry."""
    return svg_text.count("<path")


@pytest.fixture(scope="module")
def empty_board_paths(tmp_path_factory: pytest.TempPathFactory) -> int:
    """<path> count for a board with no components: the no-op-drawer floor."""
    layout = Layout(title="t", columns=10, components=(), style=None)
    out = tmp_path_factory.mktemp("empty") / "o"
    render_layout.render(layout, out)
    return _path_count(out.with_suffix(".svg").read_text(encoding="utf-8"))


def test_crystal_draws_geometry(tmp_path: Path, empty_board_paths: int) -> None:
    crystal = Component(kind="crystal", ref="X1", value="16MHz", legs=("A1", "A3"))
    layout = Layout(title="t", columns=10, components=(crystal,), style=None)
    render_layout.render(layout, tmp_path / "o")
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")
    assert _path_count(svg) > empty_board_paths, (
        "crystal drawer added no geometry beyond the bare board (no-op drawer?)"
    )


def test_inductor_draws_geometry(tmp_path: Path, empty_board_paths: int) -> None:
    inductor = Component(kind="inductor", ref="L1", value="10uH", legs=("A1", "A3"))
    layout = Layout(title="t", columns=10, components=(inductor,), style=None)
    render_layout.render(layout, tmp_path / "o")
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")
    assert _path_count(svg) > empty_board_paths, (
        "inductor drawer added no geometry beyond the bare board (no-op drawer?)"
    )


def test_buzzer_draws_geometry(tmp_path: Path, empty_board_paths: int) -> None:
    buzzer = Component(kind="buzzer", ref="BZ1", legs=("A1", "A3"))
    layout = Layout(title="t", columns=10, components=(buzzer,), style=None)
    render_layout.render(layout, tmp_path / "o")
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")
    assert _path_count(svg) > empty_board_paths, (
        "buzzer drawer added no geometry beyond the bare board (no-op drawer?)"
    )


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


def test_potentiometer_draws_geometry(tmp_path: Path, empty_board_paths: int) -> None:
    pot = Component(kind="potentiometer", ref="RV1", value="10k", legs=("D1", "D2", "D3"))
    layout = Layout(title="t", columns=10, components=(pot,), style=None)
    render_layout.render(layout, tmp_path / "o")
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")
    assert _path_count(svg) > empty_board_paths, (
        "potentiometer drawer added no geometry beyond the bare board (no-op drawer?)"
    )


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


def test_relay_draws_geometry(tmp_path: Path, empty_board_paths: int) -> None:
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
    assert _path_count(svg) > empty_board_paths, (
        "relay drawer added no geometry beyond the bare board (no-op drawer?)"
    )


def test_seven_segment_draws_geometry(tmp_path: Path, empty_board_paths: int) -> None:
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
    assert _path_count(svg) > empty_board_paths, (
        "7segment drawer added no geometry beyond the bare board (no-op drawer?)"
    )


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

    all_warnings = [
        r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING
    ]
    pin_warnings = [w for w in all_warnings if "pin" in w.lower()]
    assert pin_warnings, (
        "expected at least one WARNING referencing pins when 7segment has no pins; got none"
    )
    # 7segment IS a registered kind: it must reach its drawer (which warns about the
    # missing pins), not fall through to the dispatch loop's "unknown kind" skip.
    # Check the UNFILTERED warning list — filtering to "pin" first would always exclude
    # the dispatch message ("unknown component kind ...") and make this assertion vacuous.
    assert not any("unknown component kind" in w for w in all_warnings), (
        "7segment IS a registered kind; it must not trigger the dispatch loop's "
        "'unknown component kind' warning"
    )


def test_seven_segment_digits_defaults_to_one() -> None:
    """A 7-segment mapping with no `digits:` key parses as a single-digit display."""
    seg = _component_from_dict({"kind": "7segment", "ref": "DS1"})
    assert seg.digits == 1, "absent `digits:` must default to a single digit"


def test_seven_segment_digits_parsed_from_yaml_mapping() -> None:
    """The PRD lists `digits` as a 7-segment input; the parser must carry it through."""
    seg = _component_from_dict({"kind": "7segment", "ref": "DS1", "digits": 4})
    assert seg.digits == 4, "`digits:` from the layout mapping was dropped by the parser"


def test_seven_segment_digits_draws_one_figure_eight_per_digit(tmp_path: Path) -> None:
    """`digits: N` renders N figure-8 groups; more digits means strictly more segment geometry.

    Binds to intent: the optional `digits` count must actually multiply the drawn
    seven-segment figure-8s, not be silently ignored. Each extra digit adds its own
    7 segment polygons (+ a decimal point), so a 3-digit display draws at least
    2 * 7 more segment paths than a 1-digit one.
    """
    one = Component(
        kind="7segment", ref="DS1", common="cathode", digits=1,
        span=(1, 6), pins=(Pin(name="a", hole="A1"), Pin(name="b", hole="A6")),
    )
    three = Component(
        kind="7segment", ref="DS1", common="cathode", digits=3,
        span=(1, 6), pins=(Pin(name="a", hole="A1"), Pin(name="b", hole="A6")),
    )

    render_layout.render(Layout(title="t", columns=10, components=(one,), style=None), tmp_path / "d1")
    render_layout.render(Layout(title="t", columns=10, components=(three,), style=None), tmp_path / "d3")
    svg1 = _scrub((tmp_path / "d1.svg").read_text(encoding="utf-8"))
    svg3 = _scrub((tmp_path / "d3.svg").read_text(encoding="utf-8"))

    assert svg1 != svg3, "changing `digits` produced an identical render: the input is ignored"
    paths1 = svg1.count("<path")
    paths3 = svg3.count("<path")
    assert paths3 - paths1 >= 14, (
        f"3-digit display drew too few extra segment polygons "
        f"({paths3} vs {paths1}); expected >= 14 more for two extra figure-8s"
    )


def test_seven_segment_default_digit_render_is_unchanged(tmp_path: Path) -> None:
    """A 7-segment with no explicit `digits` renders identically to `digits=1`.

    Guards the additive invariant: introducing `digits` must not perturb the
    existing single-digit output (the golden parity fixture depends on this).
    """
    implicit = Component(
        kind="7segment", ref="DS1", common="cathode",
        span=(1, 4), pins=(Pin(name="a", hole="A1"), Pin(name="b", hole="A4")),
    )
    explicit_one = Component(
        kind="7segment", ref="DS1", common="cathode", digits=1,
        span=(1, 4), pins=(Pin(name="a", hole="A1"), Pin(name="b", hole="A4")),
    )
    render_layout.render(Layout(title="t", columns=10, components=(implicit,), style=None), tmp_path / "imp")
    render_layout.render(Layout(title="t", columns=10, components=(explicit_one,), style=None), tmp_path / "exp")
    svg_imp = _scrub((tmp_path / "imp.svg").read_text(encoding="utf-8"))
    svg_exp = _scrub((tmp_path / "exp.svg").read_text(encoding="utf-8"))
    assert svg_imp == svg_exp, "default digits must equal digits=1 exactly"


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
