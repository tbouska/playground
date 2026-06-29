"""Behavior-lock tests for load_style() and the Style accessor dataclass."""

import logging
from pathlib import Path

import pytest

from breadboard.style import Style, load_style


def test_load_style_no_args_returns_defaults() -> None:
    style = load_style()

    assert isinstance(style, Style)
    assert style.color("board.fill") == "#efeae0"
    assert style.dim("dot.radius") == 0.13
    assert style.resistor_digit_colors[2] == "#c0392b"


def test_deep_merge_override_changes_key_and_leaves_siblings() -> None:
    style = load_style(inline={"hole": {"shadow": "#000000"}})

    assert style.color("hole.shadow") == "#000000"
    assert style.color("hole.fill") != "#000000"
    assert style.color("board.fill") == "#efeae0"


def test_partial_override_unmentioned_keys_remain_at_defaults() -> None:
    style = load_style(inline={"rail": {"plus": "#ff0000"}})

    assert style.color("rail.plus") == "#ff0000"
    assert style.color("board.fill") == "#efeae0"
    assert style.color("hole.shadow") == "#c8c1af"
    assert style.dim("dot.radius") == 0.13
    assert style.dim("hole.radius") == 0.18
    assert style.dim("render.dpi") == 200


def test_unknown_top_level_key_warns_and_does_not_crash(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="breadboard"):
        style = load_style(inline={"bogus_top": {"x": 1}})

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) >= 1

    assert style.color("board.fill") == "#efeae0"
    assert style.dim("dot.radius") == 0.13


def test_unknown_nested_key_warns_and_does_not_crash(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="breadboard"):
        style = load_style(inline={"hole": {"bogus": 1}})

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) >= 1

    assert style.color("hole.shadow") == "#c8c1af"
    assert style.color("board.fill") == "#efeae0"


def test_path_file_override_changes_key_and_leaves_rest_default(tmp_path: Path) -> None:
    import yaml

    override_file = tmp_path / "override.yaml"
    override_file.write_text(yaml.dump({"board": {"fill": "#123456"}}))

    style = load_style(path=override_file)

    assert style.color("board.fill") == "#123456"
    assert style.color("hole.shadow") == "#c8c1af"
    assert style.dim("dot.radius") == 0.13


def test_inline_wins_over_path_file_for_same_key(tmp_path: Path) -> None:
    import yaml

    override_file = tmp_path / "override.yaml"
    override_file.write_text(yaml.dump({"board": {"fill": "#aaaaaa"}}))

    style = load_style(path=override_file, inline={"board": {"fill": "#bbbbbb"}})

    assert style.color("board.fill") == "#bbbbbb"


def test_style_accessors_return_correct_types() -> None:
    style = load_style()

    assert isinstance(style.color("rail.plus"), str)
    assert isinstance(style.dim("dot.radius"), float)
    assert isinstance(style.resistor_digit_colors, tuple)
    assert len(style.resistor_digit_colors) == 10
    assert style.resistor_digit_colors[0] == "#1a1a1a"
    assert style.resistor_multiplier_extra == {-1: "#cda434", -2: "#bfc1c2"}
    assert style.channel_colors == {"R": "#c0392b", "G": "#27ae60", "B": "#2c5fb3"}
    assert style.label_bbox["facecolor"] == "#efeae0"
    assert style.label_bbox["boxstyle"] == "round,pad=0.18"
