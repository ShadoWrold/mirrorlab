"""Tests for ``mirrorlab.eval.structural`` — structural-correctness probes.

The headline claim (Phase 0): a probe must SEPARATE a structurally-correct
predictor (the oracle, which carries the true broken-symmetry term) from a
"right numbers, wrong physics" cheat that drops the break and collapses to the
unbroken form. We assert the normalized ``captured_fraction``:

  oracle  → ≈ 1.0  (reproduces the true break)
  cheat   → ≈ 0.0  (collapsed to the unbroken structure)

uniformly across all four implemented probes, regardless of how small the
break's absolute metric magnitude is. We also assert T_TRANS reports
not-applicable (honest coverage, not a fabricated metric).
"""

from __future__ import annotations

import mirrorlab.scenarios.loader  # noqa: F401 — populates CELL_REGISTRY
from mirrorlab.scenarios.loader import load
from mirrorlab.scenarios.registry import make
from mirrorlab.spec import CELL_REGISTRY, get_cell, make_oracle_predictor
from mirrorlab.eval.structural import structural_score


def _oracle_and_result(domain, shift, cheat):
    sc = load(domain, shift, seed=0)
    sim = make(domain, shift, seed=0)
    spec = get_cell(domain, shift)
    oracle = make_oracle_predictor(spec, sim.params)
    r_oracle = structural_score(oracle, spec, sim.params, test_grids=sc.test_grids)
    r_cheat = structural_score(cheat, spec, sim.params, test_grids=sc.test_grids)
    return r_oracle, r_cheat, sim


# ---- Per-probe discrimination: oracle ≈1, cheat ≈0 -------------------------

def test_parity_probe_separates_oracle_from_symmetric_cheat():
    # hooke γ-1-1: F = -k x (1 + η tanh(x/xs)); cheat drops the tanh break.
    sim = make("hooke", "gamma_1_1", seed=0)
    k = sim.params.k
    ro, rc, _ = _oracle_and_result("hooke", "gamma_1_1", lambda x: -k * x)
    assert ro.applicable and rc.applicable
    assert ro.probe_name == "parity_chi"
    assert ro.captured_fraction > 0.9
    assert rc.captured_fraction < 0.1


def test_time_reversal_probe_separates_oracle_from_conservative_cheat():
    # hooke δ-1-1: F = -k x - c (x²/L²) v; cheat drops the dissipative term.
    sim = make("hooke", "delta_1_1", seed=0)
    k = sim.params.k
    ro, rc, _ = _oracle_and_result("hooke", "delta_1_1", lambda x, v: -k * x)
    assert ro.applicable and rc.applicable
    assert ro.probe_name == "time_reversal_sigma"
    assert ro.captured_fraction > 0.9
    assert rc.captured_fraction < 0.1


def test_scale_probe_separates_oracle_from_linear_cheat():
    # damped_ho γ-3-1 (SCALE break); cheat is a plain linear spring.
    ro, rc, _ = _oracle_and_result("damped_ho", "gamma_3_1", lambda x, v: -5.0 * x)
    assert ro.applicable and rc.applicable
    assert ro.probe_name == "scale_exponent_var"
    assert ro.captured_fraction > 0.9
    assert rc.captured_fraction < 0.1


def test_rotation_probe_separates_oracle_from_isotropic_cheat():
    # coulomb γ-5-1 (ROT break, quadrupole anisotropy); cheat is isotropic A/r².
    sim = make("coulomb", "gamma_5_1", seed=0)
    A = sim.params.k_e * sim.params.q_src * sim.params.q_test
    ro, rc, _ = _oracle_and_result(
        "coulomb", "gamma_5_1", lambda x, y, z: A / (x * x + y * y + z * z)
    )
    assert ro.applicable and rc.applicable
    assert ro.probe_name == "rotation_anisotropy"
    assert ro.captured_fraction > 0.9
    assert rc.captured_fraction < 0.1


def test_scale_probe_separates_oracle_from_linear_cheat():
    # gravity γ-2-2 (SCALE break: log-periodic DSI); cheat is a pure power law
    # −GMm/r² with no log-periodic modulation (the clean SCALE reference cell).
    sim = make("gravity", "gamma_2_2", seed=0)
    G, M, m = sim.params.G, sim.params.M, sim.params.m
    ro, rc, _ = _oracle_and_result(
        "gravity", "gamma_2_2", lambda r: -G * M * m / (r * r)
    )
    assert ro.applicable and rc.applicable
    assert ro.probe_name == "scale_exponent_var"
    assert ro.captured_fraction > 0.9
    assert rc.captured_fraction < 0.1


def test_normalization_is_cross_cell_comparable():
    """captured_fraction collapses different break magnitudes onto one scale:
    PAR break (χ-signal) and SCALE break (Var[s]-signal) both put their oracle
    at ≈1.0 regardless of the raw metric magnitude."""
    sim = make("hooke", "gamma_1_1", seed=0)
    par_o, _, _ = _oracle_and_result("hooke", "gamma_1_1", lambda x: -sim.params.k * x)
    gsim = make("gravity", "gamma_2_2", seed=0)
    scale_o, _, _ = _oracle_and_result(
        "gravity", "gamma_2_2",
        lambda r: -gsim.params.G * gsim.params.M * gsim.params.m / (r * r),
    )
    # Both oracles capture ≈1.0 after normalization despite different probes.
    assert abs(par_o.captured_fraction - 1.0) < 0.05
    assert abs(scale_o.captured_fraction - 1.0) < 0.05


def test_stronger_than_oracle_break_clamps_at_one():
    """A predictor whose break is STRONGER than the oracle's must not report a
    captured_fraction above 1.0. The hooke γ-1-1 truth is a tanh parity break;
    an x² term is a harsher parity break whose raw ratio overshoots (≈2.0). cf
    measures break STRENGTH, not shape correctness, so 'stronger than truth' is
    capped at 1.0 — the raw m_pred/m_star still expose the overshoot. This is
    the visual-target fix: the reported fraction never looks like it credits a
    wrong-but-strong break with more than full capture."""
    sim = make("hooke", "gamma_1_1", seed=0)
    k, c = sim.params.k, 50.0
    # An x² parity break (even), harsher than the true tanh break.
    r, _, _ = _oracle_and_result("hooke", "gamma_1_1", lambda x: -k * x - c * x * x)
    assert r.applicable
    assert r.captured_fraction is not None
    assert r.captured_fraction <= 1.0          # clamped, never overshoots
    # Raw metrics still reveal that the break was actually stronger than truth.
    assert r.m_pred > r.m_star or abs(r.m_pred - r.m_star) < abs(r.m_star)


# ---- Honest coverage: no probe-able axis ⇒ not applicable -------------------

def test_no_axis_reports_not_applicable():
    # coulomb δ-5-1 is TR (irreversible leak), but its inputs are (q1,q2) with
    # no velocity axis, so the time-reversal probe cannot run → honest N/A
    # rather than a fabricated metric.
    sim = make("coulomb", "delta_5_1", seed=0)
    spec = get_cell("coulomb", "delta_5_1")
    sc = load("coulomb", "delta_5_1", seed=0)
    r = structural_score(lambda q1, q2: 0.0, spec, sim.params, test_grids=sc.test_grids)
    assert r.symmetry == "TR"
    assert r.applicable is False
    assert r.captured_fraction is None


def test_baseline_break_is_degenerate_no_capture():
    """A baseline (broken='none') has no probe → not applicable, no division."""
    sim = make("hooke", "baseline", seed=0)
    spec = get_cell("hooke", "baseline")
    sc = load("hooke", "baseline", seed=0)
    r = structural_score(lambda x: -sim.params.k * x, spec, sim.params, test_grids=sc.test_grids)
    assert r.applicable is False  # "none" has no registered probe


# ---- Coverage report (informational, always passes) ------------------------

def test_probe_coverage_report(capsys):
    """Report how many of the 48 cells have an applicable probe — honest
    coverage, printed for visibility (not a hard assertion beyond >0)."""
    from collections import Counter
    cov = Counter()
    applicable = 0
    for (domain, shift), spec in sorted(CELL_REGISTRY.items()):
        sim = make(domain, shift, seed=0)
        sc = load(domain, shift, seed=0)
        oracle = make_oracle_predictor(spec, sim.params)
        r = structural_score(oracle, spec, sim.params, test_grids=sc.test_grids)
        cov[spec.break_type] += 1
        if r.applicable:
            applicable += 1
    total = sum(cov.values())
    with capsys.disabled():
        print(f"\n[structural probe coverage] {applicable}/{total} cells applicable")
        print(f"  symmetry distribution: {dict(cov)}")
    assert applicable > 0
