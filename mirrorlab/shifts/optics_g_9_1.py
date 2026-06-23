"""γ-9-1 — Optics: polarization-dependent absorption (dichroism).

Catalog (Domain 9, Tier-1, ROUND-2 redesign):
    transmittance through a dichroic film:
        T(θ_i, θ_pol) = (1 − R0) · exp(−β(θ_pol) / cos θ_i),
        β(θ_pol) = β0 · (1 + χ · sin²(2·θ_pol − φ)).
    The absorption depth depends on the polarization angle θ_pol → the energy
    that gets transmitted is polarization-selective (dichroism).

Broken : polarization U(1) (transmittance depends on θ_pol; a pol-symmetric
         interface would transmit independent of θ_pol).
Retained: reciprocity, Fermat, tangential k_∥, SO(2) about normal.

The earlier index-modulation form (n_eff = n0 + dn·sin²(2θ_pol−φ), scored in the
ANGLE channel) was unhardenable: the bounded multiplicative index modulation
(dn/n0 ≤ 0.23) kept a fixed-index stub above 0.5, and a Fourier refit that
declares the canonical n0/dn/phi was handed the perturbed truth on sub-grid (c)
→ oracle-indistinguishable. Moving the polarization break into a TRANSMITTANCE
channel with a grazing-angle cliff (cos θ_i → 0) makes a free power-law / 2-D
polynomial fit to the flat in-domain region unable to extrapolate the OOD cliff,
while β(θ_pol) keeps the break polarization-selective.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from math import cos, exp
from typing import Dict

import numpy as np

from mirrorlab.spec import P, CellSpec, register_cell
from mirrorlab.shifts import ShiftImpl

R0_MIN, R0_MAX = 0.05, 0.20
BETA0_MIN, BETA0_MAX = 0.30, 1.00
CHI_MIN, CHI_MAX = 0.5, 1.5


@dataclass(frozen=True)
class OpticsGamma91Params:
    n1: float = field(metadata=P.ic())       # incident-side index [1] (angle channel, retained)
    n0: float = field(metadata=P.ic())       # transmitted-side index [1]
    R0: float = field(metadata=P.law("R0"))       # normal-incidence reflectance [1]
    beta0: float = field(metadata=P.law("beta0"))    # base normal optical depth [1]
    chi: float = field(metadata=P.law("chi"))      # polarization dichroism amplitude [1]
    phi: float = field(metadata=P.law("phi"))      # polarization phase [rad]
    theta1: float = field(metadata=P.ic())   # incidence angle [rad]
    theta_pol: float = field(metadata=P.axis())  # polarization angle [rad]


def beta_of(params: OpticsGamma91Params, theta_pol: float) -> float:
    return params.beta0 * (1.0 + params.chi * math.sin(2.0 * theta_pol - params.phi) ** 2)


def transmittance(params: OpticsGamma91Params, theta_i: float, theta_pol: float) -> float:
    return (1.0 - params.R0) * exp(-beta_of(params, theta_pol) / cos(theta_i))


class OpticsGamma91Instance:
    def __init__(self, params: OpticsGamma91Params) -> None:
        if not validator(params):
            raise ValueError(f"γ-9-1 params failed validator: {params!r}")
        self._params = params

    @property
    def params(self) -> OpticsGamma91Params:
        return self._params

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        p = self._params
        return {
            "t": float(t),
            "theta1": float(p.theta1),
            "theta_pol": float(p.theta_pol),
            "T": float(transmittance(p, p.theta1, p.theta_pol)),
        }


def sampler(seed: int) -> OpticsGamma91Params:
    rng = np.random.default_rng(seed)
    n0 = float(rng.uniform(1.3, 2.2))
    R0 = float(rng.uniform(R0_MIN, R0_MAX))
    beta0 = float(rng.uniform(BETA0_MIN, BETA0_MAX))
    chi = float(rng.uniform(CHI_MIN, CHI_MAX))
    phi = float(rng.uniform(0.0, math.pi))
    theta_pol = float(rng.uniform(0.0, math.pi))
    return OpticsGamma91Params(n1=1.0, n0=n0, R0=R0, beta0=beta0, chi=chi,
                               phi=phi, theta1=0.3, theta_pol=theta_pol)


def validator(params: OpticsGamma91Params) -> bool:
    if not isinstance(params, OpticsGamma91Params):
        return False
    if not (R0_MIN <= params.R0 <= R0_MAX):
        return False
    if not (BETA0_MIN <= params.beta0 <= BETA0_MAX):
        return False
    if not (CHI_MIN <= params.chi <= CHI_MAX):
        return False
    if params.n1 <= 0 or params.n0 <= 0:
        return False
    return True


def build(*, params: OpticsGamma91Params | None = None, seed: int = 0) -> OpticsGamma91Instance:
    if params is None:
        params = sampler(seed)
    return OpticsGamma91Instance(params)


shift = ShiftImpl(law=lambda t, p: transmittance(p, p.theta1, p.theta_pol),
                  sampler=sampler, validator=validator)


def law(inputs, p: OpticsGamma91Params) -> float:
    """Unified GT/oracle law: polarization-dependent (dichroic) transmittance
    T(θ_i, θ_pol). θ_i (theta1) and θ_pol are swept grid inputs."""
    return transmittance(p, inputs["theta1"], inputs["theta_pol"])


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"theta1": "1", "theta_pol": "1"},
    "outputs": {"T": "1"},
    "params": {"n0": "1", "R0": "1", "beta0": "1", "chi": "1", "phi": "1"},
}

CELL = CellSpec(
    domain="optics", shift="gamma_9_1",
    params_type=OpticsGamma91Params, law=law,
    sampler=sampler, validator=validator,
    output="T", break_type="U1",
)
register_cell(CELL)

__all__ = [
    "OpticsGamma91Params", "OpticsGamma91Instance", "beta_of", "transmittance",
    "law", "sampler", "validator", "build", "shift", "DIM_SIGNATURE", "CELL",
]
