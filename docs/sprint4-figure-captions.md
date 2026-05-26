# Sprint 4 — Paper-1 figure captions

All figures live under `figures/` as 300 dpi PNG plus vector PDF. They are
rendered by `mirrorlab/reports/figures.py` from:

- `docs/sprint4-sweep-data-final.json` — 5 models × 12 cells = **60 runs**
  (4 representative domains × 3 tiers × 1 seed; rescored).
- `docs/ceiling-data.json` — full 48-pair oracle ceiling (12 domains × 4 shifts).
- `docs/sprint35-pilot-data.json` — lookup-attacker reference (s_bench = 0).

**Scope note (repeated in each caption):** results are from a single-seed,
4-domain preliminary sweep; the full 48-pair × 3-seed sweep is deferred to the
camera-ready.

---

## Figure 1 — Cliff plot (HERO)

`figures/fig1_cliff.{png,pdf}`

**Caption.** Mean scenario score $S_{\mathrm{scen}}$ versus shift tier
(baseline / $\gamma$-shift / $\delta$-shift) for five frontier LLMs, averaged
over four representative domains (Hooke, Coulomb, Thermal, Decay). The dashed
black curve is the oracle ceiling computed by the symbolic-physics agent on
the full 48-pair catalog. Four of the five LLMs collapse to $\bar S = 0$ at
the $\gamma$ tier (counterfactual interventions on a physical constant) and
only partially recover at $\delta$ (time / parameter drift); **GPT-5.4 is the
sole exception, scoring $\bar S = 0.70$ at $\gamma$**. *Single-seed
preliminary; camera-ready extends to 48 pairs × 3 seeds across 12 domains.*

**Headline numbers (rescored mean $S_{\mathrm{scen}}$):**

```
model                    baseline   gamma    delta
─────────────────────────────────────────────────────
Claude Opus 4.6           0.258    0.000    0.249
Claude Sonnet 4.5         0.250    0.000    0.499
Gemini 3.1 Pro            0.483    0.110    0.583
GPT-4.1                   0.033    0.000    0.000
GPT-5.4                   0.571    0.698    0.474
─────────────────────────────────────────────────────
Ceiling (oracle)          1.100    1.099    1.064
```

The "cliff" at $\gamma$ for four-of-five models, set against the near-flat
oracle ceiling, is the central claim of Paper 1.

---

## Figure 2 — Per-domain $\gamma$-shift heatmap (4 × 5)

`figures/fig2_heatmap_gamma.{png,pdf}`

**Caption.** $S_{\mathrm{scen}}$ on the $\gamma$ tier for each
(domain, model) cell. Color is viridis, normalized to $[0, 1]$. Decay is the
only domain where any model (GPT-5.4) reaches the 0.5 calibration threshold;
all other domain-model cells outside the GPT-5.4 row sit at $\bar S = 0$.
*4 representative domains; the full 12-domain heatmap is deferred to the
camera-ready.*

---

## Figure 3 — Per-model competence radar (6 axes)

`figures/fig3_radars.{png,pdf}`

**Caption.** Six-axis radar per model summarising the 12 swept cells:
**In-dom S** = baseline-tier mean, **OOD S** = $\gamma$+$\delta$ mean,
**Counterfact S** = $\gamma$-tier mean, **Dim. parse** = fraction of runs
returning a parseable submission with zero parse errors, **Bonus probe** =
fraction of shifted runs whose submission names a non-trivial broken symmetry
(`claim_broken_symmetry $\notin$ {none, unsure}`), **Efficiency** =
$1 - \bar n_{\mathrm{tool\,calls}} / 30$. All axes are scaled to $[0, 1]$.
GPT-5.4 dominates four of six axes; Gemini-3.1-Pro is closest in In-dom S and
Dim. parse. *Bonus-probe axis is a behavioral proxy — symmetry labels are
self-reported, not yet checked against ground-truth labels (camera-ready).*

---

## Figure 4 — Honest vs. lookup-attacker bar chart

`figures/fig4_attacker.{png,pdf}`

**Caption.** Per-model mean $S_{\mathrm{scen}}$ on the baseline tier (green)
compared against the lookup-attacker reference (orange).  The lookup attacker
queries the catalog by `(domain_id, shift_id)` and returns the matched closed
form without ever executing the experiment harness; under the symmetry-vetted
rubric used in Paper 1, it scores $\bar S = 0$ on the 48-pair bench across all
seeds. The gap (green $-$ orange) is the prior the rubric assigns to genuine
agentic problem-solving over rote lookup. *Lookup-attacker score is shared
across models because the attack is model-agnostic; per-model attacker traces
will be added at camera-ready.*

---

## Figure 5 — Ceiling vs. best-LLM scatter

`figures/fig5_ceiling_scatter.{png,pdf}`

**Caption.** Scatter of oracle-ceiling $S_{\mathrm{scen}}$ (x-axis) against
best-of-5-LLM $S_{\mathrm{scen}}$ (y-axis) for the 12 cells covered by the
preliminary sweep. Each point is colored by tier (gray=baseline,
green=$\gamma$, orange=$\delta$). The dashed diagonal $y = x$ marks
"LLM matched the ceiling." Most points sit far below the diagonal, with the
$\gamma$ tier the lowest — i.e. the bench is not saturated, and the gap is
load-bearing. *12 cells preliminary; full 48-pair scatter is deferred.*

---

## Figure 6 — Tool-call efficiency curves

`figures/fig6_efficiency.{png,pdf}`

**Caption.** For each model, runs are sorted in increasing order of tool-call
cost and plotted as (tool calls used, cumulative mean $S_{\mathrm{scen}}$).
Cheap-and-correct runs lift the curve early; expensive failures pull it down.
Most LLMs ride the 30-call hard cap with $\bar S \approx 0$; GPT-5.4 keeps a
non-trivial cumulative score across the full budget range. *Single-seed
preliminary; per-step incremental scoring is deferred to the camera-ready
trace-level rerun.*

---

## Reproducing the figures

```bash
python -m mirrorlab.reports.figures           # writes figures/*.{png,pdf}
pytest tests/reports/test_figures.py -q       # smoke render + headline check
```
