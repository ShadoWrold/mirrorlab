"""Manipulate tools. Spec §4.1.

Mutating operations on a ``SimInstance``. v1 wraps the Hooke-style 1-D backend
and the multi-D (2-D / 3-D) shift backends — for both, ``sim._params`` is a
frozen dataclass, so we rebind it via ``dataclasses.replace`` and clear the
cached solution so the next ``step(t)`` re-integrates under the new state.

Multi-D support: operations derive the set of mutable fields from the actual
``params`` dataclass instead of a Hooke-only whitelist. ``set_initial`` accepts
any subset of params fields (``{x0, y0, vx0, vy0, ...}``); ``apply_impulse``
accepts a scalar, list/tuple, or ``{"px","py","pz"}`` dict and distributes it
across the corresponding ``v*0`` fields.
"""

from __future__ import annotations

import dataclasses
import sys
from typing import Any, Dict, Iterable, List, Mapping, Sequence


def _params_attr(sim: Any) -> str:
    """Backend-agnostic params attribute name (``_params`` or ``_p``)."""
    if hasattr(sim, "_params"):
        return "_params"
    if hasattr(sim, "_p"):
        return "_p"
    raise AttributeError("sim has neither '_params' nor '_p'")


def _get_params(sim: Any) -> Any:
    return getattr(sim, _params_attr(sim))


def _set_params(sim: Any, params: Any) -> None:
    setattr(sim, _params_attr(sim), params)


def _reset_solution(sim: Any) -> None:
    if hasattr(sim, "_sol"):
        sim._sol = None
    if hasattr(sim, "_t_end"):
        sim._t_end = 0.0


def _settable_fields(sim: Any) -> set[str]:
    params = _get_params(sim)
    if not dataclasses.is_dataclass(params):
        raise TypeError("sim.params is not a dataclass; cannot mutate in v1")
    return {f.name for f in dataclasses.fields(params)}


def _shift_validator(sim: Any):
    """Best-effort lookup of the shift module's ``validator`` callable."""
    params = _get_params(sim)
    mod_name = type(params).__module__
    mod = sys.modules.get(mod_name)
    val = getattr(mod, "validator", None) if mod is not None else None
    return val if callable(val) else None


def _try_replace(sim: Any, changes: Mapping[str, Any]) -> Dict[str, Any]:
    """Replace params, re-validate, rollback on failure."""
    original = _get_params(sim)
    try:
        new = dataclasses.replace(original, **changes)
    except TypeError as exc:
        return {"ok": False, "error": str(exc), "applied": {}}
    validator = _shift_validator(sim)
    if validator is not None:
        try:
            valid = bool(validator(new))
        except Exception as exc:
            return {"ok": False, "error": f"validator raised: {exc!r}", "applied": {}}
        if not valid:
            return {"ok": False, "error": "validator rejected new params",
                    "applied": {}}
    _set_params(sim, new)
    _reset_solution(sim)
    return {"ok": True, "applied": dict(changes)}


def set_initial(sim: Any, *, body_id: int = 0,
                state: Dict[str, float]) -> Dict[str, Any]:
    """Set initial-condition fields on the params dataclass.

    Accepts any subset of fields the params dataclass declares. Legacy aliases
    ``x``→``x0`` / ``v``→``v0`` are kept for 1-D back-compat.
    """
    if body_id != 0:
        raise ValueError("v1 backend only supports body_id=0")
    if not isinstance(state, Mapping) or not state:
        raise ValueError("state must be a non-empty mapping")
    fields = _settable_fields(sim)
    changes: Dict[str, float] = {}
    # Legacy 1-D aliases.
    aliases = {"x": "x0", "v": "v0"}
    for key, value in state.items():
        target = aliases.get(key, key)
        if target not in fields:
            continue
        changes[target] = float(value)
    if not changes:
        raise ValueError(
            f"no field in state {sorted(state)} matches params fields "
            f"{sorted(fields)}"
        )
    res = _try_replace(sim, changes)
    if not res["ok"]:
        raise ValueError(res["error"])
    return res


def _velocity_fields(fields: Iterable[str]) -> List[str]:
    """Return ordered velocity-IC field names: ``v0`` first, then vx0/vy0/vz0."""
    fields = set(fields)
    ordered: List[str] = []
    if "v0" in fields:
        ordered.append("v0")
    for name in ("vx0", "vy0", "vz0"):
        if name in fields:
            ordered.append(name)
    return ordered


def apply_impulse(sim: Any, *, body_id: int = 0,
                  delta_p: Any, t: float = 0.0) -> Dict[str, Any]:
    """Apply impulse Δp at ``t`` to the body (v1: only t=0 supported).

    ``delta_p`` may be:
      * a scalar (legacy 1-D path)
      * a list/tuple of components, matched positionally to ``vx0/vy0/vz0`` (or
        ``v0`` if that's the only velocity field)
      * a dict ``{"px": ..., "py": ..., "pz": ...}`` (any subset)
    """
    if body_id != 0:
        raise ValueError("v1 backend only supports body_id=0")
    if abs(float(t)) > 1e-12:
        raise NotImplementedError("v1: impulse only at t=0")
    fields = _settable_fields(sim)
    v_fields = _velocity_fields(fields)
    if not v_fields:
        raise ValueError("sim params expose no velocity IC field to impulse")
    m = float(getattr(sim.params, "m", 1.0))
    if m <= 0:
        raise ValueError("mass must be positive to apply impulse")

    # Normalize delta_p to a {field_name: dp_component} dict.
    components: Dict[str, float] = {}
    if isinstance(delta_p, Mapping):
        comp_aliases = {"px": "vx0", "py": "vy0", "pz": "vz0", "p": "v0"}
        for key, value in delta_p.items():
            target = comp_aliases.get(key, key)
            if target not in v_fields:
                raise ValueError(
                    f"impulse component {key!r} has no matching v-field in "
                    f"params (available: {v_fields})"
                )
            components[target] = float(value)
    elif isinstance(delta_p, (list, tuple, Sequence)) and not isinstance(delta_p, (str, bytes)):
        seq = list(delta_p)
        if len(seq) > len(v_fields):
            raise ValueError(
                f"impulse vector length {len(seq)} > velocity fields {v_fields}"
            )
        for name, comp in zip(v_fields, seq):
            components[name] = float(comp)
    else:
        # scalar
        components[v_fields[0]] = float(delta_p)

    dv = {name: components[name] / m for name in components}
    changes = {name: float(getattr(sim.params, name)) + dv[name]
               for name in components}

    res = _try_replace(sim, changes)
    if not res["ok"]:
        raise ValueError(res["error"])
    # Scalar back-compat: return single-component dv as a float when 1-D.
    dv_out: Any = dv[v_fields[0]] if len(dv) == 1 and v_fields[0] == "v0" else dv
    return {"ok": True, "dv": dv_out, "applied": res["applied"]}


def set_external_field(sim: Any, *, field_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Domain-allowed external field setter. v1 mechanical: not applicable."""
    domain = type(_get_params(sim)).__module__.rsplit(".", 1)[-1]
    return {"applicable": False, "field_spec": field_spec,
            "reason": f"{domain} does not support set_external_field"}


def set_boundary(sim: Any, *, boundary_spec: Dict[str, Any]) -> Dict[str, Any]:
    """PDE boundary setter. v1 ODE backend: not applicable."""
    domain = type(_get_params(sim)).__module__.rsplit(".", 1)[-1]
    return {"applicable": False, "boundary_spec": boundary_spec,
            "reason": f"{domain} does not support set_boundary"}


def set_parameter(sim: Any, *, param_name: str, value: float) -> Dict[str, Any]:
    """Set any scalar field on the sim's params dataclass.

    The whitelist is now derived from ``dataclasses.fields(sim.params)`` —
    requesting a name that's not a params field raises ``ValueError``.
    """
    fields = _settable_fields(sim)
    if param_name not in fields:
        raise ValueError(
            f"param {param_name!r} is not a field of "
            f"{type(_get_params(sim)).__name__} (available: {sorted(fields)})"
        )
    res = _try_replace(sim, {param_name: float(value)})
    if not res["ok"]:
        raise ValueError(res["error"])
    return {"ok": True, "param": param_name, "value": float(value)}


def reset(sim: Any, *, original_params: Any = None) -> Dict[str, Any]:
    """Reset the integrator. If ``original_params`` is supplied, restore them."""
    if original_params is not None:
        _set_params(sim, original_params)
    _reset_solution(sim)
    return {"ok": True}


def swap_bodies(sim: Any, *, i: int, j: int) -> Dict[str, Any]:
    """Interchange bodies i↔j. v1 single-body backend: only (0,0) is a no-op."""
    if i == j == 0:
        return {"ok": True, "applied": False, "note": "single-body scenario"}
    raise ValueError("v1 backend only supports body_id=0")


def _primary_position_key(obs: Mapping[str, Any]) -> str:
    """Pick the first scalar position-ish observable from obs (excluding ``t``)."""
    preferred = ("x", "r", "theta", "q", "N", "C", "T", "T_mean")
    for key in preferred:
        if key in obs:
            return key
    for key, value in obs.items():
        if key == "t":
            continue
        if isinstance(value, (int, float)):
            return key
    raise KeyError(f"no scalar observable in obs (keys: {list(obs)})")


def time_reverse_probe(sim: Any, *, t_window: List[float]) -> Dict[str, Any]:
    """T-rev probe: sample the primary observable across ``t_window``.

    Picks the first scalar position-ish observable that the sim exposes
    (``x``, ``r``, ``theta``, ...) so the probe works for multi-D backends
    that don't have an ``x`` key. The probe never mutates ``sim``.

    The returned ``reversed_x`` is the forward list reversed — kept for
    back-compat. A true T-reversal probe (integrate forward, flip velocity,
    integrate again) requires impulse + re-integration support that the v1
    sim API doesn't cleanly expose; documenting the limitation rather than
    faking it.
    """
    t0, t1 = float(t_window[0]), float(t_window[1])
    if t1 <= t0:
        raise ValueError("bad t_window")
    times = (t0, 0.5 * (t0 + t1), t1)
    samples = [sim.step(float(t)) for t in times]
    key = _primary_position_key(samples[0])
    fwd = [float(s[key]) for s in samples]
    rev = list(reversed(fwd))
    return {"forward_x": fwd, "reversed_x": rev, "observable": key,
            "note": ("compare reversed_x to a hypothetical T-reversed run; "
                     "v1 probe does not re-integrate from a flipped end state")}


__all__ = ["set_initial", "apply_impulse", "set_external_field", "set_boundary",
           "set_parameter", "reset", "swap_bodies", "time_reverse_probe"]
