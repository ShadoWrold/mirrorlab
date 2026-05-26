"""Contract tests for the 32-tool MVS.

Per task #4: for each tool, verify input schema (smoke call), output shape,
and side-effect class (write tools mutate sim; read tools don't).
The knowledge-tool denylist test enforces spec §8 R-1 (no shift-specific
formula leak through ``knowledge.lookup_formula``).
"""

from __future__ import annotations

import dataclasses
import re

import pytest

from mirrorlab.scenarios.loader import load
from mirrorlab.tools.registry import REGISTRY, call, categories
from mirrorlab.tools.sandbox import SandboxContext


@pytest.fixture
def ctx():
    scen = load("hooke", "baseline", seed=42)
    return SandboxContext(sim=scen.sim, scenario_id="hooke:baseline:42")


def test_registry_size_and_categories():
    assert len(REGISTRY) == 32
    cats = categories()
    assert cats == {"measure": 8, "manipulate": 8, "analyze": 8, "knowledge": 8}


# ---- Measure --------------------------------------------------------------

def _snapshot_params(sim):
    return dataclasses.replace(sim._params)


def _params_equal(a, b):
    return dataclasses.asdict(a) == dataclasses.asdict(b)


def test_measure_position(ctx):
    snap = _snapshot_params(ctx.sim)
    r = call(ctx, "measure.position", body_id=0, t=0.0)
    assert "t" in r and "x" in r
    assert _params_equal(ctx.sim._params, snap)  # no side-effect


def test_measure_velocity(ctx):
    r = call(ctx, "measure.velocity", body_id=0, t=0.5)
    assert "t" in r and "v" in r


def test_measure_field(ctx):
    r = call(ctx, "measure.field", probe_point=[0.0], field_type="force")
    assert r["field_type"] == "force"
    assert "value" in r


def test_measure_energy(ctx):
    r = call(ctx, "measure.energy", system="total", t=0.0)
    assert "kinetic" in r


def test_measure_spectrum(ctx):
    r = call(ctx, "measure.spectrum", signal="x", window=[0.0, 2.0], n_samples=64)
    assert len(r["freqs"]) == len(r["magnitude"])


def test_measure_trajectory(ctx):
    snap = _snapshot_params(ctx.sim)
    r = call(ctx, "measure.trajectory", body_id=0, t_window=[0.0, 1.0], sample_rate=20)
    assert len(r["t"]) == len(r["x"]) == len(r["v"])
    assert _params_equal(ctx.sim._params, snap)


def test_measure_scattering(ctx):
    r = call(ctx, "measure.scattering", beam={"angle": 0.0}, target={"id": 0})
    assert "applicable" in r


def test_measure_observable(ctx):
    r = call(ctx, "measure.observable", name="x", t=0.0)
    assert r["name"] == "x"


# ---- Manipulate -----------------------------------------------------------

def test_manipulate_set_initial(ctx):
    snap = _snapshot_params(ctx.sim)
    r = call(ctx, "manipulate.set_initial", body_id=0, state={"x0": 0.5, "v0": 0.1})
    assert r["ok"]
    assert not _params_equal(ctx.sim._params, snap)
    assert ctx.sim._params.x0 == 0.5 and ctx.sim._params.v0 == 0.1


def test_manipulate_apply_impulse(ctx):
    v0_before = ctx.sim._params.v0
    r = call(ctx, "manipulate.apply_impulse", body_id=0, delta_p=0.3, t=0.0)
    assert r["ok"]
    assert ctx.sim._params.v0 != v0_before


def test_manipulate_set_external_field(ctx):
    r = call(ctx, "manipulate.set_external_field", field_spec={"E": [0, 0, 1]})
    assert r["applicable"] is False


def test_manipulate_set_boundary(ctx):
    r = call(ctx, "manipulate.set_boundary", boundary_spec={"type": "dirichlet"})
    assert r["applicable"] is False


def test_manipulate_set_parameter(ctx):
    r = call(ctx, "manipulate.set_parameter", param_name="k", value=99.0)
    assert ctx.sim._params.k == 99.0
    with pytest.raises(ValueError):
        call(ctx, "manipulate.set_parameter", param_name="not_whitelisted", value=1.0)


def test_manipulate_reset(ctx):
    original = _snapshot_params(ctx.sim)
    call(ctx, "manipulate.set_parameter", param_name="k", value=999.0)
    r = call(ctx, "manipulate.reset", original_params=original)
    assert r["ok"]
    assert _params_equal(ctx.sim._params, original)


def test_manipulate_swap_bodies(ctx):
    r = call(ctx, "manipulate.swap_bodies", i=0, j=0)
    assert r["ok"]


def test_manipulate_time_reverse_probe(ctx):
    snap = _snapshot_params(ctx.sim)
    r = call(ctx, "manipulate.time_reverse_probe", t_window=[0.0, 1.0])
    assert "forward_x" in r and "reversed_x" in r
    assert _params_equal(ctx.sim._params, snap)  # probe doesn't mutate


# ---- Analyze --------------------------------------------------------------

def test_analyze_fit(ctx):
    r = call(ctx, "analyze.fit", model="linear",
             data={"x": [0, 1, 2, 3], "y": [1, 3, 5, 7]})
    assert abs(r["params"]["b"] - 2.0) < 1e-6
    assert abs(r["params"]["a"] - 1.0) < 1e-6


def test_analyze_regress(ctx):
    r = call(ctx, "analyze.regress", x=[0, 1, 2, 3], y=[1, 3, 5, 7], family="ols")
    assert abs(r["slope"] - 2.0) < 1e-6
    assert r["r2"] > 0.99


def test_analyze_invariant_check(ctx):
    r = call(ctx, "analyze.invariant_check",
             quantity=[1.0, 1.0001, 0.9999, 1.0002], tol=1e-2)
    assert r["conserved"] is True


def test_analyze_dimensional_analysis(ctx):
    r = call(ctx, "analyze.dimensional_analysis", expr="kg*m*s**-2")
    assert r["exponents"]["kg"] == 1
    assert r["exponents"]["m"] == 1
    assert r["exponents"]["s"] == -2


def test_analyze_symbolic_simplify(ctx):
    r = call(ctx, "analyze.symbolic_simplify", expr="((x + y))")
    assert "(x+y)" in r["simplified"]


def test_analyze_numerical_solve(ctx):
    r = call(ctx, "analyze.numerical_solve",
             ode={"a": -1.0, "b": 0.0, "y0": 1.0, "t": [0.0, 1.0, 2.0]})
    assert abs(r["y"][0] - 1.0) < 1e-9
    assert r["y"][1] < r["y"][0]


def test_analyze_spectrum_fit(ctx):
    import numpy as np
    t = np.linspace(0, 1.0, 256)
    signal = np.sin(2 * np.pi * 5.0 * t)
    r = call(ctx, "analyze.spectrum_fit", signal=signal.tolist(), dt=float(t[1] - t[0]))
    assert abs(r["peak_freq"] - 5.0) < 1.0


def test_analyze_statistical_test(ctx):
    r = call(ctx, "analyze.statistical_test", hypothesis="zero_mean",
             data={"x": [0.01, -0.02, 0.03, -0.01, 0.02]})
    assert "t_stat" in r


# ---- Knowledge ------------------------------------------------------------

def test_knowledge_lookup_constant(ctx):
    r = call(ctx, "knowledge.lookup_constant", name="G")
    assert abs(r["value"] - 6.6743e-11) < 1e-14
    with pytest.raises(KeyError):
        call(ctx, "knowledge.lookup_constant", name="nope")


def test_knowledge_lookup_formula_textbook(ctx):
    r = call(ctx, "knowledge.lookup_formula", label="Hooke's law")
    assert r["formula"] == "F = -k*x"


# CRITICAL: spec §8 R-1 — knowledge tools must never leak shift-specific motifs.
_SHIFT_MOTIF_DENYLIST = [
    r"tanh", r"x\s*\*\*\s*3", r"x\^3", r"sinh", r"cosh",
    r"\balpha\b", r"\bbeta\b", r"odd[-_ ]cubic",
]


def test_knowledge_no_shift_leak(ctx):
    """Every formula in the lookup must be a clean baseline form."""
    from mirrorlab.tools.knowledge import _FORMULAS
    pat = re.compile("|".join(_SHIFT_MOTIF_DENYLIST), re.IGNORECASE)
    leaks = [(label, entry["formula"]) for label, entry in _FORMULAS.items()
             if pat.search(entry["formula"])]
    assert not leaks, f"shift-specific motifs leaked into knowledge: {leaks}"


def test_knowledge_unit_convert(ctx):
    r = call(ctx, "knowledge.unit_convert", value=1.0, from_="km", to="m")
    assert abs(r["value"] - 1000.0) < 1e-9


def test_knowledge_list_observables(ctx):
    r = call(ctx, "knowledge.list_observables", domain="hooke")
    assert any("x" in o for o in r["observables"])


def test_knowledge_suggest_probe(ctx):
    r = call(ctx, "knowledge.suggest_probe", domain="hooke")
    assert isinstance(r["suggestion"], str) and r["suggestion"]


def test_knowledge_symmetry_glossary(ctx):
    r = call(ctx, "knowledge.symmetry_glossary", label="PAR")
    assert "Parity" in r["definition"]


def test_knowledge_dim_table(ctx):
    r = call(ctx, "knowledge.dim_table", quantity="force")
    assert r["si_dim"] == "kg*m*s**-2"


def test_knowledge_related_phenomena(ctx):
    r = call(ctx, "knowledge.related_phenomena", query="oscillation")
    assert "hooke" in r["matches"]


# ---- Read-only tools never mutate sim ------------------------------------

def test_read_only_tools_never_mutate(ctx):
    snap = _snapshot_params(ctx.sim)
    # Exhaustively call every read-only tool with safe defaults.
    call(ctx, "measure.position", body_id=0, t=0.0)
    call(ctx, "measure.velocity", body_id=0, t=0.1)
    call(ctx, "measure.field", probe_point=[0.0], field_type="force")
    call(ctx, "measure.energy", system="total", t=0.0)
    call(ctx, "measure.trajectory", body_id=0, t_window=[0, 1], sample_rate=10)
    call(ctx, "measure.observable", name="x", t=0.0)
    call(ctx, "knowledge.lookup_constant", name="G")
    assert _params_equal(ctx.sim._params, snap)


def test_monitoring_records_calls(ctx):
    call(ctx, "measure.position", body_id=0, t=0.0)
    call(ctx, "measure.position", body_id=0, t=0.1)
    assert ctx.call_counts["measure.position"] == 2
    assert len(ctx.call_log) == 2
    assert all(rec.ok for rec in ctx.call_log)
    assert all(rec.latency_ms >= 0 for rec in ctx.call_log)
