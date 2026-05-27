# Blocker fix architectures — X / Y / Z (+ hybrids)

**Author**: bench-fixer-architect
**Date**: 2026-05-27
**Inputs**: `docs/blocker-trace.md` (#1, code-tracer), `docs/blocker-physics.md` (#2, physics-claim-checker)
**Status**: spec only — no code changes in this task

---

## 0. What the audits actually established

From #1 (call-graph trace, γ-2-1 verified numerically):

- `mirrorlab/scenarios/loader.py:_pack` (L179-204) builds GT as `gt_fn(sim.params)` for (a)/(b) and `gt_fn(cf_params[i])` for (c).
- `gt_fn` is a **baseline-form closure** per domain (`_gravity_test_grids` L248-267, `_thermal_test_grids` L350-378, etc.) that hard-codes the canonical law (Newton inverse-square, Fourier conduction, Hooke, ...).
- `shifted_force` / `shifted_*` from `mirrorlab/shifts/*.py` is **never imported by the scorer**. It only animates `sim.step()`.
- `mirrorlab/eval/numeric.py:_entry_predictor` (L92-125) closes over `entry["params"]` once; `counterfactual_params` is **never delivered** to the predictor. (c) tests "does GT shift when we re-evaluate the *baseline* closure with perturbed params?" — not "does the predictor track perturbation?"

From #2 (physics simulation across 3 shifts, S_scen measured):

- Numeric channel never rewards truth; punishes it severely when the shift's true law lives outside the grid's input vocabulary (γ-7-1 seed=1: ΔS_numeric = -0.44 for truth predictor).
- The +0.10 CAL-5 symmetry bonus does 100% of the discovery work.
- Generalizes by inspection to every ROT-break and every T_TRANS-break in the catalog.

**Root cause (one sentence)**: the scoring channel's input vocabulary `{r}`, `{T_hot,T_cold,L}`, `{theta}`, ... is too narrow to express the discriminating axes (direction `n̂`, time `t`, vector flux components) of the shifts in `mirrorlab/shifts/*.py`, and GT is computed by a baseline closure that pretends those axes don't exist.

Two distinct mechanisms break:

1. **Truth-vs-baseline mismatch on (a)/(b)** — γ-anisotropic / δ-time-modulated laws can't be expressed in the scalar inputs that GT closures consume; baseline beats truth in `rmsle`.
2. **Counterfactual leak / non-leak on (c)** — predictor has no channel to *receive* perturbed params, so (c) measures "does the baseline closure respond to param scaling," not "does the agent's submission generalize to param shifts."

X addresses (1), Y addresses (2), Z addresses neither in code but reframes the paper.

---

## 1. Option X — GT uses shift truth

### 1.1 Intent

Replace each baseline `gt_fn` closure in `loader.py` with a call to the corresponding `shifted_*` law from `mirrorlab/shifts/<domain>_<class>_<i>_<j>.py`, and **expand the test-grid input vocabulary** so the shift's discriminating axes are exposed to the predictor.

Without the vocabulary expansion, X collapses into the current state (a scalar can't carry direction). So X is really **X = X.A (truth-form GT) + X.B (input-vocabulary expansion per shift family)**.

### 1.2 Per-domain change matrix

| Domain | Shift family | Current grid keys | New keys required | New gt source |
|---|---|---|---|---|
| gravity γ-2-1 (ROT) | anisotropic quadrupole | `{r}` | `{x,y,z}` (or `{r,μ}` with μ=cos(angle to n̂)) | `gravity_g_2_1.shifted_force(...)[0]` magnitude or component |
| gravity δ-2-1 (T_TRANS) | G(t) modulation | `{r}` | `{r, t}` | `gravity_d_2_1.shifted_force(r,t,p)` |
| gravity γ-2-2 | scale-dependent | `{r}` | `{r}` (no new axis) | `gravity_g_2_2.shifted_force` |
| coulomb γ/δ-5-* | analogous | `{r}` | per shift | `coulomb_*` |
| hooke γ/δ-1-* | spring nonlinearity / drift | `{x,v}` | `{x,v}` or `{x,v,t}` for δ | `hooke_*` |
| damped_ho γ/δ-3-* | similar | `{x,v}` | per shift | `damped_ho_*` |
| pendulum γ/δ-4-* | g(t)/L break | `{theta}` | `{theta, t}` for δ | `pendulum_*` |
| rlc γ/δ-6-* | L(t)/R(i) | `{i,didt,q}` | `{...,t}` for δ | `rlc_*` |
| thermal γ-7-1 (ROT) | k·(I+β n̂n̂ᵀ) | `{T_hot,T_cold,L}` | `{T_hot,T_cold,L, n̂·d̂}` or `{∇T_x,∇T_y,∇T_z}` | `thermal_g_7_1._flux_components` |
| thermal δ-7-1 | k(t) | as above | add `t` | `thermal_d_7_1` |
| wave γ/δ-8-* | mode-coupling / drift | `{x,t}` | maybe add `n̂` for direction | `wave_*` |
| optics γ/δ-9-* | per shift | `{...}` | per shift | `optics_*` |
| fluid γ/δ-10-* | per shift | `{...}` | per shift | `fluid_*` |
| kinetics γ/δ-11-* | per shift | `{...}` | per shift | `kinetics_*` |
| decay γ/δ-12-* | λ(t) / λ-anisotropy | `{N, t}` | per shift | `decay_*` |

12 domains × ≈2.5 shifts each = ~30 distinct loader closures touched. 36 shift modules surfaced into loader namespace.

### 1.3 Illustrative diff sketch (loader.py, γ-2-1 only)

```python
# CURRENT (loader.py:248-267):
def _gravity_test_grids(sim, seed, magnitude):
    r0 = _attr(sim.params, ("r0",), 1.0e7) or 1.0e7
    def gt(inputs):
        def fn(p):
            G = _attr(p, ("G","G0"), 6.6743e-11)
            M = _attr(p, ("M",), 1.0); m = _attr(p, ("m",), 1.0)
            return -G*M*m / (inputs["r"]**2)
        return fn
    def build(rng, mode): ...
    return _pack(seed, magnitude, sim, build)

# SKETCH (truth-form, vocabulary-expanded):
from mirrorlab.shifts import gravity_g_2_1 as _g221
def _gravity_g_2_1_test_grids(sim, seed, magnitude):
    r0 = _attr(sim.params, ("r0",), 1.0e7) or 1.0e7
    def gt(inputs):
        def fn(p):
            pos = (inputs["x"], inputs["y"], inputs["z"])
            Fx, Fy, Fz = _g221.shifted_force(pos, p)   # 3-D vector
            return float(np.sqrt(Fx*Fx + Fy*Fy + Fz*Fz)) * np.sign(Fx*pos[0]+Fy*pos[1]+Fz*pos[2])
        return fn
    def build(rng, mode):
        rs = np.linspace(0.5*r0, 1.5*r0, _GRID_SIZE) if mode != "b" else ...
        thetas = rng.uniform(0, math.pi, _GRID_SIZE)
        phis   = rng.uniform(0, 2*math.pi, _GRID_SIZE)
        pts = []
        for r,th,ph in zip(rs,thetas,phis):
            x = r*math.sin(th)*math.cos(ph); y = r*math.sin(th)*math.sin(ph); z = r*math.cos(th)
            ins = {"x": x, "y": y, "z": z, "r": r}
            pts.append((ins, gt(ins)))
        return pts
    return _pack(seed, magnitude, sim, build)
```

This requires **dispatch per shift_id**, not per domain — current loader dispatches per `domain_id` (loader.py:545-548). The dispatch table grows from 12 entries to ~36.

### 1.4 Downstream ripples

- `mirrorlab/runners/ceiling_agent.py` (~180-380): every per-domain `_*_pred` function consumes scalar inputs. Needs a 3-D form per shift if the ceiling agent is to remain "knows the true law." ~30 functions touched.
- `mirrorlab/runners/agent_stub.py`: input schema generation. Real LLM agents need to know the new input keys exist; prompt template must list `(x,y,z)` not just `r`.
- Spec §5 (submission format): predictor signature must accept the new kwargs. Existing submissions are invalid (or accept a lenient adapter that injects `r=sqrt(x²+y²+z²)` and discards direction — sidesteps the whole fix).
- `mirrorlab/scenarios/counterfactual.py:perturb_params` and `_LAW_PARAM_FIELDS`: probably unchanged, since the perturbation is over the shift's param namespace.
- All sprint3/sprint4 sweep JSONs (`docs/sprint3-pilot-data.json`, `docs/sprint35-pilot-data.json`, `docs/sprint4-sweep-data*.json`) are invalidated. Full rerun needed (ceiling + 4 attackers × 36 cells × ≥3 seeds).
- Tests under `tests/` that assert `gt_a[0] ≈ -G·M·m/r²` (numeric, see #1 numeric example): need rewriting. Estimated ~25-50 test cases touched in `tests/test_loader*.py`, `tests/test_ceiling*.py`, `tests/test_eval*.py`.

### 1.5 Risks unique to X

- **Direction sampling has zero-mean modes.** γ-2-1's anisotropic correction `(μ²-1/3)` averages to zero over the sphere. If the grid uniformly samples solid angle and uses scalar `|F|`, the anisotropy STILL hides at coarse seeds. The grid must be deliberately biased (e.g. pin n̂ aligned with z, sample direction in (μ²-1/3) ≠ 0 regions) or report per-component F.
- **OOD sub-grid (b)** semantics change: "OOD in r" was 1-D; "OOD in (r,θ,φ)" requires a new convention.
- **Lookup attackers** (`sprint3-attacker-spec.md` defines them) currently exploit GT being a closed-form function of `r` alone. Truth-form GT may make lookup harder OR easier depending on whether the LLM remembers the truth law from training data. Sweep needed to recheck attacker hit rates.
- **Symmetry-claim bonus interpretation** (CAL-5): if GT actually encodes the broken symmetry, the bonus becomes redundant. May warrant removing CAL-5 or repurposing it.

### 1.6 Cost (X, full)

- **Hours**: 40-50 (engineer-equivalent, one person, well-versed in the codebase).
- **LOC**:
  - `loader.py`: ~+400 net (12 → 36 functions, vocabulary expansion).
  - `ceiling_agent.py`: ~+300.
  - `agent_stub.py` + prompt templates: ~+150.
  - `spec §5` markdown: ~50 lines.
  - Tests: ~+500 (rewrites + new direction/time tests).
- **Reruns**: 100% — every sweep, every ceiling, every attacker. Estimate at current LLM-rate-limited throughput: ~24-48 hours of API time.

---

## 2. Option Y — Predictor receives counterfactual params at (c)

### 2.1 Intent

Keep `gt_fn` baseline-form on (a)/(b). For sub-grid (c), pass perturbed params into the predictor at call time instead of baking the entry's declared constants. This makes (c) a real "does the submission generalize over parameter shifts" test.

Note Y does NOT fix the anisotropy/time-modulation issue identified in #2 — that lives in (a)/(b). Y only repairs (c)'s broken counterfactual semantics.

### 2.2 Diff sketch

**loader.py: ScenarioInstance** — attach `cf_params` to each (c) tuple.

```python
# CURRENT (_pack, loader.py:200-203):
grid_c = [(ins, float(gt_fn(cf_params[i])))
          for i, (ins, gt_fn) in enumerate(zip(pts_c_inputs, [g for _, g in pts_a]))]

# SKETCH:
grid_c = [(ins, float(gt_fn(cf_params[i])), cf_params[i])  # 3-tuple
          for i, (ins, gt_fn) in enumerate(zip(pts_c_inputs, [g for _, g in pts_a]))]
```

**numeric.py: evaluate_entry** — recognize 3-tuples on (c), substitute params.

```python
# SKETCH (numeric.py:184-205):
predictor_raw = _entry_predictor_raw(entry)   # NEW: no param closure
declared_params = {p["name"]: p["value"] for p in entry.get("params", [])}
for key, grid in test_grids.items():
    ...
    if key == "c":
        preds = []
        for tup in grid:
            ins, gt_val, cf_p = tup
            cf_overrides = _params_to_dict(cf_p)      # NEW: shift-param object → kwargs
            kwargs = {**declared_params, **cf_overrides, **_alias_inputs(ins, ...)}
            preds.append(_safe_call(predictor_raw, kwargs))
        truths = [gt for _, gt, _ in grid]
    else:
        preds  = [...as today...]
        truths = [...as today...]
```

**Spec §5 (submission format)**: `predictor.code` signature must accept the shift's param names as kwargs (e.g. `def f(r, G, M, m, xi=0.0, **_)`). Today the ceiling agent already declares `G,M,m` in `entry["params"]`; the change is "predictors must consume them as args, not closed-over constants."

**ceiling_agent.py + agent_stub.py**: emit code that takes params as args.

### 2.3 What Y buys / doesn't buy

- ✅ (c) cliff becomes meaningful: a frozen-baseline submission no longer auto-passes.
- ✅ Reusable by lookup attackers — they can encode the closed-form `f(r,G,M,m)` and pass.
- ❌ (a)/(b) still reward baseline-form. γ-7-1 truth predictor still loses by 0.44.
- ❌ The +0.10 bonus still does discovery; numeric channel still convention-recognition.
- ⚠️ Existing entries that bake constants are invalid. Forces an attacker/ceiling rerun on (c).

### 2.4 Cost (Y)

- **Hours**: 15-25.
- **LOC**: ~+200 (loader 3-tuple plumbing, numeric.py branch on (c), spec, ceiling/attacker rewrites).
- **Reruns**: partial — (a)/(b) caches can be reused if the loader writes them deterministically; (c) entries need re-emission. Estimate ~30% of sweep API budget.

### 2.5 Risks unique to Y

- The `_params_to_dict` adapter must canonicalize shift-class param names against entry-declared param names; lots of aliasing (cf. `_attr(p, ("G","G0"))` in current loader).
- Predictors that *don't* declare a param will silently default — easy to mis-score.

---

## 3. Option Z — Reframe the paper, zero code change

### 3.1 Intent

Concede that the current bench measures "parameter-exposure quality of baseline-form submissions under modified-physics simulators with parameter perturbation," not "discovery of structural breaks." Rewrite Paper 1 sections accordingly.

### 3.2 Claims in `paper1/main.tex` to revise

| Current claim (paraphrase) | Supported by current bench? | Proposed revision |
|---|---|---|
| "S_scen measures discovery of γ/δ structural breaks." | No. Numeric channel measures convention recognition; bonus measures label guessing. | "S_scen measures the agent's ability to (i) recover the canonical baseline law for the domain, (ii) propose a symmetry label consistent with the catalog, and (iii) track parameter perturbations on (c)." |
| "Cliff plot shows truth-vs-baseline separation." | No. Truth often scores below baseline (γ-7-1). | "Cliff plot shows degradation of frozen-coefficient predictors under counterfactual parameter shifts (c), with the +0.10 increment indexing whether the symmetry label was correctly named." |
| "Bench validates LLMs on novel-physics discovery." | No. Convention plus a single discrete bit. | "Bench probes LLM behavior under perturbed-parameter simulators with baseline-form scoring — a sensitivity test, not a discovery test." |
| Ceiling agent = "perfect-knowledge upper bound." | Misleading — ceiling computes baseline, not truth. | "Ceiling agent = canonical-baseline-with-correct-params upper bound (i.e. the score available to any agent that recognizes the domain)." |
| CAL-5 = "discovery bonus." | Misleading — bonus is a labeling task. | "CAL-5 = symmetry-label bonus." |

### 3.3 Cliff-plot revised interpretation

The (c)-cliff is real and useful even under Z, because the baseline-form GT closure DOES respond to `cf_params`. The cliff shows: "frozen-coefficient submissions lose on (c) at magnitude m." That's a meaningful parameter-sensitivity result. It is not a structural-discovery result.

The figure caption (`docs/sprint4-figure-captions.md`) needs rewording: "cliff" → "counterfactual parameter-sensitivity curve."

### 3.4 Cost (Z)

- **Hours**: 8-15 (paper writing, no code).
- **LOC**: 0.
- **Reruns**: 0.

### 3.5 Risks unique to Z

- Reviewer says "you renamed the problem; the headline contribution is gone." Reasonable critique. Paper becomes a smaller contribution.
- The bench gets shipped with the `shifted_*` modules looking like dead code from the scorer's perspective. Future researchers may waste time figuring out why `mirrorlab/shifts/` is so elaborate when only `sim.step()` consumes it.
- Sprint3/4 narrative documents (`sprint4-paper-trail.md`, `story.md`) need partial rewrites for consistency.

---

## 4. Hybrid options

### 4.1 X+Y — full fix

GT uses truth law AND predictor receives cf_params on (c). Maximum bench validity, maximum cost.

- **Hours**: 50-70.
- **LOC**: ~+1300.
- **Reruns**: full (100% of sweeps + ceiling + attackers).
- **Paper impact**: restores every original claim. The bench actually does what the paper says.
- **Risk**: schedule. If a venue deadline is binding within ~3 weeks, this likely misses it.

### 4.2 Z + lite-X — narrative reframe + truth-form GT only on swept cells

The Sprint-4 sweep (`docs/sprint4-sweep-summary.md`) actually exercises a subset of cells. Apply X only to the cells in the active sweep, ship Z framing for everything else. Concretely:

- Identify swept cells. Most-affected per #2: γ-2-1, γ-7-1, δ-2-1 (and likely fluid γ-10-1 per `memory/project_mirrorlab_sprint3_readiness.md`).
- For those 3-5 cells, apply X.A (truth-form GT) + X.B (input-vocabulary expansion).
- For the rest, leave loader as-is and have Z's reframe cover them.
- Add a single figure: "where the headline cells actually do measure truth-vs-baseline" with truth-form scoring.

- **Hours**: 12-20 (4-6 hours for the 3-5 cell port; 8-14 for paper rewrite).
- **LOC**: ~+250 (just the hot cells).
- **Reruns**: selective — rerun ceiling + the 3-5 cells (~10% of API budget).
- **Paper impact**: keeps a real "we DID measure structural-break discovery" result on a focused subset, while honestly reframing the rest.

---

## 5. Matrices

### 5.1 Engineering cost

```
Option          Hours    LOC      Tests touched    Reruns        Risk of regression
─────────────────────────────────────────────────────────────────────────────────
X (full)        40-50    ~+1350   ~50              100%          high
Y               15-25    ~+200    ~15              ~30%          medium
Z               8-15     0        0                0%            low
X+Y             50-70    ~+1500   ~60              100%          high
Z+lite-X        12-20    ~+250    ~10              ~10%          low-medium
```

### 5.2 Paper-impact

```
Option       Discovery-claim     Cliff-plot      Ceiling-as-truth     Symmetry-bonus
                                                  upper-bound          interpretation
─────────────────────────────────────────────────────────────────────────────────────
X (full)     restored            restored        restored             possibly redundant
Y            unchanged           clarified ((c)  unchanged            unchanged
                                  becomes real)
Z            removed             reframed as     downgraded to        relabelled as
             (renamed)            param-sens      "baseline-ceiling"   labeling
X+Y          restored            restored        restored             possibly redundant
Z+lite-X     partial (hot         reframed +     hybrid               relabelled
              cells only)         hot-cell truth
```

### 5.3 What each option leaves un-fixed

```
Option     anisotropy        time-modulation   counterfactual    direction-naive
            visible to        visible to        predictor        OOD sampling
            scorer?           scorer?           channel?
────────────────────────────────────────────────────────────────────────────────
X          yes (X.B)         yes (X.B)         no                yes (X.B)
Y          no                no                yes               no
Z          no (renamed       no (renamed       no (renamed       no
            away)             away)             away)
X+Y        yes               yes               yes               yes
Z+lite-X   yes on hot        yes on hot        no                hot cells only
            cells             cells
```

---

## 6. Recommendation

**Primary recommendation: Z + lite-X.**

Rationale:

1. **The audits don't establish that X is uniformly necessary**; they establish that X is necessary *if* the paper's headline claim is "we measure structural-break discovery on numeric S." Z removes that demand by relabelling the claim. The bench as built does measure something real (parameter sensitivity under baseline-form submissions + a discrete symmetry-labeling channel) — just not what the paper currently says.
2. **Lite-X on 3-5 hot cells** lets the paper retain *some* truth-vs-baseline result without the 40-50 hour rewrite. Pair the lite-X cells with a head-to-head table (truth-form GT vs baseline-form GT) — this becomes the paper's quantitative honesty.
3. **Y is attractive but solves the smaller of the two problems.** Adding Y without X still leaves γ-7-1 punishing truth submissions by 0.44 numeric. Y-without-X buys partial credibility on the (c) cliff at the cost of invalidating every existing entry — bad trade.
4. **Z+lite-X is reversible**: if a future submission deadline gives runway, escalate to X+Y as a v2 bench (label this as "MirrorLab v1.1 → v2" in the spec). Z+lite-X is a strict subset of X+Y, so no work is wasted.
5. **Z alone** is the conservative fallback if even lite-X is too expensive — paper still ships, but with substantially smaller contribution.

**When to escalate to X+Y instead**: if the headline "discovery of structural breaks" claim is contractually load-bearing (e.g. a venue's call-for-papers cites it verbatim, a co-author insists, a reviewer pre-commits) AND there is ≥6 weeks of runway, do X+Y. Anything less than X+Y leaves the discovery claim partially un-evidenced.

**Do not pick Y alone.** It's effort spent on the secondary issue while the primary issue (truth-vs-baseline on (a)/(b)) remains live.

---

## 7. Open questions for #4 (consensus-lead)

1. What's the actual deadline pressure? (Determines whether X+Y or Z+lite-X is the right escalation point.)
2. Is the symmetry-bonus CAL-5 = 0.10 calibration considered immutable? If X.B is adopted, CAL-5 should probably be reduced or removed (the bonus becomes redundant when GT carries the broken-symmetry information).
3. Which cells count as "hot" for lite-X? Suggestion: γ-2-1, γ-7-1, δ-2-1 (audited), plus fluid γ-10-1 (flagged in `memory/project_mirrorlab_sprint3_readiness.md` as the narrowest CAL-4 cell).
4. Do attackers (especially the lookup attacker family in `docs/sprint3-attacker-spec.md`) need to be re-spec'd under any of these options, or do they ride the loader changes transparently?

---

## 8. Cross-references

- Audits: `docs/blocker-trace.md`, `docs/blocker-physics.md`.
- Bench scoring path: `mirrorlab/scenarios/loader.py:179-562`, `mirrorlab/eval/scoring.py:28-76`, `mirrorlab/eval/numeric.py:92-210`.
- Shift modules: `mirrorlab/shifts/*.py` (36 files), notably `gravity_g_2_1.py:44-64`, `thermal_g_7_1.py`, `gravity_d_2_1.py`.
- Ceiling/attackers: `mirrorlab/runners/ceiling_agent.py:180-380`, `mirrorlab/runners/agent_stub.py`, `mirrorlab/runners/sprint4_sweep.py`.
- Paper: `paper1/main.tex` (claims), `docs/sprint4-figure-captions.md` (cliff plot), `docs/sprint4-paper-trail.md`, `docs/story.md`.
- Spec: `docs/paper1-spec.md` (CAL-3/CAL-5), `docs/sprint3-attacker-spec.md`, spec §5 (submission format) and §6.2 (s_entry).
