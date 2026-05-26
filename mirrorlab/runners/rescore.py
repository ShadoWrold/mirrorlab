"""Re-score a cached sweep JSON without spending LLM tokens.

Sprint 4's first sweep (``docs/sprint4-sweep-data.json``) was driven through
a broken scoring path that returned 0.0 for every honest submission. Now
that :mod:`mirrorlab.eval.numeric` / :mod:`mirrorlab.eval.dimensional`
bind LLM-style inputs correctly, we replay the cached entries through the
fixed scorer to recover the true ``s_scen`` field — no provider calls.

Usage::

    python -m mirrorlab.runners.rescore \\
        --in  docs/sprint4-sweep-data.json \\
        --out docs/sprint4-sweep-data-rescored.json

Outputs:
  * an updated JSON with patched ``s_scen`` and a ``meta.rescored_at`` stamp,
  * a stderr summary of per-model mean ``S_scen`` (overall + by tier).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence

from mirrorlab.runners.ceiling_agent import broken_symmetry_for
from mirrorlab.runners.sprint3_pilot import score_against_scenario
from mirrorlab.scenarios.loader import load as load_scenario

log = logging.getLogger(__name__)


def rescore_entry(entry: Mapping[str, Any]) -> Optional[float]:
    """Return the recomputed S_scen, or ``None`` when the entry is unscoreable."""
    submission = entry.get("submission") or []
    if not submission:
        return 0.0
    domain_id = entry["domain_id"]
    shift_id = entry["shift_id"]
    seed = int(entry.get("seed", 0))
    try:
        scenario = load_scenario(domain_id, shift_id, seed=seed)
    except Exception as exc:  # noqa: BLE001
        log.warning("rescore: load_scenario(%s/%s) failed: %s", domain_id, shift_id, exc)
        return None
    gt_sym = broken_symmetry_for(domain_id, shift_id) if shift_id != "baseline" else "none"
    try:
        return float(score_against_scenario(scenario, submission, gt_symmetry=gt_sym))
    except Exception as exc:  # noqa: BLE001
        log.warning("rescore: score failed for %s/%s/%s: %s",
                    entry.get("model"), domain_id, shift_id, exc)
        return None


def rescore_blob(blob: Dict[str, Any]) -> Dict[str, Any]:
    out_entries: List[Dict[str, Any]] = []
    for e in blob.get("entries", []):
        new_e = dict(e)
        new_e["s_scen_old"] = e.get("s_scen")
        rescored = rescore_entry(e)
        new_e["s_scen"] = None if rescored is None else round(float(rescored), 6)
        out_entries.append(new_e)
    meta = dict(blob.get("meta", {}))
    meta["rescored_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    meta["rescore_tool"] = "mirrorlab.runners.rescore"
    return {"meta": meta, "entries": out_entries}


def per_model_summary(entries: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, float]]:
    by_model: Dict[str, Dict[str, List[float]]] = {}
    for e in entries:
        if not e.get("ok"):
            continue
        s = e.get("s_scen")
        if s is None:
            continue
        m = e["model"]
        tier = e.get("tier", "?")
        bucket = by_model.setdefault(m, {"overall": [], "baseline": [], "gamma": [], "delta": []})
        bucket["overall"].append(float(s))
        bucket.setdefault(tier, []).append(float(s))
    out: Dict[str, Dict[str, float]] = {}
    for m, buckets in by_model.items():
        out[m] = {k: (statistics.mean(v) if v else float("nan")) for k, v in buckets.items()}
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="mirrorlab.runners.rescore")
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--out", dest="out_path", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(message)s",
    )

    with open(args.in_path, "r", encoding="utf-8") as fh:
        blob = json.load(fh)

    out_blob = rescore_blob(blob)

    tmp = args.out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(out_blob, fh, indent=2, default=repr)
    os.replace(tmp, args.out_path)

    summary = per_model_summary(out_blob["entries"])
    print("=== rescored per-model mean S_scen ===", file=sys.stderr)
    print(f"  {'model':<28} overall  baseline  gamma   delta", file=sys.stderr)
    for m, buckets in sorted(summary.items()):
        def fmt(k: str) -> str:
            v = buckets.get(k, float("nan"))
            return "  nan " if v != v else f"{v:6.3f}"
        print(
            f"  {m:<28} {fmt('overall')}   {fmt('baseline')}  {fmt('gamma')}  {fmt('delta')}",
            file=sys.stderr,
        )
    print(f"\nwrote {args.out_path}", file=sys.stderr)
    return 0


__all__ = ["rescore_entry", "rescore_blob", "per_model_summary", "main"]


if __name__ == "__main__":
    sys.exit(main())
