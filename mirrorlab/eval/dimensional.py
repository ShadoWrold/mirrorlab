"""Stage-1 dimensional pre-filter.

Per spec §6.1: each submission entry must declare an SI dimensional signature
on its declared output. We parse the declared output units into a 7-tuple of
SI base-dimension exponents and compare to the scenario's target signature.
Failure ⇒ auto-0 (fail closed).

SI 7-tuple convention: ``(M, L, T, I, Θ, N, J)`` of integer exponents over
(mass, length, time, current, temperature, amount, luminous intensity).

The parser accepts both raw SI base units (``kg``, ``m``, ``s``, ``A``, ``K``,
``mol``, ``cd``) and symbolic dimensions (``M``, ``L``, ``T``, ``I``, ``Θ`` /
``Theta``, ``N`` for amount, ``J`` for luminous intensity). A leading/trailing
``[`` ``]`` bracket is stripped, ``·`` is treated as ``*``, and exponents may
be written ``**n`` or ``^n``. ``"1"`` (or ``""``) is the dimensionless tuple.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Tuple

Dim7 = Tuple[int, int, int, int, int, int, int]

ZERO: Dim7 = (0, 0, 0, 0, 0, 0, 0)

_UNIT_TO_INDEX = {
    "kg": 0, "M": 0,
    "m":  1, "L": 1,
    "s":  2, "T": 2,
    "A":  3, "I": 3,
    "K":  4, "Θ": 4, "Theta": 4,
    "mol": 5, "N": 5,
    "cd": 6, "J": 6,
}

_TOKEN_RE = re.compile(
    r"(?P<unit>[A-Za-zΘ]+)\s*(?:(?:\*\*|\^)\s*(?P<exp>[+-]?\d+))?"
)


def parse_dim(spec: str) -> Dim7:
    """Parse a units string into the SI 7-tuple ``(M, L, T, I, Θ, N, J)``.

    Examples:
        ``"kg*m*s**-2"`` → ``(1, 1, -2, 0, 0, 0, 0)``
        ``"[M·L/T²]"``   → ``(1, 1, -2, 0, 0, 0, 0)``
        ``"1"``          → ``(0,)*7``
    """
    if spec is None:
        raise ValueError("dim spec is None")
    s = spec.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    s = s.replace("·", "*").replace("⋅", "*")
    # Unicode superscripts → ASCII exponent. Conservative: just the common ones.
    sup_map = {"²": "**2", "³": "**3", "⁴": "**4", "⁵": "**5",
               "⁰": "**0", "¹": "**1", "⁻": "**-"}
    for k, v in sup_map.items():
        s = s.replace(k, v)
    # Fix "**-2" already, and "**2" already fine. But "⁻²" became "**-**2"; fix:
    s = s.replace("**-**", "**-")
    if not s or s == "1":
        return ZERO

    exps = [0] * 7
    parts = s.split("/")
    sign = 1
    for part in parts:
        for match in _TOKEN_RE.finditer(part):
            unit = match.group("unit")
            exp = int(match.group("exp") or "1")
            if unit not in _UNIT_TO_INDEX:
                raise ValueError(f"unknown unit token {unit!r} in {spec!r}")
            exps[_UNIT_TO_INDEX[unit]] += sign * exp
        sign = -1  # everything after the first '/' is inverted
    return tuple(exps)  # type: ignore[return-value]


def match_dim(entry: Mapping[str, Any], target_signature: str | Dim7) -> bool:
    """Return True iff the entry's declared output units match the target.

    ``entry["outputs"]`` is expected as ``[{"name": ..., "units": "..."}]``;
    Sprint-1 scenarios declare a single output channel, so we compare the
    first declared output against ``target_signature`` (a units string or a
    pre-parsed 7-tuple). Missing / malformed units ⇒ False (fail closed).
    """
    try:
        outputs = entry.get("outputs") or []
        if not outputs:
            return False
        units = outputs[0].get("units")
        if units is None:
            return False
        got = parse_dim(units)
        want = target_signature if isinstance(target_signature, tuple) else parse_dim(target_signature)
        return got == want
    except (ValueError, AttributeError, TypeError):
        return False


__all__ = ["Dim7", "ZERO", "parse_dim", "match_dim"]
