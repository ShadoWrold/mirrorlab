# Blueprint X+Y — Round 2 Final Review

**Reviewer**: final-reviewer (mirrorlab-blueprint team)
**Date**: 2026-05-27
**Target**: `docs/blueprint-xy.md` v2 (post-task-#3 revision)
**Standard**: would I bet $1000 that a competent AI assistant can execute this blueprint without coming back to ask design questions?

---

## §1 Verdict

**SHIP.**

The v2 revision closes all six critical issues raised in round-1 inline, locks the seven load-bearing §9 questions (Q2/Q3/Q5/Q6/Q8/Q9/Q10), inverts the DAG so Y plumbing ships first (T1), pins the step()-only scalar observables per cell, and codifies the §2.4 input-vs-coefficient disjointness invariant with a unit-test enforcement plan. The three §10 pushbacks (legacy-pathway regression rejection, test-count approximate, γ-2-1 as P0) are individually defensible: the first is logically required by §1.3 ("no backward-compat"), the second is a sub-agent deferral with negligible blast radius, and the third is acknowledged as a stress-test choice with tradeoff recorded. The blueprint is now executable end-to-end by parallel sub-agents from §5 DAG + Appendix A assignments; team-lead does not need to keep designing on the fly.

I would take the $1000 bet.

---

## §2 Re-run of round-1 checks on v2

### 2.1 Six critical issues from round-1: status

| Issue | Round-1 status | v2 status | Verdict |
|---|---|---|---|
| 2.1 step()-only shifts (5 → 6 missed kinetics γ-11-2) | BLOCK | §3.2.1 + §4 footer fixed; 7 cells locked with per-cell observable table | **CLOSED** |
| 2.2 Q2 ROT GT projection load-bearing | BLOCK | §9 Q2 RESOLVED, signed-\|F\|·r̂ inlined in §4 row 4 + propagated to rows 13/14/19/23/28/29 | **CLOSED** |
| 2.3 predictor signature 3 unstated reqs | BLOCK | §2.3 paragraphs (A)/(B)/(C) explicit; (B) documents the zip-min-length silent drop as **by design** for X.B | **CLOSED** |
| 2.4 Q8 disjointness load-bearing | BLOCK | §2.4 invariant + `_assert_builder_mutates_only` runtime guard + parametrized disjointness test over all 36 shifts | **CLOSED** |
| 2.5 Q10 canonicalization rule | BLOCK | §2.5 5-step rule + round-trip bijection test; **see §2.2 below — illustration has minor errors but task is self-correcting** | **CLOSED (with caveat)** |
| 2.6 ceiling fallback masks signature mismatch | BLOCK | §2.6 SignatureMismatchError + WARN log on first-call-per-(cell,seed) + stub exemption via `meta.expected_baseline` | **CLOSED** |

### 2.2 §2.5 canonicalization rule — illustration bugs

Verified against `counterfactual.py:87+` (`_LAW_PARAM_FIELDS`):

- **RLC γ-6-2 example wrong.** Blueprint §2.5 illustrates "RLC has `L0, L1, L2`" mapping to `L_0, L_1, L_2`, and "`M01, M02, M12` mutual inductances" preserving to `M_01, M_02, M_12`. **Actual fields**: `(L1, L2, R1, R2, C1, C2, M0, dM)`. There is no `L0`, no `M01/M02/M12`. The example references a fabricated schema.
- **Coulomb γ-5-2 ordering inconsistent.** Blueprint claims `(src1_q, src2_q, test_q) → (q_1, q_2, q_3)` "test is last by convention". Actual `_LAW_PARAM_FIELDS` order is `(k_e, xi, phi0, q_test, src1_q, src2_q)` — q_test appears 4th, not last. The example's stated convention contradicts the codebase order.
- **Coulomb γ-5-1 example OK.** `(k_e, q_src, q_test, chi)` → `(k_e, q_1, q_2, chi)` under the rule is unambiguous.

**Why this does not block SHIP**: §2.5 explicitly states "The dict is hand-built (not derived)" and §3.6 done-criteria adds a round-trip bijection unit test + superset-of-predictor-declared-kwargs property. A T14 sub-agent will write `_PREDICTOR_NAME_MAP[RLCGamma62Params]` by reading the actual Params dataclass — the illustration error misleads the example but not the task contract. The bijection test will catch any hand-built mistake. Recommend (non-blocking) follow-up commit fixing the §2.5 RLC + γ-5-2 illustrations to match codebase, but this is a docs polish, not a $1000-bet blocker.

### 2.3 Did v2 introduce new issues?

Searched the v2 diff surface for regressions:

- **§3.2.1 step()-only count went from 6 → 7** (added decay γ-12-2 to reject reaching into private `_integrated_rate`). Confirmed by reading the decay/kinetics/wave/optics module exports: rows 24, 27, 32, 33, 34, 35, 36 all need step()-projection. Net count of 7 is correct.
- **§4 row 35 (γ-12-2)** previously planned to call `_integrated_rate` (a private underscore-prefixed helper). v2 redirects to `step(t)["N"]` — uniform with other decay cells. No regression.
- **§5 DAG T1↔T2 swap** is clean: T1 (eval/numeric subgrid-c branch) has its own synthetic 3-tuple unit test (§6.2 sketch) and does not require any loader builder. The §5 rationale paragraph spells this out. Sub-agent can land T1 from blueprint alone.
- **§2.6 SignatureMismatchError** — walked through 3 predictor shapes (baseline-form `f(r,G,M,m)`, X+Y-form `f(x,y,z,G,M,m)`, kwargs-catchall `f(**kw)`). Gate logic (filtered-non-empty AND no `**kwargs`) plus `meta.expected_baseline` exemption gives correct behavior: stub baselines drop inputs silently and CLAMP (as designed for X.B); ceiling submissions with malformed signatures hard-fail (as required). No false-positive surface found.

---

## §3 Pushback evaluation (§10)

Three pushbacks. Each evaluated:

### 3.1 Legacy-pathway regression assertion — REJECTED in v2

Round-1 §3 bullet 4 asked for: "ceiling re-scored on OLD pre-XY grids reproduces sprint-3.5's ≥0.95 on γ-2-1". v2 rejects with: "the whole point of X+Y is that the old grids are wrong (`blocker-trace.md`), so reproducing ceiling numbers on them is not a stability signal".

**I agree.** Round-1's recommendation was defensive-coding hygiene; v2's rejection is logically correct. Keeping the old grid evaluation path alive would directly violate §1.3 ("no backward-compat layer"), require maintaining two parallel scoring code paths during P0, and the resulting "reproducibility check" would prove only that the OLD code still does its OLD (wrong) thing. The forensic copy in `docs/archive/pre-xy/` is the right answer. **Pushback convincing.**

### 3.2 Test-count "~25" approximate — KEPT APPROXIMATE

Round-1 §4 A.4 noted "~25 test files broken" is unaudited. v2 keeps the approximation, defers enumeration to T7-T11 sub-agents at touch-time.

**I agree.** Enumerating exact test file count at blueprint-time is busywork — the sub-agent rewriting `loader_shifts/hooke.py` will discover the broken tests when they fail and rewrite them in the same commit. The estimate doesn't drive any gate or budget downstream. **Pushback convincing.**

### 3.3 γ-2-1 as P0 (instead of δ-2-1) — KEPT

Round-1 §4 C.3 suggested δ-2-1 (T_TRANS, +t only) as a strictly simpler P0 to disambiguate failure modes; v2 keeps γ-2-1 as P0 with rationale "ROT-3D is the hardest cell so passing P0 on it is a stronger signal" and acknowledges the failure-ambiguity tradeoff (X.B-specific vs generic plumbing bug).

**I agree.** The risk asymmetry favors hardest-first: passing γ-2-1 P0 means every easier cell is unlocked; failing γ-2-1 P0 tells you something is broken AT THE SCAFFOLDING LEVEL even if you can't immediately pin X.B vs plumbing. The auditor's "secondary δ-2-1 smoke" is captured as a soft recommendation in §10 — sub-agent on T6 may opt-in. **Pushback convincing.**

---

## §4 Dry-run: sub-agent assigned T3 (gravity γ-2-1 builder)

Walking the P0 cell end-to-end as a fresh sub-agent reading only the blueprint + HANDOVER.md:

1. **Read §3.2 "Per-builder contract"** → return shape `(test_grids, cf_params, canonical_inputs)`. Clear.
2. **Read §4 row 4** → grid keys `(x, y, z)`; truth = `shifted_force((x,y,z), p)` → projected per Q2 = signed-|F|·r̂. Clear.
3. **Read §2.2 ROT sampling** → "half cone around n̂, half wide cone". Cone angles unstated. **Minor ambiguity** — sub-agent must pick numbers (e.g. 10° vs 60°). Resolvable empirically against §8.1 gate (spread ≥ 0.10); not a $1000-bet blocker because gate failure modes are enumerated in §8.1 ("re-bias direction sampling" listed as first cause).
4. **Read §9 Q9** → OOD (b) is 5× along `‖(x,y,z)‖` magnitude with same direction. Clear.
5. **Read §3.6 + §2.5** → `_PREDICTOR_NAME_MAP[GravityGamma21Params] = {"G0":"G", "M":"M", "xi":"xi"}`. From `_LAW_PARAM_FIELDS[GravityGamma21Params] = ("G0","M","xi")` and §2.5 rule (G0→G strips canonical-symbol-0). Clear.
6. **Implement builder** → ~60 LOC: sample 11 (x,y,z) points with biased direction, compute `F = shifted_force((x,y,z), p)`, project `gt = (F · r̂)`. For (c), call `perturb_params(p, magnitude=cf_magnitude)` 11 times. Clear.
7. **Hand off to T4 (ceiling predictor)** → §3.5 says `pred(x, y, z, G, M, m, xi)` returns signed-projection from `shifted_force`. Clear.
8. **Smoke** → §8.1 gate. Three concrete bounds. Clear.

**Where did I get stuck?** Only on the cone-angle hyperparameter in step 3, and that's an empirical tuning knob the §8.1 gate explicitly anticipates. No design-decision returns required.

---

## §5 Scope / cost sanity

- **LOC estimate**: ~450 loader.py net + ~700 loader_shifts/ + ~90 numeric.py + ~350 ceiling_agent.py + ~80 counterfactual.py + ~200 agent_stub + ~30 rescore.py + ~30 spec docs = **~1930 LOC**. Distributed across ~17 files. Realistic for a 12-domain refactor; ceiling_agent rewrite alone is ~350 LOC and is the long pole. Honest.
- **Test budget**: ~370 new test cases, ~50 rewrites. Wall-clock ~3-4 min claimed in §6.5 (the thermal δ-7-1 `solve_ivp` cache by `(seed, round(t,6))` is the load-bearing optimization here — without it, 30 seed-pass solves would explode this budget). Cache decision is locked at §9 Q5. **Plausible**, though "if slow, mark @pytest.mark.slow" is the right escape hatch.
- **Rerun cost**: R4 (sprint4 model sweep) ≈ 100% of sprint4 = ~4-6 h wall-clock + LLM cost. R5 deferred to camera-ready. **Honest** — not undercounted. R1/R3 (ceiling) is zero-LLM. R2 (lookup attacker) is ~10% of sprint-3.5. The user has the budget signal they need.
- **Parallelism**: T7-T11 (5 sub-agents on P1 domains) and T16-T22 (7 sub-agents on P2) is real — each owns a distinct `loader_shifts/<domain>.py` file with independent done criteria (§6.1 per-cell snapshot tests). No shared mutable state across sub-agents.

---

## §6 Specific items team-lead flagged

- **§3.2.1 step() observables**: 7 cells × 1 observable each = 7 choices. Each matches the agent prompt's `observables` declaration. wave δ-8-1 picks amplitude (envelope), optics δ-9-1 picks sin_theta_t (matches Snell), kinetics/decay all pick the obvious state scalar (C or N). **Not hand-waved** — each cell's observable is the same scalar the agent stub would predict from the canonical law, so ceiling-vs-baseline comparison is meaningful.
- **§2.5 RLC γ-6-2 + coulomb γ-5-1 walkthrough**: see §2.2 above. Illustration bugs present but task is self-correcting via the hand-built dict + bijection test in §3.6 done-criteria.
- **§3.7 stub fixture test**: done criterion is "(i) parses, (ii) evaluates without raising on canonical_inputs synthetic input, (iii) `inspect.signature` exposes declared kwargs". All three are mechanically checkable. Clear.
- **§2.6 SignatureMismatchError false-positive surface**: walked through baseline-form, X+Y-form, and `**kwargs`-catchall predictors. Gate fires correctly on ceiling submissions with declared canonical_inputs but mismatched signature; does not fire on stub baselines (exemption keyed on `meta.expected_baseline`); does not fire on `**kwargs`-catchall predictors. No false-positive case found.

---

## §7 Recommended (non-blocking) follow-ups

These do not gate SHIP; record them as v2.1 polish:

1. Fix §2.5 RLC illustration to use actual fields `(L1, L2, R1, R2, C1, C2, M0, dM)` instead of fabricated `L0/L1/L2/M01/M02/M12`.
2. Reconcile §2.5 coulomb γ-5-2 "test is last by convention" with actual `_LAW_PARAM_FIELDS` ordering (q_test 4th, src1_q/src2_q 5th/6th) — pick one and inline.
3. §2.2 ROT cone-angle defaults: suggest concrete (10°, 60°) split as starter, to be tuned at P0 gate.
4. Pre-commit hook for `docs/sprint*-data*.json` lacking `"xy_version": 1` — recorded in §10 as a known follow-up; capture as a v2.1 CI ticket.

---

## §8 Why I'd bet $1000

A competent AI assistant assigned the P0 task (T0→T6) can execute end-to-end without returning for design clarification because:

1. Every load-bearing §9 question is resolved inline with a concrete decision and rationale.
2. The two unstated requirements in §2.3 (signature filtering, alias-drop semantics) are now explicit; the by-design alias-drop is the precise mechanism that makes X.B work.
3. §8.1 gate has three quantitative bounds and an enumerated list of three failure causes with remediation steps.
4. Y plumbing (T1) is unit-testable against a synthetic 3-tuple without any loader being live — the chicken-and-egg dependency is broken.
5. The §2.4 disjointness invariant is enforced both by unit test and by a runtime guard in builders — sub-agents cannot accidentally cross the input-vs-coefficient line.
6. The Appendix A table maps every work item to a section, a file, and a done-criteria source.

The remaining ambiguities (cone angles, §2.5 illustration bugs) have empirical gates that catch errors within a sub-second smoke. Sub-agents will not need to escalate design questions back to team-lead.

— end round 2 review — SHIP —
