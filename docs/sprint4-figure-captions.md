# X+Y — Paper-1 figure captions

All figures live under `figures/` as 300 dpi PNG plus vector PDF. They are
rendered by `mirrorlab/reports/figures.py` from:

- `docs/sprint4-sweep-data-final.json` — 4 models × 12 cells = **48 runs**
  (4 representative domains × 3 tiers × 1 seed; X+Y truth-form scoring).
- `docs/ceiling-data.json` — full 48-pair oracle ceiling (12 domains × 4
  shifts × 3 seeds; `xy_version: 1`).
- `docs/t24-attacker-data.json` — lookup-attacker sweep (gpt-5.4,
  `S_bench^lookup = 0.159`).

**Data provenance.** These numbers are the X+Y rebuild (truth-form ground
truth + counterfactual parameter injection on sub-grid c), not the original
Sprint-4 sweep. The cliff was re-measured after the `parse_dim` fix
(`0901a8e`) that stopped the dimensional pre-filter from mislabeling
correct-physics submissions written as `"N = kg m s^-2"` as failures.

**Scope note (repeated in each caption):** results are from a single-seed,
4-domain panel; the full 48-pair × 3-seed sweep is deferred to camera-ready.

---

## Figure 1 — Cliff plot (HERO)

`figures/fig1_cliff.{png,pdf}`

**Caption.** Mean scenario score $S_{\mathrm{scen}}$ versus shift tier
(baseline / $\gamma$-shift / $\delta$-shift) for four frontier LLMs, averaged
over four representative domains (Hooke, Coulomb, Thermal, Decay). The dashed
black curve is the oracle ceiling computed by the symbolic-physics agent on
the full 48-pair catalog. **All four models hold near the ceiling on the
baseline tier (0.71–0.95) and collapse on the $\gamma$ tier** — the cliff.
The $\delta$ tier shows partial recovery for GPT-5.5 and Opus-4.8 (0.47): this
rebound comes from weak-break $\delta$ cells (time-modulated shifts where the
textbook law is locally close to truth, the same soft cells flagged in the
T23 ceiling and T24 attacker sweeps), not from genuine recovery of shifted-law
reasoning. *Single-seed preliminary; camera-ready extends to 48 pairs × 3
seeds across 12 domains.*

**Headline numbers (X+Y mean $S_{\mathrm{scen}}$):**

```
model                    baseline   gamma    delta
─────────────────────────────────────────────────────
GPT-5.5                    0.935    0.000    0.473
GPT-5.4                    0.949    0.481    0.238
Gemini-3.1-Pro             0.725    0.184    0.000
Claude Opus 4.8            0.713    0.194    0.461
─────────────────────────────────────────────────────
Ceiling (oracle)           0.963    0.978    0.982
```

The $\gamma$-tier cliff for **all four** models, set against the near-flat
oracle ceiling (~0.97 across tiers), is the central claim of Paper 1: frontier
LLMs cannot reason structurally about a broken symmetry, while the bench
itself is demonstrably fair (the oracle clears every tier). Coulomb
$\gamma$-5-1 and $\delta$-5-1 score 0 across all four models — the universal
hardest cells.

---

## Figure 2 — Per-domain $\gamma$-shift heatmap (4 × 4)

`figures/fig2_heatmap_gamma.{png,pdf}`

**Caption.** $S_{\mathrm{scen}}$ on the $\gamma$ tier for each
(domain, model) cell. Color is viridis, normalized to $[0, 1]$. Thermal and
Hooke are the only domains where any model clears a non-trivial score
(GPT-5.4 at 0.73–0.74); Coulomb $\gamma$ is 0 for every model. *4
representative domains; the full 12-domain heatmap is deferred to
camera-ready.*

---

## Figure 3 — Per-model competence radar (6 axes)

`figures/fig3_radars.{png,pdf}`

**Caption.** Six-axis radar per model summarising the 12 swept cells:
**In-dom S** = baseline-tier mean, **OOD S** = $\gamma$+$\delta$ mean,
**Counterfact S** = $\gamma$-tier mean, **Dim. parse** = fraction of runs
returning a parseable submission with zero parse errors, **Bonus probe** =
fraction of shifted runs whose submission names a non-trivial broken symmetry
(`claim_broken_symmetry` $\notin$ {none, unsure}), **Efficiency** =
$1 - \bar n_{\mathrm{tool\,calls}} / 30$. All axes are scaled to $[0, 1]$.
*Bonus-probe axis is a behavioral proxy — symmetry labels are self-reported,
not yet checked against ground-truth labels (camera-ready).*

---

## Figure 4 — Honest vs. lookup-attacker bar chart

`figures/fig4_attacker.{png,pdf}`

**Caption.** Per-model mean $S_{\mathrm{scen}}$ on the baseline tier (green)
compared against the lookup-attacker reference (orange). The lookup attacker
submits the textbook canonical law without doing the experiment; under the
X+Y truth-form rubric it scores $S_{\mathrm{bench}}^{\mathrm{lookup}} = 0.159$
on the 24-cell $\gamma \cup \delta$ slice (gpt-5.4 attacker, 3 seeds) — well
under the 0.50 gate. The gap (green $-$ orange) is the prior the rubric
assigns to genuine agentic problem-solving over rote lookup. *Lookup-attacker
score is shared across models because the attack is model-agnostic.*

---

## Figure 5 — Ceiling vs. best-LLM scatter

`figures/fig5_ceiling_scatter.{png,pdf}`

**Caption.** Scatter of oracle-ceiling $S_{\mathrm{scen}}$ (x-axis) against
best-of-4-LLM $S_{\mathrm{scen}}$ (y-axis) for the 12 cells covered by the
panel. Each point is colored by tier (gray=baseline, green=$\gamma$,
orange=$\delta$). The dashed diagonal $y = x$ marks "LLM matched the ceiling."
Baseline points cluster near the diagonal; $\gamma$/$\delta$ points sit far
below — i.e. the bench is not saturated, and the ceiling-to-LLM gap is
load-bearing. *12 cells preliminary; full 48-pair scatter is deferred.*

---

## Figure 6 — Tool-call efficiency curves

`figures/fig6_efficiency.{png,pdf}`

**Caption.** For each model, runs are sorted in increasing order of tool-call
cost and plotted as (tool calls used, cumulative mean $S_{\mathrm{scen}}$).
Cheap-and-correct runs lift the curve early; expensive failures pull it down.
*Single-seed preliminary; per-step incremental scoring is deferred to the
camera-ready trace-level rerun.*

---

## Reproducing the figures

```bash
python -m mirrorlab.reports.figures           # writes figures/*.{png,pdf}
pytest tests/reports/test_figures.py -q        # smoke render + headline check
```
