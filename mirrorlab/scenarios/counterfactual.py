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

from dataclasses import replace
from typing import Any

import numpy as np

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

# Per-type whitelist of law-parameter field names that may be perturbed.
# Excluded by construction: IC fields (x0/v0/theta0/omega0/q0/i0/N0/C0/…),
# masses (m / reduced mass), source and probe positions (x1..z2, x_probe),
# direction unit vectors (n / nx/ny/nz / grad_dir / theta_pol / theta_k /
# theta0 axis / theta1 / theta_i query angles), and numerical sentinels
# (T_sim, dt, tau_min). Each entry is the explicit law-vs-BC verdict.
_LAW_PARAM_FIELDS: dict[type, tuple[str, ...]] = {
    # --- 12 baselines ---------------------------------------------------
    HookeParams: ("k",),
    DampedHOParams: ("k", "c"),
    GravityParams: ("G", "M"),
    CoulombParams: ("k_e", "q1", "q2"),
    PendulumParams: ("L", "g"),
    RLCParams: ("L", "R", "C"),
    ThermalParams: ("k",),
    WaveParams: ("A", "k", "c", "phi"),
    OpticsParams: ("n1", "n2"),
    FluidParams: ("rho", "g"),
    KineticsParams: ("k", "n"),
    DecayParams: ("lam",),
    # --- 36 shifts ------------------------------------------------------
    # Domain 1 — Hooke
    HookeGamma11Params: ("k", "eta", "x_scale"),
    HookeGamma12Params: ("k0", "xi", "phi"),
    HookeDelta11Params: ("k", "c", "L"),
    # Domain 2 — Gravity
    GravityGamma21Params: ("G0", "M", "xi"),
    GravityGamma22Params: ("G", "M", "alpha", "r_scale"),
    GravityDelta21Params: ("G0", "M", "beta", "omega_G"),
    # Domain 3 — Damped HO
    DampedHOGamma31Params: ("omega0", "gamma", "kappa", "tau", "x_ref"),
    DampedHOGamma32Params: ("omega0", "gamma", "eps", "Omega_p"),
    DampedHODelta31Params: ("omega0", "gamma", "L"),
    # Domain 4 — Pendulum
    PendulumGamma41Params: ("g_over_L", "alpha"),
    PendulumGamma42Params: ("g0_over_L", "alpha", "L", "H"),
    PendulumDelta41Params: ("g0_over_L", "eps", "Omega"),
    # Domain 5 — Coulomb
    CoulombGamma51Params: ("k_e", "q_src", "q_test", "chi"),
    CoulombGamma52Params: ("k_e", "xi", "phi0", "q_test", "src1_q", "src2_q"),
    CoulombDelta51Params: ("k_e", "alpha", "n_exp", "E_ref"),
    # Domain 6 — RLC
    RLCGamma61Params: ("L0", "R", "C", "I_sat"),
    RLCGamma62Params: ("L1", "L2", "R1", "R2", "C1", "C2", "M0", "dM"),
    RLCDelta61Params: ("L0", "R", "C", "eps", "Omega_p"),
    # Domain 7 — Thermal
    ThermalGamma71Params: ("k0", "beta"),
    ThermalGamma72Params: ("k0", "p"),
    ThermalDelta71Params: ("alpha", "lam"),
    # Domain 8 — Wave
    WaveGamma81Params: ("A", "k", "c", "gamma"),
    WaveGamma82Params: ("A", "k", "c", "beta"),
    WaveDelta81Params: ("A", "k", "c", "alpha0", "u_ref"),
    # Domain 9 — Optics
    OpticsGamma91Params: ("n1", "n0", "dn", "phi"),
    OpticsGamma92Params: ("n1", "n2", "kappa"),
    OpticsDelta91Params: ("n1", "n2", "xi", "p"),
    # Domain 10 — Fluid
    FluidGamma101Params: ("rho", "alpha", "g"),
    FluidGamma102Params: ("rho", "g", "h0", "lam", "q"),
    FluidDelta101Params: ("rho", "g", "zeta"),
    # Domain 11 — Kinetics
    KineticsGamma111Params: ("k", "n", "beta"),
    KineticsGamma112Params: ("k", "n", "m", "C_sat"),
    KineticsDelta111Params: ("k", "n", "eta"),
    # Domain 12 — Decay
    DecayGamma121Params: ("lam", "alpha", "p", "N_scale"),
    DecayGamma122Params: ("lam0", "eps", "omega"),
    DecayDelta121Params: ("lam", "xi"),
}


def _factor(rng: np.random.Generator, magnitude: float) -> float:
    return 1.0 + float(rng.uniform(-magnitude, magnitude))


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


__all__ = ["DEFAULT_MAGNITUDE", "perturb_params"]
