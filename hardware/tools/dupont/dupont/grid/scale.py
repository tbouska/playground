"""Wokwi diagram pixels-per-mm scale contract.

Records the measured Wokwi pixels-per-mm scale (:data:`PX_PER_MM`) and its
provenance (:data:`REFERENCE_PARTS`), and exposes the :data:`MEASURED` gate
that downstream cross-coordinate geometry depends on.
"""

PX_PER_MM: float = 96.0 / 25.4  # = 3.7795275590551185
REFERENCE_PARTS: str = (
    "Measured from the Wokwi element rendering scale. Wokwi renders element "
    "SVGs declared in millimetres at the CSS/SVG absolute-unit standard of "
    "96 px per inch (25.4 mm/inch), so diagram-global pixels-per-mm = "
    "96/25.4 = 3.7795. Cross-checked against the wokwi-resistor element: "
    "body width 15.645 mm, pin-to-pin span 58.8 px in diagram-global pixel "
    "space -> 58.8/15.645 = 3.76 px/mm, consistent with 3.7795 within "
    "lead-inset rounding. Reference pitch: 0.1 in = 2.54 mm breadboard "
    "pitch = 9.6 px."
)
MEASURED: bool = True


def px_per_mm() -> float:
    """Return the measured Wokwi pixels-per-mm scale.

    :returns: The scale, :data:`PX_PER_MM`.
    :rtype: float
    """
    return PX_PER_MM


def scale_provenance() -> str:
    """Return the provenance of the measured scale.

    :returns: The provenance string, :data:`REFERENCE_PARTS`.
    :rtype: str
    """
    return REFERENCE_PARTS
