"""Sprint 2 catalog smoke runner.

Iterates every ``(domain_id, shift_id)`` pair registered in
``mirrorlab.scenarios.registry.REGISTRY`` (12 baselines + 36 shifts = 48 pairs)
and verifies the Sprint-2 exit-criterion contract (spec §9.2):

  * registry factory builds without raising
  * ``sim.step(0.0)`` returns a finite numeric dict containing ``t``

In addition, for the subset of domains where the agent-facing
``scenarios.loader.load`` is wired (Sprint 1: ``hooke`` only), we also exercise
the full loader path — prompt + dim-signature + counterfactual sub-grid
construction. Loader failures are reported as discrepancies but do not gate
the exit criterion (which is the catalog→sim contract at the registry layer).

CLI:
    python -m mirrorlab.runners.sprint2_smoke
    python -m mirrorlab.runners.sprint2_smoke --seed 7 --quiet
"""

from __future__ import annotations

import argparse
import math
import sys
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from mirrorlab.scenarios import loader
from mirrorlab.scenarios.registry import REGISTRY, make as registry_make

_LOADER_DOMAINS = {"hooke"}  # rest of the loader wiring lands in Sprint 3


@dataclass
class PairResult:
    domain: str
    shift: str
    registry_status: str        # "PASS" / "FAIL"
    registry_reason: str = ""
    loader_status: str = "SKIP"  # "PASS" / "FAIL" / "SKIP"
    loader_reason: str = ""

    @property
    def exit_passes(self) -> bool:
        """Sprint-2 exit-criterion gate (§9.2) — registry layer only."""
        return self.registry_status == "PASS"


def _is_finite_numeric_dict(obs: Any) -> Tuple[bool, str]:
    if not isinstance(obs, dict):
        return False, f"step() returned {type(obs).__name__}, expected dict"
    if "t" not in obs:
        return False, "step() output missing 't' key"
    for k, v in obs.items():
        try:
            fv = float(v)
        except (TypeError, ValueError):
            return False, f"observable {k!r}={v!r} not numeric"
        if not math.isfinite(fv):
            return False, f"observable {k!r}={fv} is not finite"
    return True, ""


def _short_exc(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def _run_pair(domain: str, shift: str, seed: int) -> PairResult:
    # --- registry layer (exit criterion) ---
    try:
        sim = registry_make(domain, shift, seed=seed)
        obs = sim.step(0.0)
    except Exception as exc:  # noqa: BLE001 — smoke runner catches all
        return PairResult(
            domain=domain, shift=shift,
            registry_status="FAIL", registry_reason=_short_exc(exc),
        )
    ok, reason = _is_finite_numeric_dict(obs)
    if not ok:
        return PairResult(
            domain=domain, shift=shift,
            registry_status="FAIL", registry_reason=reason,
        )
    result = PairResult(domain=domain, shift=shift, registry_status="PASS")
    # --- loader layer (diagnostic, non-gating) ---
    if domain in _LOADER_DOMAINS:
        try:
            scen = loader.load(domain, shift, seed=seed)
            lobs = scen.sim.step(0.0)
        except Exception as exc:  # noqa: BLE001
            result.loader_status = "FAIL"
            result.loader_reason = _short_exc(exc)
            return result
        ok, reason = _is_finite_numeric_dict(lobs)
        if not ok:
            result.loader_status = "FAIL"
            result.loader_reason = reason
        else:
            result.loader_status = "PASS"
    return result


def run(seed: int = 0) -> List[PairResult]:
    """Iterate every registry pair; return per-pair results."""
    pairs = sorted(REGISTRY.keys())
    return [_run_pair(d, s, seed) for d, s in pairs]


def summarize(results: List[PairResult]) -> Dict[str, Any]:
    n = len(results)
    n_reg_pass = sum(1 for r in results if r.registry_status == "PASS")
    n_reg_fail = n - n_reg_pass
    n_baseline = sum(1 for r in results if r.shift == "baseline")
    n_shifts = n - n_baseline
    n_load_total = sum(1 for r in results if r.loader_status != "SKIP")
    n_load_pass = sum(1 for r in results if r.loader_status == "PASS")
    n_load_fail = sum(1 for r in results if r.loader_status == "FAIL")
    return {
        "total": n,
        "baselines": n_baseline,
        "shifts": n_shifts,
        "registry_pass": n_reg_pass,
        "registry_fail": n_reg_fail,
        "loader_total": n_load_total,
        "loader_pass": n_load_pass,
        "loader_fail": n_load_fail,
        "exit_pass": n_reg_fail == 0,
    }


def format_report(results: List[PairResult], summary: Dict[str, Any]) -> str:
    lines = ["Sprint 2 catalog smoke run", "=" * 60]
    for r in results:
        if r.loader_status == "SKIP":
            tag = "  -"
        else:
            tag = "  " + ("L" if r.loader_status == "PASS" else "x")
        line = f"[{r.registry_status}]{tag} {r.domain:<11} / {r.shift}"
        if r.registry_status == "FAIL":
            line += f"  -- registry: {r.registry_reason}"
        elif r.loader_status == "FAIL":
            line += f"  -- loader: {r.loader_reason}"
        lines.append(line)
    lines.append("=" * 60)
    lines.append(
        f"Registry layer: PASS={summary['registry_pass']}/{summary['total']} "
        f"FAIL={summary['registry_fail']} "
        f"(baselines={summary['baselines']}, shifts={summary['shifts']})"
    )
    if summary["loader_total"]:
        lines.append(
            f"Loader layer:   PASS={summary['loader_pass']}/{summary['loader_total']} "
            f"FAIL={summary['loader_fail']} "
            "(diagnostic — non-gating; loader wired for hooke only in Sprint 2)"
        )
    lines.append(f"Exit criterion (§9.2): {'PASS' if summary['exit_pass'] else 'FAIL'}")
    lines.append("Legend: row tags — L=loader PASS, x=loader FAIL, -=loader not wired")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="sprint2_smoke")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--quiet", action="store_true",
                        help="suppress per-pair lines; print summary only")
    args = parser.parse_args(argv)
    results = run(seed=args.seed)
    summary = summarize(results)
    if args.quiet:
        print(
            f"registry={summary['registry_pass']}/{summary['total']} "
            f"loader={summary['loader_pass']}/{summary['loader_total']} "
            f"exit={'PASS' if summary['exit_pass'] else 'FAIL'}"
        )
    else:
        print(format_report(results, summary))
    return 0 if summary["exit_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
