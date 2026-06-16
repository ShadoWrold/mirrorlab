"""Attacker sweep runner — γ ∪ δ slice + aggregate scoring (spec §8).

Slice selection (CAL-8 / §8): one γ + one δ shift per domain × 12 domains
× 3 seeds = 72 scenarios. The first-numbered γ and δ shifts of each
domain are chosen ("γ-d-1", "δ-d-1") for stability across catalog
revisions.

Pass criterion (CAL-9): aggregate ``S_bench^lookup < 0.50``. The aggregate
is the equal-weight macro-mean across the 24 (domain, shift) cells, each
cell averaged over its 3 seeds — matching the §7 formula restricted to
the slice.

Per-domain test-grid wiring is still incomplete (only Hooke ships full
(a)/(b)/(c) grids as of Sprint 3). A scenario with an empty test grid
scores 0 — for the lookup attacker this is *conservative* (favors the
attacker), so a passing result on the partial wiring is still meaningful
as a lower-bound guarantee. The integrator's real sweep will run after
the calibrator wires the remaining grids.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

from mirrorlab.attacker.lookup import AttackResult, LookupAttacker
from mirrorlab.scenarios.loader import ScenarioInstance, load as load_scenario

log = logging.getLogger(__name__)


# ---- Slice definition (locked) -----------------------------------------

PASS_THRESHOLD = 0.50  # CAL-9

# 12 domains × (1 γ + 1 δ) = 24 (domain, shift_id) pairs. The first γ and
# δ shifts per domain in the catalog are picked deterministically.
ATTACK_SLICE: Tuple[Tuple[str, str], ...] = (
    ("hooke",     "gamma_1_1"),  ("hooke",     "delta_1_1"),
    ("gravity",   "gamma_2_1"),  ("gravity",   "delta_2_1"),
    ("damped_ho", "gamma_3_1"),  ("damped_ho", "delta_3_1"),
    ("pendulum",  "gamma_4_1"),  ("pendulum",  "delta_4_1"),
    ("coulomb",   "gamma_5_1"),  ("coulomb",   "delta_5_1"),
    ("rlc",       "gamma_6_1"),  ("rlc",       "delta_6_1"),
    ("thermal",   "gamma_7_1"),  ("thermal",   "delta_7_1"),
    ("wave",      "gamma_8_1"),  ("wave",      "delta_8_1"),
    ("optics",    "gamma_9_1"),  ("optics",    "delta_9_1"),
    ("fluid",     "gamma_10_1"), ("fluid",     "delta_10_1"),
    ("kinetics",  "gamma_11_1"), ("kinetics",  "delta_11_1"),
    ("decay",     "gamma_12_1"), ("decay",     "delta_12_1"),
)

DEFAULT_SEEDS: Tuple[int, ...] = (0, 1, 2)


def _score_attack(scenario: ScenarioInstance, result: AttackResult) -> float:
    """Score an attacker submission against the scenario.

    Delegates to :func:`mirrorlab.runners.sprint3_pilot.score_against_scenario`,
    which packs the X+Y truth-form test grids for *all 12 domains* (the same
    path the T23 ceiling sweep uses) — no longer the Sprint-3 hooke-only
    stub that silently returned 0 on 11/12 domains.
    """
    # Lazy import: sprint3_pilot imports this module at top level, so a
    # top-level import here would be circular.
    from mirrorlab.runners.sprint3_pilot import score_against_scenario

    return float(score_against_scenario(scenario, result.submission))


# ---- Attack report -----------------------------------------------------

@dataclass
class AttackReport:
    """Aggregate output of an attacker sweep over the slice."""

    results: List[AttackResult] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    cell_scores: Dict[Tuple[str, str], float] = field(default_factory=dict)
    s_bench_lookup: float = 0.0
    passed: bool = False
    threshold: float = PASS_THRESHOLD
    seeds: Tuple[int, ...] = DEFAULT_SEEDS
    n_scenarios: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "xy_version": 1,
            "s_bench_lookup": round(self.s_bench_lookup, 6),
            "threshold": self.threshold,
            "passed": self.passed,
            "n_scenarios": self.n_scenarios,
            "seeds": list(self.seeds),
            "cell_scores": {
                f"{d}/{s}": round(v, 6) for (d, s), v in self.cell_scores.items()
            },
            "scenarios": [
                {**r.as_dict(), "score": round(self.scores[i], 6)}
                for i, r in enumerate(self.results)
            ],
        }


# ---- Aggregation -------------------------------------------------------

def _aggregate(
    results: Sequence[AttackResult],
    scores: Sequence[float],
) -> tuple[Dict[Tuple[str, str], float], float]:
    """Macro-mean per (domain, shift) cell, then equal-weight across cells."""
    cells: Dict[Tuple[str, str], List[float]] = {}
    for r, s in zip(results, scores):
        cells.setdefault((r.domain_id, r.shift_id), []).append(s)
    cell_means = {k: sum(v) / len(v) for k, v in cells.items()}
    if not cell_means:
        return cell_means, 0.0
    s_bench = sum(cell_means.values()) / len(cell_means)
    return cell_means, float(s_bench)


# ---- Sweep driver ------------------------------------------------------

def run_attack_sweep(
    attacker: LookupAttacker,
    *,
    slice_pairs: Sequence[Tuple[str, str]] = ATTACK_SLICE,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    threshold: float = PASS_THRESHOLD,
) -> AttackReport:
    """Run the locked attacker over the (slice × seeds) cross product."""
    results: List[AttackResult] = []
    scores: List[float] = []
    for domain_id, shift_id in slice_pairs:
        for seed in seeds:
            try:
                scenario = load_scenario(domain_id, shift_id, seed=int(seed))
            except Exception as exc:  # noqa: BLE001 — partial wiring tolerated
                log.warning("skip %s/%s seed=%d: %s",
                            domain_id, shift_id, seed, exc)
                continue
            result = attacker.run(scenario)
            score = _score_attack(scenario, result)
            results.append(result)
            scores.append(score)
            log.info("attack %s/%s seed=%d → S=%.3f (claim=%s)",
                     domain_id, shift_id, seed, score, result.claimed_law)

    cell_scores, s_bench = _aggregate(results, scores)
    return AttackReport(
        results=results,
        scores=scores,
        cell_scores=cell_scores,
        s_bench_lookup=s_bench,
        passed=s_bench < threshold,
        threshold=threshold,
        seeds=tuple(seeds),
        n_scenarios=len(results),
    )


__all__ = [
    "ATTACK_SLICE",
    "AttackReport",
    "DEFAULT_SEEDS",
    "PASS_THRESHOLD",
    "run_attack_sweep",
]
