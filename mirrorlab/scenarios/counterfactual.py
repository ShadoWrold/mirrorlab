"""Counterfactual parameter perturbation (CAL-3).

Per spec §6.2 sub-grid (c) and ``docs/sprint1-report.md`` §3.3 'Known gaps':
the counterfactual sub-grid must defeat frozen-coefficient curve-fits by
re-instantiating the *physical law* with shifted free parameters at every
test point. Curve-fits whose coefficients are locked to the probe sim cannot
follow a re-instantiated law; a real physical theory re-evaluates and tracks.

Perturbation policy (CAL-3 default, ±30%): each numeric law parameter is
scaled by an independent factor ``1 + U(-magnitude, +magnitude)``. Initial
conditions, masses, source/probe positions, direction unit vectors, and
numerical sentinels (``T_sim``, ``dt``, ``tau_min``) are *not* law
parameters and are left untouched — only the free coefficients of the
shift / baseline force law move.

Sprint 3 readiness memo: the ``TypeError`` guard is intentional. Silent
fall-through on an unregistered params type would let a new domain's
counterfactual sub-grid be built from un-perturbed parameters (effectively
collapsing (c) into (a)), so each domain's law-vs-BC split must be made
explicit here.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

import numpy as np

from mirrorlab.spec import (
    law_fields as _law_fields,
    predictor_name_map as _predictor_name_map,
)

from mirrorlab.domains.coulomb import CoulombParams
from mirrorlab.domains.damped_ho import DampedHOParams
from mirrorlab.domains.decay import DecayParams
from mirrorlab.domains.fluid import FluidParams
from mirrorlab.domains.gravity import GravityParams
from mirrorlab.domains.hooke import HookeParams
from mirrorlab.domains.kinetics import KineticsParams
from mirrorlab.domains.optics import OpticsParams
from mirrorlab.domains.pendulum import PendulumParams
from mirrorlab.domains.rlc import RLCParams
from mirrorlab.domains.thermal import ThermalParams
from mirrorlab.domains.wave import WaveParams
from mirrorlab.shifts.coulomb_d_5_1 import CoulombDelta51Params
from mirrorlab.shifts.coulomb_g_5_1 import CoulombGamma51Params
from mirrorlab.shifts.coulomb_g_5_2 import CoulombGamma52Params
from mirrorlab.shifts.damped_ho_d_3_1 import DampedHODelta31Params
from mirrorlab.shifts.damped_ho_g_3_1 import DampedHOGamma31Params
from mirrorlab.shifts.damped_ho_g_3_2 import DampedHOGamma32Params
from mirrorlab.shifts.decay_d_12_1 import DecayDelta121Params
from mirrorlab.shifts.decay_g_12_1 import DecayGamma121Params
from mirrorlab.shifts.decay_g_12_2 import DecayGamma122Params
from mirrorlab.shifts.fluid_d_10_1 import FluidDelta101Params
from mirrorlab.shifts.fluid_g_10_1 import FluidGamma101Params
from mirrorlab.shifts.fluid_g_10_2 import FluidGamma102Params
from mirrorlab.shifts.gravity_d_2_1 import GravityDelta21Params
from mirrorlab.shifts.gravity_g_2_1 import GravityGamma21Params
from mirrorlab.shifts.gravity_g_2_2 import GravityGamma22Params
from mirrorlab.shifts.hooke_d_1_1 import HookeDelta11Params
from mirrorlab.shifts.hooke_g_1_1 import HookeGamma11Params
from mirrorlab.shifts.hooke_g_1_2 import HookeGamma12Params
from mirrorlab.shifts.kinetics_d_11_1 import KineticsDelta111Params
from mirrorlab.shifts.kinetics_g_11_1 import KineticsGamma111Params
from mirrorlab.shifts.kinetics_g_11_2 import KineticsGamma112Params
from mirrorlab.shifts.optics_d_9_1 import OpticsDelta91Params
from mirrorlab.shifts.optics_g_9_1 import OpticsGamma91Params
from mirrorlab.shifts.optics_g_9_2 import OpticsGamma92Params
from mirrorlab.shifts.pendulum_d_4_1 import PendulumDelta41Params
from mirrorlab.shifts.pendulum_g_4_1 import PendulumGamma41Params
from mirrorlab.shifts.pendulum_g_4_2 import PendulumGamma42Params
from mirrorlab.shifts.rlc_d_6_1 import RLCDelta61Params
from mirrorlab.shifts.rlc_g_6_1 import RLCGamma61Params
from mirrorlab.shifts.rlc_g_6_2 import RLCGamma62Params
from mirrorlab.shifts.thermal_d_7_1 import ThermalDelta71Params
from mirrorlab.shifts.thermal_g_7_1 import ThermalGamma71Params
from mirrorlab.shifts.thermal_g_7_2 import ThermalGamma72Params
from mirrorlab.shifts.wave_d_8_1 import WaveDelta81Params
from mirrorlab.shifts.wave_g_8_1 import WaveGamma81Params
from mirrorlab.shifts.wave_g_8_2 import WaveGamma82Params

DEFAULT_MAGNITUDE = 0.30  # CAL-3

# ---------------------------------------------------------------------------
# Counterfactual policy tables — DERIVED from per-field role metadata.
#
# `_LAW_PARAM_FIELDS` (which fields the cf perturbs) and `_PREDICTOR_NAME_MAP`
# (the predictor-facing canonical name per law field) used to be two hand-
# written tables kept in sync with the Params dataclasses by hand. They are
# now PROJECTIONS of the field-role metadata declared at each Params field
# (see mirrorlab/spec.py): role=="law" fields are perturbed and carry an
# explicit canonical name; mass/ic/axis fields are excluded.
#
# Canonical names remain explicit (stored in metadata, not computed by a rule)
# because real naming is irregular: k0->k but L1->L_1, q_src->q_1. Round-trip
# bijection is asserted by tests/eval/test_predictor_name_map_bijection.py;
# byte-equality with the former hand-written tables was guarded during the
# migration by tests/spec/test_cellspec_golden_parity.py.
_ALL_PARAM_TYPES: tuple[type, ...] = (
    CoulombParams,
    DampedHOParams,
    DecayParams,
    FluidParams,
    GravityParams,
    HookeParams,
    KineticsParams,
    OpticsParams,
    PendulumParams,
    RLCParams,
    ThermalParams,
    WaveParams,
    CoulombDelta51Params,
    CoulombGamma51Params,
    CoulombGamma52Params,
    DampedHODelta31Params,
    DampedHOGamma31Params,
    DampedHOGamma32Params,
    DecayDelta121Params,
    DecayGamma121Params,
    DecayGamma122Params,
    FluidDelta101Params,
    FluidGamma101Params,
    FluidGamma102Params,
    GravityDelta21Params,
    GravityGamma21Params,
    GravityGamma22Params,
    HookeDelta11Params,
    HookeGamma11Params,
    HookeGamma12Params,
    KineticsDelta111Params,
    KineticsGamma111Params,
    KineticsGamma112Params,
    OpticsDelta91Params,
    OpticsGamma91Params,
    OpticsGamma92Params,
    PendulumDelta41Params,
    PendulumGamma41Params,
    PendulumGamma42Params,
    RLCDelta61Params,
    RLCGamma61Params,
    RLCGamma62Params,
    ThermalDelta71Params,
    ThermalGamma71Params,
    ThermalGamma72Params,
    WaveDelta81Params,
    WaveGamma81Params,
    WaveGamma82Params,
)

_LAW_PARAM_FIELDS: dict[type, tuple[str, ...]] = {
    T: _law_fields(T) for T in _ALL_PARAM_TYPES
}

_PREDICTOR_NAME_MAP: dict[type, dict[str, str]] = {
    T: _predictor_name_map(T) for T in _ALL_PARAM_TYPES
}


def _factor(rng: np.random.Generator, magnitude: float) -> float:
    return 1.0 + float(rng.uniform(-magnitude, magnitude))


def params_to_predictor_kwargs(params: Any) -> dict[str, float]:
    """Flatten a registered Params dataclass to predictor-facing kwargs.

    Used on counterfactual sub-grid (c) by ``eval/numeric.py`` to override
    declared predictor params with the per-point perturbed values. Pass-
    through behavior for non-registered types and dict-like inputs so
    callers do not need a special case.

    The output dict is keyed on the predictor-facing canonical names from
    ``_PREDICTOR_NAME_MAP`` (see blueprint-xy §2.5), NOT the internal
    Params field names. Field values are coerced to ``float``; only finite
    values are emitted (NaN/inf are dropped so a degenerate perturbation
    does not poison the merge).

    Idempotency: ``params_to_predictor_kwargs(d)`` returns ``dict(d)`` when
    ``d`` is already a Mapping.
    """
    if isinstance(params, dict):
        return {str(k): float(v) for k, v in params.items()
                if isinstance(v, (int, float)) and math.isfinite(v)}
    name_map = _PREDICTOR_NAME_MAP.get(type(params))
    if name_map is None:
        return {}
    out: dict[str, float] = {}
    for internal, canonical in name_map.items():
        if not hasattr(params, internal):
            continue
        try:
            v = float(getattr(params, internal))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(v):
            continue
        out[canonical] = v
    return out


def perturb_params(
    params: Any,
    *,
    magnitude: float = DEFAULT_MAGNITUDE,
    rng: np.random.Generator,
) -> Any:
    """Return a new params dataclass with law parameters scaled by ``1±magnitude``.

    Each law-parameter field gets an independent uniform factor in
    ``[1-magnitude, 1+magnitude]``. IC, mass, position, direction-vector,
    and sentinel fields are passed through unchanged.

    Raises ``TypeError`` if ``params`` is not a registered law-parameter
    dataclass — extending the whitelist is the explicit signal that a new
    domain has thought through *which* coefficients are the law's free
    parameters versus its boundary conditions.
    """
    if magnitude < 0:
        raise ValueError(f"magnitude must be non-negative; got {magnitude}")
    fields = _LAW_PARAM_FIELDS.get(type(params))
    if fields is None:
        raise TypeError(
            f"no counterfactual policy registered for {type(params).__name__}; "
            f"known: {[t.__name__ for t in _LAW_PARAM_FIELDS]}"
        )
    updates = {name: getattr(params, name) * _factor(rng, magnitude) for name in fields}
    return replace(params, **updates)


__all__ = [
    "DEFAULT_MAGNITUDE",
    "perturb_params",
    "params_to_predictor_kwargs",
    "_LAW_PARAM_FIELDS",
    "_PREDICTOR_NAME_MAP",
]
