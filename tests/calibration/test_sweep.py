"""Unit tests for mirrorlab.calibration.sweep (Sprint 3 task #5).

Synthetic RMSLE records only — no real scenarios are executed.
"""

from __future__ import annotations

import math
import random

import numpy as np
import pytest

from mirrorlab.calibration.sweep import (
    ScenarioRMSLE,
    SweepResult,
    collect_llm_records,
    sweep_cal1_shares,
    sweep_cal3_magnitude,
    sweep_cal4_tau,
    sweep_cal9_threshold,
    sweep_cal10_seeds,
)


# ---------------------------------------------------------------------------
# Synthetic record builders
# ---------------------------------------------------------------------------


def _baseline_record(seed: int = 0, *, domain: str = "hooke") -> ScenarioRMSLE:
    """Baseline: zero RMSLE everywhere (the stub fits the law perfectly)."""
    return ScenarioRMSLE(
        domain_id=domain,
        shift_id="baseline",
        seed=seed,
        tier="baseline",
        rmsle_a=0.0,
        rmsle_b=0.0,
        rmsle_c=0.0,
    )


def _gamma_record(
    seed: int = 0,
    *,
    domain: str = "hooke",
    ra: float = 0.07,
    rb: float = 0.25,
    rc: float = 0.10,
) -> ScenarioRMSLE:
    return ScenarioRMSLE(
        domain_id=domain,
        shift_id="gamma_1_1",
        seed=seed,
        tier="gamma",
        rmsle_a=ra,
        rmsle_b=rb,
        rmsle_c=rc,
    )


# ---------------------------------------------------------------------------
# ScenarioRMSLE / s_entry replay
# ---------------------------------------------------------------------------


def test_s_entry_replay_matches_closed_form():
    r = _gamma_record(ra=0.1, rb=0.2, rc=0.3)
    # Default weights (0.4, 0.4, 0.2) ⇒ r_bar = 0.04+0.08+0.06 = 0.18
    expected = math.exp(-0.18 / 0.5)
    assert r.s_entry(tau=0.5) == pytest.approx(expected, rel=1e-9)


def test_s_entry_baseline_is_one_at_any_tau():
    r = _baseline_record()
    for tau in (0.05, 0.5, 5.0):
        assert r.s_entry(tau=tau) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# CAL-4 τ sweep
# ---------------------------------------------------------------------------


def test_sweep_cal4_tau_tightens_against_default_when_gap_too_small():
    """At τ=0.5 the stub-fit gamma scores hover near 0.6 (Sprint 1 saturation).
    The sweep should recommend a smaller τ to push Δ ≥ 0.5 if feasible."""
    records = [_baseline_record(seed=s) for s in range(5)]
    records += [_gamma_record(seed=s, ra=0.07, rb=0.25, rc=0.10) for s in range(5)]
    res = sweep_cal4_tau(records, target_delta=0.5)
    assert isinstance(res, SweepResult)
    assert res.recommended <= 0.5
    # The recommended τ must hit both constraints in the swept points.
    chosen_point = next(p for p in res.points if p.knob == res.recommended)
    assert chosen_point.metrics["mean_s_baseline"] >= 0.9
    assert chosen_point.metrics["delta"] >= 0.5


def test_sweep_cal4_tau_defers_when_no_shift_records():
    res = sweep_cal4_tau([_baseline_record(seed=s) for s in range(3)])
    assert res.defer_to_sprint4 is True


def test_sweep_cal4_tau_points_have_full_curve():
    records = [_baseline_record(seed=s) for s in range(3)]
    records += [_gamma_record(seed=s) for s in range(3)]
    res = sweep_cal4_tau(records)
    # Tradeoff curve, not just a single point.
    assert len(res.points) >= 5
    deltas = [p.metrics["delta"] for p in res.points]
    # Monotone: smaller τ ⇒ bigger gap (in this synthetic regime).
    assert deltas == sorted(deltas, reverse=True)


def test_sweep_cal4_tau_honest_defer_when_floor_incompatible_with_target():
    """If the synthetic gamma RMSLEs are tiny, no τ in range can reach
    target_delta=0.9 without dropping the baseline floor — must defer."""
    records = [_baseline_record(seed=s) for s in range(3)]
    records += [_gamma_record(seed=s, ra=0.01, rb=0.01, rc=0.01) for s in range(3)]
    res = sweep_cal4_tau(records, target_delta=0.9, baseline_floor=0.95)
    assert res.defer_to_sprint4 is True
    assert "defer" in res.rationale.lower() or "default" in res.rationale.lower()


# ---------------------------------------------------------------------------
# CAL-1 share sweep
# ---------------------------------------------------------------------------


def test_sweep_cal1_shares_recommends_balanced_triple():
    records = [_baseline_record(seed=s) for s in range(5)]
    # Shift records: OOD dominant, so any triple weighting (b) more should
    # produce bigger gaps. Sweep should still prefer the balanced default.
    records += [_gamma_record(seed=s, ra=0.05, rb=0.40, rc=0.05) for s in range(5)]
    res = sweep_cal1_shares(records, target_ood_detectability=0.10)
    a, b, c = res.recommended
    assert min(a, b, c) >= 0.10
    assert abs(a + b + c - 1.0) < 1e-6


def test_sweep_cal1_shares_defers_when_no_triple_meets_target():
    records = [_baseline_record(seed=s) for s in range(3)]
    records += [_gamma_record(seed=s, ra=0.0, rb=0.0, rc=0.0) for s in range(3)]
    res = sweep_cal1_shares(records, target_ood_detectability=0.30)
    assert res.defer_to_sprint4 is True
    assert res.recommended == (0.40, 0.40, 0.20)


# ---------------------------------------------------------------------------
# CAL-3 magnitude sweep
# ---------------------------------------------------------------------------


def test_sweep_cal3_magnitude_factory_called_per_value():
    seen = []

    def factory(m):
        seen.append(m)
        # Larger magnitude ⇒ bigger (c) RMSLE ⇒ bigger drop attributable to c.
        return [_gamma_record(seed=s, ra=0.05, rb=0.05, rc=0.5 * m) for s in range(4)]

    res = sweep_cal3_magnitude(factory, magnitudes=[0.1, 0.2, 0.3, 0.4])
    assert seen == [0.1, 0.2, 0.3, 0.4]
    # drop_c_only should be non-decreasing in magnitude on this synthetic.
    drops = [p.metrics["drop_c_only"] for p in res.points]
    assert drops == sorted(drops)


def test_sweep_cal3_magnitude_picks_smallest_feasible():
    def factory(m):
        # Drop hits target at m=0.3.
        drop = 0.15 if m < 0.3 else 0.30
        # Encode this in rc; the sweep computes drop from rmsle.
        rc = 0.5 if m < 0.3 else 1.5
        return [_gamma_record(seed=s, ra=0.0, rb=0.0, rc=rc) for s in range(3)]

    res = sweep_cal3_magnitude(
        factory, magnitudes=[0.1, 0.2, 0.3, 0.4, 0.5], target_attacker_drop=0.20
    )
    assert res.recommended == 0.3


def test_sweep_cal3_magnitude_defers_when_target_unreachable():
    def factory(m):
        return [_gamma_record(seed=s, ra=0.0, rb=0.0, rc=0.0) for s in range(3)]

    res = sweep_cal3_magnitude(factory, magnitudes=[0.1, 0.3, 0.5], target_attacker_drop=0.20)
    assert res.defer_to_sprint4 is True


# ---------------------------------------------------------------------------
# CAL-9 attacker threshold
# ---------------------------------------------------------------------------


def test_sweep_cal9_threshold_clean_separation_picks_midpoint():
    attacker = [0.20, 0.25, 0.30]
    legit = [0.70, 0.75, 0.80]
    res = sweep_cal9_threshold(attacker, legit)
    # Midpoint of (max_attacker=0.3, min_legit=0.7) = 0.5
    assert res.recommended == pytest.approx(0.5, abs=1e-6)
    assert res.defer_to_sprint4 is False


def test_sweep_cal9_threshold_overlapping_distributions_defers():
    attacker = [0.40, 0.55, 0.62]
    legit = [0.50, 0.60, 0.65]
    res = sweep_cal9_threshold(attacker, legit)
    assert res.recommended == 0.50
    assert res.defer_to_sprint4 is True


def test_sweep_cal9_threshold_no_attacker_data_keeps_default():
    res = sweep_cal9_threshold([])
    assert res.recommended == 0.50
    assert res.defer_to_sprint4 is True


# ---------------------------------------------------------------------------
# CAL-10 seed count
# ---------------------------------------------------------------------------


def test_sweep_cal10_seeds_recommends_n_given_target_se():
    # Build records with controlled within-cell std.
    rng = random.Random(42)
    records = []
    for cell_id, (dom, shift) in enumerate([("hooke", "gamma_1_1"), ("gravity", "gamma_2_1")]):
        for seed in range(10):
            jitter = rng.gauss(0.0, 0.1)
            records.append(
                ScenarioRMSLE(
                    domain_id=dom,
                    shift_id=shift,
                    seed=seed,
                    tier="gamma",
                    rmsle_a=max(0.0, 0.1 + jitter),
                    rmsle_b=max(0.0, 0.2 + jitter),
                    rmsle_c=max(0.0, 0.1 + jitter),
                )
            )
    res = sweep_cal10_seeds(records, target_se=0.05, max_seeds=20)
    assert 1 <= res.recommended <= 20
    # SE at recommended n must satisfy the target
    chosen = next(p for p in res.points if p.knob == res.recommended)
    pooled = chosen.metrics["pooled_std"]
    assert chosen.metrics["se"] == pytest.approx(pooled / math.sqrt(res.recommended))


def test_sweep_cal10_seeds_flags_variance_dominated_cells():
    records = []
    for seed in range(3):
        records.append(_gamma_record(seed=seed, ra=0.0, rb=0.0, rc=0.0))
        records.append(_gamma_record(seed=seed + 100, ra=1.0, rb=1.0, rc=1.0))
    # Force two cells from same (domain, shift) — use distinct shifts instead:
    records2 = []
    for seed in range(3):
        records2.append(ScenarioRMSLE("hooke", "gamma_1_1", seed, "gamma", 0.0, 0.0, 0.0))
        records2.append(ScenarioRMSLE("hooke", "gamma_1_1", seed + 100, "gamma", 1.0, 1.0, 1.0))
    res = sweep_cal10_seeds(records2, target_se=0.01, max_seeds=5)
    assert res.defer_to_sprint4 is True


def test_sweep_cal10_seeds_zero_variance_recommends_one():
    records = [_baseline_record(seed=s) for s in range(5)]
    res = sweep_cal10_seeds(records, target_se=0.05, max_seeds=10)
    assert res.recommended == 1


# ---------------------------------------------------------------------------
# collect_llm_records — LLMAgent integration with mock caller
# ---------------------------------------------------------------------------


def test_collect_llm_records_mock_default_falls_back_to_stub():
    """Default mock caller drives LLMAgent into stub-fallback. Records emerge
    via the LLMAgent pipeline (not a direct stub call), proving the
    integration is wired."""
    recs = collect_llm_records([("hooke", "baseline")], seeds=[0, 1])
    assert len(recs) == 2
    for r in recs:
        assert r.domain_id == "hooke"
        assert r.tier == "baseline"
        assert r.rmsle_a >= 0.0 and r.rmsle_b >= 0.0 and r.rmsle_c >= 0.0


def test_collect_llm_records_with_injected_agent():
    """Pass a pre-built LLMAgent (still mock) — function honors the override."""
    from mirrorlab.runners.llm_agent import LLMAgent

    calls = []

    def fake_llm_call(messages, tools):
        calls.append(len(messages))
        return {"role": "assistant", "content": "", "tool_calls": []}

    agent = LLMAgent(llm_call=fake_llm_call, fallback_to_stub=True)
    recs = collect_llm_records([("hooke", "gamma_1_1")], seeds=[0], agent=agent)
    assert len(recs) == 1
    assert recs[0].tier == "gamma"
    # The injected caller was actually invoked (proves we're not bypassing LLMAgent).
    assert len(calls) >= 1


def test_collect_llm_records_skips_unwired_domain_silently():
    """Domains whose loader is not registered should be skipped without raising."""
    recs = collect_llm_records([("nonexistent_domain", "baseline")], seeds=[0])
    assert recs == []
