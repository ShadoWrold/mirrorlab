"""Measure tools (read-only). Spec §4.1.

Each ``measure.*`` reads the live ``SimInstance`` and never mutates it.
Tools accept ``sim`` (or ``ctx: SandboxContext``) and a small set of
domain-agnostic parameters.  Keys are discovered reflectively from
``sim.step(0)`` so the same tool works across all 12 domains.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set

import numpy as np


_POSITION_KEYS = {"x", "y", "z", "r", "theta", "theta1", "theta2", "phi", "u"}
_VELOCITY_KEYS = {"v", "vx", "vy", "vz", "omega", "i", "rate"}


def _is_velocity_key(k: str) -> bool:
    if k in _VELOCITY_KEYS:
        return True
    return k.endswith("_dot") or k.endswith("_dt")


def _extract(obs: Dict[str, Any], keys: Iterable[str]) -> Dict[str, Any]:
    return {k: obs[k] for k in keys if k in obs}


def position(sim: Any, *, body_id: int = 0, t: float) -> Dict[str, float]:
    """Return ``{"t": t, <pos-keys>: ...}`` from the domain's step output."""
    if body_id != 0:
        raise ValueError("v1 backend only supports body_id=0")
    obs = sim.step(float(t))
    pos = {k: v for k, v in obs.items() if k in _POSITION_KEYS}
    if not pos:
        raise KeyError("no position observable in this domain")
    return {"t": obs["t"], **pos}


def velocity(sim: Any, *, body_id: int = 0, t: float) -> Dict[str, float]:
    """Return ``{"t": t, <vel-keys>: ...}`` from the domain's step output."""
    if body_id != 0:
        raise ValueError("v1 backend only supports body_id=0")
    obs = sim.step(float(t))
    vel = {k: v for k, v in obs.items() if _is_velocity_key(k)}
    if not vel:
        raise KeyError("no velocity observable in this domain")
    return {"t": obs["t"], **vel}


def field(sim: Any, *, probe_point: List[float], field_type: str) -> Dict[str, Any]:
    """Sample a domain-specific field at ``probe_point``.

    Mechanical domains expose the force key ``F`` at t=0; other ``field_type``s
    are not represented in the v1 backend.
    """
    if field_type not in {"force", "electric", "magnetic", "thermal", "fluid"}:
        raise ValueError(f"unknown field_type {field_type!r}")
    if field_type != "force":
        return {"field_type": field_type, "value": None,
                "note": "not available in mechanical domain"}
    obs = sim.step(0.0)
    if "F" not in obs:
        raise KeyError(f"force field is not exposed by this domain "
                       f"(observables: {sorted(obs)})")
    return {"field_type": "force", "probe_point": list(probe_point),
            "value": obs["F"]}


def energy(sim: Any, *, system: str = "total", t: float = 0.0) -> Dict[str, float]:
    """Energy estimator. Passes through ``E`` if exposed; else best-effort KE."""
    obs = sim.step(float(t))
    if "E" in obs:
        return {"t": obs["t"], "E": float(obs["E"]), "system": system}
    params = sim.params
    m = getattr(params, "m", None)
    if "v" in obs and m is not None:
        ke = 0.5 * float(m) * float(obs["v"]) ** 2
        return {"t": obs["t"], "kinetic": ke, "system": system}
    return {"t": obs["t"], "kinetic": None, "system": system,
            "note": "no canonical energy observable for this domain"}


def spectrum(sim: Any, *, signal: str = "x", window: List[float] = (0.0, 10.0),
             n_samples: int = 256) -> Dict[str, Any]:
    """FFT magnitude spectrum of a scalar observable sampled on ``window``."""
    probe = sim.step(0.0)
    if signal not in probe:
        raise ValueError(f"unknown signal {signal!r}; "
                         f"available: {sorted(k for k in probe if k != 't')}")
    t0, t1 = float(window[0]), float(window[1])
    if t1 <= t0:
        raise ValueError("window must be (t0, t1) with t1 > t0")
    n = int(n_samples)
    ts = np.linspace(t0, t1, n)
    vals = np.array([float(sim.step(float(t))[signal]) for t in ts])
    spec = np.abs(np.fft.rfft(vals - vals.mean()))
    freqs = np.fft.rfftfreq(n, d=(t1 - t0) / (n - 1))
    return {"freqs": freqs.tolist(), "magnitude": spec.tolist()}


def trajectory(sim: Any, *, body_id: int = 0,
               t_window: List[float], sample_rate: float) -> Dict[str, List[float]]:
    """Bulk pull of every step-observable over ``t_window`` at ``sample_rate``."""
    if body_id != 0:
        raise ValueError("v1 backend only supports body_id=0")
    t0, t1 = float(t_window[0]), float(t_window[1])
    if t1 <= t0 or sample_rate <= 0:
        raise ValueError("bad t_window / sample_rate")
    n = max(2, int((t1 - t0) * float(sample_rate)) + 1)
    ts = np.linspace(t0, t1, n)
    probe = sim.step(float(ts[0]))
    keys = [k for k in probe.keys() if k != "t"]
    series: Dict[str, List[float]] = {k: [] for k in keys}
    series_t: List[float] = []
    for t in ts:
        obs = sim.step(float(t))
        series_t.append(float(obs["t"]))
        for k in keys:
            series[k].append(obs[k] if k in obs else None)
    return {"t": series_t, **series}


def scattering(sim: Any, *, beam: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
    """Domain-specific scattering probe. Stub for 1-D mechanical: not applicable."""
    return {"applicable": False, "beam": beam, "target": target,
            "note": "scattering is not defined for this domain"}


def observable(sim: Any, *, name: str, t: float = 0.0) -> Dict[str, Any]:
    """Return a named extra observable from the domain's observable list."""
    obs = sim.step(float(t))
    if name not in obs:
        raise KeyError(f"observable {name!r} not exposed by this scenario")
    return {"name": name, "t": obs["t"], "value": obs[name]}


__all__ = ["position", "velocity", "field", "energy", "spectrum",
           "trajectory", "scattering", "observable"]
