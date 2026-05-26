"""CAL knob sweep functions (spec §10 calibration registry).

Each ``sweep_calN_*`` returns a ``SweepResult`` containing the full tradeoff
curve (``points``) and a single ``recommended`` value with ``rationale``. Per
task #5 deliverable: "tradeoff curves, not just point estimates". Honest
sweeps only — if the data does not support a tightening of a knob, the
recommendation is the existing default and the rationale says so.

The core abstraction is the **per-scenario RMSLE triple** captured at run
time. Once collected, knobs CAL-1 (sub-grid shares) and CAL-4 (τ) can be
swept analytically — there is no need to re-run scenarios. CAL-3 (CF
magnitude) requires re-execution because it changes the (c) sub-grid's
ground truth, so it takes a callable that produces records for a given
magnitude. CAL-9 / CAL-10 are aggregate-only sweeps.

Sprint 3 calibration is stub-data first; when real-LLM records land
(task #3) the same sweep functions accept those records unchanged.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np

from mirrorlab.eval.numeric import SUBGRID_WEIGHTS, TAU_DEFAULT


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioRMSLE:
    """Frozen per-scenario RMSLE triple.

    Tier is one of ``"baseline" | "gamma" | "delta"``. Recording the
    individual sub-grid RMSLEs (rather than the collapsed ``s_entry``) lets
    downstream sweeps over CAL-1 / CAL-4 stay analytic.
    """

    domain_id: str
    shift_id: str
    seed: int
    tier: str
    rmsle_a: float
    rmsle_b: float
    rmsle_c: float

    def s_entry(
        self,
        *,
        tau: float = TAU_DEFAULT,
        weights: Mapping[str, float] = SUBGRID_WEIGHTS,
    ) -> float:
        """Replay ``s_entry`` for arbitrary τ / share triple."""
        r_bar = _weighted_rbar(self.rmsle_a, self.rmsle_b, self.rmsle_c, weights)
        return float(math.exp(-r_bar / tau))


@dataclass(frozen=True)
class SweepPoint:
    knob: Any                  # scalar or tuple identifying the knob value
    metrics: Mapping[str, float]


@dataclass
class SweepResult:
    knob_name: str
    points: list[SweepPoint]
    recommended: Any
    rationale: str
    defer_to_sprint4: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _weighted_rbar(
    ra: float,
    rb: float,
    rc: float,
    weights: Mapping[str, float],
) -> float:
    wa, wb, wc = weights.get("a", 0.0), weights.get("b", 0.0), weights.get("c", 0.0)
    wsum = wa + wb + wc
    if wsum <= 0:
        return 0.0
    return (wa * ra + wb * rb + wc * rc) / wsum


def _group_by_tier(records: Iterable[ScenarioRMSLE]) -> dict[str, list[ScenarioRMSLE]]:
    out: dict[str, list[ScenarioRMSLE]] = {"baseline": [], "gamma": [], "delta": []}
    for r in records:
        if r.tier not in out:
            out[r.tier] = []
        out[r.tier].append(r)
    return out


# ---------------------------------------------------------------------------
# Record collection (stub-data convenience)
# ---------------------------------------------------------------------------


def _tier_of(shift_id: str) -> str:
    if shift_id == "baseline":
        return "baseline"
    if shift_id.startswith("gamma"):
        return "gamma"
    if shift_id.startswith("delta"):
        return "delta"
    return "unknown"


def _submission_to_rmsle_triple(
    submission: Sequence[Mapping[str, Any]],
    scenario: Any,
) -> tuple[float, float, float] | None:
    """Score a submission against its scenario's test grids and return the
    per-sub-grid RMSLE triple. ``None`` means no dim-valid entry produced
    finite per-sub-grid RMSLEs — sweep treats this as "no record".

    Reuses ``sprint1_demo._grids_with_ground_truth`` /
    ``_per_subgrid_rmsle`` to keep semantics identical to the existing
    eval path. Picks the dim-valid entry with the **smallest weighted
    RMSLE** (matches what ``score_submission`` would surface).
    """
    if not submission:
        return None
    from mirrorlab.eval.dimensional import match_dim
    from mirrorlab.runners.sprint1_demo import (
        _grids_with_ground_truth,
        _per_subgrid_rmsle,
    )
    try:
        grids = _grids_with_ground_truth(scenario)
    except Exception:
        return None
    target_dim = scenario.dim_signature["outputs"]["F"]
    best: tuple[float, float, float] | None = None
    best_score = float("inf")
    for entry in submission:
        try:
            if not match_dim(entry, target_dim):
                continue
            pg = _per_subgrid_rmsle(entry, grids)
        except Exception:
            continue
        if not all(k in pg for k in ("a", "b", "c")):
            continue
        w = SUBGRID_WEIGHTS
        agg = w["a"] * pg["a"] + w["b"] * pg["b"] + w["c"] * pg["c"]
        if agg < best_score:
            best_score = agg
            best = (float(pg["a"]), float(pg["b"]), float(pg["c"]))
    return best


def _mock_llm_call(messages: Sequence[Mapping[str, Any]], tools: Any) -> Mapping[str, Any]:
    """Default no-op LLM caller for mock-mode record collection.

    Returns an assistant message with no tool calls and no content, which
    drives ``LLMAgent`` into its parse-error → stub-fallback branch. The
    resulting submission is what the rule-based stub would emit, but
    routed through ``LLMAgent.run`` so the integration is exercised end
    to end. Replace with a real client once pilot data is ready.
    """
    return {"role": "assistant", "content": "", "tool_calls": []}


def collect_llm_records(
    pairs: Sequence[tuple[str, str]],
    seeds: Sequence[int],
    *,
    agent: Any | None = None,
    magnitude: float | None = None,
) -> list[ScenarioRMSLE]:
    """Run ``LLMAgent`` across ``(domain, shift) × seeds`` and emit records.

    Mock-default: if ``agent`` is ``None`` we build ``LLMAgent`` with
    ``llm_call=_mock_llm_call`` and ``fallback_to_stub=True``. No real
    API is called; the run completes via stub-fallback. Pass a configured
    ``LLMAgent`` to use a real (or test-bound) LLM caller.

    Domains whose loader is not wired are skipped silently — same policy
    as ``collect_stub_records``.
    """
    from mirrorlab.runners.llm_agent import LLMAgent
    from mirrorlab.scenarios.loader import load

    if agent is None:
        agent = LLMAgent(llm_call=_mock_llm_call, fallback_to_stub=True)

    records: list[ScenarioRMSLE] = []
    for domain_id, shift_id in pairs:
        for seed in seeds:
            try:
                kwargs: dict[str, Any] = {"seed": seed}
                if magnitude is not None:
                    kwargs["counterfactual_magnitude"] = magnitude
                scenario = load(domain_id, shift_id, **kwargs)
            except Exception:
                continue
            try:
                submission = agent.run(scenario)
            except Exception:
                continue
            triple = _submission_to_rmsle_triple(submission, scenario)
            if triple is None:
                continue
            ra, rb, rc = triple
            records.append(
                ScenarioRMSLE(
                    domain_id=domain_id,
                    shift_id=shift_id,
                    seed=seed,
                    tier=_tier_of(shift_id),
                    rmsle_a=ra,
                    rmsle_b=rb,
                    rmsle_c=rc,
                )
            )
    return records


def collect_stub_records(
    pairs: Sequence[tuple[str, str]],
    seeds: Sequence[int],
    *,
    magnitude: float | None = None,
    runner: Callable[..., Mapping[str, float]] | None = None,
) -> list[ScenarioRMSLE]:
    """Run the rule-based stub across ``(domain, shift) × seeds`` and emit records.

    ``runner`` defaults to ``mirrorlab.runners.sprint1_demo.run_demo`` and
    must return a mapping with ``"per_subgrid_rmsle"`` ⊇ {"a","b","c"}. The
    ``magnitude`` arg is only honored by the default Hooke loader path —
    other domains' loaders are wired by task #2 (``prompt-generalizer``).
    Records for domains whose loader is unwired are skipped silently so
    Sprint-3 stub sweeps can run before #2 completes.
    """
    if runner is None:
        from mirrorlab.runners.sprint1_demo import run_demo as runner  # type: ignore

    records: list[ScenarioRMSLE] = []
    for domain_id, shift_id in pairs:
        for seed in seeds:
            try:
                kwargs: dict[str, Any] = {"seed": seed}
                if magnitude is not None:
                    kwargs["counterfactual_magnitude"] = magnitude
                try:
                    result = runner(domain_id, shift_id, **kwargs)
                except TypeError:
                    # runner does not accept counterfactual_magnitude — fall back
                    result = runner(domain_id, shift_id, seed=seed)
            except Exception:
                continue
            pg = result.get("per_subgrid_rmsle", {})
            if not all(k in pg for k in ("a", "b", "c")):
                continue
            records.append(
                ScenarioRMSLE(
                    domain_id=domain_id,
                    shift_id=shift_id,
                    seed=seed,
                    tier=_tier_of(shift_id),
                    rmsle_a=float(pg["a"]),
                    rmsle_b=float(pg["b"]),
                    rmsle_c=float(pg["c"]),
                )
            )
    return records


# ---------------------------------------------------------------------------
# CAL-4 — score temperature τ
# ---------------------------------------------------------------------------


def sweep_cal4_tau(
    records: Sequence[ScenarioRMSLE],
    *,
    taus: Sequence[float] | None = None,
    target_delta: float = 0.5,
    baseline_floor: float = 0.90,
    weights: Mapping[str, float] = SUBGRID_WEIGHTS,
) -> SweepResult:
    """Sweep τ; recommend the smallest τ s.t. Δ(baseline − shift) ≥ target_delta
    while ``mean s_entry`` on baseline stays ≥ ``baseline_floor``.

    Sprint 1 finding (``docs/sprint1-report.md`` §3.1): τ=0.5 saturates
    discrimination — baseline scores 1.0 trivially but γ-1-1 scores can't
    drop below ≈0.6 even at strong η. Tightening τ lifts the gap. The lower
    bound on τ is set by the baseline-floor constraint: too small a τ and
    baseline scenarios with numerical noise fall below 0.9.
    """
    if taus is None:
        taus = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.75, 1.0]

    by_tier = _group_by_tier(records)
    base_recs = by_tier.get("baseline", [])
    shift_recs = by_tier.get("gamma", []) + by_tier.get("delta", [])

    points: list[SweepPoint] = []
    for tau in taus:
        s_base = [r.s_entry(tau=tau, weights=weights) for r in base_recs]
        s_shift = [r.s_entry(tau=tau, weights=weights) for r in shift_recs]
        m_base = float(np.mean(s_base)) if s_base else 0.0
        m_shift = float(np.mean(s_shift)) if s_shift else 0.0
        points.append(
            SweepPoint(
                knob=float(tau),
                metrics={
                    "mean_s_baseline": m_base,
                    "mean_s_shift": m_shift,
                    "delta": m_base - m_shift,
                    "n_baseline": float(len(s_base)),
                    "n_shift": float(len(s_shift)),
                },
            )
        )

    have_both_tiers = bool(base_recs) and bool(shift_recs)
    feasible = [
        p for p in points
        if have_both_tiers
        and p.metrics["mean_s_baseline"] >= baseline_floor
        and p.metrics["delta"] >= target_delta
    ]
    if feasible:
        # Among feasible τ, prefer the *largest* (least aggressive tightening
        # that still meets the gap target) — keeps headroom for noisier real
        # LLMs. Honest rationale.
        chosen = max(feasible, key=lambda p: p.knob)
        rationale = (
            f"τ={chosen.knob:.3f} is the largest swept τ where baseline mean "
            f"s_entry ≥ {baseline_floor:.2f} and Δ ≥ {target_delta:.2f} "
            f"(mean_base={chosen.metrics['mean_s_baseline']:.3f}, "
            f"mean_shift={chosen.metrics['mean_s_shift']:.3f})."
        )
        defer = False
    else:
        # No feasible τ — either records are too sparse, or the floor / target
        # are mutually exclusive on this data. Defer to Sprint 4 with the
        # closest-fit τ.
        if shift_recs and base_recs:
            chosen = max(points, key=lambda p: p.metrics["delta"])
            rationale = (
                f"No τ in the swept range satisfies both Δ ≥ {target_delta:.2f} "
                f"and baseline floor ≥ {baseline_floor:.2f}; best gap is "
                f"Δ={chosen.metrics['delta']:.3f} at τ={chosen.knob:.3f}. "
                f"Recommend deferring CAL-4 to Sprint 4 real-LLM data."
            )
        else:
            chosen = SweepPoint(knob=TAU_DEFAULT, metrics={})
            rationale = (
                "Insufficient tier coverage in records "
                f"(baseline={len(base_recs)}, shift={len(shift_recs)}). "
                "Retain CAL-4 default τ=0.5 pending more data."
            )
        defer = True

    return SweepResult(
        knob_name="CAL-4 τ (score temperature)",
        points=points,
        recommended=chosen.knob,
        rationale=rationale,
        defer_to_sprint4=defer,
        metadata={"target_delta": target_delta, "baseline_floor": baseline_floor},
    )


# ---------------------------------------------------------------------------
# CAL-1 — sub-grid shares (π_a, π_b, π_c)
# ---------------------------------------------------------------------------


def _default_share_candidates() -> list[tuple[float, float, float]]:
    cands = []
    for a in (0.2, 0.3, 0.4, 0.5, 0.6):
        for b in (0.2, 0.3, 0.4, 0.5):
            c = round(1.0 - a - b, 3)
            if 0.05 <= c <= 0.5:
                cands.append((a, b, c))
    return cands


def sweep_cal1_shares(
    records: Sequence[ScenarioRMSLE],
    *,
    candidates: Sequence[tuple[float, float, float]] | None = None,
    tau: float = TAU_DEFAULT,
    target_ood_detectability: float = 0.15,
) -> SweepResult:
    """Sweep (π_a, π_b, π_c); recommend a share triple where the shift-tier
    score is detectably below baseline, with non-trivial weight on each
    sub-grid (no single sub-grid dominates).

    "OOD detectability" here = baseline − shift gap in ``mean s_entry`` after
    applying the candidate share weights. We additionally require all three
    π values to be ≥ 0.10 so no sub-grid is effectively disabled.
    """
    if candidates is None:
        candidates = _default_share_candidates()

    by_tier = _group_by_tier(records)
    base_recs = by_tier.get("baseline", [])
    shift_recs = by_tier.get("gamma", []) + by_tier.get("delta", [])

    points: list[SweepPoint] = []
    for (a, b, c) in candidates:
        w = {"a": a, "b": b, "c": c}
        s_base = [r.s_entry(tau=tau, weights=w) for r in base_recs]
        s_shift = [r.s_entry(tau=tau, weights=w) for r in shift_recs]
        m_base = float(np.mean(s_base)) if s_base else 0.0
        m_shift = float(np.mean(s_shift)) if s_shift else 0.0
        # Penalize share triples where any π < 0.10
        balance_ok = min(a, b, c) >= 0.10
        points.append(
            SweepPoint(
                knob=(round(a, 3), round(b, 3), round(c, 3)),
                metrics={
                    "mean_s_baseline": m_base,
                    "mean_s_shift": m_shift,
                    "gap": m_base - m_shift,
                    "balance_ok": float(balance_ok),
                },
            )
        )

    feasible = [
        p for p in points
        if p.metrics["balance_ok"] >= 1.0
        and p.metrics["gap"] >= target_ood_detectability
    ]
    if feasible and shift_recs and base_recs:
        # Recommend the balanced triple closest to the current spec default
        # (0.40, 0.40, 0.20) that meets the target — minimises spec churn
        # while honoring the data.
        default = (0.40, 0.40, 0.20)
        chosen = min(
            feasible,
            key=lambda p: sum((p.knob[i] - default[i]) ** 2 for i in range(3)),
        )
        rationale = (
            f"Triple {chosen.knob} meets target OOD-detectability gap "
            f"(gap={chosen.metrics['gap']:.3f} ≥ {target_ood_detectability:.2f}) "
            f"and is the balanced candidate closest to the spec default."
        )
        defer = False
    else:
        chosen = SweepPoint(knob=(0.40, 0.40, 0.20), metrics={})
        rationale = (
            "No share triple in the swept grid meets the OOD-detectability "
            "target on stub data; retain spec default (0.40, 0.40, 0.20). "
            "Re-sweep with Sprint-3 LLM scores once #3 lands."
        )
        defer = True

    return SweepResult(
        knob_name="CAL-1 sub-grid shares (π_a, π_b, π_c)",
        points=points,
        recommended=chosen.knob,
        rationale=rationale,
        defer_to_sprint4=defer,
        metadata={"target_ood_detectability": target_ood_detectability, "tau": tau},
    )


# ---------------------------------------------------------------------------
# CAL-3 — counterfactual perturbation magnitude
# ---------------------------------------------------------------------------


def sweep_cal3_magnitude(
    record_factory: Callable[[float], Sequence[ScenarioRMSLE]],
    *,
    magnitudes: Sequence[float] | None = None,
    target_attacker_drop: float = 0.20,
    tau: float = TAU_DEFAULT,
    weights: Mapping[str, float] = SUBGRID_WEIGHTS,
) -> SweepResult:
    """Sweep the CF perturbation magnitude.

    ``record_factory(m)`` must return per-scenario records under CF magnitude
    ``m``. The sweep reports, per magnitude, the **counterfactual-only**
    contribution to the stub-agent score drop on shift-tier scenarios — i.e.
    how much the (c) sub-grid alone is doing to depress curve-fit attackers.
    Recommended magnitude is the smallest ``m`` whose drop ≥ ``target``;
    larger ``m`` is not better (spec §10: "small enough that the *correct*
    law transports, large enough that fitted constants don't").
    """
    if magnitudes is None:
        magnitudes = [0.10, 0.20, 0.30, 0.40, 0.50]

    points: list[SweepPoint] = []
    for m in magnitudes:
        recs = list(record_factory(float(m)))
        by_tier = _group_by_tier(recs)
        shift_recs = by_tier.get("gamma", []) + by_tier.get("delta", [])
        if not shift_recs:
            points.append(
                SweepPoint(knob=float(m), metrics={"drop_c_only": 0.0, "n_shift": 0.0})
            )
            continue
        # Drop attributable to (c) alone: compare s_entry with full weights
        # vs s_entry with c weight zeroed out (re-normalize a,b).
        full_w = dict(weights)
        no_c = {"a": weights.get("a", 0.0), "b": weights.get("b", 0.0), "c": 0.0}
        drops = []
        for r in shift_recs:
            s_full = r.s_entry(tau=tau, weights=full_w)
            s_noc = r.s_entry(tau=tau, weights=no_c)
            drops.append(s_noc - s_full)  # positive when (c) hurts curve-fit
        points.append(
            SweepPoint(
                knob=float(m),
                metrics={
                    "drop_c_only": float(np.mean(drops)),
                    "drop_c_max": float(np.max(drops)),
                    "n_shift": float(len(shift_recs)),
                },
            )
        )

    feasible = [p for p in points if p.metrics["drop_c_only"] >= target_attacker_drop]
    if feasible:
        chosen = min(feasible, key=lambda p: p.knob)
        rationale = (
            f"Magnitude={chosen.knob:.2f} is the smallest swept value whose "
            f"(c)-only contribution to the attacker score drop reaches "
            f"{target_attacker_drop:.2f} (observed {chosen.metrics['drop_c_only']:.3f})."
        )
        defer = False
    else:
        if points:
            chosen = max(points, key=lambda p: p.metrics["drop_c_only"])
            rationale = (
                f"No magnitude in {list(magnitudes)} reaches the "
                f"{target_attacker_drop:.2f} drop target on stub data; "
                f"best={chosen.metrics['drop_c_only']:.3f} at m={chosen.knob:.2f}. "
                "Either the curve-fit stub already transports under (c) — in "
                "which case keep default ±30% and re-test with LLM agents — "
                "or per-cell magnitude widening is warranted "
                "(see fluid/γ-10-1 cell-level note in docs/sprint3-calibration.md)."
            )
        else:
            chosen = SweepPoint(knob=0.30, metrics={})
            rationale = "No records produced; retain default 0.30."
        defer = True

    return SweepResult(
        knob_name="CAL-3 counterfactual magnitude",
        points=points,
        recommended=chosen.knob,
        rationale=rationale,
        defer_to_sprint4=defer,
        metadata={"target_attacker_drop": target_attacker_drop},
    )


# ---------------------------------------------------------------------------
# CAL-9 — lookup-attacker pass threshold
# ---------------------------------------------------------------------------


def sweep_cal9_threshold(
    attacker_scores: Sequence[float],
    legit_scores: Sequence[float] | None = None,
    *,
    candidates: Sequence[float] | None = None,
) -> SweepResult:
    """Sweep the attacker pass threshold.

    Goal (spec §8.1): demonstrate ``S_bench^lookup(γ ∪ δ) < threshold``.
    With attacker scores alone the sweep reports the **pass rate** at each
    threshold; if ``legit_scores`` are supplied (the strongest legit model's
    scores on the same cells) we additionally report the separation margin.

    Honest rule: recommend a threshold only when attacker scores
    *unambiguously* cluster below some value with a clear gap to legit. If
    the distributions overlap the recommendation defers — moving CAL-9 to
    paper our way around an ambiguous result hides the signal.
    """
    if candidates is None:
        candidates = [0.30, 0.40, 0.45, 0.50, 0.55, 0.60]

    a = np.asarray(list(attacker_scores), dtype=float)
    points: list[SweepPoint] = []
    for t in candidates:
        pass_rate = float(np.mean(a < t)) if a.size else 0.0
        m = {"attacker_pass_rate": pass_rate}
        if legit_scores is not None and len(legit_scores):
            l = np.asarray(list(legit_scores), dtype=float)
            m["legit_pass_rate"] = float(np.mean(l < t))
            m["margin"] = float(np.mean(l) - np.mean(a))
        points.append(SweepPoint(knob=float(t), metrics=m))

    if not a.size:
        return SweepResult(
            knob_name="CAL-9 attacker pass threshold",
            points=points,
            recommended=0.50,
            rationale="No attacker scores available; retain spec default 0.50.",
            defer_to_sprint4=True,
        )

    attacker_max = float(np.max(a))
    if legit_scores is not None and len(legit_scores):
        legit_min = float(np.min(legit_scores))
        gap = legit_min - attacker_max
        if gap > 0.05:
            chosen = 0.5 * (attacker_max + legit_min)
            return SweepResult(
                knob_name="CAL-9 attacker pass threshold",
                points=points,
                recommended=round(chosen, 3),
                rationale=(
                    f"Attacker scores max at {attacker_max:.3f}; legit min "
                    f"{legit_min:.3f}; clean gap of {gap:.3f}. Recommend "
                    f"midpoint {chosen:.3f}."
                ),
            )
        return SweepResult(
            knob_name="CAL-9 attacker pass threshold",
            points=points,
            recommended=0.50,
            rationale=(
                f"Attacker / legit distributions overlap "
                f"(attacker_max={attacker_max:.3f}, legit_min={legit_min:.3f}). "
                "Retain spec default 0.50; do not redefine the gate around "
                "ambiguous data."
            ),
            defer_to_sprint4=True,
        )
    return SweepResult(
        knob_name="CAL-9 attacker pass threshold",
        points=points,
        recommended=0.50,
        rationale=(
            f"Attacker-only sweep: pass rate at 0.50 = "
            f"{float(np.mean(a < 0.50)):.3f}. Retain spec default 0.50 until "
            "legit-model scores from #6 land."
        ),
        defer_to_sprint4=True,
    )


# ---------------------------------------------------------------------------
# CAL-10 — per-cell seed count
# ---------------------------------------------------------------------------


def sweep_cal10_seeds(
    records: Sequence[ScenarioRMSLE],
    *,
    max_seeds: int = 10,
    target_se: float = 0.05,
    tau: float = TAU_DEFAULT,
    weights: Mapping[str, float] = SUBGRID_WEIGHTS,
) -> SweepResult:
    """Sweep per-cell seed count; recommend the smallest ``n`` whose
    estimated standard error of the cell mean is ≤ ``target_se``.

    Standard-error model: SE(n) = std(per-seed s_entry) / √n, where the std
    is pooled across cells. This is the textbook estimator; it assumes seed
    draws are exchangeable inside a cell, which is true by construction.
    """
    # Group records by cell = (domain, shift)
    by_cell: dict[tuple[str, str], list[float]] = {}
    for r in records:
        s = r.s_entry(tau=tau, weights=weights)
        by_cell.setdefault((r.domain_id, r.shift_id), []).append(s)

    if not by_cell:
        return SweepResult(
            knob_name="CAL-10 per-cell seed count",
            points=[],
            recommended=3,
            rationale="No records; retain spec default n=3.",
            defer_to_sprint4=True,
        )

    # Pooled within-cell std (use ddof=1 only when a cell has >1 seed)
    stds = []
    for vs in by_cell.values():
        if len(vs) > 1:
            stds.append(float(np.std(vs, ddof=1)))
    pooled_std = float(np.mean(stds)) if stds else 0.0

    points: list[SweepPoint] = []
    for n in range(1, max_seeds + 1):
        se = pooled_std / math.sqrt(n) if n > 0 else float("inf")
        points.append(SweepPoint(knob=int(n), metrics={"pooled_std": pooled_std, "se": se}))

    feasible = [p for p in points if p.metrics["se"] <= target_se]
    if feasible:
        chosen = min(feasible, key=lambda p: p.knob)
        rationale = (
            f"n={chosen.knob} reaches the target SE ≤ {target_se:.3f} "
            f"(pooled within-cell std = {pooled_std:.3f}, "
            f"SE = {chosen.metrics['se']:.3f})."
        )
        defer = False
    else:
        chosen = SweepPoint(knob=max_seeds, metrics={"se": pooled_std / math.sqrt(max_seeds)})
        rationale = (
            f"Even n={max_seeds} does not reach SE ≤ {target_se:.3f} "
            f"(pooled std = {pooled_std:.3f}); cell-level variance dominates. "
            "Either tighten upstream noise sources or accept the wider CI."
        )
        defer = True

    return SweepResult(
        knob_name="CAL-10 per-cell seed count",
        points=points,
        recommended=chosen.knob,
        rationale=rationale,
        defer_to_sprint4=defer,
        metadata={"target_se": target_se, "pooled_std": pooled_std},
    )
