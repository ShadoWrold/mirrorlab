"""Measure tools (read-only). Spec §4.1.

Each ``measure.*`` reads the live ``SimInstance`` and never mutates it.
Tools accept ``sim`` (or ``ctx: SandboxContext``) and a small set of
domain-agnostic parameters; the v1 backend exposes a single 1-D body, so
``body_id`` is currently accepted-but-ignored beyond schema validation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np


def position(sim: Any, *, body_id: int = 0, t: float) -> Dict[str, float]:
    """Return ``{"t": t, "x": x}`` at time ``t``."""
    if body_id != 0:
        raise ValueError("v1 backend only supports body_id=0")
    obs = sim.step(float(t))
    return {"t": obs["t"], "x": obs["x"]}


def velocity(sim: Any, *, body_id: int = 0, t: float) -> Dict[str, float]:
    """Return ``{"t": t, "v": v}`` at time ``t``."""
    if body_id != 0:
        raise ValueError("v1 backend only supports body_id=0")
    obs = sim.step(float(t))
    return {"t": obs["t"], "v": obs["v"]}


def field(sim: Any, *, probe_point: List[float], field_type: str) -> Dict[str, Any]:
    """Sample a domain-specific field at ``probe_point``.

    1-D mechanical domains expose the force as the only field at t=0.
    """
    if field_type not in {"force", "electric", "magnetic", "thermal", "fluid"}:
        raise ValueError(f"unknown field_type {field_type!r}")
    if field_type != "force":
        return {"field_type": field_type, "value": None,
                "note": "not available in mechanical domain"}
    obs = sim.step(0.0)
    return {"field_type": "force", "probe_point": list(probe_point),
            "value": obs.get("F")}


def energy(sim: Any, *, system: str = "total", t: float = 0.0) -> Dict[str, float]:
    """Total mechanical energy estimator at time ``t`` (single-body 1-D)."""
    obs = sim.step(float(t))
    params = sim.params
    m = float(getattr(params, "m", 1.0))
    ke = 0.5 * m * obs["v"] ** 2
    return {"t": obs["t"], "kinetic": ke, "system": system}


def spectrum(sim: Any, *, signal: str = "x", window: List[float] = (0.0, 10.0),
             n_samples: int = 256) -> Dict[str, Any]:
    """FFT magnitude spectrum of a sampled signal on the window."""
    if signal not in {"x", "v", "F"}:
        raise ValueError(f"unknown signal {signal!r}")
    t0, t1 = float(window[0]), float(window[1])
    if t1 <= t0:
        raise ValueError("window must be (t0, t1) with t1 > t0")
    n = int(n_samples)
    ts = np.linspace(t0, t1, n)
    vals = np.array([sim.step(float(t))[signal] for t in ts])
    spec = np.abs(np.fft.rfft(vals - vals.mean()))
    freqs = np.fft.rfftfreq(n, d=(t1 - t0) / (n - 1))
    return {"freqs": freqs.tolist(), "magnitude": spec.tolist()}


def trajectory(sim: Any, *, body_id: int = 0,
               t_window: List[float], sample_rate: float) -> Dict[str, List[float]]:
    """Bulk pull of (t, x, v) over ``t_window`` at ``sample_rate`` (Hz)."""
    if body_id != 0:
        raise ValueError("v1 backend only supports body_id=0")
    t0, t1 = float(t_window[0]), float(t_window[1])
    if t1 <= t0 or sample_rate <= 0:
        raise ValueError("bad t_window / sample_rate")
    n = max(2, int((t1 - t0) * float(sample_rate)) + 1)
    ts = np.linspace(t0, t1, n)
    xs, vs = [], []
    for t in ts:
        obs = sim.step(float(t))
        xs.append(obs["x"])
        vs.append(obs["v"])
    return {"t": ts.tolist(), "x": xs, "v": vs}


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
