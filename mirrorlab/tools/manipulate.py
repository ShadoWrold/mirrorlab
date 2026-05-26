"""Manipulate tools. Spec §4.1.

Mutating operations on a ``SimInstance``. v1 wraps the Hooke-style 1-D
backend, where ``params`` is a frozen dataclass — we rebind the underlying
sim's params via ``dataclasses.replace`` and clear its cached solution so the
next ``step(t)`` re-integrates under the new state.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Dict, List


def _reset_solution(sim: Any) -> None:
    sim._sol = None
    sim._t_end = 0.0


def _replace_params(sim: Any, **changes: Any) -> None:
    params = sim._params
    if not dataclasses.is_dataclass(params):
        raise TypeError("sim.params is not a dataclass; cannot mutate in v1")
    sim._params = dataclasses.replace(params, **changes)
    _reset_solution(sim)


def set_initial(sim: Any, *, body_id: int = 0, state: Dict[str, float]) -> Dict[str, Any]:
    """Set initial state (``x0`` / ``v0``) for the body, then reset integrator."""
    if body_id != 0:
        raise ValueError("v1 backend only supports body_id=0")
    changes: Dict[str, float] = {}
    if "x0" in state or "x" in state:
        changes["x0"] = float(state.get("x0", state.get("x")))
    if "v0" in state or "v" in state:
        changes["v0"] = float(state.get("v0", state.get("v")))
    if not changes:
        raise ValueError("state must contain x0/x and/or v0/v")
    _replace_params(sim, **changes)
    return {"ok": True, "applied": changes}


def apply_impulse(sim: Any, *, body_id: int = 0,
                  delta_p: float, t: float = 0.0) -> Dict[str, Any]:
    """Apply impulse Δp at time ``t`` to the body (v1: only t=0 supported)."""
    if body_id != 0:
        raise ValueError("v1 backend only supports body_id=0")
    if abs(float(t)) > 1e-12:
        raise NotImplementedError("v1: impulse only at t=0")
    m = float(getattr(sim.params, "m", 1.0))
    dv = float(delta_p) / m
    _replace_params(sim, v0=float(sim.params.v0) + dv)
    return {"ok": True, "dv": dv}


def set_external_field(sim: Any, *, field_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Domain-allowed external field setter. v1 1-D mechanical: not applicable."""
    return {"applicable": False, "field_spec": field_spec,
            "note": "no external-field envelope in this scenario"}


def set_boundary(sim: Any, *, boundary_spec: Dict[str, Any]) -> Dict[str, Any]:
    """PDE boundary setter. v1 ODE backend: not applicable."""
    return {"applicable": False, "boundary_spec": boundary_spec,
            "note": "no spatial boundary in this scenario"}


_WHITELIST_PARAMS = {"k", "m", "x0", "v0"}


def set_parameter(sim: Any, *, param_name: str, value: float) -> Dict[str, Any]:
    """Set a whitelisted scalar parameter on the sim's params dataclass."""
    if param_name not in _WHITELIST_PARAMS:
        raise ValueError(f"param {param_name!r} not whitelisted for manipulation")
    params = sim._params
    if not hasattr(params, param_name):
        raise ValueError(f"params has no field {param_name!r}")
    _replace_params(sim, **{param_name: float(value)})
    return {"ok": True, "param": param_name, "value": float(value)}


def reset(sim: Any, *, original_params: Any = None) -> Dict[str, Any]:
    """Reset the integrator. If ``original_params`` is supplied, restore them."""
    if original_params is not None:
        sim._params = original_params
    _reset_solution(sim)
    return {"ok": True}


def swap_bodies(sim: Any, *, i: int, j: int) -> Dict[str, Any]:
    """Interchange bodies i↔j. v1 single-body backend: only (0,0) is a no-op."""
    if i == j == 0:
        return {"ok": True, "applied": False, "note": "single-body scenario"}
    raise ValueError("v1 backend only supports body_id=0")


def time_reverse_probe(sim: Any, *, t_window: List[float]) -> Dict[str, Any]:
    """T-rev probe: compare x(t) vs x(-t) (here: forward + reflected pair).

    Returns the pair of trajectories the agent can compare. Does not mutate.
    """
    t0, t1 = float(t_window[0]), float(t_window[1])
    if t1 <= t0:
        raise ValueError("bad t_window")
    fwd = [sim.step(float(t))["x"] for t in (t0, 0.5 * (t0 + t1), t1)]
    rev = list(reversed(fwd))
    return {"forward_x": fwd, "reversed_x": rev,
            "note": "compare reversed_x to a hypothetical T-reversed run"}


__all__ = ["set_initial", "apply_impulse", "set_external_field", "set_boundary",
           "set_parameter", "reset", "swap_bodies", "time_reverse_probe"]
