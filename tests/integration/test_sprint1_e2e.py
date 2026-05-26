"""Sprint 1 exit-criterion golden tests.

Thresholds are deliberately loose because CAL-4 (τ=0.5) is a Sprint-1
placeholder; the headline claim Sprint 1 makes is that the eval *discriminates*
baseline from γ-1-1, not that any particular numeric bar is hit. See
``docs/sprint1-report.md`` 'Known gaps / Sprint 3 inputs'.

  - baseline (seed=0): S_scen > 0.95  — stub matches truth
  - γ-1-1   (seed=0): S_scen < 0.80   — single-seed discrimination (Δ ≥ 0.2)
  - γ-1-1   (seeds 0..9 mean): < 0.65 — robustness across seeds
"""

from __future__ import annotations

import io
import statistics
from contextlib import redirect_stdout

from mirrorlab.runners.sprint1_demo import format_report, main, run_demo


def test_baseline_stub_matches_truth_scores_high():
    result = run_demo("hooke", "baseline", seed=0)
    assert result["stage1_pass"] is True
    assert result["s_scen"] > 0.95, (
        f"baseline stub should score > 0.95; got S_scen={result['s_scen']:.3f}\n"
        f"per-subgrid RMSLE: {result['per_subgrid_rmsle']}"
    )


def test_gamma_1_1_stub_fails_to_extrapolate_seed_0():
    result = run_demo("hooke", "gamma_1_1", seed=0)
    # Stage-1 still passes (entry declares correct units); the discriminator
    # is the numeric stage's OOD penalty.
    assert result["stage1_pass"] is True
    assert result["s_scen"] < 0.80, (
        f"γ-1-1 linear stub should score < 0.80 at seed=0; "
        f"got S_scen={result['s_scen']:.3f}\n"
        f"per-subgrid RMSLE: {result['per_subgrid_rmsle']}"
    )


def test_gamma_1_1_robustness_mean_across_seeds():
    scores = [run_demo("hooke", "gamma_1_1", seed=s)["s_scen"] for s in range(10)]
    mean = statistics.fmean(scores)
    assert mean < 0.65, (
        f"γ-1-1 mean S_scen over seeds 0..9 should be < 0.65 "
        f"(guards against single-seed flukes); got mean={mean:.3f}\n"
        f"scores: {[f'{s:.3f}' for s in scores]}"
    )


def test_eval_discriminates_baseline_vs_gamma_1_1():
    """Headline Sprint 1 exit criterion: same agent, different worlds, score gap.

    Note: Sprint 2 turned sub-grid (c) into a true CAL-3 counterfactual
    (per-point perturbed params). This penalizes the baseline-correct stub
    too (its locked ``k_hat`` cannot track per-point ``k``), so the seed-0
    gap is smaller than Sprint 1's placeholder reported (~0.19 vs ~0.22) —
    but the multi-seed mean gap is roughly *double* what it was before (see
    ``test_eval_discriminates_mean_gap_across_seeds`` below).
    """
    base = run_demo("hooke", "baseline", seed=0)
    gam = run_demo("hooke", "gamma_1_1", seed=0)
    assert base["s_scen"] - gam["s_scen"] > 0.15


def test_eval_discriminates_mean_gap_across_seeds():
    """Multi-seed guard against single-seed flukes after CAL-3 went live."""
    gaps = [
        run_demo("hooke", "baseline", seed=s)["s_scen"]
        - run_demo("hooke", "gamma_1_1", seed=s)["s_scen"]
        for s in range(10)
    ]
    mean = statistics.fmean(gaps)
    assert mean > 0.30, (
        f"mean Δ(baseline − γ-1-1) across seeds 0..9 should exceed 0.30 "
        f"with the CAL-3 counterfactual live; got mean={mean:.3f}\n"
        f"gaps: {[f'{g:.3f}' for g in gaps]}"
    )


def test_cli_g_1_1_alias_runs_and_prints_report():
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["--scenario", "hooke,g_1_1", "--seed", "0"])
    assert rc == 0
    out = buf.getvalue()
    assert "Scenario: hooke / gamma_1_1" in out
    assert "Stage-1 (dim): PASS" in out
    assert "S_scen:" in out


def test_format_report_baseline_shape():
    result = run_demo("hooke", "baseline", seed=0)
    txt = format_report(result)
    assert "in-domain RMSLE" in txt
    assert "OOD RMSLE" in txt
    assert "counterfactual RMSLE" in txt
