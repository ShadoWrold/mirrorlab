"""(domain_id, shift_id) → factory mapping.

Sprint 2: 12 baselines + γ-1-1 Hooke shift (shift expansion is task #2/#3).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np

from mirrorlab.domains.hooke import HookeBaseline, HookeParams, SimInstance
from mirrorlab.domains.gravity import GravityBaseline, GravityParams
from mirrorlab.domains.damped_ho import DampedHOBaseline, DampedHOParams
from mirrorlab.domains.pendulum import PendulumBaseline, PendulumParams
from mirrorlab.domains.coulomb import CoulombBaseline, CoulombParams
from mirrorlab.domains.rlc import RLCBaseline, RLCParams
from mirrorlab.domains.thermal import ThermalBaseline, ThermalParams
from mirrorlab.domains.wave import WaveBaseline, WaveParams
from mirrorlab.domains.optics import OpticsBaseline, OpticsParams
from mirrorlab.domains.fluid import FluidBaseline, FluidParams
from mirrorlab.domains.kinetics import KineticsBaseline, KineticsParams
from mirrorlab.domains.decay import DecayBaseline, DecayParams
from mirrorlab.shifts import (
    hooke_g_1_1, hooke_g_1_2, hooke_d_1_1,
    gravity_g_2_1, gravity_g_2_2, gravity_d_2_1,
    damped_ho_g_3_1, damped_ho_g_3_2, damped_ho_d_3_1,
    pendulum_g_4_1, pendulum_g_4_2, pendulum_d_4_1,
    coulomb_g_5_1, coulomb_g_5_2, coulomb_d_5_1,
    rlc_g_6_1, rlc_g_6_2, rlc_d_6_1,
)
from mirrorlab.shifts import (
    thermal_g_7_1, thermal_g_7_2, thermal_d_7_1,
    wave_g_8_1, wave_g_8_2, wave_d_8_1,
    optics_g_9_1, optics_g_9_2, optics_d_9_1,
    fluid_g_10_1, fluid_g_10_2, fluid_d_10_1,
    kinetics_g_11_1, kinetics_g_11_2, kinetics_d_11_1,
    decay_g_12_1, decay_g_12_2, decay_d_12_1,
)

Factory = Callable[..., Any]


def _hooke_default(seed: int) -> HookeParams:
    rng = np.random.default_rng(seed)
    k = float(np.exp(rng.uniform(np.log(1.0), np.log(100.0))))
    return HookeParams(k=k, m=1.0, x0=0.1, v0=0.0)


def _gravity_default(seed: int) -> GravityParams:
    rng = np.random.default_rng(seed)
    M = float(10 ** rng.uniform(20.0, 24.0))
    return GravityParams(M=M, m=1.0, r0=1.0e7, v0=0.0)


def _damped_ho_default(seed: int) -> DampedHOParams:
    rng = np.random.default_rng(seed)
    k = float(np.exp(rng.uniform(np.log(1.0), np.log(100.0))))
    c = float(rng.uniform(0.05, 0.5))
    return DampedHOParams(k=k, c=c, m=1.0, x0=0.1, v0=0.0)


def _pendulum_default(seed: int) -> PendulumParams:
    rng = np.random.default_rng(seed)
    L = float(np.exp(rng.uniform(np.log(0.1), np.log(2.0))))
    return PendulumParams(L=L, g=9.81, theta0=0.1, omega0=0.0)


def _coulomb_default(seed: int) -> CoulombParams:
    rng = np.random.default_rng(seed)
    q1 = float(rng.uniform(1e-9, 1e-6))
    q2 = float(rng.uniform(1e-9, 1e-6))
    return CoulombParams(q1=q1, q2=q2, m=1e-3, r0=1.0, v0=0.0)


def _rlc_default(seed: int) -> RLCParams:
    rng = np.random.default_rng(seed)
    L = float(np.exp(rng.uniform(np.log(1e-3), np.log(1e-1))))
    C = float(np.exp(rng.uniform(np.log(1e-6), np.log(1e-4))))
    R = float(rng.uniform(0.1, 10.0))
    return RLCParams(L=L, R=R, C=C, q0=1e-6, i0=0.0)


def _thermal_default(seed: int) -> ThermalParams:
    rng = np.random.default_rng(seed)
    k = float(rng.uniform(0.1, 400.0))
    return ThermalParams(k=k, L=0.1, T_hot=373.0, T_cold=293.0)


def _wave_default(seed: int) -> WaveParams:
    rng = np.random.default_rng(seed)
    A = float(rng.uniform(0.1, 1.0))
    k = float(rng.uniform(1.0, 10.0))
    c = float(rng.uniform(1.0, 343.0))
    return WaveParams(A=A, k=k, c=c, phi=0.0, x_probe=0.5)


def _optics_default(seed: int) -> OpticsParams:
    rng = np.random.default_rng(seed)
    n1 = float(rng.uniform(1.0, 1.6))
    n2 = float(rng.uniform(1.0, 1.6))
    return OpticsParams(n1=n1, n2=n2, theta1=0.3)


def _fluid_default(seed: int) -> FluidParams:
    rng = np.random.default_rng(seed)
    rho = float(rng.uniform(800.0, 1200.0))
    return FluidParams(rho=rho, g=9.81, h1=2.0, v1=1.0, p1=1.01e5, h2=0.0, v2=3.0)


def _kinetics_default(seed: int) -> KineticsParams:
    rng = np.random.default_rng(seed)
    k = float(rng.uniform(0.01, 0.5))
    n = float(rng.choice([1.0, 2.0]))
    return KineticsParams(k=k, n=n, C0=1.0)


def _decay_default(seed: int) -> DecayParams:
    rng = np.random.default_rng(seed)
    lam = float(rng.uniform(1e-3, 1.0))
    return DecayParams(lam=lam, N0=1.0e6)


def _make_baseline_factory(default_params_fn, baseline_cls):
    def factory(*, seed: int = 0, params=None):
        if params is None:
            params = default_params_fn(seed)
        return baseline_cls(params)
    return factory


def _hooke_g_1_1_factory(*, seed: int = 0, params=None):
    return hooke_g_1_1.build(params=params, seed=seed)


REGISTRY: Dict[Tuple[str, str], Factory] = {
    ("hooke", "baseline"): _make_baseline_factory(_hooke_default, HookeBaseline),
    ("hooke", "gamma_1_1"): _hooke_g_1_1_factory,
    ("hooke", "gamma_1_2"): lambda *, seed=0, params=None: hooke_g_1_2.build(params=params, seed=seed),
    ("hooke", "delta_1_1"): lambda *, seed=0, params=None: hooke_d_1_1.build(params=params, seed=seed),
    ("gravity", "baseline"): _make_baseline_factory(_gravity_default, GravityBaseline),
    ("gravity", "gamma_2_1"): lambda *, seed=0, params=None: gravity_g_2_1.build(params=params, seed=seed),
    ("gravity", "gamma_2_2"): lambda *, seed=0, params=None: gravity_g_2_2.build(params=params, seed=seed),
    ("gravity", "delta_2_1"): lambda *, seed=0, params=None: gravity_d_2_1.build(params=params, seed=seed),
    ("damped_ho", "baseline"): _make_baseline_factory(_damped_ho_default, DampedHOBaseline),
    ("damped_ho", "gamma_3_1"): lambda *, seed=0, params=None: damped_ho_g_3_1.build(params=params, seed=seed),
    ("damped_ho", "gamma_3_2"): lambda *, seed=0, params=None: damped_ho_g_3_2.build(params=params, seed=seed),
    ("damped_ho", "delta_3_1"): lambda *, seed=0, params=None: damped_ho_d_3_1.build(params=params, seed=seed),
    ("pendulum", "baseline"): _make_baseline_factory(_pendulum_default, PendulumBaseline),
    ("pendulum", "gamma_4_1"): lambda *, seed=0, params=None: pendulum_g_4_1.build(params=params, seed=seed),
    ("pendulum", "gamma_4_2"): lambda *, seed=0, params=None: pendulum_g_4_2.build(params=params, seed=seed),
    ("pendulum", "delta_4_1"): lambda *, seed=0, params=None: pendulum_d_4_1.build(params=params, seed=seed),
    ("coulomb", "baseline"): _make_baseline_factory(_coulomb_default, CoulombBaseline),
    ("coulomb", "gamma_5_1"): lambda *, seed=0, params=None: coulomb_g_5_1.build(params=params, seed=seed),
    ("coulomb", "gamma_5_2"): lambda *, seed=0, params=None: coulomb_g_5_2.build(params=params, seed=seed),
    ("coulomb", "delta_5_1"): lambda *, seed=0, params=None: coulomb_d_5_1.build(params=params, seed=seed),
    ("rlc", "baseline"): _make_baseline_factory(_rlc_default, RLCBaseline),
    ("rlc", "gamma_6_1"): lambda *, seed=0, params=None: rlc_g_6_1.build(params=params, seed=seed),
    ("rlc", "gamma_6_2"): lambda *, seed=0, params=None: rlc_g_6_2.build(params=params, seed=seed),
    ("rlc", "delta_6_1"): lambda *, seed=0, params=None: rlc_d_6_1.build(params=params, seed=seed),
    ("thermal", "baseline"): _make_baseline_factory(_thermal_default, ThermalBaseline),
    ("wave", "baseline"): _make_baseline_factory(_wave_default, WaveBaseline),
    ("optics", "baseline"): _make_baseline_factory(_optics_default, OpticsBaseline),
    ("fluid", "baseline"): _make_baseline_factory(_fluid_default, FluidBaseline),
    ("kinetics", "baseline"): _make_baseline_factory(_kinetics_default, KineticsBaseline),
    ("decay", "baseline"): _make_baseline_factory(_decay_default, DecayBaseline),
    # Domain 7 Thermal
    ("thermal", "gamma_7_1"): lambda *, seed=0, params=None: thermal_g_7_1.build(params=params, seed=seed),
    ("thermal", "gamma_7_2"): lambda *, seed=0, params=None: thermal_g_7_2.build(params=params, seed=seed),
    ("thermal", "delta_7_1"): lambda *, seed=0, params=None: thermal_d_7_1.build(params=params, seed=seed),
    # Domain 8 Wave
    ("wave", "gamma_8_1"): lambda *, seed=0, params=None: wave_g_8_1.build(params=params, seed=seed),
    ("wave", "gamma_8_2"): lambda *, seed=0, params=None: wave_g_8_2.build(params=params, seed=seed),
    ("wave", "delta_8_1"): lambda *, seed=0, params=None: wave_d_8_1.build(params=params, seed=seed),
    # Domain 9 Optics
    ("optics", "gamma_9_1"): lambda *, seed=0, params=None: optics_g_9_1.build(params=params, seed=seed),
    ("optics", "gamma_9_2"): lambda *, seed=0, params=None: optics_g_9_2.build(params=params, seed=seed),
    ("optics", "delta_9_1"): lambda *, seed=0, params=None: optics_d_9_1.build(params=params, seed=seed),
    # Domain 10 Fluid
    ("fluid", "gamma_10_1"): lambda *, seed=0, params=None: fluid_g_10_1.build(params=params, seed=seed),
    ("fluid", "gamma_10_2"): lambda *, seed=0, params=None: fluid_g_10_2.build(params=params, seed=seed),
    ("fluid", "delta_10_1"): lambda *, seed=0, params=None: fluid_d_10_1.build(params=params, seed=seed),
    # Domain 11 Kinetics
    ("kinetics", "gamma_11_1"): lambda *, seed=0, params=None: kinetics_g_11_1.build(params=params, seed=seed),
    ("kinetics", "gamma_11_2"): lambda *, seed=0, params=None: kinetics_g_11_2.build(params=params, seed=seed),
    ("kinetics", "delta_11_1"): lambda *, seed=0, params=None: kinetics_d_11_1.build(params=params, seed=seed),
    # Domain 12 Decay
    ("decay", "gamma_12_1"): lambda *, seed=0, params=None: decay_g_12_1.build(params=params, seed=seed),
    ("decay", "gamma_12_2"): lambda *, seed=0, params=None: decay_g_12_2.build(params=params, seed=seed),
    ("decay", "delta_12_1"): lambda *, seed=0, params=None: decay_d_12_1.build(params=params, seed=seed),
}


def make(
    domain_id: str,
    shift_id: str,
    *,
    seed: int = 0,
    params: Optional[Any] = None,
) -> Any:
    """Build a SimInstance for the requested `(domain_id, shift_id)`.

    Use `shift_id="baseline"` for the unmodified domain law. If `params` is
    omitted the factory draws a default / sampled parameter set under `seed`.
    """
    key = (domain_id, shift_id)
    if key not in REGISTRY:
        raise KeyError(
            f"unknown scenario {key!r}; registered: {sorted(REGISTRY)}"
        )
    return REGISTRY[key](seed=seed, params=params)


__all__ = ["REGISTRY", "make", "SimInstance"]
