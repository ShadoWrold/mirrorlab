"""Cost analysis for budget-as-instrument measurement sweeps.

Turns a sweep JSON (``mirrorlab.runners.sprint4_sweep`` output) into the cost
tables of the budget-measurement design (docs Process §6): the budget stops
being a constraint and becomes a *measure* — how much it costs to discover a
law, and which (model, cell) pairs cannot do it at any affordable budget.

Cost definition
---------------
We measure **cost-to-submit**: the number of tool calls (and wall seconds) the
agent spent before it submitted. The agent submits once and is scored once, so
"cost-to-correct" coincides with cost-to-submit *when the submission is
correct*, and is undefined otherwise — there is no mid-run "became correct"
event to time. A run is therefore one of:

- **solved**    : submitted AND scored at/above the solve threshold → its cost
                  is the observed cost-to-submit (an exact event time).
- **censored**  : saturated a ceiling, or submitted-but-wrong, or errored → we
                  only know the true cost-to-solve is *greater than* the budget
                  spent (right-censored); we never observed a solve.

Right-censoring is the crux (design §6.7): naively averaging cost over solved
runs only, while dropping the censored ones, underestimates difficulty via
survivorship bias. So every cost statistic is reported **with its solve rate**,
and the budget–discovery curve (table D) is a Kaplan–Meier-style estimator that
treats censored runs correctly.

Tables
------
- B : per-cell cost profile (median cost over SOLVED runs, IQR, solve rate,
      saturation rate, cheapest-model cost = an internal-difficulty lower bound)
- C : tier / domain cost aggregation (the "cost cliff")
- D : budget–discovery survival curve (fraction solved at cost ≤ b), the
      censoring-correct headline figure, emitted as a numeric table
- E : score × cost four-quadrant counts (cheap-right / dear-right /
      cheap-wrong / dear-wrong) — the structure the score axis alone hides
- H : saturation / impossibility frontier (which (cell, model) never solved)

Run::

    python -m mirrorlab.reports.cost_analysis docs/sprint4-full-sweep.json
    python -m mirrorlab.reports.cost_analysis <sweep.json> --cost wall --csv out/
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

# A submission scoring at/above this is "solved" for cost purposes. The bench
# headline metric is continuous S_scen; for cost-to-solve we need a binary
# success event, and a high bar avoids crediting a barely-better-than-baseline
# fit as a discovery.
SOLVE_THRESHOLD = 0.80


@dataclass(frozen=True)
class Run:
    """One (model, cell, seed) run, normalized for cost analysis."""

    model: str
    domain_id: str
    shift_id: str
    tier: str
    seed: int
    ok: bool
    s_scen: Optional[float]
    cost_calls: int
    cost_wall: float
    terminated_by: str
    saturated: bool
    s_single: Optional[float] = None

    @property
    def _solve_score(self) -> Optional[float]:
        """Score used for the solve decision. Prefer the single-submission
        score (exhaustion-proof primary metric); fall back to s_scen / best-of-k
        for sweeps that predate the dual metric."""
        return self.s_single if self.s_single is not None else self.s_scen

    @property
    def solved(self) -> bool:
        s = self._solve_score
        return bool(self.ok and s is not None and s >= SOLVE_THRESHOLD)

    @property
    def cell(self) -> Tuple[str, str]:
        return (self.domain_id, self.shift_id)

    def cost(self, axis: str) -> float:
        return float(self.cost_calls if axis == "calls" else self.cost_wall)


def _derive_saturated(entry: Dict[str, Any]) -> bool:
    """Use the explicit field when present (new sweeps); else fall back to the
    termination reason (old sweeps predating the saturated field)."""
    if "saturated" in entry:
        return bool(entry["saturated"])
    return str(entry.get("terminated_by", "")) in ("budget", "wall")


def load_runs(path: str) -> Tuple[List[Run], Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        blob = json.load(fh)
    meta = blob.get("meta", {}) if isinstance(blob, dict) else {}
    entries = blob.get("entries", blob) if isinstance(blob, dict) else blob
    runs: List[Run] = []
    for e in entries:
        runs.append(Run(
            model=e["model"],
            domain_id=e["domain_id"],
            shift_id=e["shift_id"],
            tier=e.get("tier", _tier_of(e["shift_id"])),
            seed=int(e.get("seed", 0)),
            ok=bool(e.get("ok", False)),
            s_scen=(None if e.get("s_scen") is None else float(e["s_scen"])),
            cost_calls=int(e.get("n_tool_calls", 0)),
            cost_wall=float(e.get("elapsed_s", 0.0)),
            terminated_by=str(e.get("terminated_by", "unknown")),
            saturated=_derive_saturated(e),
            s_single=(None if e.get("s_single") is None else float(e["s_single"])),
        ))
    return runs, meta


def _tier_of(shift: str) -> str:
    if shift == "baseline":
        return "baseline"
    return "gamma" if shift.startswith("gamma") else "delta"


# ---- helpers ----------------------------------------------------------------

def _median(xs: Sequence[float]) -> Optional[float]:
    return statistics.median(xs) if xs else None


def _iqr(xs: Sequence[float]) -> Optional[Tuple[float, float]]:
    if len(xs) < 2:
        return None
    q = statistics.quantiles(sorted(xs), n=4)
    return (q[0], q[2])  # 25th, 75th


def _fmt(x: Optional[float], nd: int = 1) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


# ---- Table B: per-cell cost profile -----------------------------------------

def table_b(runs: List[Run], axis: str) -> List[Dict[str, Any]]:
    by_cell: Dict[Tuple[str, str], List[Run]] = defaultdict(list)
    for r in runs:
        by_cell[r.cell].append(r)
    rows: List[Dict[str, Any]] = []
    for cell, rs in sorted(by_cell.items()):
        solved = [r for r in rs if r.solved]
        solved_costs = [r.cost(axis) for r in solved]
        # Cheapest-model lower bound: the minimum cost-to-solve across models —
        # an internal-difficulty floor (best case any model achieved). None if
        # nobody solved it.
        cheapest = min(solved_costs) if solved_costs else None
        iqr = _iqr(solved_costs)
        rows.append({
            "domain": cell[0],
            "shift": cell[1],
            "tier": rs[0].tier,
            "n": len(rs),
            "solve_rate": sum(r.solved for r in rs) / len(rs),
            "sat_rate": sum(r.saturated for r in rs) / len(rs),
            "median_cost_solved": _median(solved_costs),
            "iqr": iqr,
            "cheapest_solved": cheapest,
        })
    return rows


# ---- Table C: tier / domain aggregation (cost cliff) ------------------------

def table_c(runs: List[Run], axis: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for key_fn, label in ((lambda r: r.tier, "tier"),):
        groups: Dict[str, List[Run]] = defaultdict(list)
        for r in runs:
            groups[key_fn(r)].append(r)
        for g, rs in sorted(groups.items()):
            solved_costs = [r.cost(axis) for r in rs if r.solved]
            out[g] = {
                "n": len(rs),
                "solve_rate": sum(r.solved for r in rs) / len(rs),
                "sat_rate": sum(r.saturated for r in rs) / len(rs),
                "median_cost_solved": _median(solved_costs),
            }
    return out


# ---- Table D: budget–discovery survival curve -------------------------------

def table_d(runs: List[Run], axis: str,
            n_steps: int = 20) -> List[Tuple[float, float]]:
    """Fraction of runs solved at cost ≤ b, swept over budget b.

    This is the empirical CDF of cost-to-solve where censored runs (never
    solved within their ceiling) correctly count as "not solved at any b" —
    they pull the curve's ceiling below 1.0. That is the Kaplan–Meier-correct
    way to read difficulty: the asymptote is the overall solve rate, and the
    rise shows how cheaply solves accrue. Denominator is ALL runs (solved +
    censored), never just solved — that is what avoids survivorship bias.
    """
    n_total = len(runs)
    if n_total == 0:
        return []
    max_cost = max((r.cost(axis) for r in runs), default=0.0)
    if max_cost <= 0:
        return [(0.0, 0.0)]
    curve: List[Tuple[float, float]] = []
    for i in range(1, n_steps + 1):
        b = max_cost * i / n_steps
        solved_by_b = sum(1 for r in runs if r.solved and r.cost(axis) <= b)
        curve.append((b, solved_by_b / n_total))
    return curve


# ---- Table E: score × cost four quadrants -----------------------------------

def table_e(runs: List[Run], axis: str) -> Dict[str, int]:
    """Split runs into cheap/dear × right/wrong. The cost median over ALL runs
    is the cheap|dear divider; solved is the right|wrong divider. The two
    'dear' quadrants are what a fixed budget conflates into a single 0 — dear-
    right (hard but doable, mis-scored as failure under a tight cap) vs dear-
    wrong (genuinely could not)."""
    costs = [r.cost(axis) for r in runs]
    if not costs:
        return {}
    divider = statistics.median(costs)
    q = {"cheap_right": 0, "dear_right": 0, "cheap_wrong": 0, "dear_wrong": 0}
    for r in runs:
        dear = r.cost(axis) > divider
        right = r.solved
        key = f"{'dear' if dear else 'cheap'}_{'right' if right else 'wrong'}"
        q[key] += 1
    return q


# ---- Table H: saturation / impossibility frontier ---------------------------

def table_h(runs: List[Run]) -> List[Dict[str, Any]]:
    """(model, cell) pairs that NEVER solved across seeds — the impossibility
    frontier 'for this model at this ceiling' (not absolute). Sorted by how
    saturated they were (fully-saturated = strongest could-not-do-it signal)."""
    by_pair: Dict[Tuple[str, str, str], List[Run]] = defaultdict(list)
    for r in runs:
        by_pair[(r.model, r.domain_id, r.shift_id)].append(r)
    rows: List[Dict[str, Any]] = []
    for (model, dom, shift), rs in by_pair.items():
        if any(r.solved for r in rs):
            continue
        rows.append({
            "model": model,
            "domain": dom,
            "shift": shift,
            "tier": rs[0].tier,
            "n": len(rs),
            "sat_rate": sum(r.saturated for r in rs) / len(rs),
        })
    rows.sort(key=lambda d: (-d["sat_rate"], d["domain"], d["shift"], d["model"]))
    return rows


# ---- Rendering --------------------------------------------------------------

def render_report(runs: List[Run], meta: Dict[str, Any], axis: str) -> str:
    unit = "tool calls" if axis == "calls" else "wall seconds"
    mode = meta.get("budget_mode", "unknown")
    cap = meta.get("max_tool_calls" if axis == "calls" else "max_wall_seconds")
    L: List[str] = []
    L.append(f"# Cost analysis ({unit})\n")
    L.append(f"runs={len(runs)}  budget_mode={mode}  ceiling={cap}  "
             f"solve_threshold={SOLVE_THRESHOLD}")
    if mode != "measurement":
        L.append("\n[!] budget_mode != measurement: costs are truncated at a "
                 "CONSTRAINT ceiling, so saturated runs understate true "
                 "cost-to-solve. Read solve/saturation rates, not absolute "
                 "cost. Re-run with --measurement for clean cost data.")
    overall_solve = sum(r.solved for r in runs) / len(runs) if runs else 0.0
    overall_sat = sum(r.saturated for r in runs) / len(runs) if runs else 0.0
    L.append(f"\noverall solve_rate={overall_solve:.3f}  "
             f"saturation_rate={overall_sat:.3f}\n")

    # Table C — cliff
    L.append("\n## C. Tier cost aggregation (the cost cliff)\n")
    L.append(f"{'tier':<10} {'n':>4} {'solve%':>7} {'sat%':>6} "
             f"{'med cost(solved)':>16}")
    L.append("-" * 48)
    for tier, d in table_c(runs, axis).items():
        L.append(f"{tier:<10} {d['n']:>4} {d['solve_rate']*100:>6.0f}% "
                 f"{d['sat_rate']*100:>5.0f}% {_fmt(d['median_cost_solved']):>16}")

    # Table D — survival curve
    L.append("\n## D. Budget–discovery curve (fraction solved at cost ≤ b)\n")
    L.append("  censoring-correct: denominator is ALL runs; asymptote = solve rate\n")
    L.append(f"{'budget≤':>10} {'frac solved':>12}")
    L.append("-" * 24)
    for b, frac in table_d(runs, axis):
        L.append(f"{b:>10.1f} {frac:>12.3f}")

    # Table E — four quadrants
    L.append("\n## E. Score × cost quadrants (median-cost divider)\n")
    q = table_e(runs, axis)
    L.append(f"  cheap·right (easy)         : {q.get('cheap_right', 0)}")
    L.append(f"  dear·right  (hard but done): {q.get('dear_right', 0)}  "
             f"<- a tight cap would mis-score these as failures")
    L.append(f"  cheap·wrong (gave up early): {q.get('cheap_wrong', 0)}")
    L.append(f"  dear·wrong  (truly cannot) : {q.get('dear_wrong', 0)}")

    # Table B — per-cell (top of cost + lowest solve)
    L.append("\n## B. Per-cell cost profile (sorted by solve rate)\n")
    L.append(f"{'domain/shift':<26} {'tier':<9} {'solve%':>7} {'sat%':>6} "
             f"{'med':>7} {'cheapest':>9}")
    L.append("-" * 70)
    rows_b = sorted(table_b(runs, axis), key=lambda d: (d["solve_rate"], d["domain"]))
    for d in rows_b:
        name = f"{d['domain']}/{d['shift']}"
        L.append(f"{name:<26} {d['tier']:<9} {d['solve_rate']*100:>6.0f}% "
                 f"{d['sat_rate']*100:>5.0f}% {_fmt(d['median_cost_solved']):>7} "
                 f"{_fmt(d['cheapest_solved']):>9}")

    # Table H — impossibility frontier
    L.append("\n## H. Impossibility frontier (model×cell never solved)\n")
    rows_h = table_h(runs)
    if not rows_h:
        L.append("  (none — every model×cell solved at least one seed)")
    else:
        L.append(f"{'model':<22} {'domain/shift':<24} {'tier':<8} {'sat%':>6}")
        L.append("-" * 64)
        for d in rows_h[:40]:
            name = f"{d['domain']}/{d['shift']}"
            L.append(f"{d['model']:<22} {name:<24} {d['tier']:<8} "
                     f"{d['sat_rate']*100:>5.0f}%")
        if len(rows_h) > 40:
            L.append(f"  … and {len(rows_h) - 40} more")
    return "\n".join(L) + "\n"


def _write_csvs(runs: List[Run], axis: str, out_dir: str) -> None:
    import csv
    import os
    os.makedirs(out_dir, exist_ok=True)
    # B
    with open(os.path.join(out_dir, "table_b_cell_cost.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["domain", "shift", "tier", "n", "solve_rate", "sat_rate",
                    "median_cost_solved", "iqr_lo", "iqr_hi", "cheapest_solved"])
        for d in table_b(runs, axis):
            iqr = d["iqr"] or (None, None)
            w.writerow([d["domain"], d["shift"], d["tier"], d["n"],
                        round(d["solve_rate"], 4), round(d["sat_rate"], 4),
                        d["median_cost_solved"], iqr[0], iqr[1],
                        d["cheapest_solved"]])
    # D
    with open(os.path.join(out_dir, "table_d_survival.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["budget_le", "frac_solved"])
        for b, frac in table_d(runs, axis):
            w.writerow([round(b, 3), round(frac, 4)])
    # H
    with open(os.path.join(out_dir, "table_h_frontier.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "domain", "shift", "tier", "n", "sat_rate"])
        for d in table_h(runs):
            w.writerow([d["model"], d["domain"], d["shift"], d["tier"],
                        d["n"], round(d["sat_rate"], 4)])


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="cost_analysis")
    ap.add_argument("sweep_json", help="sprint4_sweep output JSON")
    ap.add_argument("--cost", choices=("calls", "wall"), default="calls",
                    help="cost axis: tool calls (default) or wall seconds")
    ap.add_argument("--csv", default=None,
                    help="also write table B/D/H CSVs into this directory")
    args = ap.parse_args(list(argv) if argv is not None else None)

    runs, meta = load_runs(args.sweep_json)
    if not runs:
        print("no runs in sweep file", file=sys.stderr)
        return 1
    print(render_report(runs, meta, args.cost))
    if args.csv:
        _write_csvs(runs, args.cost, args.csv)
        print(f"[csv written to {args.csv}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
