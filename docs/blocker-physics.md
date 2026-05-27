# Independent physics-claim assessment: does the bench reward truth?

**Author**: physics-claim-checker (independent, no prior reading of team-lead/code-tracer)
**Date**: 2026-05-27
**Scope**: γ-2-1 (anisotropic gravity), δ-2-1 (time-varying G), γ-7-1 (anisotropic thermal conductivity)

## TL;DR

**Verdict: BLOCKER confirmed.** As implemented, the bench does **not** measure
"discovery of γ/δ structural breaks" in the numeric channel. The scoring path
on sub-grids (a)/(b) actively prefers baseline-form predictors over
truth-form predictors for every shift whose true law lives in a richer input
space than the test grid exposes. The only signal that the *truth* law was
found is the discrete `+0.10` symmetry-claim bonus (CAL-5). Strip that bonus
and a "perfect Newton agent" scores at or above a "perfect anisotropic
gravity agent" on all three shifts examined.

## Method

1. Read `mirrorlab/scenarios/loader.py:_gravity_test_grids` (L248-267),
   `_thermal_test_grids` (L350-378), and `mirrorlab/runners/ceiling_agent.py:_gravity_pred` / `_thermal_pred`.
2. Read the shift specs in `mirrorlab/shifts/gravity_g_2_1.py`, `gravity_d_2_1.py`, `thermal_g_7_1.py`.
3. Built two submissions per scenario and scored them through the real evaluator (`mirrorlab/eval/scoring.py:score_submission`):
   - **A (baseline)**: canonical law with the shift's fitted params, `claim_broken_symmetry = "none"`.
   - **B (truth-projected)**: best truth-law approximation the test grid's input vocabulary admits, with the catalog symmetry label.
4. Measured S_scen across three seeds.
5. Script: `/tmp/blocker_eval.py`.

## Measured S_scen

```
shift                    seed   baseline-A   truth-B    Δ(B-A)    bonus?
─────────────────────────────────────────────────────────────────────────
γ-2-1 anisotropic grav    0       0.9998     1.0998    +0.100     +0.10
γ-2-1 anisotropic grav    1       0.9594     1.0530    +0.094     +0.10
γ-2-1 anisotropic grav    2       0.9999     1.0997    +0.100     +0.10
δ-2-1 time-varying G      0       0.9998     1.0997    +0.100     +0.10
δ-2-1 time-varying G      1       0.9597     1.0272    +0.068     +0.10
δ-2-1 time-varying G      2       0.9999     1.0996    +0.100     +0.10
γ-7-1 anisotropic thermal 0       0.9473     0.8947    -0.053     +0.10
γ-7-1 anisotropic thermal 1       0.9278     0.5839    -0.344     +0.10
γ-7-1 anisotropic thermal 2       0.9245     1.0197    +0.095     +0.10
```

Subtracting the `+0.10` symmetry bonus gives the pure-numeric component:

```
shift                    seed   numeric-A   numeric-B    Δ_numeric
─────────────────────────────────────────────────────────────────
γ-2-1                     0       0.9998     0.9998     +0.0000
γ-2-1                     1       0.9594     0.9530     -0.0064
γ-2-1                     2       0.9999     0.9997     -0.0002
δ-2-1                     0       0.9998     0.9997     -0.0001
δ-2-1                     1       0.9597     0.9272     -0.0325
δ-2-1                     2       0.9999     0.9996     -0.0003
γ-7-1                     0       0.9473     0.7947     -0.1526
γ-7-1                     1       0.9278     0.4839     -0.4439
γ-7-1                     2       0.9245     0.9197     -0.0048
```

**The numeric channel never rewards truth and sometimes punishes it severely
(γ-7-1 seed=1: −0.44).** The bonus is doing 100% of the discovery work.

## Per-shift root-cause analysis

### γ-2-1 — Gravity quadrupolar anisotropic (ROT break)

- **True law** (`gravity_g_2_1.shifted_force`): full 3-D vector
  `F = -G₀Mm[1+ξ(μ²-1/3)]r̂/r² + (perpendicular term in n̂-μr̂)`. Requires `(x,y,z)` input to evaluate.
- **Test grid** (`loader.py:248-267`): inputs are `{"r": float}` only. **No direction.** GT formula hard-codes canonical Newton `-G·M·m/r²` (L256-257) using `G₀` from the shift's params.
- **Ceiling-agent γ-2-1 branch** (`ceiling_agent.py:208-215`): falls back to `-G*M*m/r²` — the exact GT formula. This isn't "truth"; this is "baseline-with-bonus".
- **Why truth can't help**: ξ multiplies an angular factor `(μ²-1/3)`. Averaged over the sphere, `⟨μ²⟩=1/3`, so the anisotropic correction has zero mean. The grid's scalar `r` input erases the information that distinguishes the anisotropic law from baseline.

**Result**: numeric S identical. Only the bonus differs.

### δ-2-1 — Gravity slow harmonic G(t) modulation (T_TRANS break)

- **True law** (`gravity_d_2_1.shifted_force`): `F = -G(t)·M·m/r²` with `G(t) = G₀[1 + β cos(ω_G t)]`.
- **Test grid**: passes `r` only, no `t`. GT (L256-258) uses `_attr(p, ("G", "G0"), ...)` = **bare G₀**, *not* the time-averaged G.
- **Ceiling-agent δ-2-1 branch** (`ceiling_agent.py:196-206`): evaluates `gravity_d_2_1.shifted_force(r, 0.0, p)` → uses `G(0) = G₀(1+β)` — the *peak* G — which **deviates from GT by a factor `(1+β)`**, predictable mis-fit ~5-30%.
- **Why truth hurts (mildly)**: The bench GT assumes the time-averaged law equals the canonical with `G=G₀`. An agent who correctly identifies time-varying G has no `t` channel to express it, and any non-zero β-correction moves them *away* from the GT formula. The +0.10 bonus barely covers it on lucky seeds.

**Result**: numeric S slightly worse for truth; bonus saves it.

### γ-7-1 — Thermal anisotropic conductivity (ROT break)

- **True law** (`thermal_g_7_1._flux_components`): vector flux `q = -K·∇T` with `K = k₀(I + β n̂ n̂ᵀ)`. The flux magnitude scales as `k₀ · ‖I·d̂ + β(n̂·d̂)n̂‖`, which varies between `k₀` (n̂ ⊥ ∇T) and `k₀(1+β)` (n̂ ∥ ∇T). With `β ∈ [0.05, 5.0]` (`thermal_g_7_1.py:21`), this is a **huge** swing.
- **Test grid** (`loader.py:350-378`): inputs are `{T_hot, T_cold, L}`. GT formula uses scalar `k₀` (L358-360) → ignores anisotropy entirely.
- **Ceiling-agent γ-7-1 branch** (`ceiling_agent.py:295-304`): identical to GT formula. "Ceiling" = baseline-with-bonus.
- **Why truth backfires hard**: An agent that figures out the anisotropy and inserts the effective `k_eff = k₀·‖K·d̂‖` will be off from GT by `k_eff/k₀ ∈ [1, 1+β]` — up to **6x** when β=5. RMSLE blows up. Seed=1 case: numeric S=0.48 vs baseline 0.93; even with bonus, truth loses by 0.34.

**Result**: truth predictor scored *substantially worse* than baseline.

## What the bench actually measures

In the sub-grid (a)/(b) numeric channel, the bench rewards "compute the canonical
baseline formula using the shift's fitted scalar params". On these three shifts
(and likely on every shift whose true law lives in inputs the grid does not
expose: 3-D anisotropy, time-modulation, vector flux, etc.), this is *trivially*
achievable by any agent who recognizes the domain — no break-discovery needed.

The break-discovery signal lives **exclusively in the symmetry-claim bonus**
(`CAL-5 = 0.10`). This is a single discrete bit of credit. The continuous
numeric score is decoupled from the structural shift.

Sub-grid (c) (`counterfactual`) doesn't fix this: GT is recomputed with
perturbed *baseline-form params*, and the ceiling agent's predictor closes
over the original `sim.params` (frozen), so the ceiling agent ALSO fails (c)
symmetrically with baseline. (c) tests "does the predictor re-derive when
params shift," not "is the law right."

## Final verdict

**The bench, as currently implemented, does not test the core claim of Paper 1
("discovery of structural breaks via γ/δ shifts").**

It tests two things:

1. **Convention recognition** (numeric channel, 90%+ of score weight): "can
   you write the canonical formula for this domain with the shift's params?"
   Real LLM agents already do this reliably — the convention is in their
   training data. No discovery required.
2. **Symmetry-label trivia** (bonus, ≤10% of score weight): "given the
   scenario name/prompt, can you guess one of {PAR, ROT, SCALE, TR, T_TRANS}?"
   This is a *labeling* task, not a *discovery* task.

A "perfect Newton agent" that knows zero physics beyond Newton's law, plus a
lucky symmetry guess, ties or beats a "perfect anisotropic gravity agent"
on every γ-2-1 / δ-2-1 / γ-7-1 cell measured. This generalizes (by
inspection) to every shift whose true law lives outside the test grid's
input vocabulary, which is most ROT and most T_TRANS shifts in the catalog.

**Recommendation**: the test-grid GT must encode the *shifted* law in the
inputs available to the agent, OR the input vocabulary must expand to expose
the discriminating axes (direction vectors, time channel). Until then,
`S_scen` is not a discovery metric.

## Artifacts

- Verification script: `/tmp/blocker_eval.py`
- Key code touched: `/Data/tanh/phyLLM/mirrorlab/scenarios/loader.py:248-378`, `/Data/tanh/phyLLM/mirrorlab/runners/ceiling_agent.py:180-304`, `/Data/tanh/phyLLM/mirrorlab/eval/scoring.py:28-76`, `/Data/tanh/phyLLM/mirrorlab/eval/numeric.py:164-210`
