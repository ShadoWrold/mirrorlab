"""δ-9-1 — Optics: absorbing-film energy non-conservation (Beer-Lambert).

Catalog (Domain 9, Tier-2, ROUND-2 redesign):
    angles: Snell baseline preserved (still observable, but NOT the scored channel).
    intensity (scored): transmittance through a lossy interface coating
        T(θ_i) = (1 − R0) · exp(−β / cos θ_i),   β = α·d normal optical depth.
    energy:  R + T = R0 + (1−R0)·exp(−β/cosθ_i) < 1  ⇒ absorptance A > 0.

Broken : energy conservation (R + T ≠ 1; the coating absorbs).
Retained: Snell angle law, reciprocity (loss same in/out), SO(2), Fermat,
          tangential k_∥, polarization U(1), 1↔2 interchange.

Why refit-resistant (vs the earlier ξ·|sinθ|^p, a closed-form power law that a
free power-law refit absorbed): exp(−β/cosθ) is FLAT in-domain (cosθ≈1) then
falls off a CLIFF toward grazing (cosθ→0). A free power-law / polynomial fit to
the flat in-domain (a) cannot extrapolate the grazing cliff in OOD (b). Using
cos(θ_i incidence) — not θ_t — makes the cliff reachable for ALL n1,n2 (no TIR
dependence), so hardness is consistent across seeds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, exp
from typing import Dict

import numpy as np

from mirrorlab.spec import P, CellSpec, register_cell
from mirrorlab.shifts import ShiftImpl

R0_MIN, R0_MAX = 0.05, 0.20
BETA_MIN, BETA_MAX = 0.30, 1.00


@dataclass(frozen=True)
class OpticsDelta91Params:
    n1: float = field(metadata=P.ic())       # [1] (angle channel, retained)
    n2: float = field(metadata=P.ic())       # [1]
    theta_i: float = field(metadata=P.axis())  # [rad]
    R0: float = field(metadata=P.law("R0"))       # normal-incidence reflectance [1]
    beta: float = field(metadata=P.law("beta"))     # normal optical depth α·d [1]


def transmittance(theta_i: float, params: OpticsDelta91Params) -> float:
    """Beer-Lambert transmittance through the absorbing film."""
    return (1.0 - params.R0) * exp(-params.beta / cos(theta_i))


class OpticsDelta91Instance:
    def __init__(self, params: OpticsDelta91Params) -> None:
        if not validator(params):
            raise ValueError(f"δ-9-1 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> OpticsDelta91Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        p = self._params
        return {
            "t": float(t),
            "theta_i": float(p.theta_i),
            "T": float(transmittance(p.theta_i, p)),
        }


def sampler(seed: int) -> OpticsDelta91Params:
    rng = np.random.default_rng(seed)
    n1 = float(rng.uniform(1.0, 2.0))
    n2 = float(rng.uniform(1.0, 2.0))
    R0 = float(rng.uniform(R0_MIN, R0_MAX))
    beta = float(rng.uniform(BETA_MIN, BETA_MAX))
    return OpticsDelta91Params(n1=n1, n2=n2, theta_i=0.3, R0=R0, beta=beta)


def validator(params: OpticsDelta91Params) -> bool:
    if not isinstance(params, OpticsDelta91Params):
        return False
    if not (R0_MIN <= params.R0 <= R0_MAX):
        return False
    if not (BETA_MIN <= params.beta <= BETA_MAX):
        return False
    if params.n1 <= 0 or params.n2 <= 0:
        return False
    return True


def build(*, params: OpticsDelta91Params | None = None, seed: int = 0) -> OpticsDelta91Instance:
    if params is None:
        params = sampler(seed)
    return OpticsDelta91Instance(params)


shift = ShiftImpl(law=lambda t, p: transmittance(p.theta_i, p),
                  sampler=sampler, validator=validator)


def law(inputs, p: OpticsDelta91Params) -> float:
    """Unified GT/oracle law: Beer-Lambert transmittance T(θ_i)=
    (1−R0)·exp(−β/cosθ_i). θ_i (theta1) is the swept grid input."""
    return transmittance(inputs["theta1"], p)


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"theta_i": "1"},
    "outputs": {"T": "1"},
    "params": {"n1": "1", "n2": "1", "R0": "1", "beta": "1"},
}

CELL = CellSpec(
    domain="optics", shift="delta_9_1",
    params_type=OpticsDelta91Params, law=law,
    sampler=sampler, validator=validator,
    output="T", break_type="CONS_E",
)
register_cell(CELL)

__all__ = [
    "OpticsDelta91Params", "OpticsDelta91Instance", "transmittance", "law",
    "sampler", "validator", "build", "shift", "DIM_SIGNATURE", "CELL",
]
