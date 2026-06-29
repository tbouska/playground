import re

# Ordered vertical lines of the board, top to bottom. "" marks a blank gap slot.
LINE_ORDER: tuple[str, ...] = (
    "T+",
    "T-",
    "",
    "A",
    "B",
    "C",
    "D",
    "E",
    "",
    "F",
    "G",
    "H",
    "I",
    "J",
    "",
    "B+",
    "B-",
)
RAIL_ADDRESS = re.compile(r"^([TB][+-])(\d+)$")
GRID_ADDRESS = re.compile(r"^([A-J])(\d+)$")


class Geometry:
    """Map hole addresses to drawing coordinates for a board width.

    :ivar columns: The number of numbered columns.
    :vartype columns: int
    :ivar line_y: The y coordinate of each named line.
    :vartype line_y: dict[str, float]
    """

    def __init__(self, columns: int) -> None:
        """Build the geometry for a board with the given column count.

        :param columns: The number of numbered columns.
        :type columns: int
        """
        self.columns = columns
        self.line_y = {
            key: -float(index) for index, key in enumerate(LINE_ORDER) if key
        }

    def hole(self, address: str) -> tuple[float, float]:
        """Resolve a hole address to an ``(x, y)`` coordinate.

        :param address: A hole address such as ``"F12"`` or ``"B-28"``.
        :type address: str
        :returns: The coordinate of the hole center.
        :rtype: tuple[float, float]
        :raises ValueError: If the address does not match a known hole.
        """
        rail = RAIL_ADDRESS.match(address)
        if rail:
            return float(rail.group(2)), self.line_y[rail.group(1)]
        grid = GRID_ADDRESS.match(address)
        if grid:
            return float(grid.group(2)), self.line_y[grid.group(1)]
        raise ValueError(f"invalid hole address: {address!r}")
