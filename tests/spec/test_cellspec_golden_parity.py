"""Golden-parity guard for the CellSpec migration.

The counterfactual tables `_LAW_PARAM_FIELDS` and `_PREDICTOR_NAME_MAP` are now
DERIVED from per-field role metadata (see mirrorlab/spec.py). This test pins
them against the authoritative hand-written values from the git commit that
introduced the metadata, so a future metadata edit that silently changes a
cell's law set or canonical names is caught.

Authoritative values are captured below as frozen literals (copied from the
pre-derivation hand-written tables). Field ORDER is intentionally compared as
a SET: `perturb_params` perturbs each law field independently, so the law-set
membership is what matters, not declaration order. (Two baselines — Gravity
and Coulomb — have G/k_e declared last because they carry a physics-constant
default, so the derived tuple order differs harmlessly from the old literal.)
"""

from __future__ import annotations

from mirrorlab.scenarios.counterfactual import (
    _LAW_PARAM_FIELDS,
    _PREDICTOR_NAME_MAP,
)
from mirrorlab.spec import is_fully_tagged

# Authoritative law-field SETS, keyed by Params type name (copied verbatim from
# the hand-written _LAW_PARAM_FIELDS before it was switched to derivation).
_GOLDEN_LAW = {
    "HookeParams": {"k"},
    "DampedHOParams": {"k", "c"},
    "GravityParams": {"G", "M"},
    "CoulombParams": {"k_e", "q1", "q2"},
    "PendulumParams": {"L", "g"},
    "RLCParams": {"L", "R", "C"},
    "ThermalParams": {"k"},
    "WaveParams": {"A", "k", "c", "phi"},
    "OpticsParams": {"n1", "n2"},
    "FluidParams": {"rho", "g"},
    "KineticsParams": {"k", "n"},
    "DecayParams": {"lam"},
    "HookeGamma11Params": {"k", "eta", "x_scale"},
    "HookeGamma12Params": {"k0", "xi", "phi"},
    "HookeDelta11Params": {"k", "c", "L"},
    "GravityGamma21Params": {"G0", "M", "xi"},
    "GravityGamma22Params": {"G", "M", "alpha", "omega", "r_scale"},
    "GravityDelta21Params": {"G0", "M", "beta", "omega_G"},
    "DampedHOGamma31Params": {"omega0", "gamma", "kappa", "tau", "x_ref"},
    "DampedHOGamma32Params": {"omega0", "gamma", "eps", "Omega_p"},
    "DampedHODelta31Params": {"omega0", "gamma", "L"},
    "PendulumGamma41Params": {"g_over_L", "alpha"},
    "PendulumGamma42Params": {"g0_over_L", "alpha", "L", "H"},
    "PendulumDelta41Params": {"g0_over_L", "eps", "Omega"},
    "CoulombGamma51Params": {"k_e", "q_src", "q_test", "chi"},
    "CoulombGamma52Params": {"k_e", "xi", "phi0", "q_test", "src1_q", "src2_q"},
    "CoulombDelta51Params": {"k_e", "alpha", "n_exp", "E_ref"},
    "RLCGamma61Params": {"L0", "R", "C", "I_sat"},
    "RLCGamma62Params": {"L1", "L2", "R1", "R2", "C1", "C2", "M0", "dM"},
    "RLCDelta61Params": {"L0", "R", "C", "eps", "Omega_p"},
    "ThermalGamma71Params": {"k0", "beta"},
    "ThermalGamma72Params": {"k0", "p"},
    "ThermalDelta71Params": {"alpha", "lam"},
    "WaveGamma81Params": {"A", "c", "gamma"},
    "WaveGamma82Params": {"A", "k", "c", "beta"},
    "WaveDelta81Params": {"A", "k", "c", "alpha0", "u_ref"},
    "OpticsGamma91Params": {"R0", "beta0", "chi", "phi"},
    "OpticsGamma92Params": {"n1", "n2", "kappa"},
    "OpticsDelta91Params": {"R0", "beta"},
    "FluidGamma101Params": {"rho", "alpha", "g"},
    "FluidGamma102Params": {"rho", "g", "h0", "lam", "q"},
    "FluidDelta101Params": {"rho", "g", "zeta"},
    "KineticsGamma111Params": {"k", "n", "beta"},
    "KineticsGamma112Params": {"k", "n", "m", "C_sat"},
    "KineticsDelta111Params": {"k", "n", "eta"},
    "DecayGamma121Params": {"lam", "alpha", "p", "N_scale"},
    "DecayGamma122Params": {"lam0", "eps", "omega"},
    "DecayDelta121Params": {"lam", "xi"},
}

# Authoritative canonical name maps (order-independent dict comparison).
_GOLDEN_NAME_MAP = {
    "CoulombParams": {"q1": "q_1", "q2": "q_2", "k_e": "k_e"},
    "OpticsParams": {"n1": "n_1", "n2": "n_2"},
    "GravityGamma21Params": {"G0": "G", "M": "M", "xi": "xi"},
    "CoulombGamma51Params": {"k_e": "k_e", "q_src": "q_1", "q_test": "q_2", "chi": "chi"},
    "CoulombGamma52Params": {"k_e": "k_e", "xi": "xi", "phi0": "phi_0",
                             "src1_q": "q_1", "src2_q": "q_2", "q_test": "q_3"},
    "RLCGamma62Params": {"L1": "L_1", "L2": "L_2", "R1": "R_1", "R2": "R_2",
                         "C1": "C_1", "C2": "C_2", "M0": "M_0", "dM": "dM"},
    "ThermalGamma71Params": {"k0": "k", "beta": "beta"},
    "PendulumGamma42Params": {"g0_over_L": "g_over_L", "alpha": "alpha", "L": "L", "H": "H"},
}


def _by_name():
    return {T.__name__: T for T in _LAW_PARAM_FIELDS}


def test_all_48_cells_tagged():
    untagged = [T.__name__ for T in _LAW_PARAM_FIELDS if not is_fully_tagged(T)]
    assert not untagged, f"Params still missing field-role metadata: {untagged}"


def test_law_field_sets_match_golden():
    by_name = _by_name()
    for name, golden in _GOLDEN_LAW.items():
        assert name in by_name, f"{name} missing from registry"
        got = set(_LAW_PARAM_FIELDS[by_name[name]])
        assert got == golden, f"{name}: law set {sorted(got)} != golden {sorted(golden)}"


def test_canonical_name_maps_match_golden():
    by_name = _by_name()
    for name, golden in _GOLDEN_NAME_MAP.items():
        got = _PREDICTOR_NAME_MAP[by_name[name]]
        assert got == golden, f"{name}: name map {got} != golden {golden}"
