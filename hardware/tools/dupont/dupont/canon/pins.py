from __future__ import annotations

_NORMALIZE: dict[str, dict[str, str]] = {
    "led": {"A": "anode", "K": "cathode"},
    "led-rgb": {"K": "cathode"},
}

_DENORMALIZE: dict[str, dict[str, str]] = {
    "led": {"anode": "A", "cathode": "K"},
    "led-rgb": {"cathode": "K"},
}


def normalize_pin_name(kind: str, raw_name: str) -> str:
    return _NORMALIZE.get(kind, {}).get(raw_name, raw_name)


def denormalize_pin_name(kind: str, canonical: str) -> str:
    return _DENORMALIZE.get(kind, {}).get(canonical, canonical)
