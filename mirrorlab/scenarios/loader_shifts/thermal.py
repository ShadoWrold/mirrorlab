"""Per-shift truth-form grid builders for the Thermal domain.

Blueprint-xy §3.2, §4 rows 22-24 + baseline.

- baseline   inputs {T_hot, T_cold, L}, GT k·(T_hot−T_cold)/L (Fourier)
- γ-7-1 ROT  inputs {T_hot, T_cold, L, dx, dy, dz}, GT |K·∇T| with
             K = k₀(I + β·n̂n̂ᵀ). Sample grad direction d̂ on S² so
             ⟨(n̂·d̂)²⟩ ≠ 1/3 — without bias, the anisotropic correction
             averages out.
- γ-7-2 mem  inputs {T_hot, T_cold, L, t}, GT from shifted_flux(t, p)
             (power-law memory kernel; grid samples t away from
             tau_min).
- δ-7-1 PDE  inputs {t}, GT step()-based (per blueprint §3.2.1):
             instantiate a ThermalDelta71Instance with the sim's params
             and read T_a at the grid's t. Predictor on (c) must do
             the same with cf_params — see ceiling_agent.py.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

import numpy as np

from mirrorlab.scenarios import loader_shifts as _shifts
from mirrorlab.scenarios.loader_shifts._common import (
    _GRID_SIZE,
    _OOD_FACTOR,
    _attr,
    _linspace_signed,
    _ood_signed,
    _pack,
)
from mirrorlab.shifts import (
    thermal_d_7_1 as _d71,
    thermal_g_7_1 as _g71,
    thermal_g_7_2 as _g72,
)


# Direction-biased schedule for γ-7-1 grad direction projection onto n̂.
# Same shape as gravity ROT schedule: pole-heavy to maximize ξ-correction
# visibility. <(n̂·d̂)²> ≈ 0.67 (vs uniform 1/3).
_MU_SCHEDULE = np.concatenate([
    np.linspace(-1.0, -0.7, 5),
    np.array([0.0]),
    np.linspace(0.7, 1.0, 5),
])


def _xyz_direction_at(mu: float, nhat: Tuple[float, float, float],
                       rng: np.random.Generator) -> Tuple[float, float, float]:
    """Return a unit vector d̂ with d̂·n̂ = μ."""
    sin_theta = math.sqrt(max(0.0, 1.0 - mu * mu))
    nx, ny, nz = nhat
    helper = (0.0, 0.0, 1.0) if abs(nz) < 0.9 else (1.0, 0.0, 0.0)
    e1x = ny * helper[2] - nz * helper[1]
    e1y = nz * helper[0] - nx * helper[2]
    e1z = nx * helper[1] - ny * helper[0]
    e1n = math.sqrt(e1x * e1x + e1y * e1y + e1z * e1z) or 1.0
    e1 = (e1x / e1n, e1y / e1n, e1z / e1n)
    e2 = (
        ny * e1[2] - nz * e1[1],
        nz * e1[0] - nx * e1[2],
        nx * e1[1] - ny * e1[0],
    )
    phi = float(rng.uniform(0.0, 2.0 * math.pi))
    return (
        mu * nx + sin_theta * (math.cos(phi) * e1[0] + math.sin(phi) * e2[0]),
        mu * ny + sin_theta * (math.cos(phi) * e1[1] + math.sin(phi) * e2[1]),
        mu * nz + sin_theta * (math.cos(phi) * e1[2] + math.sin(phi) * e2[2]),
    )


# ---- baseline ---------------------------------------------------------------

def baseline_grids(sim: Any, seed: int, magnitude: float):
    p0 = sim.params
    T_hot0 = float(_attr(p0, ("T_hot",), 373.0))
    T_cold0 = float(_attr(p0, ("T_cold",), 293.0))
    L0 = abs(_attr(p0, ("L",), 0.1)) or 0.1

    def gt(inputs: Dict[str, float]):
        T_h = inputs["T_hot"]
        T_c = inputs["T_cold"]
        L = inputs["L"]

        def fn(p):
            k = _attr(p, ("k",), 1.0)
            return k * (T_h - T_c) / L

        return fn

    def build(rng: np.random.Generator, mode: str):
        # Vary ΔT in a band around the nominal; L slightly varied; T_cold fixed.
        if mode == "b":
            dT_factors = np.linspace(1.5, _OOD_FACTOR, _GRID_SIZE)
        else:
            dT_factors = np.linspace(0.3, 1.5, _GRID_SIZE)
        dT0 = T_hot0 - T_cold0
        L_factors = rng.uniform(0.5, 1.5, size=_GRID_SIZE)
        pts = []
        for f, Lf in zip(dT_factors, L_factors):
            T_h = T_cold0 + float(f) * dT0
            L = L0 * float(Lf)
            ins = {"T_hot": T_h, "T_cold": T_cold0, "L": L}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# ---- γ-7-1 (ROT anisotropic conductivity) ----------------------------------

def gamma_7_1_grids(sim: Any, seed: int, magnitude: float):
    p0 = sim.params
    nhat = tuple(float(x) for x in _attr_tuple(p0, "n", (0.0, 0.0, 1.0)))
    T_hot0 = float(_attr(p0, ("T_hot",), 373.0))
    T_cold0 = float(_attr(p0, ("T_cold",), 293.0))
    L0 = abs(_attr(p0, ("L",), 0.1)) or 0.1

    def gt(inputs: Dict[str, float]):
        # Inputs carry T_hot, T_cold, L and the grad direction d̂ as
        # (dx, dy, dz). The GT is the magnitude of the anisotropic flux
        # |K·∇T| with K = k₀(I + β·n̂n̂ᵀ).
        T_h = inputs["T_hot"]
        T_c = inputs["T_cold"]
        L = inputs["L"]
        d = (inputs["dx"], inputs["dy"], inputs["dz"])

        def fn(p):
            k0 = float(_attr(p, ("k0",), 1.0))
            beta = float(_attr(p, ("beta",), 0.0))
            # n̂ is a tuple attribute; perturb_params leaves it alone
            # (only scalar law coefficients move). Fall back to the sim's
            # n̂ if the cf params object exposes the same attribute.
            n_vec = _attr_tuple(p, "n", nhat)
            p_eff = _g71.ThermalGamma71Params(
                k0=k0, beta=beta, n=n_vec,
                L=L, T_hot=T_h, T_cold=T_c, grad_dir=d,
            )
            return _g71.shifted_flux_magnitude(p_eff)

        return fn

    def build(rng: np.random.Generator, mode: str):
        if mode == "b":
            dT_factors = np.linspace(1.5, _OOD_FACTOR, _GRID_SIZE)
        else:
            dT_factors = np.linspace(0.3, 1.5, _GRID_SIZE)
        dT0 = T_hot0 - T_cold0
        L_factors = rng.uniform(0.5, 1.5, size=_GRID_SIZE)
        pts = []
        for f, Lf, mu in zip(dT_factors, L_factors, _MU_SCHEDULE):
            T_h = T_cold0 + float(f) * dT0
            L = L0 * float(Lf)
            d = _xyz_direction_at(float(mu), nhat, rng)
            ins = {
                "T_hot": T_h, "T_cold": T_cold0, "L": L,
                "dx": d[0], "dy": d[1], "dz": d[2],
            }
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


def _attr_tuple(p: Any, name: str, default: Tuple[float, ...]) -> Tuple[float, ...]:
    """Read a tuple/array attribute, falling back to ``default``."""
    val = getattr(p, name, None)
    if val is None:
        return default
    try:
        return tuple(float(x) for x in val)
    except (TypeError, ValueError):
        return default


# ---- γ-7-2 (power-law memory kernel) ---------------------------------------

def gamma_7_2_grids(sim: Any, seed: int, magnitude: float):
    p0 = sim.params
    T_hot0 = float(_attr(p0, ("T_hot",), 373.0))
    T_cold0 = float(_attr(p0, ("T_cold",), 293.0))
    L0 = abs(_attr(p0, ("L",), 0.1)) or 0.1
    tau_min0 = float(_attr(p0, ("tau_min",), 1e-3))

    def gt(inputs: Dict[str, float]):
        T_h = inputs["T_hot"]
        T_c = inputs["T_cold"]
        L = inputs["L"]
        t = inputs["t"]

        def fn(p):
            k0 = float(_attr(p, ("k0",), 1.0))
            p_exp = float(_attr(p, ("p",), 0.5))
            tau_m = float(_attr(p, ("tau_min",), tau_min0))
            p_eff = _g72.ThermalGamma72Params(
                k0=k0, p=p_exp, L=L, T_hot=T_h, T_cold=T_c, tau_min=tau_m,
            )
            return _g72.shifted_flux(t, p_eff)

        return fn

    def build(rng: np.random.Generator, mode: str):
        # Sample t on a log schedule away from tau_min; vary T and L too.
        if mode == "b":
            ts = np.geomspace(tau_min0 * 100.0, tau_min0 * 10000.0, _GRID_SIZE)
            dT_factors = np.linspace(1.5, _OOD_FACTOR, _GRID_SIZE)
        else:
            ts = np.geomspace(tau_min0 * 5.0, tau_min0 * 500.0, _GRID_SIZE)
            dT_factors = np.linspace(0.3, 1.5, _GRID_SIZE)
        dT0 = T_hot0 - T_cold0
        L_factors = rng.uniform(0.5, 1.5, size=_GRID_SIZE)
        pts = []
        for t, f, Lf in zip(ts, dT_factors, L_factors):
            T_h = T_cold0 + float(f) * dT0
            L = L0 * float(Lf)
            ins = {"T_hot": T_h, "T_cold": T_cold0, "L": L, "t": float(t)}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


# ---- δ-7-1 (PDE sink, step()-based truth per blueprint §3.2.1) -------------

def delta_7_1_grids(sim: Any, seed: int, magnitude: float):
    """GT = ``step(t)["T_a"]``.

    The δ-7-1 truth law is the ODE-integrated probe-node temperature
    T_a(t). For each grid point we instantiate a ThermalDelta71Instance
    with the sim's params and read T_a at the grid's t. Cf overrides on
    (c) work the same way: the gt_fn closure receives the perturbed
    params and instantiates a fresh Instance with them.

    Performance: each call solves the small 2-node ODE; ~ms per call.
    """
    p0 = sim.params
    # Sample t on a log schedule. Cap at a horizon where the ODE
    # response is still well-resolved (~1/lam).
    t_horizon = min(1.0 / float(_attr(p0, ("lam",), 1e-3)), 1.0e4)

    def gt(inputs: Dict[str, float]):
        t = inputs["t"]

        def fn(p):
            inst = _d71.ThermalDelta71Instance(p)
            return inst.step(t)["T_a"]

        return fn

    def build(rng: np.random.Generator, mode: str):
        if mode == "b":
            ts = np.geomspace(0.5 * t_horizon, 5.0 * t_horizon, _GRID_SIZE)
        else:
            ts = np.geomspace(0.01 * t_horizon, 0.5 * t_horizon, _GRID_SIZE)
        return [({"t": float(t)}, gt({"t": float(t)})) for t in ts]

    return _pack(seed, magnitude, sim, build)


# Register all four.
_shifts.register("thermal", "baseline", baseline_grids)
_shifts.register("thermal", "gamma_7_1", gamma_7_1_grids)
_shifts.register("thermal", "gamma_7_2", gamma_7_2_grids)
_shifts.register("thermal", "delta_7_1", delta_7_1_grids)


__all__ = [
    "baseline_grids",
    "gamma_7_1_grids",
    "gamma_7_2_grids",
    "delta_7_1_grids",
]
