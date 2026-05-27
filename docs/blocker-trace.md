# Blocker trace — γ-2-1 / gravity scoring path

**Author**: code-tracer (independent trace, no audit docs read)
**Date**: 2026-05-27
**Bottom line**: **GT is baseline-form**, not shift-form. Confirmed by code reading *and* a numeric instantiation (γ-2-1, seed=0).

---

## 1. Call graph

Entry points where γ-2-1 actually gets scored:

- `mirrorlab/runners/sprint4_sweep.py` and `mirrorlab/runners/sprint3_pilot.py`
  → drive scenarios through `mirrorlab/scenarios/loader.py:load()` (loader.py:523)
  → submission set is fed to `mirrorlab/eval/scoring.py:score_submission()` (scoring.py:28)
  → which calls `mirrorlab/eval/numeric.py:evaluate_entry()` (numeric.py:164) per entry that survives the dim filter.

Detailed flow for one γ-2-1 scenario:

1. **`loader.load("gravity", "gamma_2_1", seed=...)`** (loader.py:523-562)
   - builds `sim = _make_sim(...)` — the live 3D anisotropic-quadrupole sim from `mirrorlab/shifts/gravity_g_2_1.py`.
   - dispatches to `_gravity_test_grids(sim, seed, magnitude)` because `domain_id == "gravity"` (loader.py:545-548).
2. **`_gravity_test_grids`** (loader.py:248-267) builds `(a)`/`(b)`/`(c)` via `_pack(...)` (loader.py:179-204).
3. **`_pack`** (loader.py:179-204) evaluates GT for each sub-grid:
   - `grid_a`: `gt_fn(sim.params)` — baseline formula closure evaluated with the **unperturbed sim params** (loader.py:198).
   - `grid_b`: same, at OOD inputs (loader.py:199).
   - `grid_c`: same baseline formula closure, but **`cf_params[i]`** — perturbed params from `perturb_params(...)` (loader.py:200-203; counterfactual.py:157-183).
4. **`evaluate_entry`** (numeric.py:164-210) reads `(inputs, gt)` tuples and calls `predictor(**inputs)` — predictor never sees `counterfactual_params`.

---

## 2. The GT formula for gravity (loader.py:251-258)

```python
def gt(inputs):
    def fn(p):
        G = _attr(p, ("G", "G0"), 6.6743e-11)
        M = _attr(p, ("M",), 1.0)
        m = _attr(p, ("m",), 1.0)
        r = inputs["r"]
        return -G * M * m / (r * r)     # <-- BASELINE Newtonian scalar form
    return fn
```

This is the **Newtonian inverse-square radial scalar force** `−GMm/r²`. It uses only the scalar input `r`. It does **not** call `shifted_force`, does **not** consume `xi` or `(nx,ny,nz)`, and does **not** produce the 3D `(Fx,Fy,Fz)` vector that the actual γ-2-1 law in `mirrorlab/shifts/gravity_g_2_1.py:44-64` produces.

For comparison the shift's true law (gravity_g_2_1.py:44-64) is:
```
F_r  = −G₀ M m [1 + ξ(μ²−⅓)] / r²
F_⊥  = +(2 G₀ M m ξ μ / r²) · (n̂ − μ r̂)
```
— anisotropic, vector-valued, three position inputs `(x,y,z)`. None of this surfaces in `gt`.

---

## 3. What `evaluate_entry` and `_entry_predictor` actually see

`evaluate_entry(entry, test_grids, …)` (numeric.py:164-210):
- materializes `predictor = _entry_predictor(entry)` (numeric.py:184; def at numeric.py:92-125)
- iterates each sub-grid's `(inputs_dict, gt_scalar)` tuples
- per point: `pred = _safe_call(predictor, _alias_inputs(inputs, …))` (numeric.py:194-202)
- scores `rmsle(preds, truths)` (numeric.py:205)

The predictor receives **only** `inputs` (here `{"r": …}`) plus the entry's own declared `params` dict (numeric.py:116, `param_values = {p["name"]: p["value"] for p in entry.get("params", [])}`). It never receives `cf_params` or `sim.params`. The only channel through which counterfactual perturbation reaches the predictor is the **scalar GT value** it is compared against in `rmsle`.

---

## 4. Numeric example — γ-2-1, seed=0

Instantiated via `load("gravity", "gamma_2_1", seed=0)`:

```
sim.params:
  G0 = 8.069839e-11
  M  = 1.1999e+21
  m  = 1.0
  xi = 0.06434
  n̂  = (0.0987, -0.2351, -0.9669)
  IC: (x0,y0,z0)=(1e7,0,0), v0=(0, 89.49, 0)

test_grids["a"][0]: ({"r": 5_000_000.0}, gt = -0.003873216045442974)
test_grids["c"][0]: ({"r": 5_000_000.0}, gt = -0.002917908155220575)

shifted_force((5e6, 0, 0), sim.params)
  → (Fx, Fy, Fz) = (-0.003792576, -1.157e-5, -4.758e-5)

baseline  -G0·M·m / r²           = -0.003873216045442974
diff (GT_a[0] − baseline)        =  0.0          ← exact match
diff (GT_a[0] − shifted Fx)      = -8.06e-5      ← does NOT match shifted law

counterfactual_params[0]:
  G0=6.916e-11, M=1.055e+21, xi=0.0765, (n̂, IC unchanged)
baseline -G0_cf·M_cf·m / r²      = -0.002917908155220575
diff (GT_c[0] − baseline_cf)     =  0.0          ← exact match
```

So **at every checkable point, the GT equals the baseline scalar formula** with whichever params object was passed in. The γ-2-1 anisotropy is invisible to the scorer.

---

## 5. Direct answers to Q1-Q4

### Q1 — for `test_grids["a"][i]`, is `gt` computed via `shifted_force` or the loader baseline formula?

**Baseline formula in loader.py.** The closure at `loader.py:252-258` returns `-G*M*m/r²`. `shifted_force` from `mirrorlab/shifts/gravity_g_2_1.py` is **never imported or invoked** by `loader.py`. Verified numerically: GT_a[0] − baseline = 0 exactly, GT_a[0] − shifted Fx ≠ 0.

### Q2 — for `test_grids["c"][i]`, is GT computed using `sim.params` or `counterfactual_params`?

GT uses **the same baseline closure** but with `cf_params[i]` (a `perturb_params` output, type `GravityGamma21Params` with `G0`, `M`, `xi` independently scaled by `1±0.30`). See `loader.py:200-203`: `grid_c = [(ins, float(gt_fn(cf_params[i]))) …]`. The closure ignores `xi` and `n̂`, so the only effective perturbation on GT_c is the scaling of `G0·M`. `sim.params` is not used for sub-grid (c). Verified numerically: GT_c[0] = `-G0_cf · M_cf · m / r²` to machine precision.

### Q3 — does `_entry_predictor` ever receive `counterfactual_params` (or anything derived from them beyond the scalar GT)?

**No.** `_entry_predictor` (numeric.py:92-125) closes over `param_values` extracted from `entry["params"]` only. The grid tuple delivered to it is `(inputs_dict, gt_scalar)`; the predictor sees only `inputs_dict` (after alias renaming via `_alias_inputs`, numeric.py:128-161). `counterfactual_params` is stored on `ScenarioInstance` (loader.py:123) and used solely inside the loader to compute GT scalars. It is not threaded into `score_submission` and is not visible to entries.

### Q4 — predictor `f(r, G, M, m) = -G*M*m/r**2` with declared `G=6.67e-11`: does evaluator substitute the perturbed G at sub-grid (c)?

**No — the declared G is used unchanged at every point**, including (c). Flow:
1. `_entry_predictor` builds `param_values = {"G": 6.67e-11, "M": …, "m": …}` from `entry["params"]` once (numeric.py:116).
2. `bound(**kwargs)` merges `{**param_values, **kwargs}` — kwargs are just the grid `inputs` (e.g. `{"r": …}`) (numeric.py:119-123).
3. For sub-grid (c), `inputs` is `{"r": …}` (no `G` key). Merge yields `{"r": …, "G": 6.67e-11, "M": …, "m": …}`. The declared G wins.

This is the entire mechanism by which sub-grid (c) is meant to defeat frozen-coefficient fits: the predictor's declared coefficients can't follow the perturbed law because they are never told to. A "physical" submission would have to express the dependence on the *true* shifted parameters explicitly to track GT_c, but those parameters are never delivered.

---

## 6. Bottom line

For γ-shift scenarios (γ-2-1 verified, and by inspection γ-{1,3,…,12}-{1,2} all use the same `_pack` + baseline-form gt closure pattern in loader.py:223-505), **the bench scores agent predictors against the baseline (Newtonian / Hookean / etc.) law evaluated on the sim's params**, not against the shifted law. The shift-form law (`shifted_force` and equivalents in `mirrorlab/shifts/*.py`) is used only inside the live `sim` object the agent observes via `sim.step()` — it never enters scoring GT.

Sub-grid (c) does add a counterfactual signal, but only by re-evaluating the *same baseline closure* with perturbed params — not by re-evaluating the shifted law.

**Implication**: an agent that recovers the baseline law exactly (e.g. `f(r,G,M,m) = -G*M*m/r²` for gravity) and declares its params correctly will score `s_entry ≈ 1` on sub-grids (a) and (b). It will lose only on (c), and only to the extent that the perturbation magnitude (CAL-3 default ±30%) creates a residual in `slog`-RMSLE space. The γ-2-1 anisotropy (ξ, n̂) is undetectable in the scored channel.

---

## 7. Files & line cites

- `mirrorlab/scenarios/loader.py:248-267` — `_gravity_test_grids`, baseline-form GT closure
- `mirrorlab/scenarios/loader.py:179-204` — `_pack`, `grid_c = gt_fn(cf_params[i])`
- `mirrorlab/scenarios/loader.py:523-562` — `load(...)` entry
- `mirrorlab/scenarios/counterfactual.py:79,87-150,157-183` — `_LAW_PARAM_FIELDS`, `perturb_params`
- `mirrorlab/eval/scoring.py:28-76` — `score_submission`
- `mirrorlab/eval/numeric.py:92-125` — `_entry_predictor` (only `entry["params"]` + grid inputs)
- `mirrorlab/eval/numeric.py:164-210` — `evaluate_entry` (consumes `(inputs, gt_scalar)`)
- `mirrorlab/shifts/gravity_g_2_1.py:44-64` — true 3D anisotropic `shifted_force` (NOT used by scorer)
