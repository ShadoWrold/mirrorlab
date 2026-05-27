"""T7 (P1, hooke): truth-form builders end-to-end smoke.

Verifies the 4 hooke cells (baseline + γ-1-1 + γ-1-2 + δ-1-1) after
T7 migration off the Sprint-1 ndarray path.

- baseline: ceiling ≈ stub (both compute -k·x; no spread expected)
- γ-1-1: stub baseline misses the tanh saturation → measurable spread
- γ-1-2 (ROT): stub declares 1-D ``f(x, k)``; the 2-D grid keys (x, y)
  are filtered out by ``_predictor_signature``, predictor raises on
  missing ``x`` after filter, CLAMP'd → stub ≈ 0 vs ceiling ≈ 1.
- δ-1-1: drag term is c·(x²/L²)·v. The catalog sampler gives c in
  [1e-3, 1.0]; spread is large on the upper-c seeds (~0.25) but
  near-zero on small-c seeds where drag is physically dominated by
  spring. This reflects real physics, not a builder defect — paper 1
  will report δ-1-1 as a low-detectability cell.
"""

from __future__ import annotations

import pytest

from mirrorlab.runners.ceiling_agent import build_submission as ceiling_submission
from mirrorlab.runners.sprint3_pilot import score_against_scenario
from mirrorlab.scenarios.agent_stub import run as stub_submission
from mirrorlab.scenarios.loader import load


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_hooke_baseline_no_spread(seed):
    sc = load("hooke", "baseline", seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    s_s = score_against_scenario(sc, [stub_submission(sc)])
    assert s_c >= 0.95, f"seed={seed}: hooke baseline ceiling {s_c:.4f} < 0.95"
    # Stub IS the baseline → spread must be tiny (≤ 1e-4).
    assert abs(s_c - s_s) <= 1e-4


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_hooke_gamma_1_1_spread(seed):
    sc = load("hooke", "gamma_1_1", seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    s_s = score_against_scenario(sc, [stub_submission(sc)])
    assert s_c >= 0.90, f"seed={seed}: γ-1-1 ceiling {s_c:.4f} < 0.90"
    assert s_c - s_s >= 0.10, (
        f"seed={seed}: γ-1-1 spread {s_c - s_s:+.4f} < 0.10 "
        f"(ceiling {s_c:.4f}, stub {s_s:.4f})"
    )


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_hooke_gamma_1_2_large_spread(seed):
    sc = load("hooke", "gamma_1_2", seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    s_s = score_against_scenario(sc, [stub_submission(sc)])
    assert s_c >= 0.90, f"seed={seed}: γ-1-2 ceiling {s_c:.4f} < 0.90"
    # ROT 2-D shift exposes the X.B baseline-stub failure mode: 1-D stub
    # is filtered out → CLAMP → near-zero score.
    assert s_c - s_s >= 0.50, (
        f"seed={seed}: γ-1-2 spread {s_c - s_s:+.4f} < 0.50 "
        f"(ceiling {s_c:.4f}, stub {s_s:.4f})"
    )


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_hooke_delta_1_1_truth_at_least_as_good(seed):
    sc = load("hooke", "delta_1_1", seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    s_s = score_against_scenario(sc, [stub_submission(sc)])
    assert s_c >= 0.90, f"seed={seed}: δ-1-1 ceiling {s_c:.4f} < 0.90"
    # δ-1-1 spread is c-dependent. Truth must at least tie baseline on
    # every seed; large spread only fires on seeds where the sampler
    # gives c near the upper bound.
    assert s_c >= s_s - 1e-4, (
        f"seed={seed}: δ-1-1 truth {s_c:.4f} < stub {s_s:.4f} (truth must "
        "not lose to baseline — direction wrong)"
    )
