"""Catalog shift implementations. Each shift exports `ShiftImpl(law, sampler, validator)`.

Sprint 1: `hooke_g_1_1` only.
"""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ShiftImpl:
    """Spec §3.2 contract for every catalog shift.

    Fields
    ------
    law : Callable[[float, Any], float]
        The shifted force / EOM / rate routine. Signature matches the baseline
        domain's routine so the registry can swap it in transparently.
    sampler : Callable[[int], Any]
        Draws shift parameters from the catalog-documented distribution given
        an RNG seed; returns a domain-appropriate params dataclass.
    validator : Callable[[Any], bool]
        Re-runs the catalog's safety preconditions at scenario emit; returns
        True iff `params` are acceptable.
    """

    law: Callable[[float, Any], float]
    sampler: Callable[[int], Any]
    validator: Callable[[Any], bool]


__all__ = ["ShiftImpl"]
