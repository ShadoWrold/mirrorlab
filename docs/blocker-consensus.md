# MirrorLab bench blocker — consensus document

**Author**: consensus-lead (synthesis of #1 code-tracer, #2 physics-claim-checker, #3 bench-fixer-architect)
**Date**: 2026-05-27
**Confidence**: **HIGH** — three independent investigators (one static trace, one empirical simulation, one architectural review) converged on the same factual finding with explicit CONFIRM statements.

---

## 1. Factual finding

The MirrorLab bench, as currently implemented, **does not score agent predictors against the shifted (γ/δ) law**. The ground-truth values fed to `rmsle` are produced by **baseline-form closures** in `mirrorlab/scenarios/loader.py` that hard-code the canonical law for each domain (Newton inverse-square for gravity, Fourier conduction for thermal, Hooke for hooke, ...). The `shifted_force` / `shifted_*` modules in `mirrorlab/shifts/*.py` — which encode the γ/δ structural breaks the paper claims to measure — are imported only by the live simulator (`sim.step()`), never by the scorer. The counterfactual sub-grid (c) re-evaluates the same baseline closure with perturbed params, but `counterfactual_params` never reaches the predictor. Consequently the numeric channel of `S_scen` measures "can you write the canonical baseline formula with the right scalar params?"; the only signal tied to actual break-discovery is the discrete `+0.10` CAL-5 symmetry-label bonus.

---

## 2. Code citations

- `mirrorlab/scenarios/loader.py:179-204` — `_pack`, builds `(grid_a, grid_b, grid_c)` as `gt_fn(sim.params)` / `gt_fn(cf_params[i])`.
- `mirrorlab/scenarios/loader.py:248-267` — `_gravity_test_grids`, baseline-form closure `-G*M*m/r²`.
- `mirrorlab/scenarios/loader.py:350-378` — `_thermal_test_grids`, baseline-form Fourier closure (scalar `k₀`).
- `mirrorlab/scenarios/loader.py:523-562` — `load(...)` entry, dispatches per `domain_id` (no shift-id branching).
- `mirrorlab/eval/numeric.py:92-125` — `_entry_predictor`, closes only over `entry["params"]` + grid inputs.
- `mirrorlab/eval/numeric.py:164-210` — `evaluate_entry`, consumes `(inputs, gt_scalar)` pairs; `counterfactual_params` not threaded in.
- `mirrorlab/eval/scoring.py:28-76` — `score_submission`, top-level scoring orchestration.
- `mirrorlab/shifts/gravity_g_2_1.py:44-64` — true 3-D anisotropic `shifted_force` (used by sim, NOT by scorer).
- Numeric verification (code-tracer, γ-2-1 seed=0): `GT_a[0] = -G0·M·m/r² ≈ -3.873e-3` matches baseline closure exactly; differs from `shifted_force` Fx by ~8e-5.
- Empirical verification (physics-claim-checker, /tmp/blocker_eval.py): truth-projected predictors tie or lose on the numeric channel for γ-2-1, δ-2-1, γ-7-1; γ-7-1 seed=1 numeric Δ = −0.44.

---

## 3. Teammate confirmations

All three investigators were polled with the canonical statement: *"GT is baseline-form (closed Newton/Fourier/Hooke formula in loader.py); shifted_force from mirrorlab/shifts/* is never imported by the scorer; counterfactual_params never reaches the predictor — therefore the bench tests parameter-exposure on baseline-form submissions, NOT shift-discovery."*

- **code-tracer**: **CONFIRM**. "Verified by my trace … loader.py:179-204 `_pack` + per-domain gt_fn closures (e.g. loader.py:252-258 for gravity: `-G*M*m/r²`); shifted_force never imported by loader/scorer; `_entry_predictor` (numeric.py:92-125) only sees entry["params"] + grid inputs, never counterfactual_params. Numeric check at γ-2-1 seed=0: GT_a[0] = -G0*M*m/r² exactly (baseline), diff vs shifted_force Fx ≈ 8e-5."
- **physics-claim-checker**: **CONFIRM**. "My empirical measurements in docs/blocker-physics.md back this — truth-projected predictors tie or LOSE on the numeric channel for γ-2-1/δ-2-1/γ-7-1; only the +0.10 CAL-5 bonus differentiates."
- **bench-fixer-architect**: **CONFIRM**. "loader.py:179-204 `_pack` uses gt_fn closures hard-coding canonical laws … shifted_force from mirrorlab/shifts/* never imported by scorer; numeric.py:92-125 `_entry_predictor` closes over entry["params"] only, cf_params never reaches predictor. #2 measured truth-form predictors scoring ≤ baseline on every numeric channel of γ-2-1, δ-2-1, γ-7-1. My fix-options doc is built on this premise."

**No DISAGREE responses recorded.** No revisions were needed; all three independent reports were already mutually consistent before polling. There was no prior disagreement to surface — the three lines of investigation (static trace, dynamic simulation, fix architecture) reached the same conclusion in isolation.

---

## 4. What is *not* claimed by this consensus

- We do not claim every `S_scen` value reported in prior sweeps is meaningless. The bench does measure *something* real: (a)/(b) reward canonical-form recovery, (c) measures parameter sensitivity of frozen-coefficient submissions, and CAL-5 measures symmetry-label accuracy. The mismatch is between what is measured and what Paper 1 claims is measured.
- We do not claim `mirrorlab/shifts/*.py` modules are unused. They drive `sim.step()`, which is what the agent observes interactively. They simply do not enter the scoring path.
- We do not claim this affects all shift classes equally. Shifts whose true law lives in inputs the test grid already exposes (e.g. some γ-2-2 scale shifts that remain a function of `r`) may degrade gracefully under baseline-form GT.

---

## 5. Recommended next action

**Primary recommendation: Z + lite-X** (per bench-fixer-architect's fix-options doc §6).

- **Z** (reframe Paper 1): rewrite the headline claim from "discovery of γ/δ structural breaks" to "parameter-sensitivity probing of baseline-form submissions under modified-physics simulators, plus a symmetry-labeling bonus channel." Update `paper1/main.tex`, `docs/sprint4-figure-captions.md` (cliff → counterfactual parameter-sensitivity curve), and consistency docs (`docs/sprint4-paper-trail.md`, `docs/story.md`).
- **Lite-X** (truth-form GT + vocabulary expansion for 3-5 hot cells): pick γ-2-1, γ-7-1, δ-2-1 (audited) + fluid γ-10-1 (flagged in memory `project_mirrorlab_sprint3_readiness.md` as narrowest CAL-4 cell). Port their loader closures to call the shift module directly with expanded input vocab (`{x,y,z}` for ROT shifts, add `t` for T_TRANS shifts). Rerun ceiling + those cells only (~10% of API budget).

**Why this and not pure X+Y**: full X+Y restores every original paper claim but costs 50-70 engineer-hours, ~+1500 LOC, full sweep rerun (~24-48h API time). Z+lite-X is 12-20 hours, ~+250 LOC, ~10% rerun, and preserves a real truth-vs-baseline result on the headline cells while honestly reframing the rest. Z+lite-X is also a strict subset of X+Y, so escalation later wastes no work.

**Why not Y alone**: Y fixes only the (c) counterfactual leak — it leaves the dominant (a)/(b) truth-vs-baseline mismatch live (γ-7-1 truth still loses by 0.44 numeric). Solves the smaller problem at the cost of invalidating existing entries.

**Open questions deferred to user** (per fix-options §7):
1. Deadline pressure — determines whether to escalate Z+lite-X → X+Y.
2. CAL-5 = 0.10 mutability — if lite-X is adopted and GT carries broken-symmetry info, the bonus becomes partially redundant on those cells.
3. Hot-cell selection — γ-2-1, γ-7-1, δ-2-1, fluid γ-10-1 is the suggested set.
4. Attacker re-spec — `docs/sprint3-attacker-spec.md` lookup attackers may need updates if lite-X changes grid vocabulary.

---

## 6. Confidence

**HIGH.**

- Three independent investigators using three different methods (static trace, dynamic eval, architectural design) reached the same factual conclusion before any cross-talk.
- The static trace is numerically verified at a real seed (γ-2-1 seed=0): GT matches baseline to machine precision and differs from shifted truth.
- The empirical eval measures S_scen for truth vs baseline predictors across 3 shifts × 3 seeds, with results that *cannot* be explained under the alternative hypothesis (bench measures shift-discovery).
- All three teammates explicitly CONFIRMed; none DISAGREEd.

The factual finding is not in doubt. The only remaining decision space is the **fix choice** (Z+lite-X vs Y vs X+Y vs Z-only), which is a paper-scope and schedule judgment call for the user/team-lead.

---

## 7. References

- `/Data/tanh/phyLLM/docs/blocker-trace.md` (code-tracer)
- `/Data/tanh/phyLLM/docs/blocker-physics.md` (physics-claim-checker)
- `/Data/tanh/phyLLM/docs/blocker-fix-options.md` (bench-fixer-architect)
- `/tmp/blocker_eval.py` (physics-claim-checker's verification script)
