"""Hooke spring baseline domain.

Baseline law: F(x) = -k x  (SI: [k]=N/m=kg·s⁻², [x]=m, [F]=N).
Invariants: T-trans (E), PAR (x→-x), T-rev, LIN, scale-free.

Sprint-1 sim backend is self-contained (1-D ODE under scipy). The NewtonBench
fork wiring (vendor/newtonbench) is left for Sprint 2 — the API contract
exposed here (`HookeBaseline(params) → SimInstance`, `SimInstance.step(t)`,
`SimInstance.params`) is the surface that downstream task #3 (scenarios) and
#4 (eval) consume, and is identical either way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import numpy as np
from scipy.integrate import quad, solve_ivp

ForceLaw = Callable[[float, Any], float]
PotentialLaw = Callable[[float], float]


@dataclass(frozen=True)
class HookeParams:
    """Baseline Hooke parameters + initial conditions."""

    k: float        # spring constant [N/m]
    m: float        # mass [kg]
    x0: float       # initial displacement [m]
    v0: float       # initial velocity [m/s]


def baseline_force(x: float, params: HookeParams) -> float:
    """Baseline Hooke force: F = -k x."""
    return -params.k * x


class SimInstance:
    """Integrable 1-D mechanical sim under an arbitrary force law F(x; params).

    The integrator is lazily invoked and re-extended as `step(t)` requests
    larger horizons. State is dense-interpolated, so repeated `step(t)` calls
    at intermediate times are cheap.
    """

    def __init__(
        self,
        params: Any,
        force_law: ForceLaw,
        *,
        rtol: float = 1e-9,
        atol: float = 1e-12,
    ) -> None:
        if getattr(params, "m", 0.0) <= 0:
            raise ValueError("mass must be positive")
        self._params = params
        self._force = force_law
        self._rtol = rtol
        self._atol = atol
        self._sol = None
        self._t_end = 0.0

    @property
    def params(self) -> Any:
        return self._params

    def _integrate(self, t_max: float) -> None:
        m = self._params.m
        force = self._force
        params = self._params

        def rhs(t, y):
            x, v = y
            return (v, force(x, params) / m)

        sol = solve_ivp(
            rhs,
            (0.0, t_max),
            [self._params.x0, self._params.v0],
            method="DOP853",
            rtol=self._rtol,
            atol=self._atol,
            dense_output=True,
        )
        if not sol.success:
            raise RuntimeError(f"ODE integration failed: {sol.message}")
        self._sol = sol
        self._t_end = t_max

    def step(self, t: float) -> Dict[str, float]:
        """Return state observation at time `t ≥ 0`.

        Keys: `t`, `x` [m], `v` [m/s], `F` [N].
        """
        if t < 0:
            raise ValueError("t must be non-negative")
        if self._sol is None or t > self._t_end:
            self._integrate(max(t * 2.0, 1.0))
        y = self._sol.sol(t)
        x, v = float(y[0]), float(y[1])
        return {
            "t": float(t),
            "x": x,
            "v": v,
            "F": float(self._force(x, self._params)),
        }


class HookeBaseline(SimInstance):
    """Hooke baseline: convenience subclass binding `baseline_force`."""

    def __init__(self, params: HookeParams) -> None:
        if not isinstance(params, HookeParams):
            raise TypeError(f"expected HookeParams, got {type(params).__name__}")
        super().__init__(params, baseline_force)


def make_potential(
    force_law: ForceLaw,
    params: Any,
    *,
    lower: float = 0.0,
    quad_epsabs: float = 1e-12,
    quad_epsrel: float = 1e-10,
) -> PotentialLaw:
    """F → U bridge: ``U(x) = -∫_lower^x F(s; params) ds``.

    NewtonBench's Hooke domain consumes the energy form ``U(x)`` rather than
    the force, so the catalog's force-form shifts route through this adapter
    when wired into a NewtonBench-style scoring path. The returned callable
    is per-instance memoized; evaluation grids hit the same ``x`` repeatedly
    so the cache pays for itself after the first sweep. A single fresh
    ``scipy.integrate.quad`` call is well under ~50 µs.
    """

    cache: Dict[float, float] = {0.0: 0.0} if lower == 0.0 else {}

    def potential(x: float) -> float:
        cached = cache.get(x)
        if cached is not None:
            return cached
        val, _ = quad(
            lambda s: -force_law(s, params),
            lower,
            x,
            epsabs=quad_epsabs,
            epsrel=quad_epsrel,
        )
        cache[x] = float(val)
        return float(val)

    return potential


DIM_SIGNATURE: Dict[str, Dict[str, str]] = {
    "inputs": {"x": "m"},
    "outputs": {"F": "kg*m*s**-2"},
    "params": {"k": "kg*s**-2", "m": "kg"},
}
