"""γ-3-1 — Damped HO amplitude-memory stiffness (LIN break).

Catalog: ẍ + 2γẋ + ω₀²·[1 + κ ⟨x²⟩_τ / x_ref²]·x = 0,
         ⟨x²⟩_τ = (1/τ)∫_{t−τ}^t x²(s) ds.
Broken: LIN. Retained: T-trans (sliding window), PAR (x² even).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Tuple

import numpy as np

from mirrorlab.shifts import ShiftImpl
from mirrorlab.shifts._util import loguniform

OMEGA_MIN, OMEGA_MAX = 0.5, 10.0
KAPPA_MIN, KAPPA_MAX = 0.05, 0.5
XREF_MIN, XREF_MAX = 0.1, 2.0


@dataclass(frozen=True)
class DampedHOGamma31Params:
    omega0: float
    gamma: float
    kappa: float
    tau: float
    x_ref: float
    m: float
    x0: float
    v0: float


def shifted_law(x: float, v: float, x2_mean: float,
                p: DampedHOGamma31Params) -> float:
    """Returns ẍ for current state and running ⟨x²⟩_τ."""
    omega2_eff = p.omega0 * p.omega0 * (1.0 + p.kappa * x2_mean / (p.x_ref * p.x_ref))
    return -2.0 * p.gamma * v - omega2_eff * x


def sampler(seed: int) -> DampedHOGamma31Params:
    rng = np.random.default_rng(seed)
    omega0 = loguniform(rng, OMEGA_MIN, OMEGA_MAX)
    gamma = omega0 * loguniform(rng, 0.01, 0.3)
    kappa = float(rng.uniform(KAPPA_MIN, KAPPA_MAX))
    tau = float(rng.uniform(0.5, 5.0) / omega0)
    x_ref = loguniform(rng, XREF_MIN, XREF_MAX)
    return DampedHOGamma31Params(omega0=omega0, gamma=gamma, kappa=kappa,
                                 tau=tau, x_ref=x_ref, m=1.0,
                                 x0=0.1, v0=0.0)


def validator(p) -> bool:
    if not isinstance(p, DampedHOGamma31Params):
        return False
    if not (OMEGA_MIN <= p.omega0 <= OMEGA_MAX):
        return False
    if not (KAPPA_MIN <= p.kappa <= KAPPA_MAX):
        return False
    if not (XREF_MIN <= p.x_ref <= XREF_MAX):
        return False
    if p.kappa > 0.6:
        return False
    if p.gamma <= 0 or p.tau <= 0 or p.m <= 0:
        return False
    if p.gamma / p.omega0 < 0.01 or p.gamma / p.omega0 > 0.3:
        return False
    return True


class _Sim:
    """Manual RK4 integrator with sliding history buffer for ⟨x²⟩_τ."""

    def __init__(self, p: DampedHOGamma31Params, dt: float = 1e-3) -> None:
        self._p = p
        self._dt = dt
        self._t = 0.0
        self._x = p.x0
        self._v = p.v0
        # initialize history with x0²
        n_hist = max(2, int(math.ceil(p.tau / dt)))
        self._hist: Deque[float] = deque([p.x0 * p.x0] * n_hist, maxlen=n_hist)
        self._cache: Dict[float, Tuple[float, float]] = {0.0: (p.x0, p.v0)}

    @property
    def params(self):
        return self._p

    def _x2_mean(self) -> float:
        return sum(self._hist) / len(self._hist)

    def _step_one(self) -> None:
        p = self._p
        dt = self._dt
        x2m = self._x2_mean()
        x, v = self._x, self._v
        a1 = shifted_law(x, v, x2m, p)
        a2 = shifted_law(x + 0.5 * dt * v, v + 0.5 * dt * a1, x2m, p)
        a3 = shifted_law(x + 0.5 * dt * (v + 0.5 * dt * a1),
                         v + 0.5 * dt * a2, x2m, p)
        a4 = shifted_law(x + dt * (v + 0.5 * dt * a2),
                         v + dt * a3, x2m, p)
        self._x = x + dt * (v + dt * (a1 + a2 + a3) / 6.0)
        self._v = v + dt * (a1 + 2 * a2 + 2 * a3 + a4) / 6.0
        self._t += dt
        self._hist.append(self._x * self._x)

    def _advance_to(self, t: float) -> None:
        while self._t < t - 1e-15:
            self._step_one()

    def step(self, t: float) -> Dict[str, float]:
        if t < 0:
            raise ValueError("t must be non-negative")
        if t in self._cache:
            x, v = self._cache[t]
            return {"t": float(t), "x": x, "v": v}
        if t < self._t:
            raise ValueError("γ-3-1 sim is forward-only; t < t_current")
        self._advance_to(t)
        self._cache[t] = (self._x, self._v)
        return {"t": float(t), "x": float(self._x), "v": float(self._v)}


def build(*, params: DampedHOGamma31Params | None = None, seed: int = 0) -> _Sim:
    if params is None:
        params = sampler(seed)
    if not validator(params):
        raise ValueError(f"γ-3-1 params failed validator: {params!r}")
    return _Sim(params)


shift = ShiftImpl(law=shifted_law, sampler=sampler, validator=validator)

DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m", "v": "m*s**-1", "x2_mean": "m**2"},
    "outputs": {"a": "m*s**-2"},
    "params": {"omega0": "s**-1", "gamma": "s**-1", "kappa": "1",
               "tau": "s", "x_ref": "m", "m": "kg"},
}

__all__ = ["DampedHOGamma31Params", "shifted_law", "sampler", "validator",
           "build", "shift", "DIM_SIGNATURE"]
