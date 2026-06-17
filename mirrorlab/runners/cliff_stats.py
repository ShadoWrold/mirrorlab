"""Aggregate the multi-seed cliff sweep into per-(model, tier) mean ± CI.

Reads docs/sprint4-sweep-data-final.json (4 models × 12 cells × N seeds)
and reports, per model and tier, the mean S_scen across cells×seeds plus a
bootstrap 95% confidence interval. This is the statistical backing for the
cliff claim: a γ-tier mean whose CI sits well below the baseline CI is a
significant drop, not seed noise.

Usage:
    python3 -m mirrorlab.runners.cliff_stats
    python3 -m mirrorlab.runners.cliff_stats --json docs/sprint4-sweep-data-final.json

No LLM calls. Bootstrap is seeded deterministically so the CI is reproducible.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = ROOT / "docs" / "sprint4-sweep-data-final.json"

MODELS = [
    "gpt-5.5",
    "gpt-5.4-20260305",
    "gemini-3.1-pro-preview",
    "claude-opus-4.8",
]
MODEL_SHORT = {
    "gpt-5.5": "GPT-5.5",
    "gpt-5.4-20260305": "GPT-5.4",
    "gemini-3.1-pro-preview": "Gemini-3.1-Pro",
    "claude-opus-4.8": "Opus-4.8",
}
TIERS = ["baseline", "gamma", "delta"]
TIER_LABEL = {"baseline": "baseline", "gamma": "γ-shift", "delta": "δ-shift"}


def _bootstrap_ci(
    samples: Sequence[float],
    *,
    n_boot: int = 2000,
    alpha: float = 0.05,
    rng_seed: int = 12345,
) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean. Returns (lo, hi).

    Seeded with a fixed rng so the reported interval is reproducible.
    """
    n = len(samples)
    if n == 0:
        return (float("nan"), float("nan"))
    if n == 1:
        return (samples[0], samples[0])
    rng = random.Random(rng_seed)
    means = []
    for _ in range(n_boot):
        resample = [rng.choice(samples) for _ in range(n)]
        means.append(sum(resample) / n)
    means.sort()
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[int((1 - alpha / 2) * n_boot)]
    return (lo, hi)


def _collect(entries: list[dict]) -> dict[tuple[str, str], list[float]]:
    """{(model, tier): [s_scen over all cells × seeds]}. FAIL → 0.0."""
    bucket: dict[tuple[str, str], list[float]] = defaultdict(list)
    for e in entries:
        m, tier = e["model"], e["tier"]
        if m not in MODELS:
            continue
        s = e.get("s_scen")
        bucket[(m, tier)].append(float(s) if s is not None else 0.0)
    return bucket


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default=str(DEFAULT_JSON))
    ap.add_argument("--n-boot", type=int, default=2000)
    args = ap.parse_args(list(argv) if argv is not None else None)

    blob = json.loads(Path(args.json).read_text())
    entries = blob["entries"]
    bucket = _collect(entries)

    # seed inventory
    seeds = sorted({e["seed"] for e in entries if e["model"] in MODELS})
    n_per_cell = len(seeds)

    print(f"Multi-seed cliff stats  ({args.json})")
    print(f"seeds = {seeds}  ({n_per_cell} per cell)\n")
    hdr = f"{'model':<16}" + "".join(f"{TIER_LABEL[t]:>22}" for t in TIERS)
    print(hdr)
    print("-" * len(hdr))
    for m in MODELS:
        row = f"{MODEL_SHORT[m]:<16}"
        for t in TIERS:
            xs = bucket.get((m, t), [])
            if not xs:
                row += f"{'—':>22}"
                continue
            mean = statistics.fmean(xs)
            lo, hi = _bootstrap_ci(xs, n_boot=args.n_boot)
            row += f"{f'{mean:.3f} [{lo:.2f},{hi:.2f}]':>22}"
        print(row)

    # cliff drop per model: baseline mean − gamma mean, with the gamma CI
    print("\nCliff drop (baseline mean → γ mean):")
    for m in MODELS:
        b = bucket.get((m, "baseline"), [])
        g = bucket.get((m, "gamma"), [])
        if not b or not g:
            continue
        bm, gm = statistics.fmean(b), statistics.fmean(g)
        glo, ghi = _bootstrap_ci(g, n_boot=args.n_boot)
        sig = "significant" if ghi < bm else "overlaps baseline"
        print(f"  {MODEL_SHORT[m]:<16} {bm:.3f} → {gm:.3f}  "
              f"(γ CI [{glo:.2f},{ghi:.2f}], drop {bm-gm:+.3f}, {sig})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
