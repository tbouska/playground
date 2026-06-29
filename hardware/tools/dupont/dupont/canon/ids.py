from __future__ import annotations

ID_PREFIX: dict[str, str] = {
    "mcu": "U",
    "led": "D",
    "led-rgb": "D",
    "resistor": "R",
    "button": "SW",
}


def mint_id(kind: str, ordinal: int) -> str:
    if kind not in ID_PREFIX:
        raise ValueError(f"Unknown kind: {kind!r}")
    return f"{ID_PREFIX[kind]}{ordinal}"


def mint_ids(kinds: list[str]) -> list[str]:
    counters: dict[str, int] = {}
    result = []
    for kind in kinds:
        if kind not in ID_PREFIX:
            raise ValueError(f"Unknown kind: {kind!r}")
        prefix = ID_PREFIX[kind]
        counters[prefix] = counters.get(prefix, 0) + 1
        result.append(f"{prefix}{counters[prefix]}")
    return result
