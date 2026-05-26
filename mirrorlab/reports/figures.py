"""Paper-1 figure renderer.

Reads:
- docs/sprint4-sweep-data-final.json   (5 models x 4 domains x 3 tiers = 60 runs)
- docs/ceiling-data.json               (48 ceiling pairs, full 12-domain)
- docs/sprint35-pilot-data.json        (attacker reference, s_bench_lookup = 0)

Writes 6 paper-grade figures into figures/ as 300dpi PNG + vector PDF.

Conventions: 3.5 inch single-column friendly, color-blind safe (Set2 for
discrete models, viridis for sequential heatmap), serif font, 300dpi.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
FIG_DIR = ROOT / "figures"

SWEEP_PATH = DOCS / "sprint4-sweep-data-final.json"
CEILING_PATH = DOCS / "ceiling-data.json"
ATTACKER_PATH = DOCS / "sprint35-pilot-data.json"

MODELS = [
    "claude-opus-4.6",
    "claude-sonnet-4.5",
    "gemini-3.1-pro-preview",
    "gpt-4.1-20250414",
    "gpt-5.4-20260305",
]
MODEL_SHORT = {
    "claude-opus-4.6": "Opus-4.6",
    "claude-sonnet-4.5": "Sonnet-4.5",
    "gemini-3.1-pro-preview": "Gemini-3.1-Pro",
    "gpt-4.1-20250414": "GPT-4.1",
    "gpt-5.4-20260305": "GPT-5.4",
}
TIERS = ["baseline", "gamma", "delta"]
TIER_LABEL = {"baseline": "Baseline", "gamma": "$\\gamma$-shift", "delta": "$\\delta$-shift"}
DOMAINS = ["hooke", "coulomb", "thermal", "decay"]
DOMAIN_LABEL = {"hooke": "Hooke", "coulomb": "Coulomb", "thermal": "Thermal", "decay": "Decay"}

# Set2-derived color-blind-safe palette, 5 distinct hues
MODEL_COLORS = {
    "claude-opus-4.6": "#66c2a5",
    "claude-sonnet-4.5": "#fc8d62",
    "gemini-3.1-pro-preview": "#8da0cb",
    "gpt-4.1-20250414": "#e78ac3",
    "gpt-5.4-20260305": "#a6d854",
}
MODEL_MARKERS = {
    "claude-opus-4.6": "o",
    "claude-sonnet-4.5": "s",
    "gemini-3.1-pro-preview": "D",
    "gpt-4.1-20250414": "v",
    "gpt-5.4-20260305": "^",
}

MAX_TOOL_CALLS = 30


def _s(r: dict) -> float:
    s = r.get("s_scen")
    return float(s) if s is not None else 0.0


def _set_style() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "legend.fontsize": 6.5,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.7,
        "lines.linewidth": 1.3,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def _load() -> tuple[dict, dict, dict]:
    sweep = json.loads(SWEEP_PATH.read_text())
    ceiling = json.loads(CEILING_PATH.read_text())
    attacker = json.loads(ATTACKER_PATH.read_text())
    return sweep, ceiling, attacker


def _save(fig: plt.Figure, name: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png", dpi=300)
    fig.savefig(FIG_DIR / f"{name}.pdf")
    plt.close(fig)


def _tier_means(sweep: dict) -> dict[str, dict[str, float]]:
    """{model: {tier: mean S_scen}} averaged over the 4 swept domains."""
    bucket: dict[tuple[str, str], list[float]] = defaultdict(list)
    for e in sweep["entries"]:
        s = e.get("s_scen")
        if s is None:
            continue
        bucket[(e["model"], e["tier"])].append(float(s))
    return {m: {t: (float(np.mean(bucket[(m, t)])) if bucket[(m, t)] else 0.0) for t in TIERS} for m in MODELS}


def _ceiling_tier_means(ceiling: dict) -> dict[str, float]:
    bucket: dict[str, list[float]] = defaultdict(list)
    for row in ceiling["rows"]:
        sh = row["shift_id"]
        tier = "baseline" if sh == "baseline" else ("gamma" if sh.startswith("gamma") else "delta")
        bucket[tier].append(row["s_scen"])
    return {t: float(np.mean(bucket[t])) for t in TIERS}


# ----- Figure 1: Cliff plot (HERO) ----------------------------------------- #


def fig_cliff(sweep: dict, ceiling: dict) -> dict[str, float]:
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    tier_means = _tier_means(sweep)
    ceiling_means = _ceiling_tier_means(ceiling)

    x = np.arange(len(TIERS))
    headline: dict[str, float] = {}

    for m in MODELS:
        ys = [tier_means[m][t] for t in TIERS]
        ax.plot(
            x, ys,
            marker=MODEL_MARKERS[m], color=MODEL_COLORS[m],
            label=MODEL_SHORT[m], markersize=4.5, markeredgewidth=0,
        )
        headline[f"{m}/baseline"] = tier_means[m]["baseline"]
        headline[f"{m}/gamma"] = tier_means[m]["gamma"]
        headline[f"{m}/delta"] = tier_means[m]["delta"]

    ceiling_ys = [ceiling_means[t] for t in TIERS]
    ax.plot(
        x, ceiling_ys, linestyle="--", color="#444444",
        linewidth=1.2, label="Ceiling (oracle)", marker="x", markersize=4.5,
    )

    ax.set_xticks(x)
    ax.set_xticklabels([TIER_LABEL[t] for t in TIERS])
    ax.set_ylabel(r"Mean $S_{\mathrm{scen}}$ (4 domains)")
    ax.set_ylim(-0.05, 1.15)
    ax.axhline(0.5, color="#aaaaaa", linewidth=0.5, linestyle=":")
    ax.set_title("Frontier LLMs cliff-drop on $\\gamma$/$\\delta$ shifts")
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, handlelength=1.6)

    _save(fig, "fig1_cliff")
    return headline


# ----- Figure 2: Per-domain heatmap (gamma tier) ---------------------------- #


def fig_heatmap(sweep: dict) -> None:
    M = np.full((len(DOMAINS), len(MODELS)), np.nan)
    for e in sweep["entries"]:
        if e["tier"] != "gamma":
            continue
        if e["domain_id"] in DOMAINS and e["model"] in MODELS:
            i = DOMAINS.index(e["domain_id"])
            j = MODELS.index(e["model"])
            M[i, j] = _s(e)

    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    im = ax.imshow(M, cmap="viridis", vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_xticks(np.arange(len(MODELS)))
    ax.set_xticklabels([MODEL_SHORT[m] for m in MODELS], rotation=30, ha="right")
    ax.set_yticks(np.arange(len(DOMAINS)))
    ax.set_yticklabels([DOMAIN_LABEL[d] for d in DOMAINS])
    for i in range(len(DOMAINS)):
        for j in range(len(MODELS)):
            v = M[i, j]
            if np.isnan(v):
                continue
            color = "white" if v < 0.5 else "black"
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    color=color, fontsize=6.5)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"$S_{\mathrm{scen}}$ on $\gamma$-shift")
    ax.set_title("Per-domain $\\gamma$-shift score (4 domains $\\times$ 5 models)")
    _save(fig, "fig2_heatmap_gamma")


# ----- Figure 3: Radar per model ------------------------------------------- #


def _model_radar_axes(sweep: dict, model: str) -> list[float]:
    rows = [e for e in sweep["entries"] if e["model"] == model]
    by_tier = defaultdict(list)
    for r in rows:
        by_tier[r["tier"]].append(r)

    def mean_s(tier: str) -> float:
        rs = by_tier.get(tier, [])
        return float(np.mean([_s(r) for r in rs])) if rs else 0.0

    in_domain = mean_s("baseline")
    ood = float(np.mean([_s(r) for r in rows if r["tier"] != "baseline"])) if rows else 0.0
    counterfactual = mean_s("gamma")
    # dim correctness proxy: fraction of runs that produced any submission with parse_errors == 0
    dim_correct = float(np.mean([
        1.0 if (r.get("submission_len", 0) > 0 and r.get("parse_errors", 0) == 0) else 0.0
        for r in rows
    ])) if rows else 0.0
    # bonus probe: fraction of shifted (gamma/delta) runs whose submission claims a non-trivial broken symmetry
    bonus_rows = [r for r in rows if r["tier"] != "baseline"]
    def claims_symmetry(r: dict) -> bool:
        for s in r.get("submission", []) or []:
            tag = (s.get("claim_broken_symmetry") or "").lower()
            if tag and tag not in {"none", "unsure", ""}:
                return True
        return False
    bonus = float(np.mean([1.0 if claims_symmetry(r) else 0.0 for r in bonus_rows])) if bonus_rows else 0.0
    # efficiency: 1 - mean(tool_calls / 30)
    efficiency = 1.0 - float(np.mean([r["n_tool_calls"] for r in rows])) / MAX_TOOL_CALLS if rows else 0.0
    efficiency = max(0.0, min(1.0, efficiency))
    return [in_domain, ood, counterfactual, dim_correct, bonus, efficiency]


def fig_radars(sweep: dict) -> None:
    axes_labels = [
        "In-dom S", "OOD S", "Counterfact S",
        "Dim. parse", "Bonus probe", "Efficiency",
    ]
    n = len(axes_labels)
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    theta_closed = np.concatenate([theta, theta[:1]])

    fig, axs = plt.subplots(1, 5, figsize=(8.2, 2.0), subplot_kw={"projection": "polar"})
    for ax, m in zip(axs, MODELS):
        vals = _model_radar_axes(sweep, m)
        vals_closed = vals + vals[:1]
        ax.plot(theta_closed, vals_closed, color=MODEL_COLORS[m], linewidth=1.2)
        ax.fill(theta_closed, vals_closed, color=MODEL_COLORS[m], alpha=0.25)
        ax.set_xticks(theta)
        ax.set_xticklabels(axes_labels, fontsize=5.5)
        ax.set_yticks([0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["", "0.5", "", "1.0"], fontsize=5.5)
        ax.set_ylim(0, 1.0)
        ax.set_title(MODEL_SHORT[m], fontsize=8, pad=8)
    fig.suptitle("Per-model competence profile (6 axes)", fontsize=9, y=1.03)
    _save(fig, "fig3_radars")


# ----- Figure 4: Attacker comparison bar ----------------------------------- #


def fig_attacker(sweep: dict, attacker: dict) -> None:
    tier_means = _tier_means(sweep)
    honest = [tier_means[m]["baseline"] for m in MODELS]  # in-domain honest S
    # Lookup attacker bench score is 0 across the board (verified in sprint3.5 pilot)
    attacker_s = [attacker["attacker"]["s_bench_lookup"]] * len(MODELS)

    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    x = np.arange(len(MODELS))
    w = 0.38
    ax.bar(x - w / 2, honest, width=w, color="#66c2a5", label="Honest (baseline tier)")
    ax.bar(x + w / 2, attacker_s, width=w, color="#fc8d62", label="Lookup attacker")
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT[m] for m in MODELS], rotation=30, ha="right")
    ax.set_ylabel(r"Mean $S_{\mathrm{scen}}$")
    ax.set_ylim(0, 1.05)
    ax.set_title("Honest run vs. lookup attacker")
    ax.legend(frameon=False, loc="upper left")
    _save(fig, "fig4_attacker")


# ----- Figure 5: Ceiling vs best-LLM scatter ------------------------------- #


def fig_ceiling_scatter(sweep: dict, ceiling: dict) -> None:
    ceiling_idx = {(r["domain_id"], r["shift_id"]): r["s_scen"] for r in ceiling["rows"]}
    # 12 cells = 4 domains x 3 tiers (baseline, gamma, delta), with shift_id from sweep
    sweep_cells: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for e in sweep["entries"]:
        sweep_cells[(e["domain_id"], e["shift_id"])][e["model"]] = _s(e)

    xs, ys, colors, labels = [], [], [], []
    tier_color = {"baseline": "#999999", "gamma": "#1b9e77", "delta": "#d95f02"}
    for (dom, sh), scores in sweep_cells.items():
        if (dom, sh) not in ceiling_idx:
            continue
        xs.append(ceiling_idx[(dom, sh)])
        ys.append(max(scores.values()))
        tier = "baseline" if sh == "baseline" else ("gamma" if sh.startswith("gamma") else "delta")
        colors.append(tier_color[tier])
        labels.append(f"{dom}/{sh}")

    fig, ax = plt.subplots(figsize=(3.5, 3.0))
    ax.plot([0, 1.15], [0, 1.15], color="#888888", linestyle="--", linewidth=0.8, label="y = x")
    for tier, c in tier_color.items():
        idx = [i for i, t in enumerate(labels) if (
            (tier == "baseline" and "baseline" in t) or
            (tier == "gamma" and "/gamma" in t) or
            (tier == "delta" and "/delta" in t)
        )]
        if not idx:
            continue
        ax.scatter([xs[i] for i in idx], [ys[i] for i in idx],
                   color=c, s=28, alpha=0.85, edgecolors="white", linewidths=0.6,
                   label=TIER_LABEL[tier])
    ax.set_xlim(0, 1.15)
    ax.set_ylim(-0.05, 1.15)
    ax.set_xlabel(r"Ceiling $S_{\mathrm{scen}}$")
    ax.set_ylabel(r"Best-of-5 LLM $S_{\mathrm{scen}}$")
    ax.set_title("Ceiling vs. best LLM (12 cells)")
    ax.legend(frameon=False, loc="lower right")
    _save(fig, "fig5_ceiling_scatter")


# ----- Figure 6: Tool-call efficiency curves ------------------------------- #


def fig_efficiency(sweep: dict) -> None:
    """Pareto-style: for each model, sort runs by tool-call cost and plot
    cumulative mean score as more tool-call budget is consumed."""
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    for m in MODELS:
        runs = [e for e in sweep["entries"] if e["model"] == m]
        runs.sort(key=lambda r: r["n_tool_calls"])
        if not runs:
            continue
        xs = np.array([r["n_tool_calls"] for r in runs], dtype=float)
        ys = np.array([_s(r) for r in runs], dtype=float)
        cum = np.cumsum(ys) / np.arange(1, len(ys) + 1)
        ax.plot(xs, cum, marker=MODEL_MARKERS[m], color=MODEL_COLORS[m],
                markersize=3.2, label=MODEL_SHORT[m], linewidth=1.0,
                markeredgewidth=0)
    ax.set_xlabel("Tool calls used (per run)")
    ax.set_ylabel(r"Cumulative mean $S_{\mathrm{scen}}$")
    ax.set_xlim(0, MAX_TOOL_CALLS + 1)
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Tool-call efficiency (cumulative)")
    ax.legend(frameon=False, loc="upper right", ncol=2)
    _save(fig, "fig6_efficiency")


# ----- Driver -------------------------------------------------------------- #


def render_all() -> dict[str, float]:
    _set_style()
    sweep, ceiling, attacker = _load()
    headline = fig_cliff(sweep, ceiling)
    fig_heatmap(sweep)
    fig_radars(sweep)
    fig_attacker(sweep, attacker)
    fig_ceiling_scatter(sweep, ceiling)
    fig_efficiency(sweep)
    return headline


if __name__ == "__main__":
    nums = render_all()
    print("Cliff plot headline (mean S_scen):")
    for m in MODELS:
        print(f"  {MODEL_SHORT[m]:16s}  baseline={nums[f'{m}/baseline']:.3f}  "
              f"gamma={nums[f'{m}/gamma']:.3f}  delta={nums[f'{m}/delta']:.3f}")
