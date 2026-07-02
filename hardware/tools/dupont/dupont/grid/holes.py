"""Breadboard hole-address grid contract.

Classifies a hole address into its electrical base node (:func:`node_key`)
and its integer grid position (:func:`hole_coords`), reusing the address
grammar defined in :mod:`breadboard.geometry`.
"""

from dataclasses import dataclass

from breadboard.geometry import GRID_ADDRESS, LINE_ORDER, RAIL_ADDRESS

PITCH_MM: float = 2.54
BANK_UPPER: frozenset[str] = frozenset("ABCDE")
BANK_LOWER: frozenset[str] = frozenset("FGHIJ")


@dataclass(frozen=True)
class HoleAddr:
    """A parsed hole address.

    :ivar kind: Either ``"grid"`` or ``"rail"``.
    :vartype kind: str
    :ivar line: The line identifier, e.g. ``"B"`` or ``"B-"``.
    :vartype line: str
    :ivar column: The numbered column.
    :vartype column: int
    """

    kind: str
    line: str
    column: int


def parse_hole(address: str) -> HoleAddr:
    """Classify a hole address as a grid or rail hole.

    :param address: A hole address such as ``"F12"`` or ``"B-28"``.
    :type address: str
    :returns: The parsed address.
    :rtype: HoleAddr
    :raises ValueError: If the address does not match a known hole.
    """
    rail = RAIL_ADDRESS.match(address)
    if rail:
        return HoleAddr(kind="rail", line=rail.group(1), column=int(rail.group(2)))
    grid = GRID_ADDRESS.match(address)
    if grid:
        return HoleAddr(kind="grid", line=grid.group(1), column=int(grid.group(2)))
    raise ValueError(f"invalid hole address: {address!r}")


def node_key(address: str) -> tuple:
    """Resolve a hole address to its electrical base node.

    :param address: A hole address such as ``"F12"`` or ``"B-28"``.
    :type address: str
    :returns: ``("bank", "upper"|"lower", column)`` for grid holes, or
        ``("rail", line)`` for rail holes.
    :rtype: tuple
    :raises ValueError: If the address does not match a known hole.
    """
    hole = parse_hole(address)
    if hole.kind == "rail":
        return ("rail", hole.line)
    bank = "upper" if hole.line in BANK_UPPER else "lower"
    return ("bank", bank, hole.column)


def hole_coords(address: str) -> tuple[int, int]:
    """Resolve a hole address to its integer pitch-grid position.

    :param address: A hole address such as ``"F12"`` or ``"B-28"``.
    :type address: str
    :returns: The ``(column, row)`` position, where row is the line's
        index in ``LINE_ORDER``.
    :rtype: tuple[int, int]
    :raises ValueError: If the address does not match a known hole.
    """
    hole = parse_hole(address)
    return (hole.column, LINE_ORDER.index(hole.line))
