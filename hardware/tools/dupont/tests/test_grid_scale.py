"""Contract tests for the Wokwi pixel scale + provenance (dupont/grid/scale.py).

These tests pin the measured-scale contract: a positive pixels-per-mm value
derived from real Wokwi reference parts, its human-readable provenance, and
the MEASURED gate that downstream cross-coordinate geometry depends on.
Values are taken from the PRD contract (00009 / A3), not from running an
implementation.
"""

from dupont.grid.scale import (
    MEASURED,
    PX_PER_MM,
    REFERENCE_PARTS,
    px_per_mm,
    scale_provenance,
)


def test_px_per_mm_returns_positive_float_matching_module_constant() -> None:
    value = px_per_mm()
    assert isinstance(value, float)
    assert value > 0
    assert value == PX_PER_MM


def test_px_per_mm_is_in_physically_plausible_range() -> None:
    assert 0.5 < px_per_mm() < 50.0


def test_measured_flag_is_true_once_real_value_is_recorded() -> None:
    assert MEASURED is True


def test_scale_provenance_returns_descriptive_string_matching_reference_parts() -> (
    None
):
    provenance = scale_provenance()
    assert isinstance(provenance, str)
    assert provenance == REFERENCE_PARTS
    assert len(provenance) > 10
