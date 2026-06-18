"""Calibrate the scoring temperature τ (CAL-4).

s_entry = exp(−R̄/τ). τ too large → mild errors still score high → textbook
"lookup" submissions pass on real breaks (soft cells). τ too small → even
the oracle and correct baselines get punished. We sweep τ and report, for
each value, the separation between three populations:

  * oracle (ceiling agent, knows the true law)        — should stay HIGH
  * baseline-tier stub (textbook law, correct there)  — should stay HIGH
  * shift-tier stub (textbook law, WRONG on the break) — should be LOW

The best τ maximizes (oracle − shift_stub) and (baseline_stub − shift_stub)
while keeping oracle and baseline_stub above a floor. Zero LLM: re-scores
the deterministic ceiling/stub submissions at each τ.

Usage:
    python3 -m mirrorlab.calibration.tau_sweep
"""

from __future__ import annotations

import argparse
import statistics
from typing import Sequence

from mirrorlab.eval.numeric import evaluate_entry
from mirrorlab.runners.ceiling_agent import build_submission as ceiling_submission
from mirrorlab.runners.sprint3_pilot import pack_grids
from mirrorlab.scenarios.agent_stub import run as stub_submission
from mirrorlab.scenarios.loader import load

_DOMAINS = [
    "hooke", "gravity", "damped_ho", "pendulum", "coulomb", "rlc",
    "thermal", "wave", "optics", "fluid", "kinetics", "decay",
]
_SHIFTS = {
    "hooke":     ("baseline", "gamma_1_1", "gamma_1_2", "delta_1_1"),
    "gravity":   ("baseline", "gamma_2_1", "gamma_2_2", "delta_2_1"),
    "damped_ho": ("baseline", "gamma_3_1", "gamma_3_2", "delta_3_1"),
    "pendulum":  ("baseline", "gamma_4_1", "gamma_4_2", "delta_4_1"),
    "coulomb":   ("baseline", "gamma_5_1", "gamma_5_2", "delta_5_1"),
    "rlc":       ("baseline", "gamma_6_1", "gamma_6_2", "delta_6_1"),
    "thermal":   ("baseline", "gamma_7_1", "gamma_7_2", "delta_7_1"),
    "wave":      ("baseline", "gamma_8_1", "gamma_8_2", "delta_8_1"),
    "optics":    ("baseline", "gamma_9_1", "gamma_9_2", "delta_9_1"),
    "fluid":     ("baseline", "gamma_10_1", "gamma_10_2", "delta_10_1"),
    "kinetics":  ("baseline", "gamma_11_1", "gamma_11_2", "delta_11_1"),
    "decay":     ("baseline", "gamma_12_1", "gamma_12_2", "delta_12_1"),
}


def _score(entry, packed, tau, canonical):
    if not packed:
        return 0.0
    return float(evaluate_entry(entry, packed, tau=tau, canonical_inputs=canonical))


def _collect(seeds: Sequence[int]):
    """Return per-(cell) cached (packed, canonical, ceiling_entry, stub_entry,
    is_baseline) so the τ sweep only re-runs the cheap scoring step."""
    rows = []
    for dom in _DOMAINS:
        for sh in _SHIFTS[dom]:
            for seed in seeds:
                sc = load(dom, sh, seed=seed)
                packed = pack_grids(sc)
                canonical = list((sc.dim_signature.get("inputs") or {}).keys())
                ceil = ceiling_submission(sc)
                stub = [stub_submission(sc)]
                rows.append({
                    "dom": dom, "sh": sh, "seed": seed,
                    "packed": packed, "canonical": canonical,
                    "ceil": ceil[0] if ceil else None,
                    "stub": stub[0] if stub else None,
                    "is_baseline": sh == "baseline",
                })
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--taus", default="0.10,0.15,0.20,0.25,0.30,0.35,0.50")
    args = ap.parse_args(list(argv) if argv is not None else None)
    seeds = tuple(int(s) for s in args.seeds.split(",") if s.strip())
    taus = [float(t) for t in args.taus.split(",") if t.strip()]

    print(f"Collecting cells (seeds={seeds})...")
    rows = _collect(seeds)
    print(f"  {len(rows)} cell-seeds cached.\n")

    print(f"{'τ':>6} | {'oracle':>8} {'base_stub':>10} {'shift_stub':>11} "
          f"| {'sep(or-sh)':>11} {'sep(ba-sh)':>11}")
    print("-" * 72)
    best = None
    for tau in taus:
        oracle, base_stub, shift_stub = [], [], []
        for r in rows:
            if r["ceil"] is not None:
                oracle.append(_score(r["ceil"], r["packed"], tau, r["canonical"]))
            if r["stub"] is not None:
                s = _score(r["stub"], r["packed"], tau, r["canonical"])
                (base_stub if r["is_baseline"] else shift_stub).append(s)
        o = statistics.mean(oracle)
        bs = statistics.mean(base_stub)
        ss = statistics.mean(shift_stub)
        sep_os = o - ss
        sep_bs = bs - ss
        # objective: large separation, but keep oracle + baseline_stub usable
        ok = o >= 0.85 and bs >= 0.70
        score = (sep_os + sep_bs) if ok else -1
        flag = "" if ok else "  (oracle/base too low)"
        if best is None or score > best[1]:
            best = (tau, score)
        print(f"{tau:>6.2f} | {o:>8.3f} {bs:>10.3f} {ss:>11.3f} "
              f"| {sep_os:>11.3f} {sep_bs:>11.3f}{flag}")
    print("-" * 72)
    print(f"Best τ (max separation, oracle≥0.85 & base_stub≥0.70): {best[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
