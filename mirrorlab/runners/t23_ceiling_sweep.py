"""T23: full ceiling + stub sweep over 48 cells × 3 seeds.

Per docs/blueprint-xy.md §5 (DAG T23) and §7.1 (R1+R3). Produces a fresh
docs/ceiling-data.json with ``"xy_version": 1`` header. Pre-XY ceiling
data lives at docs/archive/pre-xy/ceiling-data.json.

Columns recorded per (domain, shift, seed):
    s_scen_ceiling   truth-form ceiling submission
    s_scen_stub      agent_stub baseline-form submission
    spread           ceiling - stub
    error            None on success, exception repr on failure
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from mirrorlab.runners.ceiling_agent import build_submission as ceiling_submission
from mirrorlab.runners.sprint3_pilot import score_against_scenario
from mirrorlab.scenarios.agent_stub import run as stub_submission
from mirrorlab.scenarios.loader import load


_DOMAINS = [
    "hooke",
    "gravity",
    "damped_ho",
    "pendulum",
    "coulomb",
    "rlc",
    "thermal",
    "wave",
    "optics",
    "fluid",
    "kinetics",
    "decay",
]

_SHIFTS_BY_DOMAIN = {
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


@dataclass
class _Row:
    domain_id: str
    shift_id: str
    seed: int
    s_scen_ceiling: float
    s_scen_stub: float
    spread: float
    error: str | None


def _iter_cells(domains: Iterable[str], seeds: Iterable[int]):
    for dom in domains:
        for shift in _SHIFTS_BY_DOMAIN[dom]:
            for seed in seeds:
                yield dom, shift, seed


def _run_cell(dom: str, shift: str, seed: int) -> _Row:
    try:
        sc = load(dom, shift, seed=seed)
        ceil = float(score_against_scenario(sc, ceiling_submission(sc)))
        stub = float(score_against_scenario(sc, [stub_submission(sc)]))
        return _Row(dom, shift, seed, ceil, stub, ceil - stub, None)
    except Exception as exc:  # surface, don't crash whole sweep
        return _Row(dom, shift, seed, math.nan, math.nan, math.nan, repr(exc))


def _summarize(rows: list[_Row]) -> dict:
    ceils = [r.s_scen_ceiling for r in rows if not math.isnan(r.s_scen_ceiling)]
    stubs = [r.s_scen_stub for r in rows if not math.isnan(r.s_scen_stub)]
    spreads = [r.spread for r in rows if not math.isnan(r.spread)]
    errors = [r for r in rows if r.error is not None]

    by_cell_ceil: dict[tuple[str, str], list[float]] = {}
    for r in rows:
        if math.isnan(r.s_scen_ceiling):
            continue
        by_cell_ceil.setdefault((r.domain_id, r.shift_id), []).append(r.s_scen_ceiling)
    medians = [statistics.median(v) for v in by_cell_ceil.values()]
    worst = [(k, min(v)) for k, v in by_cell_ceil.items()]
    worst_below_07 = sorted([w for w in worst if w[1] < 0.70], key=lambda x: x[1])

    return {
        "n_rows": len(rows),
        "n_errors": len(errors),
        "n_cells": len(by_cell_ceil),
        "ceiling_overall_median": statistics.median(medians) if medians else None,
        "ceiling_mean": statistics.fmean(ceils) if ceils else None,
        "stub_mean": statistics.fmean(stubs) if stubs else None,
        "spread_mean": statistics.fmean(spreads) if spreads else None,
        "spread_median": statistics.median(spreads) if spreads else None,
        "worst_cells_below_0_7": [[d, s, round(v, 4)] for ((d, s), v) in worst_below_07],
    }


def _write_json(out_path: Path, rows: list[_Row], summary: dict, elapsed_s: float) -> None:
    payload = {
        "xy_version": 1,
        "schema": "ceiling+stub per (domain,shift,seed)",
        "elapsed_s": round(elapsed_s, 3),
        "summary": summary,
        "rows": [
            {
                "domain_id": r.domain_id,
                "shift_id": r.shift_id,
                "seed": r.seed,
                "s_scen_ceiling": r.s_scen_ceiling if not math.isnan(r.s_scen_ceiling) else None,
                "s_scen_stub": r.s_scen_stub if not math.isnan(r.s_scen_stub) else None,
                "spread": r.spread if not math.isnan(r.spread) else None,
                "error": r.error,
            }
            for r in rows
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="0,1,2",
                        help="comma-separated seeds (default: 0,1,2)")
    parser.add_argument("--domains", default=",".join(_DOMAINS),
                        help="comma-separated domain subset")
    parser.add_argument("--out", default="docs/ceiling-data.json",
                        help="output JSON path")
    parser.add_argument("--quiet", action="store_true", help="suppress per-cell log")
    args = parser.parse_args(argv)

    seeds = tuple(int(s) for s in args.seeds.split(",") if s.strip())
    domains = tuple(d.strip() for d in args.domains.split(",") if d.strip())
    out_path = Path(args.out)

    rows: list[_Row] = []
    t0 = time.time()
    cells = list(_iter_cells(domains, seeds))
    for i, (dom, shift, seed) in enumerate(cells, 1):
        t_cell = time.time()
        row = _run_cell(dom, shift, seed)
        rows.append(row)
        if not args.quiet:
            tag = "OK" if row.error is None else "ERR"
            extra = f" err={row.error}" if row.error else ""
            print(f"[{i:3d}/{len(cells)}] {dom}/{shift} seed={seed} "
                  f"ceil={row.s_scen_ceiling:.4f} stub={row.s_scen_stub:.4f} "
                  f"spread={row.spread:+.4f} {tag} ({time.time()-t_cell:.2f}s){extra}",
                  flush=True)
    elapsed = time.time() - t0

    summary = _summarize(rows)
    _write_json(out_path, rows, summary, elapsed)

    print(
        f"\nT23 sweep done in {elapsed:.1f}s — "
        f"{summary['n_rows']} rows, {summary['n_cells']} cells, "
        f"{summary['n_errors']} errors. "
        f"ceiling_overall_median={summary['ceiling_overall_median']}. "
        f"Wrote {out_path}.",
        flush=True,
    )
    if summary["worst_cells_below_0_7"]:
        print("WARN: cells with min ceiling < 0.70:")
        for d, s, v in summary["worst_cells_below_0_7"]:
            print(f"   {d}/{s}: min={v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
