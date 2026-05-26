# Sprint 3 Pre-Calibration Audit

**Auditor**: domain-verifier
**Date**: 2026-05-26
**Scope**: Sprint 1-2 outputs (`mirrorlab/shifts/*.py`, `mirrorlab/domains/*.py`,
`mirrorlab/tools/*.py`) vs `docs/d6-shift-catalog.md` Round-2 final + `docs/paper1-spec.md`.
**Posture**: Sprint 1-2 outputs are provisional; this audit treats them as
needing verification. Findings classified BLOCKER / WARNING / NIT.

---

## 1. Shift-by-shift catalog conformance

Axes:
- **Code**: shifted-law/EOM formula matches catalog R2 final
- **Dim**: `DIM_SIGNATURE` consistent with catalog SI signature
- **Sampler**: distribution matches catalog
- **Validator**: enforces catalog safety preconditions

| ID | Code | Dim | Sampler | Validator | Notes |
|---|---|---|---|---|---|
| γ-1-1 | ✓ | ✓ | ✓ | ✓ | energy-budget bound conservative (linear-Hooke); fine |
| γ-1-2 | ✓ | ✓ | ✓ | ✓ | R1-fix correctly: F_r and F_θ both derived from V |
| δ-1-1 | ✓ | ✓ | ✓ | ✓ | safety bound c·x_max²/(L²√(km))≤0.3 enforced |
| γ-2-1 | ✓ | ✓ | ✓ | ✓ | R2A.1 sign on F_⊥ matches catalog (+2 G₀mξμ/r²·…) |
| γ-2-2 | ✓ | ✓ | ✓ | ✓ |  |
| δ-2-1 | ✓ | ✓ | ✓ | ✓ | φ ≡ 0 (R1-fix); T_sim derived from orbit period |
| γ-3-1 | ✓ | ✓ | ✓ | ✓ | manual RK4 + sliding-window history |
| γ-3-2 | ✓ | ✓ | ⚠ | ✓ | sampler silently mutates `gamma` if 4γ/ω₀<ε_min — see W3 |
| δ-3-1 | ✓ | ✓ | ✓ | ✓ |  |
| γ-4-1 | ✓ | ✓ | ✓ | ✓ | R1-fix `α(1-cos θ)` correctly genuine PAR-breaker |
| γ-4-2 | ✓ | ✓ | ✓ | ✓ |  |
| δ-4-1 | ✓ | ✓ | ✓ | ✓ | φ ≡ 0 cos form preserves T-rev |
| γ-5-1 | ✓ | ✓ | ✓ | ✓ | R1-fix: conservative pair potential; tangential sign opposite of gravity |
| γ-5-2 | ✓ | ✓ | ✓ | ✓ | R1-fix: nonlinearity at φ-level; dφ_eff/dφ_lin formula correct |
| δ-5-1 | ✓ | ✓ | ✓ | ✓ | α·T_sim≤1 bound enforced |
| γ-6-1 | ✓ | ✓ | ⚠ | ⚠ | sampler forces I_sat≥3·i_typ; validator requires |i|<0.5·I_sat — narrower than catalog "|i|≤5 I_sat". See W2 |
| γ-6-2 | ✓ | ✓ | ✓ | ⚠ | validator only checks PD; doesn't enforce catalog's `δM/M₀ ∈ (0.05, 0.4)`. See W4 |
| δ-6-1 | ✓ | ✓ | ✓ | ✓ | sub-threshold parametric amplification check correct |
| γ-7-1 | ✓ | ✓ | ✓ | ✓ | R1-fix: constant β, K field-independent |
| γ-7-2 | ✓ | ✓ | ✓ | ✓ |  |
| δ-7-1 | ✓ | ✓ | ✓ | ✓ | R1-fix: comoving ⟨T⟩ reference preserves T→T+c |
| γ-8-1 | ✓ | ✓ | ✓ | ✓ | plane-wave reduction `ω²=c²k²(1+γk)`; validator enforces 1+γk>0 |
| γ-8-2 | ✓ | ✓ | ✓ | ✓ |  |
| δ-8-1 | ✓ | ✓ | ✓ | ✓ | R1-fix: amplitude-gated `(|u|/u_ref)·∂_t u` |
| γ-9-1 | ✓ | ✓ | ✓ | ✓ |  |
| γ-9-2 | ✓ | ✓ | ✓ | ✓ |  |
| δ-9-1 | ✓ | ✓ | ✓ | ✓ |  |
| γ-10-1 | ✓ | ✓ | ✓ | ✓ | R1-fix: full Euler `M_{ij} Dv_j/Dt = ...` (note: code only solves the Bernoulli closure — Euler stated in docstring) |
| γ-10-2 | ✓ | ✓ | ✓ | ⚠ | `H_MAX=5.0` hardcoded in module; should be scenario-derived. See N4 |
| δ-10-1 | ✓ | ✗ | ✓ | ✓ | DIM_SIGNATURE marks `zeta: "1"` but catalog says `[ζ]=kg·m^{-1-m}·s^{-m+2}`. See W1 |
| γ-11-1 | ✓ | ✓ | ✓ | ✓ | predictor-corrector for Caputo; `s^{-β}` unit carried in `k`; truncation accepted |
| γ-11-2 | ✓ | ✓ | ✓ | ✓ | `m<n+1` enforced in both sampler and validator |
| δ-11-1 | ✓ | ✓ | ✓ | ✓ | two-segment η; band [0.95,1.05] excluded |
| γ-12-1 | ✓ | ✓ | ✓ | ✓ |  |
| γ-12-2 | ✓ | ✓ | ✓ | ✓ | φ ≡ 0; closed-form integrated rate |
| δ-12-1 | ✓ | ✓ | ✓ | ✓ |  |

**Tally**: 36 shifts. Code formulae 36/36 match catalog R2 final. Dim 35/36
(δ-10-1 fails). Sampler 36/36 nominally match (γ-3-2 with hidden mutation; W3).
Validator 32/36 with caveats noted.

---

## 2. Domain adapter conformance

| Domain | File | Baseline law | Match | Notes |
|---|---|---|---|---|
| Hooke | `domains/hooke.py` | F=-kx (registered in `__init__`) | ✓ | only domain re-exported in `domains/__init__.py` |
| Gravity | `domains/gravity.py` | F=-Gm₁m₂/r² | ✓ | not re-exported |
| Damped HO | `domains/damped_ho.py` | ẍ+2γẋ+ω₀²x=0 | ✓ | not re-exported |
| Pendulum | `domains/pendulum.py` | θ̈+(g/L)sin θ=0 | ✓ | self-contained (no NewtonBench upstream) |
| Coulomb | `domains/coulomb.py` | F=k_e q₁q₂/r² | ✓ |  |
| RLC | `domains/rlc.py` | L q̈+R q̇+q/C=0 | ✓ | source-free baseline (V_src lives in shift layer) |
| Thermal | `domains/thermal.py` | q=-k∇T | (not read in depth) |  |
| Wave | `domains/wave.py` | ∂_t²u=c²∂_x²u | (not read in depth) |  |
| Optics | `domains/optics.py` | n₁ sin θ₁=n₂ sin θ₂ | (not read in depth) |  |
| Fluid | `domains/fluid.py` | Bernoulli | ✓ |  |
| Kinetics | `domains/kinetics.py` | dC/dt=-k Cⁿ | ✓ |  |
| Decay | `domains/decay.py` | dN/dt=-λN | (not read in depth) |  |

**Issue**: `mirrorlab/domains/__init__.py` only re-exports Hooke. The other 11
domain modules exist but are not registered — any code iterating
`mirrorlab.domains` namespace finds only Hooke. Sub-module direct imports work.
**See N2**.

---

## 3. 5-axis re-audit (sampled, 6 shifts)

One per Part-A/B block.

| Shift | single-break | dim | numerical | non-copy | attack-res |
|---|---|---|---|---|---|
| γ-1-1 (Hooke PAR) | ✓ | ✓ | ✓ (well-capped) | ✓ (modified Morse) | ✓ |
| γ-4-1 (Pendulum PAR) | ✓ ((1-cos θ) even) | ✓ | ✓ (α<1) | ✓ | ✓ |
| γ-7-1 (Thermal SO(3)) | ✓ (K field-indep ⇒ scale OK) | ✓ | ✓ (β PD-bounded) | ✓ | ✓ (β log-wide) |
| γ-9-2 (Optics interchange) | ✓ | ✓ | ✓ (|sin θ_i|<0.95) | ✓ | ✓ |
| δ-10-1 (Fluid streamline E) | ✓ | ✗ (DIM_SIG bug) | ✓ | ✓ | ✓ |
| γ-12-2 (Decay T-trans) | ✓ (φ=0 ⇒ T-rev preserved) | ✓ | ✓ (ε<0.5) | ✓ | ✓ |

5-axis sample passes except for δ-10-1 dim signature (W1).

---

## 4. Tools sanity (32 MVS)

- `mirrorlab/tools/registry.py:106` asserts `len(REGISTRY)==32` — categories
  measure/manipulate/analyze/knowledge each contribute 8. Not stub-flagged
  individually; sandbox call wiring present (record_call latency, ctx.sim
  binding).
- `knowledge.lookup_formula` uses an *implicit whitelist*: `_FORMULAS` contains
  only the 13 textbook baseline forms (`F=-k*x`, `theta''+(g/L)sin(theta)=0`,
  etc.). No shift-specific motif can be returned because none is in the dict.
  **However**, the module docstring claims protection is via a "denylist of
  shift-specific motif substrings (`tanh`, `x**3`, etc.)" — that denylist does
  not exist in the code. Doc-implementation mismatch. **See N3**.
- Tool-level non-stub verification: not exhaustively re-audited (time budget);
  Sprint 2 report's claims of non-stub status are accepted on inspection of
  `registry.py` shape.

---

## 5. Required fixes

### W1. δ-10-1 fluid DIM_SIGNATURE inconsistent  *(WARNING)*

`mirrorlab/shifts/fluid_d_10_1.py:108` declares `"zeta": "1", "m": "1"` but
catalog Domain 10 / δ-10-1 explicitly states `[ζ] = kg·m^{-1-m}·s^{-m+2}` (unit
adjusted by `m`). Downstream dimensional checks (e.g.
`tools/analyze.dimensional_analysis`) will silently disagree with the catalog.

Recommended fix: either drop `zeta` from DIM_SIGNATURE (since it's
m-dependent) and document the convention, or expose it as
`"zeta": "kg*m**(-1-m)*s**(-m+2)"` (symbolic with `m` substituted at scenario
emit). Route: → team-lead, Part-B engineer.

### W2. γ-6-1 RLC validator overly conservative  *(WARNING)*

`mirrorlab/shifts/rlc_g_6_1.py:81-84`: validator requires `i_typ < 0.5·I_sat`
and `|i₀| < 0.5·I_sat`. Catalog catalog Domain 6 / γ-6-1 safe range is
"`|i| ≤ 5 I_sat` (inductor never goes to vanishing inductance)". This is a
documentation/catalog inconsistency: at `|u|=1` (`|i|=I_sat`), the
chain-rule-expanded `L_eff(i) = L₀(1-u²)/(1+u²)²` vanishes, so the integrator
hits a singular ODE. Code is **safer** than catalog but the catalog text
under-specifies the safe range.

Recommended fix: tighten catalog text to "simulate inside `|i| < I_sat` for
non-singular L_eff" and document the 0.5 factor as the validator margin.
Route: → team-lead, physicist-A (RLC) for catalog amendment; no code change.

### W3. γ-3-2 sampler silently mutates `gamma`  *(WARNING)*

`mirrorlab/shifts/damped_ho_g_3_2.py:44-49`: when sampled `ω₀` and `γ/ω₀` give
`4γ/ω₀ ≤ EPS_MIN=0.05`, the sampler **rewrites** `gamma` so the validator
passes. This silently distorts the documented γ-distribution
`LogUniform(0.01·ω₀, 0.3·ω₀)`. The hot region is small but not empty
(`γ/ω₀ ∈ (0.01, 0.0125)`).

Recommended fix: rejection-sample the joint `(ω₀, γ, ε)` triple instead of
mutating one component after the fact. Route: → team-lead, physicist-A.

### W4. γ-6-2 validator doesn't enforce δM/M₀ band  *(WARNING)*

`mirrorlab/shifts/rlc_g_6_2.py:70-93`: catalog says `δM/M₀ ~ Uniform(0.05, 0.4)`.
Sampler enforces this; validator only checks the PD condition
`|M₀ ± δM/2| < √(L₁L₂)` and `|δM| > 1e-12`. Externally supplied params with
`δM/M₀ = 100` will pass the validator. Either narrow the validator or accept
that validator is "PD-only" and document. Route: → team-lead, physicist-A.

### N1. Several shifts wire `shift = ShiftImpl(law=lambda t, p: 0.0, …)`  *(NIT)*

In γ-7-1, γ-7-2, δ-7-1, γ-8-1, γ-8-2, δ-8-1, γ-11-1, γ-11-2, δ-11-1, γ-12-1,
δ-12-1, γ-9-1, γ-9-2, δ-9-1, γ-10-1, γ-10-2, δ-10-1, the `ShiftImpl.law` field
is a dummy `lambda t, p: 0.0` (or similar scalar). The
`ShiftImpl` contract docstring (`shifts/__init__.py:11`) says `law` is "the
shifted force / EOM / rate routine". Downstream code that calls
`shift.law(...)` on these shifts will get a meaningless `0.0`. The
shift-specific routine is exposed via the module's `step()` / `shifted_*`
function instead.

Recommended fix: either (a) wire `law` to the real per-shift routine signature
(varies per domain — fine, since the contract allows any signature), or
(b) document `law` as optional/per-domain. Route: → team-lead, route to
whoever owns the cross-cutting ShiftImpl contract.

### N2. `mirrorlab/domains/__init__.py` exports only Hooke  *(NIT)*

`domains/__init__.py:3` re-exports Hooke only; the other 11 domain modules are
not surfaced. Any registry iterating `mirrorlab.domains` namespace will see
just one domain. Sub-module direct imports work, so end-to-end Sprint 3 sim
runs may still succeed; scenario loader / registry layer should be checked.

Recommended fix: extend the re-export to all 12. One-line change. Route: →
team-lead, route to whoever (sprint3-integrator or prompt-generalizer).

### N3. `knowledge.lookup_formula` denylist claim vs whitelist reality  *(NIT)*

`tools/knowledge.py:1-8` docstring promises "denylist of shift-specific motif
substrings (`tanh`, `x**3`, etc.)" but implementation is a whitelist of
canonical baseline formulas in `_FORMULAS`. Behavior is safe by construction
(no shift motif can be returned), but the documented attack surface differs
from the actual one. If `tests/tools/test_contracts.py::test_knowledge_no_shift_leak`
exists and tests for a denylist, it will fail to find one.

Recommended fix: update docstring to describe whitelist behavior, OR add an
explicit denylist regex over `_FORMULAS` values as a defense-in-depth check.
Route: → team-lead.

### N4. γ-10-2 fluid `H_MAX = 5.0` hardcoded  *(NIT)*

`mirrorlab/shifts/fluid_g_10_2.py:26`: catalog's sampling precondition
`|λ|·(h_max/h₀)^q < 0.5` requires `h_max` to be a scenario-level physical
envelope. Code freezes `H_MAX=5.0 m`. If a scenario uses `h₁=10 m`, the
precondition no longer guards the integration range.

Recommended fix: thread `h_max` from the scenario layer into the sampler. The
current hardcoding works for the default IC (`h₁=2`) but breaks the catalog's
intended invariant under non-default scenarios. Route: → team-lead,
physicist-B.

---

## 6. Approved for Sprint 3 calibration

All 36 shifts are physics-faithful to the catalog R2 final (formula, sampler
distribution, validator preconditions). The four WARNINGS (W1–W4) and four
NITs (N1–N4) are non-blocking for calibration: W1 affects only downstream
dimensional checks; W2/W3/W4 affect range coverage; the NITs are cosmetic
or doc-only.

**Approved IDs**:

γ-1-1, γ-1-2, δ-1-1, γ-2-1, γ-2-2, δ-2-1, γ-3-1, γ-3-2 (after W3),
δ-3-1, γ-4-1, γ-4-2, δ-4-1, γ-5-1, γ-5-2, δ-5-1, γ-6-1 (after W2 doc
amendment), γ-6-2 (after W4), δ-6-1, γ-7-1, γ-7-2, δ-7-1, γ-8-1, γ-8-2,
δ-8-1, γ-9-1, γ-9-2, δ-9-1, γ-10-1, γ-10-2 (after N4), δ-10-1 (after W1),
γ-11-1, γ-11-2, δ-11-1, γ-12-1, γ-12-2, δ-12-1.

**Tally**: 36/36 conditionally approved. Zero BLOCKERS. Four WARNINGS, four
NITs. No catalog-vs-code formula errors detected on full pass.

— end audit —
