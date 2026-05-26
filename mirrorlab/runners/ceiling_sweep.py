"""Sweep the ceiling oracle across all 48 (domain, shift) pairs.

Usage:
    python -m mirrorlab.runners.ceiling_sweep --out docs/ceiling-data.json [--seed 0]

For each (domain, shift) cell the script:
  1. Loads the scenario via :func:`mirrorlab.scenarios.loader.load`.
  2. Runs :class:`CeilingAgent` (zero LLM calls).
  3. Computes ``S_scen`` via the same path used by the LLM pilot
     (``score_against_scenario``), so the ceiling number is directly
     comparable to LLM honest scores.
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
import time
from typing import Any, Dict, List

from mirrorlab.runners.ceiling_agent import CeilingAgent, broken_symmetry_for
from mirrorlab.runners.sprint3_pilot import score_against_scenario
from mirrorlab.scenarios.loader import load as load_scenario

log = logging.getLogger(__name__)


# 12 domains × 4 shifts (baseline + γ-x-1 + γ-x-2 + δ-x-1) = 48 pairs.
DOMAINS = [
    "hooke", "gravity", "damped_ho", "pendulum", "coulomb", "rlc",
    "thermal", "wave", "optics", "fluid", "kinetics", "decay",
]


def all_pairs() -> List[tuple[str, str]]:
    pairs: List[tuple[str, str]] = []
    for i, dom in enumerate(DOMAINS, start=1):
        pairs.append((dom, "baseline"))
        pairs.append((dom, f"gamma_{i}_1"))
        pairs.append((dom, f"gamma_{i}_2"))
        pairs.append((dom, f"delta_{i}_1"))
    return pairs


def run_sweep(seed: int = 0) -> Dict[str, Any]:
    agent = CeilingAgent()
    rows: List[Dict[str, Any]] = []
    pairs = all_pairs()
    t0 = time.monotonic()
    for domain_id, shift_id in pairs:
        sym = broken_symmetry_for(domain_id, shift_id)
        try:
            scenario = load_scenario(domain_id, shift_id, seed=seed)
            submission = agent.run(scenario)
            s_scen = score_against_scenario(
                scenario, submission, gt_symmetry=sym,
            )
            err = None
        except Exception as exc:  # noqa: BLE001
            s_scen = 0.0
            err = f"{type(exc).__name__}: {exc}"
            log.warning("ceiling crash %s/%s: %s", domain_id, shift_id, err)
        rows.append({
            "domain_id": domain_id,
            "shift_id": shift_id,
            "seed": seed,
            "s_scen": float(s_scen),
            "claim_broken_symmetry": sym,
            "error": err,
        })
    elapsed = time.monotonic() - t0
    scores = [r["s_scen"] for r in rows]
    summary = {
        "n_pairs": len(rows),
        "mean": float(statistics.fmean(scores)) if scores else 0.0,
        "median": float(statistics.median(scores)) if scores else 0.0,
        "stdev": float(statistics.pstdev(scores)) if len(scores) > 1 else 0.0,
        "q25": _quantile(scores, 0.25),
        "q75": _quantile(scores, 0.75),
        "min": min(scores) if scores else 0.0,
        "max": max(scores) if scores else 0.0,
        "above_0_7": sum(1 for s in scores if s >= 0.7),
        "below_0_5": sum(1 for s in scores if s < 0.5),
        "elapsed_s": round(elapsed, 3),
    }
    return {"summary": summary, "rows": rows, "seed": seed}


def _quantile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    n = len(xs)
    idx = q * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return float(xs[lo] * (1.0 - frac) + xs[hi] * frac)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="output JSON path")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    report = run_sweep(seed=args.seed)
    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=2)
    s = report["summary"]
    print(
        f"ceiling sweep: n={s['n_pairs']} median={s['median']:.3f} "
        f"mean={s['mean']:.3f} ≥0.7:{s['above_0_7']} <0.5:{s['below_0_5']} "
        f"({s['elapsed_s']:.1f}s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
