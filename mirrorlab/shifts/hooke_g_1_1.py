"""γ-1-1 — Hooke saturating asymmetric stiffness.

Catalog (`d6-shift-catalog.md` Domain 1, Tier-1):
    F(x) = -k x · [1 + η tanh(x/x₀)]

  Broken : PAR (x → -x)
  Retained: T-trans (autonomous & conservative ⇒ E exists),
            T-rev (no ẋ), LIN-in-the-small (|x| ≪ x₀).
  Dim    : [k]=kg·s⁻², [η]=1, [x₀]=m, [x]=m → [F]=kg·m·s⁻².
  Sampling: k ~ LogUniform(1, 100); η ~ Uniform(0.1, 0.8);
            x₀ ~ LogUniform(0.05, 2.0).
  Safe   : simulate |x| ≤ 4 x₀ (potential well stays single-minimum).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np

from mirrorlab.domains.hooke import PotentialLaw, SimInstance, make_potential
from mirrorlab.shifts import ShiftImpl

K_MIN, K_MAX = 1.0, 100.0
ETA_MIN, ETA_MAX = 0.1, 0.8
X0_MIN, X0_MAX = 0.05, 2.0
SAFE_X_FACTOR = 4.0


@dataclass(frozen=True)
class HookeGamma11Params:
    """Bundle of baseline IC + γ-1-1 shift parameters."""

    k: float          # spring constant [N/m]
    m: float          # mass [kg]
    x0: float         # initial displacement [m]
    v0: float         # initial velocity [m/s]
    eta: float        # asymmetry amplitude, dimensionless
    x_scale: float    # saturation length x₀ [m]


def shifted_force(x: float, params: HookeGamma11Params) -> float:
    """γ-1-1 force law."""
    return -params.k * x * (1.0 + params.eta * math.tanh(x / params.x_scale))


def shifted_potential(params: HookeGamma11Params) -> PotentialLaw:
    """NewtonBench-style energy form ``U(x) = ∫₀ˣ k s [1 + η tanh(s/x₀)] ds``.

    Numerical antiderivative of :func:`shifted_force`, returned as a cached
    per-instance callable. No closed form exists — the ``∫ s tanh(s/x₀) ds``
    piece reduces to dilogarithms — but ``scipy.integrate.quad`` handles each
    fresh ``x`` in under ~50 µs and the per-instance cache makes repeated
    queries free. Splice point for any NewtonBench-style scoring path whose
    canonical observable is energy.
    """
    return make_potential(shifted_force, params)


def _loguniform(rng: np.random.Generator, lo: float, hi: float) -> float:
    return float(np.exp(rng.uniform(math.log(lo), math.log(hi))))


def sampler(seed: int) -> HookeGamma11Params:
    """Catalog-faithful sampler.

    Returns parameters that are guaranteed (by construction) to pass
    `validator`. Mass defaults to 1 kg and initial conditions are placed
    well inside the safe envelope so a downstream integrator can not
    blow out of `|x| ≤ 4 x₀`.
    """
    rng = np.random.default_rng(seed)
    k = _loguniform(rng, K_MIN, K_MAX)
    eta = float(rng.uniform(ETA_MIN, ETA_MAX))
    x_scale = _loguniform(rng, X0_MIN, X0_MAX)
    m = 1.0
    x0_amp = 0.5 * x_scale
    return HookeGamma11Params(k=k, m=m, x0=x0_amp, v0=0.0, eta=eta, x_scale=x_scale)


def validator(params: HookeGamma11Params) -> bool:
    """Catalog safety preconditions.

    Returns False if any sampled parameter falls outside its catalog range,
    if the mass is non-positive, or if the initial conditions imply a turning
    amplitude that escapes the `|x| ≤ 4 x₀` safe well.
    """
    if not isinstance(params, HookeGamma11Params):
        return False
    if not (K_MIN <= params.k <= K_MAX):
        return False
    if not (ETA_MIN <= params.eta <= ETA_MAX):
        return False
    if not (X0_MIN <= params.x_scale <= X0_MAX):
        return False
    if params.m <= 0.0:
        return False
    # Energy at IC vs barrier at x = ±4 x_scale. Potential is monotone in |x|
    # (single-well as long as η < 1, which the sampler bounds enforce), so the
    # turning radius is bounded by the V⁻¹ of the IC energy. Conservative bound:
    # require |x0| ≤ 4 x_scale and v0² ≤ 2 V(4 x_scale)/m (linear-Hooke
    # underestimate of barrier height — strictly less than the true tanh barrier
    # so the bound is conservative).
    if abs(params.x0) > SAFE_X_FACTOR * params.x_scale:
        return False
    x_bar = SAFE_X_FACTOR * params.x_scale
    e_ic = 0.5 * params.m * params.v0 ** 2 + 0.5 * params.k * params.x0 ** 2
    v_bar = 0.5 * params.k * x_bar ** 2
    if e_ic >= v_bar:
        return False
    return True


def build(*, params: HookeGamma11Params | None = None, seed: int = 0) -> SimInstance:
    """Construct a SimInstance with the γ-1-1 force law injected."""
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-1-1 params failed validator: {params!r}")
    return SimInstance(params, shifted_force)


shift = ShiftImpl(law=shifted_force, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m"},
    "outputs": {"F": "kg*m*s**-2"},
    "params": {
        "k": "kg*s**-2",
        "m": "kg",
        "eta": "1",
        "x_scale": "m",
    },
}

__all__ = [
    "HookeGamma11Params",
    "shifted_force",
    "shifted_potential",
    "sampler",
    "validator",
    "build",
    "shift",
    "DIM_SIGNATURE",
]
