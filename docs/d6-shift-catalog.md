# D6 Shift Catalog — γ/δ Counterfactual Physics Library

> v0.1 draft, 2026-05-25. Source: `idea-design-notes.md` D6 spec + `r1-physics-consistency.md`.
> Conventions: SI throughout. Each shift breaks **exactly one** symmetry / conservation law of the *baseline*; all other listed invariants verified to hold (analytic + to be cross-checked numerically by invariant-checker). Random distributions are *catalog-level placeholders* — final ranges set during scenario calibration.
> Cross-domain re-skinning is the design preference: most shifts borrow a *mathematical motif* from a different physics domain rather than copying a named effect inside the same domain.
> Symmetry labels here are internal ground-truth only; they MUST NOT be exposed to the evaluated AI.

---

# Part A: Domains 1–6 (mechanics + EM)

Domain selection rationale: D6 v1 prefers mechanics-heavy coverage. We pick the six NewtonBench domains where survey-verified shifts cleanly isolate one symmetry while remaining numerically tame: **Hooke spring, Newtonian gravity, Damped harmonic oscillator, Pendulum, Coulomb force, RLC circuit**. Together they cover symmetries `LIN, PAR, ROT, SCALE/Bertrand, T-trans, T-rev, Q-conservation, Onsager-reciprocity` — eight distinct breaks across 18 shifts.

---

## Domain 1: Hooke spring (1D & 2D)

**Baseline law**: `F = −k x`. Dim: `[F]=kg·m·s⁻²`, `[k]=kg·s⁻²`, `[x]=m`.
**Invariants**: T-trans (E conserved), PAR (`x→−x`), T-rev, LIN, scale-free (no internal length), in 2D additionally ROT.

### Tier-1 (γ) — structural / symmetry-breaking

- **shift-γ-1-1 — saturating asymmetric stiffness**
  - Motivation: bond-like asymmetry between extension and compression.
  - Broken: PAR (`x→−x`).
  - Modified law: `F(x) = −k x · [1 + η tanh(x/x₀)]`.
  - Dim: `[η]=1, [x₀]=m`. Inputs `x [m]` → output `F [N]`.
  - Retained: T-trans (autonomous → E exists, with `V(x)=∫₀ˣ k s(1+η tanh(s/x₀)) ds` well-defined and bounded below), T-rev (no `ẋ`), LIN-in-the-small (`|x|≪x₀`).
  - Sampling: `k ~ LogUniform(1, 100) N/m`; `η ~ Uniform(0.1, 0.8)`; `x₀ ~ LogUniform(0.05, 2.0) m`.
  - Safe range: simulate `|x| ≤ 4 x₀` (potential well stays single-minimum, no escape).
  - Lit-angle (not copied): asymmetric Morse-like wells — we replace exponential tail with bounded `tanh` to keep `F` linear at large `|x|`.

- **shift-γ-1-2 — 2D anisotropic stiffness (cross-domain re-skin of birefringence)**
  - Motivation: re-skin uniaxial birefringence (optics) into mechanics.
  - Broken: ROT (planar isotropy).
  - Modified law: force derived from potential `V(r, θ) = ½ K(θ) r²`, `K(θ) = k₀ [1 + ξ cos(2(θ − φ))]`, `F = −∇V` ⇒
    - radial component `F_r = −K(θ) r`,
    - tangential component `F_θ = −(1/r) ∂V/∂θ = k₀ ξ r · sin(2(θ − φ))`.
    The tangential piece is the structural source of `L_z` non-conservation (the Noether charge of the broken ROT).
  - Dim: `[k₀]=kg·s⁻²`, `[ξ]=1`, `[φ]=rad`. Inputs `(x,y) [m]` → `F [N]`.
  - Retained: T-trans (E exists because `V` is time-independent and `F = −∇V` is conservative), T-rev (no `ẋ`), PAR (`r→−r ⇒ θ→θ+π`, `cos(2θ+2π)=cos(2θ)`, `sin(2θ+2π)=sin(2θ)`), LIN, S-trans about origin.
  - Angular momentum `L_z` is **not** retained (consistent: ROT is the single broken symmetry, and `L_z` is its Noether charge).
  - Sampling: `k₀ ~ LogUniform(1, 100) N/m`; `ξ ~ Uniform(0.1, 0.7)`; `φ ~ Uniform(0, π)`.
  - Safe: `ξ < 1` ensures positive stiffness in all directions.

### Tier-2 (δ) — conservation-law violation

- **shift-δ-1-1 — amplitude-conditioned drag (cross-domain re-skin of Stokes drag)**
  - Motivation: re-skin viscous drag into a Hookean toy where dissipation is amplitude-gated.
  - Broken: **Energy conservation** (T-trans is *preserved* — autonomous — but dE/dt < 0 along trajectory because of velocity-coupled force; this is the standard "T-trans intact, E not conserved" pattern for explicit dissipation embedded in the force law).
  - Modified law: `F = −k x − c (x²/L²) ẋ`.
  - Dim: `[c]=kg/s`, `[L]=m`. Input `(x, ẋ)` → `F [N]`.
  - Retained: T-trans (autonomous), PAR (under `x→−x, ẋ→−ẋ`: `F → −F`), 1D-isotropy.
  - T-rev: lost as standard consequence of dissipation (counted as part of the energy-conservation break — no other independent symmetry violated).
  - Sampling: `k ~ LogUniform(1, 100) N/m`; `c ~ LogUniform(1e-3, 1) kg/s`; `L ~ LogUniform(0.5, 5) m`.
  - Safe: `c x_max² / (L² · √(km)) ≤ 0.3` keeps the system under-critically damped.
  - Lit-angle: nonlinear damping families (square-law drag), but we attach the `x²/L²` envelope so dissipation vanishes near equilibrium — no published canonical name.

---

## Domain 2: Newtonian gravity (two-body)

**Baseline law**: `F = −G m₁ m₂ r̂ / r²`. Dim: `[G]=m³·kg⁻¹·s⁻²`.
**Invariants**: T-trans (E), S-trans (p), ROT (L), T-rev, PAR, GAL, Bertrand closure of bound orbits, equivalence principle.

### Tier-1 (γ)

- **shift-γ-2-1 — quadrupolar anisotropic coupling**
  - Motivation: re-skin anisotropic-material elasticity into the gravitational coupling, with zero monopole shift so far-field tests look standard.
  - Broken: ROT.
  - Modified law: derived from potential `V(r, r̂; n̂) = −G₀ m₁ m₂ · [1 + ξ ((r̂·n̂)² − ⅓)] / r`, force `F = −∇V`. Explicit components (with `μ ≡ r̂·n̂`):
    - radial `F_r = −G₀ m₁ m₂ [1 + ξ(μ² − ⅓)] / r²`,
    - tangential `F_⊥ = +(2 G₀ m₁ m₂ ξ μ / r²) · (n̂ − μ r̂)`.
    The tangential piece supplies the torque that breaks `L` conservation (Noether-paired with ROT).
  - Dim: `[G₀]=m³·kg⁻¹·s⁻²`, `[ξ]=1`, `n̂` dimensionless unit. Inputs `(r̂, r [m])` → `F [N]`.
  - Retained: T-trans (E conserved — `V` time-independent and `F = −∇V`), S-trans, T-rev, PAR (`r→−r ⇒ μ→−μ`, `μ²` even, `n̂−μr̂ → −(n̂−μr̂)` flips with `r̂` ⇒ `F` transforms as a proper vector), GAL.
  - L is **not** conserved (only-symmetry-broken is ROT — L is its Noether charge).
  - Sampling: `G₀ = G·LogUniform(0.5, 2)`; `ξ ~ Uniform(0.05, 0.4)`; `n̂ ~ Uniform on S²`.
  - Safe: `ξ < 0.5` keeps the bracketed factor positive at every direction (`μ²−⅓ ∈ [−⅓, ⅔]` ⇒ factor ∈ `[1 − ξ/3, 1 + 2ξ/3] > 0`).
  - Lit-angle: Bianchi anisotropy / SME gravity, but the **traceless quadrupole** structure with zero monopole removes the Yukawa-like global rescaling — distinct functional form.

- **shift-γ-2-2 — Lorentzian range bump (Bertrand-breaking)**
  - Motivation: introduce an internal length scale that perturbs closed orbits without changing far-field `1/r²`.
  - Broken: SCALE invariance (Bertrand closure of bound orbits → orbits precess).
  - Modified law: `F = −G m₁m₂ /r² · [1 + α (r/r₀) / (1 + (r/r₀)²)]`.
  - Dim: `[α]=1`, `[r₀]=m`. Inputs `r [m]` → `F [N]`.
  - Retained: ROT (still central → L conserved), T-trans (E exists), T-rev, PAR, GAL, S-trans.
  - Sampling: `α ~ Uniform(0.05, 0.5)`; `r₀ ~ LogUniform(0.1, 10) · r_typical`.
  - Safe: enforce `r ≥ 1e-3 · r₀` to avoid near-collision singularity (already present in baseline `1/r²`, not worsened).
  - Lit-angle: fifth-force / Yukawa screening; we use a peaked Lorentzian envelope rather than the canonical exponential, and apply it as a multiplicative bump on `1/r²` rather than an additive term.

### Tier-2 (δ)

- **shift-δ-2-1 — slow harmonic modulation of G**
  - Motivation: re-skin parametric pumping (acoustics) into the gravitational constant.
  - Broken: T-trans (E not conserved).
  - Modified law: `F = −G(t) m₁m₂ r̂/r²`, `G(t) = G₀ [1 + β cos(ω_G t)]` (phase fixed at 0 so `G(t)` is even in `t` about `t=0`).
  - Dim: `[β]=1`, `[ω_G]=s⁻¹`. Inputs `(r̂, r [m], t [s])` → `F [N]`.
  - Retained: ROT (central force ⇒ L conserved), S-trans (p conserved), PAR, T-rev (cosine is even in `t` about `t=0`; only T-trans is the broken symmetry).
  - Sampling: `G₀ = G·LogUniform(0.5, 2)`; `β ~ Uniform(0.05, 0.3)`; `ω_G ~ LogUniform(1e-4, 1e-2) · ω_orbit`. No random phase.
  - Safe: `β·ω_G·T_sim ≤ 0.5` so net drift on `G` over the simulation window is bounded.
  - Lit-angle: Dirac LNH (linear `G(t)` drift) — we replace with a *bounded* sinusoidal modulation so the simulation cannot run away.

---

## Domain 3: Damped harmonic oscillator

**Baseline law**: `ẍ + 2γ ẋ + ω₀² x = 0`. Dim: `[γ]=s⁻¹`, `[ω₀]=s⁻¹`.
**Invariants of the baseline** (post-damping): T-trans (autonomous), PAR (`x→−x`), LIN. (Note: T-rev and E already broken by `2γẋ` — these are not available targets for further γ shifts in this domain.)

### Tier-1 (γ)

- **shift-γ-3-1 — amplitude-memory stiffness (cross-domain re-skin of nonlinear acoustics)**
  - Motivation: stiffness slowly tracks recent oscillation amplitude — borrowed from hysteretic granular media.
  - Broken: LIN.
  - Modified law: `ẍ + 2γẋ + ω₀²·[1 + κ ⟨x²⟩_τ / x_ref²]·x = 0`, where `⟨x²⟩_τ = (1/τ)∫_{t−τ}^t x²(s) ds`.
  - Dim: `[κ]=1`, `[τ]=s`, `[x_ref]=m`. Inputs `(x, ẋ, history)` → equation of motion.
  - Retained: T-trans (window slides with `t`), PAR (`x²` even). T-rev / E already absent from baseline.
  - Sampling: `ω₀ ~ LogUniform(0.5, 10) rad/s`; `γ/ω₀ ~ LogUniform(0.01, 0.3)`; `κ ~ Uniform(0.05, 0.5)`; `τ ~ Uniform(0.5, 5)/ω₀`; `x_ref ~ LogUniform(0.1, 2) m`.
  - Safe: `κ ≤ 0.6` keeps effective `ω` real and bounded.
  - Lit-angle: Duffing-style stiffness, but the **amplitude is a running mean over a finite window**, not the instantaneous value — distinguishes it from any standard named oscillator.

- **shift-γ-3-2 — slow parametric pumping with damping**
  - Motivation: pump the spring slowly enough to stay below the principal Mathieu tongue.
  - Broken: T-trans.
  - Modified law: `ẍ + 2γẋ + ω₀²·[1 + ε cos(Ω_p t)] x = 0`.
  - Dim: `[ε]=1`, `[Ω_p]=s⁻¹`.
  - Retained: PAR, LIN.
  - Sampling: `ε ~ Uniform(0.05, 0.3)`; `Ω_p ~ Uniform(0.3, 1.7) ω₀` (deliberately *off* 2ω₀ and ω₀ to avoid principal/secondary parametric resonance).
  - Safe: `ε < 4γ/ω₀` (sub-threshold parametric instability).

### Tier-2 (δ)

- **shift-δ-3-1 — amplitude-gated damping sign reversal**
  - Motivation: damping becomes anti-damping inside a "core" region, dissipation outside.
  - Broken: monotone energy dissipation (the available conservation-law analog in this dissipative baseline). The system spontaneously settles onto a limit cycle.
  - Modified law: `ẍ + 2γ·(|x|/L − 1)·ẋ + ω₀² x = 0`.
  - Dim: `[L]=m`. Inputs `(x, ẋ)` → equation of motion.
  - Retained: T-trans, PAR (`x→−x, ẋ→−ẋ` keeps equation invariant), LIN-in-stiffness.
  - Sampling: `ω₀ ~ LogUniform(0.5, 10)`; `γ/ω₀ ~ LogUniform(0.01, 0.2)`; `L ~ LogUniform(0.1, 2) m`.
  - Safe: limit-cycle radius `~2L`; total mechanical energy bounded by `2 k L²`.
  - Lit-angle: van der Pol provides the *idea* of state-gated negative damping; we use a piecewise-linear envelope `(|x|/L − 1)` instead of the `(1 − x²)` polynomial so the threshold geometry is qualitatively different.

---

## Domain 4: Pendulum (planar, rigid arm)

**Baseline law**: `θ̈ + (g/L) sin θ = 0`. Dim: `[g/L]=s⁻²`.
**Invariants**: T-trans (E), `θ→−θ` (PAR), T-rev, reflective symmetry about the vertical.

### Tier-1 (γ)

- **shift-γ-4-1 — asymmetric vertical (PAR break)**
  - Motivation: re-skin a "biased rotor" potential (molecular physics) into the planar pendulum — add an even-in-θ piece to the restoring torque so the equation of motion loses its `θ→−θ` invariance.
  - Broken: PAR (`θ→−θ`).
  - Modified law: `θ̈ + (g/L)·sin θ + (g/L)·α·(1 − cos θ) = 0`.
  - Dim: `[α]=1`. Inputs `θ [rad]` → `θ̈ [rad·s⁻²]`.
  - Retained: T-trans (autonomous → E exists with `V(θ) = (g/L)(1−cos θ) + (g/L) α (θ − sin θ)`, both terms well-defined and bounded below near `θ=0`), T-rev (no `θ̇`). Stable equilibrium at `θ=0` preserved: `V'(0)=0`, `V''(0)=g/L > 0`.
  - PAR check: `(1−cos θ)` is even, `sin θ` is odd ⇒ under `θ→−θ`, `θ̈` flips sign but the `(g/L) α (1−cos θ)` term does not ⇒ EOM not invariant ⇒ PAR genuinely broken.
  - Sampling: `g/L ~ LogUniform(1, 100) s⁻²`; `α ~ Uniform(0.05, 0.5)`.
  - Safe: `α < 1` keeps the local linearization at `θ=0` stable and prevents secondary equilibria within the swing window `|θ| ≤ π/2`.
  - Lit-angle: tilted-washboard potentials of Josephson dynamics provide the *idea* of asymmetric pendulum potentials; we use `α(1−cos θ)` rather than a constant tilt `−αθ`, so the system remains periodic and the bias vanishes at equilibrium.

- **shift-γ-4-2 — height-graded gravity (S-trans break)**
  - Motivation: borrow tidal gradient from celestial mechanics, re-skin onto a tabletop pendulum.
  - Broken: vertical S-trans (translational invariance along gravity axis).
  - Modified law: `θ̈ + (g₀/L)·[1 − α·(L(1−cos θ))/H]·sin θ = 0`.
  - Dim: `[α]=1`, `[H]=m`.
  - Retained: T-trans (E exists; potential `V(θ) = m g₀ L (1−cos θ) − m g₀ α L²/(2H)(1−cos θ)²`), PAR (`θ→−θ` leaves `(1−cos θ)` invariant), T-rev.
  - Sampling: `g₀/L ~ LogUniform(1, 100) s⁻²`; `α ~ Uniform(0.02, 0.3)`; `H ~ LogUniform(0.5, 50) · L`.
  - Safe: `α·L/H < 0.5` keeps effective gravity positive over the swing range.

### Tier-2 (δ)

- **shift-δ-4-1 — off-resonant gravity modulation**
  - Motivation: parametric drive at a frequency deliberately chosen *off* the parametric instability tongues.
  - Broken: T-trans (E not conserved).
  - Modified law: `θ̈ + (g(t)/L)·sin θ = 0`, `g(t) = g₀·[1 + ε cos(Ω t)]`.
  - Dim: `[ε]=1`, `[Ω]=s⁻¹`.
  - Retained: PAR, T-rev (cosine is even about `t=0`; with random `Ω` only T-trans is broken by the catalog's convention — `φ` is set to 0).
  - Sampling: `g₀/L ~ LogUniform(1, 100) s⁻²`; `ε ~ Uniform(0.05, 0.3)`; `Ω ~ Uniform(0.3, 1.7) ω₀` (avoid neighborhoods of `ω₀` and `2ω₀`).
  - Safe: `ε ≤ 0.4 · |Ω/(2ω₀) − 1|` (sub-threshold of principal Mathieu tongue).
  - Lit-angle: vertical pivot drive (Kapitza-style), but slow off-resonant pumping rather than the fast-stabilization regime — different dynamical regime.

---

## Domain 5: Coulomb force (electrostatic, multi-charge)

**Baseline law**: `F_{ij} = k q_i q_j r̂_{ij}/r_{ij}²`; total `F_i = Σ_j F_{ij}`.
Dim: `[k]=N·m²·C⁻²`, `[q]=C`.
**Invariants**: T-trans (E), S-trans (p), ROT (L), T-rev, PAR, Q (total charge), U(1), superposition (LIN).

### Tier-1 (γ)

- **shift-γ-5-1 — anisotropic Coulomb coupling**
  - Motivation: re-skin uniaxial-medium anisotropy from optics into the bare electrostatic force, derived from a potential so the force stays conservative.
  - Broken: ROT.
  - Modified law: pairwise potential `V_pair(r, r̂; m̂) = (k q_i q_j / r) · [1 + χ ((r̂·m̂)² − ⅓)]`, force `F_{ij} = −∇_{x_i} V_pair`. Explicit decomposition (with `ν ≡ r̂_{ij}·m̂`):
    - radial `F_{ij,r} = (k q_i q_j / r_{ij}²) · [1 + χ(ν² − ⅓)]`,
    - tangential `F_{ij,⊥} = −(2 k q_i q_j χ ν / r_{ij}²) · (m̂ − ν r̂_{ij})`.
    Total force on charge `i`: `F_i = Σ_{j≠i} F_{ij}` (pairwise additive).
  - Dim: `[χ]=1`, `m̂` unit dimensionless.
  - Retained: T-trans (E conserved — `V_pair` time-independent and conservative), S-trans (p conserved), T-rev (no `v`), PAR (vector under inversion), Q, LIN/superposition (still pair-additive).
  - L not retained (single Noether-paired loss with ROT).
  - Sampling: `k = k_Coulomb·LogUniform(0.5, 2)`; `χ ~ Uniform(0.05, 0.4)`; `m̂ ~ Uniform on S²`.
  - Safe: `χ < 0.5` ⇒ bracketed factor positive in every direction (`ν²−⅓ ∈ [−⅓, ⅔]`).

- **shift-γ-5-2 — saturating-potential nonlinearity (cross-domain re-skin of nonlinear elasticity)**
  - Motivation: borrow the "soft" cubic saturation from nonlinear springs, apply it at the *potential* level so the resulting field stays curl-free (energy-conserving) while the field-to-source map is nonlinear.
  - Broken: LIN (superposition of fields).
  - Modified law: define the linear scalar potential from the source set, `φ_lin(x) = Σ_j k q_j / |x − x_j|`. The effective potential is `φ_eff(x) = φ_lin + ξ · φ_lin³ / (φ_lin² + φ₀²)`. Field on a test charge: `E_eff = −∇φ_eff`; force on test charge `q_t`: `F = q_t E_eff`.
  - Dim: `[ξ]=1`, `[φ₀]=V`. `[φ_eff]=V` ✓.
  - Retained: T-trans (E conserved — `φ_eff` time-independent ⇒ `E_eff = −∇φ_eff` conservative), ROT (the map `φ_lin → φ_eff` is a scalar function of a scalar field ⇒ rotation-equivariant), PAR (under inversion, `φ_lin` is invariant for a charge set with reversed positions; the field transforms as a vector), Q, T-rev.
  - Sampling: `k = k_Coulomb·LogUniform(0.5, 2)`; `ξ ~ Uniform(0.05, 0.5)`; `φ₀ ~ LogUniform(0.1, 10) · φ_typical V`.
  - Safe: `ξ < 1` keeps `φ_eff(φ_lin)` monotone in `φ_lin` (derivative `1 + ξ · φ_lin²(φ_lin² + 3 φ₀²)/(φ_lin² + φ₀²)² > 0`).
  - Lit-angle: Born–Infeld nonlinear electrodynamics inspires the *idea* of a saturating EM response; we install the nonlinearity at the potential level (different mathematical layer) and use a rational cubic-saturating form rather than the Born–Infeld square root.

### Tier-2 (δ)

- **shift-δ-5-1 — field-coupled charge leakage**
  - Motivation: charges slowly bleed into the surrounding "vacuum" at a rate set by the local field — re-skin of mechanical drag onto the charge variable itself.
  - Broken: Q conservation. (T-rev is trivial in the static baseline and is lost as part of the same package; per D6 convention this counts as a single conservation-law break.)
  - Modified law: `dq_i/dt = −α · (|E_loc,i|/E_ref)^n · q_i`, where `E_loc,i = Σ_{j≠i} k q_j (x_i − x_j)/|x_i − x_j|³`. Force law itself unchanged.
  - Dim: `[α]=s⁻¹`, `[n]=1`, `[E_ref]=V/m`.
  - Retained: T-trans (rate depends only on instantaneous state), S-trans, ROT, PAR.
  - Sampling: `α ~ LogUniform(1e-4, 1e-1) s⁻¹`; `n ~ Uniform(0.5, 2)`; `E_ref ~ LogUniform(0.1, 10)·E_typical V/m`.
  - Safe: `α · T_sim ≤ 1` so total charge drift is sub-order-unity.
  - Lit-angle: millicharge / Okun-style charge non-conservation, made *deterministic and field-gated* rather than spontaneous.

---

## Domain 6: RLC circuit (one or two coupled loops)

**Baseline law (single loop)**: `L · di/dt + R · i + q/C = V_src(t)`, with `i = dq/dt`. Dim: `[L]=H`, `[R]=Ω`, `[C]=F`, `[q]=C`, `[i]=A`, `[V]=V`.
**Invariants**: T-trans (energy budget `½ L i² + ½ q²/C + ∫R i² dt = const`), LIN, `q↔−q` parity (in unbiased loop), Onsager reciprocity in multi-loop case.

### Tier-1 (γ)

- **shift-γ-6-1 — saturable inductor (cross-domain re-skin of ferromagnetic saturation)**
  - Motivation: re-skin saturating magnetisation into the inductor's response.
  - Broken: LIN.
  - Modified law: `d/dt [ L(i) · i ] + R i + q/C = V_src(t)`, with `L(i) = L₀ / (1 + (i/I_sat)²)`.
  - Dim: `[L₀]=H`, `[I_sat]=A`.
  - Retained: T-trans (autonomous if `V_src` is), `q↔−q` parity (`L(i)=L(−i)`), Onsager (single loop, vacuous).
  - Sampling: `L₀ ~ LogUniform(1e-3, 1) H`; `R ~ LogUniform(0.1, 100) Ω`; `C ~ LogUniform(1e-9, 1e-5) F`; `I_sat ~ LogUniform(0.1, 10) · i_typical A`.
  - Safe: simulate `|i| ≤ 5 I_sat` (inductor never goes to vanishing inductance).
  - Lit-angle: ferromagnetic core saturation; we use the smooth Lorentzian `1/(1+u²)` rather than the textbook `tanh`-shaped B–H curve.

- **shift-γ-6-2 — non-reciprocal mutual inductance (two-loop)**
  - Motivation: borrow gyrator-like non-reciprocity, implemented as asymmetric mutual `M_{12} ≠ M_{21}` rather than as an ideal lumped gyrator element.
  - Broken: Onsager reciprocity (i.e., T-rev of the multi-loop linear network).
  - Modified law (two loops i=1,2):
    `L_i di_i/dt + Σ_{j≠i} M_{ij} di_j/dt + R_i i_i + q_i/C_i = V_i(t)`, with `M_{12} = M₀ + δM/2`, `M_{21} = M₀ − δM/2`, `δM ≠ 0`.
  - Dim: `[M_{ij}]=H`, `[δM]=H`.
  - Retained: T-trans (autonomous part), LIN (still linear in `i, q`), `q↔−q` parity, Q at each loop.
  - Note: E is not separately conserved; the loss is Noether-paired with the T-rev/Onsager break and is counted as the single break per Part A's dissipative-bundling convention (same pattern as δ-1-1, δ-3-1, δ-6-1).
  - Sampling: `L_i ~ LogUniform(1e-3, 1) H`; `R_i ~ LogUniform(0.1, 100) Ω`; `C_i ~ LogUniform(1e-9, 1e-5) F`; `M₀ ~ Uniform(0, 0.5)·√(L₁ L₂)`; `δM/M₀ ~ Uniform(0.05, 0.4)`.
  - Safe: `|M₀ ± δM/2| < √(L₁ L₂)` (positive-definite inductance matrix, no runaway).
  - Lit-angle: non-reciprocal magnetic coupling in metamaterials; we keep the elements purely inductive (no ideal gyrator), so the mechanism is the asymmetric `M`.

### Tier-2 (δ)

- **shift-δ-6-1 — parametric inductance modulation**
  - Motivation: re-skin the pendulum's parametric gravity drive (δ-4-1) onto the inductor.
  - Broken: T-trans (energy not conserved — pumping/de-pumping per cycle).
  - Modified law: `d/dt [ L(t) · i ] + R i + q/C = 0`, `L(t) = L₀ · [1 + ε cos(Ω_p t)]`.
  - Dim: `[ε]=1`, `[Ω_p]=s⁻¹`.
  - Retained: LIN, `q↔−q` parity, T-rev (cosine even in `t` about `t=0`).
  - Sampling: `L₀, R, C` as above; `ε ~ Uniform(0.05, 0.3)`; `Ω_p ~ Uniform(0.5, 1.5)·ω_LC`, **excluding** a `±10%` band around `2ω_LC` (avoid principal parametric resonance).
  - Safe: damping ratio `R/(2√(L₀/C)) ≥ ε · Ω_p / (2 ω_LC)` (sub-threshold of parametric amplification).
  - Lit-angle: parametric amplifiers; the deliberate avoidance of `2ω_LC` keeps the system in a quasi-stationary modulation regime rather than the canonical parametric-amp operating point.

---

## Part A summary (internal ground-truth, not exposed to AI)

| Shift | Domain | Symmetry / law broken | Mechanism family (re-skin source) |
|---|---|---|---|
| γ-1-1 | Hooke | PAR | asymmetric well (Morse-like, modified) |
| γ-1-2 | Hooke | ROT (2D) | birefringence (optics → mechanics) |
| δ-1-1 | Hooke | E (energy) | amplitude-gated Stokes drag |
| γ-2-1 | Gravity | ROT | quadrupolar anisotropy (SME-inspired) |
| γ-2-2 | Gravity | SCALE (Bertrand) | Lorentzian range bump |
| δ-2-1 | Gravity | T-trans / E | harmonic `G(t)` modulation |
| γ-3-1 | Damped HO | LIN | amplitude-memory stiffness |
| γ-3-2 | Damped HO | T-trans | off-resonant parametric pumping |
| δ-3-1 | Damped HO | dissipation monotonicity | amplitude-gated negative damping (vdP-modified) |
| γ-4-1 | Pendulum | PAR | tanh-biased rotor (Josephson-inspired) |
| γ-4-2 | Pendulum | S-trans (vertical) | tidal-gradient gravity |
| δ-4-1 | Pendulum | T-trans / E | off-resonant `g(t)` modulation |
| γ-5-1 | Coulomb | ROT | uniaxial anisotropy (optics → ES) |
| γ-5-2 | Coulomb | LIN (superposition) | saturating-field nonlinear ED |
| δ-5-1 | Coulomb | Q | field-gated charge leakage |
| γ-6-1 | RLC | LIN | ferromagnetic saturation → inductor |
| γ-6-2 | RLC | Onsager / T-rev | asymmetric mutual `M` (non-reciprocal) |
| δ-6-1 | RLC | T-trans / E | parametric `L(t)` modulation |

Coverage: **8 distinct broken symmetries / laws** across 18 shifts. Cross-domain re-skinning used in 11/18.

— end Part A —

---

# Part B: Domains 7–12 (thermal / wave / optics / fluid / chemistry / nuclear)

**作者**：physicist-B。**分工**：与 physicist-A 协商 — A 取力学+EM 前 6 域，B 取非力学/电磁的后 6 域。
**域选**：`thermal conduction (Fourier), scalar wave, geometric optics / Snell, inviscid fluid (Bernoulli), reaction kinetics (rate law), radioactive decay`。
**风格保持**：与 Part A 同 — SI 全程，每 shift 只破一条对称律 / 守恒律；其余 listed invariants 必须保留（待 invariant-checker 数值复核）；分布是 catalog-level 占位，scenario 标定时再压紧。Cross-domain re-skinning 是首选 — B 域天然适合从力学 / EM 借代数结构。

---

## Domain 7: Thermal conduction (Fourier law)

**Baseline law**: `q_i = −k ∂_i T`，等价 `∂_t T = α ∇² T`（`α = k/(ρ c_p)`）。
Dim: `[T]=K, [q]=W·m⁻², [k]=W·m⁻¹·K⁻¹, [α]=m²·s⁻¹`。
**Invariants**: SO(3) 各向同性、S-trans、T-trans、`T→T+const`（baseline 只用 `∇T`）、能量积分 `∫ρc_p T dV` 在绝热边界守恒、Onsager 对称 `k_{ij}=k_{ji}`、parabolic 自相似 scale `(t→λt, x→λ^{1/2} x)`。

### Tier-1 (γ)

- **shift-γ-7-1 — constant-β anisotropic conductivity (cross-domain re-skin of dielectric tensor)** *(round-1 fix B1)*
  - Motivation: 借 EM 各向异性介电张量 `ε_{ij}=ε₀(δ_{ij}+χ n_i n_j)` 的代数形式，搬到热域。原 `tanh(|∇T|/G₀)` 门控被 invariant-checker 指出会 *独立* 破抛物 self-similar scale ⇒ dual break；改用 **常数 β + 大宽对数随机 + 每 scenario 随机 `n̂`**，仅破 SO(3)。
  - Broken: SO(3)（出现优先方向 `n̂`）。
  - Modified law: `q_i = −K_{ij} ∂_j T`, `K_{ij} = k₀ [δ_{ij} + β · n_i n_j]`.
  - Dim: `[k₀]=W·m⁻¹·K⁻¹`, `[β]=1`, `n̂` 无量纲单位向量。输入 `T [K], ∇T [K/m]` → `q [W/m²]`。
  - Retained: S-trans, T-trans, `T→T+c`（K 与 T 无关）, 能量守恒（K 对称正定 → 散度形式）, Onsager（K_{ij}=K_{ji}）, parabolic self-similar scale `(t→λt, x→λ^{1/2}x)` ✓（K 与场无关 ⇒ scale 不变）。
  - Sampling: `k₀ ~ LogUniform(0.1, 50) W·m⁻¹·K⁻¹`; `β ~ LogUniform(0.05, 5)`（两 decade 宽分布以保 non-textbook 强度）; `n̂ ~ Uniform on S²`.
  - Safe: `β > -1 ⇒ K` 严格正定；上限 `β < 5` 保平行方向传导 ≤ 6×正交 — 数值良态。
  - Lit-angle: 借介电张量代数结构；`β` 大宽对数随机 + 各 scenario 独立 `n̂` ⇒ 区别于 textbook 单晶各向异性 Fourier（系数窄、方向固定）。

- **shift-γ-7-2 — power-law memory kernel (cross-domain re-skin of fractional viscoelasticity)**
  - Motivation: 复杂介质（聚合物、多孔）有时间记忆；避开经典 Cattaneo–Vernotte 双曲方程，借分数阶力学的核形式。
  - Broken: 抛物 self-similar scale `(t→λt, x→λ^{1/2}x)`（核引入幂律时间标度 `p`，scale 变为 `x→λ^{(1-p)/2} x` — 与 baseline 不同）。
  - Modified law: `q_i(t) = − ∫_{t₀}^{t} G(t − s) · ∂_i T(s) ds`，`G(τ) = k₀ · τ^{-p} / Γ(1 − p)` for `τ ≥ τ_min`，`τ < τ_min` 用 `τ_min^{-p}/Γ(1-p)` 截断。
  - Dim: `[G]=W·m⁻¹·K⁻¹·s^{p−1}`; `[q]=W/m²` ✓。
  - Retained: 时间平移（卷积形式 + `t₀ → -∞` 极限取大窗口近似）, SO(3), S-trans, `T→T+c`, 能量守恒（核重写为分数 Fick 律仍是散度律），Onsager。
  - Sampling: `p ~ Uniform(0.10, 0.55)`; `k₀ ~ LogUniform(0.1, 50)`; `τ_min = Δt_sim`（不送给 AI）。
  - Safe: `p < 0.6` 保 `Γ(1-p)` 良态且积分收敛；下截断防 `τ=0` 奇异。
  - Lit-angle: 借 fractional heat conduction 框架，但 `p` 自由对数随机、不锁定 Caputo / Riemann-Liouville 具体定义 — 与文献固定阶数版本区分。

### Tier-2 (δ)

- **shift-δ-7-1 — quadratic-in-excess sink with comoving reference** *(round-1 fix B2)*
  - Motivation: 制造 hidden 能量泄漏，但避开 Stefan-Boltzmann `T⁴`；原版固定 `T_amb` 被 invariant-checker 指出独立破 `T→T+c`（不属 Noether-paired w/ E）⇒ 改用 **comoving 域内均值** 作参考，使 `T→T+c` 严格保持。
  - Broken: 能量守恒（`∫ρc_p T dV` 不再守恒；T-rev bundled per Part A convention）。
  - Modified law: `∂_t T = α ∇² T − λ · (T − ⟨T⟩_Ω(t))² / T_ref`，其中 `⟨T⟩_Ω(t) = (1/|Ω|) ∫_Ω T dV`。
  - Dim: `[λ]=s⁻¹`, `[T_ref]=K`, `[⟨T⟩]=K`; RHS `[K/s]` ✓。
  - Retained: SO(3), S-trans, T-trans（自治）, `T→T+c` ✓（`T→T+c ⇒ ⟨T⟩→⟨T⟩+c ⇒ (T−⟨T⟩) 不变 ⇒` sink 项不变）, Onsager（扩散部分）。
  - Sampling: `λ ~ LogUniform(1e-5, 1e-2) s⁻¹`; `T_ref ~ LogUniform(50, 1000) K`; `α` 同 baseline。
  - Safe: 关于 `⟨T⟩` 的二次中心吸引 ⇒ T 围绕动态均值收敛；初值 `T(0) ≥ 2 · max|T(0) − ⟨T(0)⟩|` 保证 `T ≥ 0` 全程；不发散。
  - Lit-angle: 借 radiation cooling 思想，弃 `T⁴` 标准式；comoving 二次形式非 textbook（标准 Newton's cooling 用绝对参考）。

---

## Domain 8: Scalar wave (1D / 2D acoustic, lossless baseline)

**Baseline law**: `∂_t² u = c² ∂_x² u` (1D)，2D: `∂_t² u = c² ∇² u`。Dim: `[u]=m, [c]=m·s⁻¹`。
**Invariants**: T-trans, S-trans, parity `x→−x`, T-rev, Lorentz-like w/ `c`, 能量 `E = ∫(½(∂_t u)² + ½ c²|∇u|²)dx` 守恒, 线性叠加, SO(2/3) 各向同性 (≥2D)。

### Tier-1 (γ)

- **shift-γ-8-1 — third-order chiral dispersion (cross-domain re-skin of KdV-linear motif)**
  - Motivation: 借 KdV 线性色散 `∂_x³` 算子搬到 d'Alembert 方程作声波 — 文献无此组合。
  - Broken: parity `x→−x`（`∂_x³` 奇）。
  - Modified law: `∂_t² u = c² ∂_x² u + γ · c² · ∂_x³ u`.
  - Dim: 选 `[γ]=m`；则 `[γ c² ∂_x³ u] = m · m²·s⁻² · m·m⁻³ = m·s⁻²` ✓。
  - Retained: T-trans, S-trans, T-rev（项含 `∂_t²` 偶, `∂_x³ u` 时间偶 ⇒ `t→-t` 保留）, 能量守恒（色散项纳入 Hamilton 形式 `H = ∫(½π² + ½c²(∂_x u)² + ½γc²·(...))`，色散非耗散）, 线性叠加。
  - Sampling: `γ ~ Uniform(-L₀, L₀)`, `L₀ ~ LogUniform(1e-4, 1e-1) m`（双符号）; `c ~ LogUniform(50, 5000) m/s`.
  - Safe: 色散非耗散 ⇒ 振幅不增；CFL 需 `Δt ≤ Δx² / (c · |γ|_max)`（高阶差分）。
  - Lit-angle: KdV linear part 搬到声学；与 textbook acoustic dispersion (`∂_x⁴` Boussinesq-like) 区分。

- **shift-γ-8-2 — 2D anisotropic phase speed (cross-domain re-skin of dielectric tensor)**
  - Motivation: 晶格 / 多层介质各向异性 — 借 EM 介电张量代数到声学。
  - Broken: SO(2) 平面旋转。
  - Modified law: `∂_t² u = c² ∂_i (M_{ij} ∂_j u)`, `M = R(θ₀) · diag(1, 1+β) · R(θ₀)ᵀ`（主轴系下 diag）。
  - Dim: `[M]=1`; RHS `[m/s²]` ✓。
  - Retained: T-trans, S-trans, parity（`x→-x`：`M` 在主轴系仍对称）, T-rev, 能量守恒（M 对称正定 ⇒ Hamilton 良态）。
  - Sampling: `β ~ Uniform(0.1, 0.8)`; `θ₀ ~ Uniform(0, π)`; `c ~ LogUniform(50, 5000) m/s`.
  - Safe: `β < 1 ⇒ M` 正定 ⇒ 双曲，标准 CFL 适用。
  - Lit-angle: 介电张量代数到声学；与 textbook anisotropic elasticity 张量（4 阶）维度不同 — 2 阶张量是 cross-domain 简化。

### Tier-2 (δ)

- **shift-δ-8-1 — amplitude-gated viscous damping (dissipative single-label)** *(round-1 fix B3)*
  - Motivation: 原版 `−α₀ ∂_t u` 是 textbook 线性阻尼波动方程，lookup-style AI 一眼识别 — invariant-checker 标记 attack-resistance fail；采用 **amplitude-gated** 子线性包络（option a），与 Part A δ-3-1 同款 motif 跨域到 PDE。
  - Broken: 能量守恒（Part A δ-1-1 / δ-3-1 / δ-6-1 同款 "dissipative ⇒ E + T-rev = 单条" 约定；非线性状态依赖阻尼按 dissipative bundle 处理）。
  - Modified law: `∂_t² u = c² ∂_x² u − α₀ · (|u| / u_ref) · ∂_t u`。
  - Dim: `[α₀]=s⁻¹`, `[u_ref]=m`; `[α₀ · |u|/u_ref · ∂_t u] = s⁻¹ · 1 · m/s = m/s²` ✓。
  - Retained: T-trans（自治）, S-trans（系数 x-无关）, parity `x→-x` ✓（项不动）；`u→-u` 下 `|u|→|u|, ∂_t u→-∂_t u, ∂_t² u→-∂_t² u` ✓。
  - Sampling: `α₀ ~ LogUniform(1e-3, 0.3) s⁻¹`; `u_ref ~ LogUniform(1e-3, 1) m`; `c ~ LogUniform(50, 5000) m/s`.
  - Safe: 振幅小 ⇒ 阻尼 → 0（线性极限恢复 baseline），大振幅 ⇒ 强阻尼自限；振幅有界，不发散。
  - Lit-angle: 与 Part A δ-3-1 (van der Pol-modified 振幅门控负阻尼) 同源 motif 但作用在 PDE 而非 ODE，且为纯耗散 — 与 textbook 线性吸收 `e^{-α t}` lookup 不匹配。

---

## Domain 9: Geometric optics / Snell

**Baseline law**: `n₁ sin θ_1 = n₂ sin θ_2`。Fresnel 在标量近似下: `R + T = 1`。
Dim: `[n]=1, [θ]=rad`。
**Invariants**: 界面切向波矢守恒、互易性（光路可逆 / time-reversal of rays）、Fermat 平稳路径、偏振 U(1)（标量近似下 polarization 旋转不变）、能量 `R+T=1`、绕界面法线轴 SO(2)、介质交换 `1↔2` 形式对称。

### Tier-1 (γ)

- **shift-γ-9-1 — polarization-modulated index (cross-domain re-skin of crystal birefringence motif)**
  - Motivation: 借 birefringence 思想，但 `sin²(2θ_pol − φ)` 双瓣形（周期 π）非标准单轴形式。
  - Broken: 偏振 U(1)（标量近似下，baseline 对 polarization 角度旋转不变；该 shift 引入显式 polarization 依赖）。
  - Modified law: `n_eff(θ_pol) = n_0 + δn · sin²(2 θ_pol − φ)`；Snell: `n_1 sin θ_1 = n_eff(θ_pol) sin θ_2`。
  - Dim: 均无量纲 ✓。
  - Retained: 互易性（固定 `θ_pol` 后路径可逆）, Fermat, 切向波矢守恒, SO(2) 绕法线, 能量 `R+T=1`, 介质 `1↔2` 对称（替换 `n_2 → n_eff` 而 `n_1` 独立）。
  - Sampling: `n_0 ~ Uniform(1.3, 2.2)`; `δn ~ Uniform(0.02, 0.30)`; `φ ~ Uniform(0, π)`; `θ_pol ~ Uniform(0, π)` per ray。
  - Safe: `n_eff = n_0 + δn · [0,1] > 0` 总成立；TIR 临界角随 `θ_pol` 动态变化但有限。
  - Lit-angle: 借 uniaxial / biaxial crystal 想法；`sin²(2θ-φ)` 双瓣 + 非介质张量直接形式 ⇒ counterfactual。

- **shift-γ-9-2 — interchange-asymmetric Snell (cross-domain re-skin of non-reciprocal magnetic coupling motif)**
  - Motivation: 借 Part A γ-6-2 非互易磁耦合思想搬到界面光学 — 同样制造 `1↔2` 不对称。
  - Broken: 介质交换对称 / 互易性（光路时间反演不再完全对称）。
  - Modified law: `sin θ_t = (n_1/n_2) sin θ_i + κ · (n_1 − n_2)/(n_1 + n_2) · sin³ θ_i`。该 cubic 项在 `1↔2` 交换下变号 ⇒ 单破互易性。
  - Dim: 无量纲 ✓。
  - Retained: SO(2) 绕法线, Fermat（每个固定方向分支内仍平稳）, 能量 `R+T=1`（另独立建模）, 切向波矢守恒（在该方向上）, 偏振 U(1)。parity 在界面平面内的`x→-x`（与法向无关）保留。
  - Sampling: `n_1, n_2 ~ Uniform(1.0, 2.0)` 独立; `κ ~ Uniform(0, 0.15)`。
  - Safe: 在 `κ < 0.2` 且 `|sin θ_i| < 0.95` 范围内 `|sin θ_t| ≤ 1`；超出按 TIR 处理（与 baseline 同款边界）。
  - Lit-angle: chiral / non-reciprocal optics 思想，但 cubic-in-`sin θ` 项 + `(n_1-n_2)/(n_1+n_2)` 反对称因子组合非 textbook。

### Tier-2 (δ)

- **shift-δ-9-1 — angle-power energy non-balance (cross-domain re-skin of Part A δ-5-1 field-gated leakage motif)**
  - Motivation: 制造能量泄漏（或反向"获得"）— 借 δ-5-1 中"law 不变，附加守恒律破"的思路，搬到光学界面。形式非 Beer-Lambert / Fresnel 标准。
  - Broken: 能量守恒（`R + T ≠ 1`）。
  - Modified law: 角度方程保持 Snell baseline；强度方程 `R + T = 1 − ξ · |sin θ_i|^p`。允许 `ξ` 双符号。
  - Dim: 无量纲 ✓。
  - Retained: Snell 角度律本身, 互易性（损失系数对入/出射方向同）, SO(2) 绕法线, Fermat, 切向波矢, 偏振 U(1), 介质交换。
  - Sampling: `ξ ~ Uniform(-0.15, 0.40)`; `p ~ Uniform(1.2, 3.0)`。
  - Safe: `|ξ| < 0.5` 保 `R, T ∈ [0, 1.5]`；`ξ < 0` 时"获得"上限为 `1.5·I_i`，与"散射进 hidden mode 再耦合回"的物理图像兼容。
  - Lit-angle: 借吸收 / 倏逝耦合思想；幂律角度依赖 + 双符号随机系数 ⇒ counterfactual，非 Beer-Lambert / Fresnel。

---

## Domain 10: Inviscid fluid (Bernoulli, steady streamline)

**Baseline law**: `½ ρ v² + ρ g h + p = const` 沿流线；附 `∇·v = 0`。
Dim: `[ρ]=kg·m⁻³, [v]=m/s, [h]=m, [p]=Pa, [g]=m·s⁻²`。
**Invariants**: 质量守恒 `∇·v=0`, 水平 Galilean, `h→h+const`（baseline 重力势吸收进 const）, SO(3) 各向同性、时间平移（steady）、流线能量、可逆性（无粘）、 SO(2) 水平旋转。

### Tier-1 (γ)

- **shift-γ-10-1 — anisotropic kinetic inertia (cross-domain re-skin of effective-mass tensor)** *(round-1 fix B4 — Euler equation added)*
  - Motivation: 取向性多相流（纤维悬浮 / 拉伸聚合物）— 借 solid-state effective-mass tensor 代数到流体动能。Round-1 invariant-checker 指出 Bernoulli 是 Euler 的流线积分 ⇒ 必须给出对应的 momentum equation。
  - Broken: SO(3) 各向同性（出现优先方向 `n̂`）。
  - Modified momentum equation (Euler 层): `M_{ij} (∂_t v_j + (v·∇) v_j) = −∂_i p − ρ g ∂_i h`，`M_{ij} = ρ [δ_{ij} + α (n_i n_j − δ_{ij}/3)]`（traceless 各向异性 ⇒ `tr(M) = 3ρ` 不变）。
  - Modified Bernoulli (streamline integral of the Euler eq.): `½ v_i M_{ij} v_j + ρ g h + p = const`（沿同一流线；由上 Euler 沿 `v` 缩并积分得出，`M` 对称 ⇒ KE-quadratic form 良定义）。
  - Dim: `[M]=kg·m⁻³`; KE 项 `[Pa]` ✓; Euler 两侧 `[kg·m⁻²·s⁻²]` ✓。
  - Retained: 质量守恒 `∇·v=0`, 水平 Galilean (M 与 v 平移无关), `h→h+const`, T-trans (steady 项自治), 流线能量（M 对称正定 ⇒ 沿 streamline 守恒）, 可逆性（无粘）。
  - Sampling: `α ~ Uniform(-0.4, 1.4)`; `n̂ ~ Uniform on S²`; `ρ ~ LogUniform(50, 5e3) kg/m³`。
  - Safe: `α > -1 ⇒ M` 正定（最小本征 `ρ(1 − α/3) > 0` for `α<3`，最大 `ρ(1 + 2α/3)`，全正于 `α∈(-1, ∞)` 实用区间）。
  - Lit-angle: 借固态有效质量张量；搬到流体动能 + 完整 Euler 一致性 ⇒ counterfactual。与 Part A γ-1-2 / γ-5-1 / γ-7-1 是同源 anisotropy motif 的不同 instantiation。

- **shift-γ-10-2 — nonlinear gravitational potential (cross-domain re-skin of stratified-atmosphere motif)** *(round-1 fix B5 — sampler constraint corrected)*
  - Motivation: 浮力分层 / 非均匀有效重力，避免 textbook 等温 / 等熵公式。Round-1 invariant-checker 指出原静态边界 `|h|<10·h₀` 在 `λ=-0.25, q=2` 下失败 (1+(-0.25)·100=-24) ⇒ 改为 **采样级约束**。
  - Broken: 垂直平移 `h → h + const`（势能不再仿射于 `h`）。
  - Modified law: `½ ρ v² + ρ g h · (1 + λ (h/h_0)^q) + p = const`。
  - Dim: 势能项 `[Pa]` ✓。
  - Retained: 水平 S-trans, SO(2) 水平旋转, 水平 Galilean, `∇·v=0`, T-trans, 流线能量, 可逆性。
  - Sampling precondition (sim layer enforces before scenario emit): 给 scenario 的物理 envelope `h_max`，按以下采样：`q ~ Uniform(0.5, 2.0)`; `h_0 ~ LogUniform(1, 100) m`; `ε(q, h_max, h_0) = 0.5 / (h_max/h_0)^q`; `λ ~ Uniform(−ε, min(ε, 0.5))`; 拒绝 `|λ| < 0.01` 邻域避免 baseline 退化; `g = 9.81 m/s²`。
  - Safe: 上 precondition 保 `|λ|·(h_max/h_0)^q < 0.5 ⇒ (1 + λ(h/h_0)^q) ∈ (0.5, 1.5)` 在整个 `|h| ≤ h_max` 上严格正 ⇒ 势能单调凸 ⇒ 不发散。
  - Lit-angle: 借 stratified buoyancy；幂律高度修正 + `λ` 双符号 + 自适应采样约束 ⇒ counterfactual。与 Part A γ-4-2 (tidal gradient pendulum) 是同源 "non-uniform `g`" motif 的流体 instantiation。

### Tier-2 (δ)

- **shift-δ-10-1 — path-integral streamline loss (cross-domain re-skin of distributed-resistance motif)**
  - Motivation: 分布式 sub-grid 损失（多孔介质 / 弱湍流耗散），非 Darcy-Weisbach 标准形式。
  - Broken: 流线能量守恒。
  - Modified law: `½ ρ v² + ρ g h + p + ζ ∫_streamline |v − v_∞|^m ds = const`（沿同一流线）。`v_∞` 设为远场参考速度以保 Galilean。
  - Dim: `[ζ] = kg · m^{-1-m} · s^{-m+2}`（按 `m` 调整使损耗项 `[Pa]`）；RHS `[Pa]` ✓。
  - Retained: `∇·v=0`, 水平 Galilean（损失项写为 `|v − v_∞|^m` ⇒ frame-shift 保留）, T-trans, SO(3) 各向同性, `h→h+const`, 可逆性 **失效** — 按 Part A δ 同款"dissipative ⇒ 单一标签"惯例算一条。
  - Sampling: `ζ ~ LogUniform(1e-4, 1e-1)` (unit adjusted by `m`); `m ~ Uniform(1.5, 2.8)`; `v_∞ ~ Uniform(0, v_typical) m/s`（per scenario）。
  - Safe: 积分单调增 ⇒ 仅能耗，总能上界 = inlet 能量；流场不发散。
  - Lit-angle: 借 distributed Darcy 思想，但路径积分 + 幂律相对速度 + `v_∞` 参考 frame ⇒ counterfactual。

---

## Domain 11: Reaction kinetics (single-step rate law)

**Baseline law**: `dC/dt = −k C^n`；配 Arrhenius `k = A exp(−E_a / (R T))`。
Dim: `[C] = mol·m⁻³, [k] = (mol·m⁻³)^{1−n}·s⁻¹, [E_a] = J·mol⁻¹, R = 8.314 J·(mol·K)⁻¹`。
**Invariants**: 时间平移, Arrhenius 温度依赖, 化学计量守恒（链 `A → B` 1:1 ⇒ `C_A + C_B = const`）, 正定性 `C ≥ 0`, dimensional homogeneity, 稀释自相似 `C → λC`（baseline 在 `n=1` 时严格 scale-invariant，`n≠1` 时仅幂律自相似）。

### Tier-1 (γ)

- **shift-γ-11-1 — fractional-time kinetics (cross-domain re-skin of anomalous-diffusion motif)**
  - Motivation: 受限介质（凝胶 / 多孔 / 反应-扩散耦合）下的非 Markov 反应；借 Domain 7 γ-7-2 同源 fractional kernel 但作用于不同 PDE。
  - Broken: 反应自相似 scale `(t→λt, C→λ^{−1/(n−1)}C)`（baseline 此 scale 律自洽；分数阶 `β` 改变 scale 指数）。
  - Modified law: `D_t^β C = −k C^n`（Caputo 分数时导）。
  - Dim: `[D_t^β C] = mol·m⁻³·s^{-β}`; `k` 携相应 `s^{-β}` 单位 ⇒ ✓。
  - Retained: T-trans（卷积分数导对 `t→t+c` 不变，取 `t_0 → -∞` 极限近似）, Arrhenius (`k = A e^{-E_a/RT}`), 正定性（`β,n` 合适区间）, 化学计量守恒（`dB = -dA` 同步分数化 ⇒ `C_A + C_B = const`）, 稀释 scale 仅在 `n=1` 极限。
  - Sampling: `β ~ Uniform(0.55, 0.95)`; `n ~ Uniform(0.5, 2.5)`; `k ~ LogUniform(1e-4, 1e-1)` (单位随 `β,n` 自动调整); 历史窗口截断 `τ_min = Δt_sim`。
  - Safe: `β > 0.5` + `n ≥ 0.5` + 截断 ⇒ 稳定且 `C ≥ 0`。
  - Lit-angle: 借 anomalous reaction kinetics；`β` 自由对数随机 + Caputo / RL 不锁定 ⇒ counterfactual。

- **shift-γ-11-2 — density-saturating rate (cross-domain re-skin of saturable nonlinearity motif)**
  - Motivation: 拥挤 / 自抑制，避开 Michaelis-Menten 固定形式。借 Part A γ-5-2 / γ-6-1 "saturating Lorentzian" motif 到反应速率。
  - Broken: 稀释自相似 `C → λ C`（饱和引入内禀浓度尺度 `C_sat`）。
  - Modified law: `dC/dt = −k C^n / (1 + (C / C_sat)^m)`。
  - Dim: denominator 无量纲；分子 `mol·m⁻³·s⁻¹` ⇒ ✓。
  - Retained: T-trans, Arrhenius, 化学计量守恒, 正定性, dimensional homogeneity。
  - Sampling: `n ~ Uniform(1.0, 3.0)`; `m ~ Uniform(0.5, 3.0)`; `C_sat ~ LogUniform(1, 1e4) mol/m³`; `k ~ LogUniform(1e-4, 1e-1)`。
  - Safe: denominator > 0 always；高 `C` 渐近 `dC/dt ~ -k C^{n-m}`，要求 `n - m > -1` 以避免数值停滞（实现时验证 `m < n + 1`）。
  - Lit-angle: 借饱和动力学；`(n, m)` 独立随机 + 双幂律分母 ⇒ 与 Michaelis-Menten / Langmuir 固定 form 区分。

### Tier-2 (δ)

- **shift-δ-11-1 — branching loss to hidden channel**
  - Motivation: 制造 "总摩尔损耗到暗通道 / 热" 的非标准副反应。
  - Broken: 化学计量守恒（`C_A + C_B ≠ const`）。
  - Modified law: `dC_A/dt = −k C_A^n`, `dC_B/dt = +η · k C_A^n`，`η ≠ 1`。
  - Dim: 两侧 `mol·m⁻³·s⁻¹` ✓。
  - Retained: T-trans, Arrhenius（`k` 仍 Arrhenius）, 正定性, 稀释 scale 在 `n=1` 极限, dimensional homogeneity。
  - Sampling: `n ~ Uniform(0.8, 2.0)`; `k ~ LogUniform(1e-4, 1e-1)`; `η ~ Uniform(0.55, 0.95) ∪ Uniform(1.05, 1.45)` (双段，跳过 `η ∈ [0.95, 1.05]` 邻域以避免 baseline 退化)。
  - Safe: `C_A` 单调减到 0；`C_B` 单调到 `η · C_A(0) / 1` 上界（`η < 1.5` ⇒ 有界）。
  - Lit-angle: 借 branching ratio 概念；作为 system-level hidden-channel 总损耗、`η` 跨 1 双侧随机 ⇒ counterfactual。与 Part A δ-5-1 (Q 泄漏) 是同源 "守恒律 leakage" motif 的化学 instantiation。

---

## Domain 12: Radioactive decay

**Baseline law**: `dN/dt = −λ N`。Dim: `[N] = count (or mol), [λ] = s⁻¹`。
**Invariants**: 时间平移、Markov memorylessness、线性 `N → a N`、粒子数守恒（链 `A → B`: `N_A + N_B = const`）、外场无关性（标准核衰变 `λ` 对常规外场免疫）、统计独立性（每个核独立）。

### Tier-1 (γ)

- **shift-γ-12-1 — density-coupled decay rate (cross-domain re-skin of stimulated-emission motif)**
  - Motivation: 制造"受激增减"型核衰变 — 真核衰变本质线性 / 单粒子；该非线性即 counterfactual。借激光受激辐射 `dN/dt ∝ N²` 动机但不复制 Einstein A/B 系数形式。
  - Broken: 线性 `N → aN`（出现内禀 `N_0` 标度）。
  - Modified law: `dN/dt = −λ N · (1 + α (N / N_0)^p)`。
  - Dim: `[s⁻¹]` ✓（括号无量纲）。
  - Retained: T-trans, Markov（仍只依赖当前 `N`）, 粒子守恒（`A → B` 链同步该非线性 `dN_B/dt = +λ N_A (1 + α(N_A/N_0)^p)`）, 外场无关, 统计独立性（在 mean-field 近似下）。
  - Sampling: `λ ~ LogUniform(1e-6, 1e-1) s⁻¹`; `α ~ Uniform(-0.4, 0.8)`; `p ~ Uniform(0.3, 1.5)`; `N_0 ~ LogUniform(1e3, 1e8)`。
  - Safe: `α > -1` 保 `λ_eff > 0`；高 `N` 时 `dN/dt ∝ N^{1+p}`（α>0）超线性但 `N` 单调减 ⇒ 不发散。
  - Lit-angle: 借受激辐射 motif；搬到本质线性的核衰变 ⇒ counterfactual。

- **shift-γ-12-2 — parametric-modulated decay rate (cross-domain re-skin of Part A δ-4-1 / δ-6-1 motif)** *(round-1 fix B6 — phase locked to 0 for T-rev preservation)*
  - Motivation: 外场调制衰变率 — 真核衰变几乎免疫外场，故是清晰 counterfactual。借 Part A pendulum / RLC 的参数泵入 motif。原版随机 `φ` 被 invariant-checker 指出会同时破 T-rev ⇒ dual break；**锁 `φ ≡ 0`** 使 `cos(ωt)` 在 t=0 偶 ⇒ 仅破 T-trans。
  - Broken: 时间平移。
  - Modified law: `dN/dt = −λ(t) N`, `λ(t) = λ_0 [1 + ε cos(ω t)]`。
  - Dim: `[s⁻¹]` ✓。
  - Retained: 线性 `N → aN`（在固定 `t` 下）, Markov, 粒子守恒（链 `A → B` 共享同一 `λ(t)`）, T-rev ✓（`cos(ωt)` 在 `t→-t` 不变）。"外场无关性" 是 T-trans 的衍生不变量，按 Part A 惯例算一条 (T-trans) 被破。
  - Sampling: `λ_0 ~ LogUniform(1e-6, 1e-1)`; `ε ~ Uniform(0.05, 0.40)`; `ω ~ LogUniform(1e-3, 1) s⁻¹`。仿真 t 窗口建议中心化在 `t=0` (`t ∈ [-T/2, T/2]`) 以保 T-rev 在数值层可观测。
  - Safe: `ε < 0.5 ⇒ λ(t) > 0 ∀t`；`ω` 跨多 decade 给 AI 识别难度。
  - Lit-angle: 借参数共振 / Floquet motif；应用于核衰变 ⇒ counterfactual。与 Part A δ-4-1 / δ-6-1 同款 `φ=0` 约定。

### Tier-2 (δ)

- **shift-δ-12-1 — branching loss to dark channel**
  - Motivation: 仿"中微子 / 暗物质损失通道"但不复制标准模型分支比表。
  - Broken: 粒子数守恒（`N_A + N_B ≠ const`）。
  - Modified law: `dN_A/dt = −λ N_A`, `dN_B/dt = +(1 − ξ) λ N_A`。
  - Dim: `[count·s⁻¹]` ✓。
  - Retained: T-trans, Markov, 线性 `N → aN`, 外场无关性, 统计独立性。
  - Sampling: `λ ~ LogUniform(1e-6, 1e-1)`; `ξ ~ Uniform(0.05, 0.45)`。
  - Safe: `ξ ∈ (0, 1) ⇒ N_B` 单调增到 `(1 − ξ) · N_A(0)`；无发散。
  - Lit-angle: 借 branching ratio 但 `ξ` 大范围随机、作为 hidden 总损耗 ⇒ 与具体核物理表标准分支不重叠。与 Part A δ-5-1 / Part B δ-11-1 同源 "守恒律 leakage" motif，跨域 anchor。

---

## Part B summary (internal ground-truth, not exposed to AI)

| Shift | Domain | Symmetry / law broken | Mechanism family (re-skin source) |
|---|---|---|---|
| γ-7-1 | Thermal | SO(3) | dielectric tensor (EM → thermal) |
| γ-7-2 | Thermal | parabolic scale | fractional viscoelastic kernel (mech → thermal) |
| δ-7-1 | Thermal | E (energy) | quadratic-in-excess radiative loss |
| γ-8-1 | Wave | parity | KdV linear dispersion (fluid → acoustic) |
| γ-8-2 | Wave | SO(2) | dielectric tensor (EM → acoustic) |
| δ-8-1 | Wave | E (dissipation single-label) | uniform viscous damping (broad-range random) |
| γ-9-1 | Optics | polarization U(1) | crystal birefringence motif (modified form) |
| γ-9-2 | Optics | interchange / reciprocity | non-reciprocal coupling (Part A γ-6-2 → optics) |
| δ-9-1 | Optics | E (R+T ≠ 1) | angle-power leakage (Part A δ-5-1 motif → optics) |
| γ-10-1 | Fluid | SO(3) | effective-mass tensor (solid-state → fluid KE) |
| γ-10-2 | Fluid | vertical S-trans | stratified-buoyancy nonlinear `gh` |
| δ-10-1 | Fluid | streamline E (dissipative) | path-integral distributed loss (Galilean-preserving) |
| γ-11-1 | Chemistry | reaction scale | fractional time kernel (anomalous diff → kinetics) |
| γ-11-2 | Chemistry | dilution scale | saturable-Lorentzian rate |
| δ-11-1 | Chemistry | stoichiometry | hidden-channel branching `η ≠ 1` |
| γ-12-1 | Nuclear | linearity `N→aN` | stimulated-emission motif (laser → decay) |
| γ-12-2 | Nuclear | T-trans | parametric `λ(t)` (pendulum / RLC → decay) |
| δ-12-1 | Nuclear | particle conservation | dark-channel branching `ξ` |

Coverage: **12 γ + 6 δ = 18 shifts**, 12 distinct broken symmetries / laws across Part B alone; cross-domain re-skinning used in 16/18.

### Part B self-audit checklist

- ≥2 γ + ≥1 δ per domain: ✓ (12 γ + 6 δ)
- Each shift breaks exactly one symmetry / law; "dissipative ⇒ E + T-rev single-label" follows Part A convention (δ-1-1, δ-3-1, δ-6-1) — flagged for invariant-checker confirmation.
- Cross-domain re-skinning used in 16/18 shifts; aggressive cross-borrowing with Part A (γ-10-2 ↔ Part A γ-4-2; γ-9-2 ↔ Part A γ-6-2; δ-11-1 / δ-12-1 ↔ Part A δ-5-1; γ-12-2 ↔ Part A δ-4-1 / δ-6-1).
- Parameters: wide distributions specified for every free parameter; `LogUniform` for scale-spanning, `Uniform` for bounded ratios, `Uniform on S²` for unit vectors.
- SI dimensional signatures: explicit on every law and parameter.
- Numerical stability bounds: given for each shift; reaction / decay positivity preserved; fluid bounds on `λ(h/h_0)^q` to prevent potential blowup.
- Symmetry labels NOT exposed: this catalog is internal ground-truth; scenario implementations must strip the "Broken" and "Retained" fields when generating AI prompts.

### Items flagged for invariant-checker review

1. **δ-8-1 / δ-10-1**: "dissipation = single label" convention — same as Part A δ-1-1 / δ-3-1; if checker rejects, fall back to splitting into "E only" + "T-rev only" pair (currently piggybacked).
2. **δ-7-1**: `T → T+c` broken to "T+c synchronized with T_amb+c" — should checker accept this as "drift-reference" sub-symmetry or count as separate break? Documented for explicit decision.
3. **γ-9-2**: "interchange asymmetry vs reciprocity" — both are listed as broken; we treat them as equivalent (same Noether-paired loss). If checker disagrees, the cubic term needs redesign.
4. **γ-11-1 / γ-7-2 fractional kernels**: long-time tail truncation `τ_min = Δt_sim` — confirm checker tolerates this as a sim-level cutoff rather than a physics-level shift.
5. **δ-11-1 / δ-12-1**: `η = 1` / `ξ = 0` should be explicitly excluded by sampling distribution (already done via two-segment uniform / lower-bound 0.05).

— end Part B —

---

# Audit Report (by invariant-checker, 2026-05-25, round 1)

> Scope: all 36 shifts in Parts A + B audited on the 5 axes mandated by D6:
> (1) single-symmetry-break credibility, (2) SI dimensional balance, (3) numerical
> stability inside sampled parameter ranges, (4) non-copy from named literature
> effects, (5) attack-resistance against lookup-style AI. Paired cross-domain
> re-skins were audited jointly to catch consistency drift.

## Audit table

| Shift | Single-break | Dim | Numerical | Non-copy | Attack-res | Overall |
|---|---|---|---|---|---|---|
| γ-1-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-1-2 | ✗ | ✓ | ✓ | ✓ | ✓ | **NEEDS FIX** (non-conservative radial form ⇒ E also breaks) |
| δ-1-1 | ✓ (T-rev bundled) | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-2-1 | ✗ | ✓ | ✓ | ✓ | ✓ | **NEEDS FIX** (same non-conservative pattern as γ-1-2) |
| γ-2-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| δ-2-1 | ✗ | ✓ | ✓ | ✓ | ✓ | **NEEDS FIX** (random φ in `sin(ωt+φ)` ⇒ T-rev also breaks) |
| γ-3-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-3-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| δ-3-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-4-1 | ✗ | ✓ | ✓ | ✓ | ✓ | **NEEDS FIX** (`sin(θ−α tanh(θ/θ₀))` is odd in θ ⇒ PAR not actually broken) |
| γ-4-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| δ-4-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (φ=0 cos form correctly preserves T-rev) |
| γ-5-1 | ✗ | ✓ | ✓ | ✓ | ✓ | **NEEDS FIX** (same non-conservative radial form as γ-1-2 / γ-2-1) |
| γ-5-2 | ✗ | ✓ | ✓ | ✓ | ✓ | **NEEDS FIX** (`f(|E|)·E` generally has nonzero curl ⇒ E also breaks) |
| δ-5-1 | ✓ (T-rev bundled) | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-6-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-6-2 | ⚠ | ✓ | ✓ | ✓ | ✓ | **APPROVED w/ doc note** (E loss is Noether-paired w/ T-rev; document explicitly as bundled) |
| δ-6-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-7-1 | ✗ | ✓ | ✓ | ✓ | ✓ | **NEEDS FIX** (`tanh(|∇T|)` gate also breaks parabolic self-similar scale, dual break) |
| γ-7-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| δ-7-1 | ✗ | ✓ | ✓ | ✓ | ✓ | **NEEDS FIX** (fixed `T_amb` independently breaks `T→T+c`, not Noether-paired with E) |
| γ-8-1 | ⚠ | ✓ | ✓ | ✓ | ✓ | **APPROVED w/ verify** (Hamiltonian form for `∂_x³` needs explicit potential-field statement) |
| γ-8-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| δ-8-1 | ✓ | ✓ | ✓ | ⚠ | ✗ | **NEEDS FIX** (textbook linearly-damped wave eq, easily identified by lookup) |
| γ-9-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-9-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (reciprocity ≡ interchange at interface = single Noether-pair, accepted) |
| δ-9-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-10-1 | ⚠ | ✓ | ✓ | ✓ | ✓ | **NEEDS FIX** (anisotropic Bernoulli without matching Euler equation is incomplete) |
| γ-10-2 | ✓ | ✓ | ✗ | ✓ | ✓ | **NEEDS FIX** (safety claim `|h|<10h₀ ⇒ positive` is false; counterexample λ=−0.25, q=2 ⇒ 1−25=−24) |
| δ-10-1 | ✓ (T-rev bundled) | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-11-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (truncation `τ_min = Δt_sim` accepted as sim-level cutoff) |
| γ-11-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| δ-11-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (η-exclusion band [0.95, 1.05] accepted) |
| γ-12-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-12-2 | ✗ | ✓ | ✓ | ✓ | ✓ | **NEEDS FIX** (random φ in `cos(ωt+φ)` ⇒ T-rev also breaks; same pattern as δ-2-1) |
| δ-12-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |

Tally: **23 APPROVED**, **12 NEEDS FIX**, **1 APPROVED w/ doc note** (γ-6-2), **1 APPROVED w/ verify** (γ-8-1).

## Required Fixes — for physicist-A (Part A)

**A1. γ-1-2 (Hooke 2D anisotropic, ROT break).** `F = −K(θ) r r̂` with `K(θ) = k₀[1+ξ cos(2(θ−φ))]` is a purely radial force whose magnitude depends on angle. The claimed potential `V = ½K(θ)r²` actually has both radial **and** tangential gradient components — so the stated force is not `−∇V` and the system is non-conservative ⇒ energy conservation **also** breaks ⇒ dual symmetry break, violates D6 rule §5.
- **Fix**: define the force *from* the potential, `F = −∇V` with `V = ½K(θ)r²`, giving `F_r = −K(θ)r`, `F_θ = −(r/2)·dK/dθ`. The tangential piece is the source of `L_z` non-conservation — ROT is then the sole broken symmetry, E and T-rev safe.

**A2. γ-2-1 (Gravity quadrupole, ROT break).** Same structural error as A1: `F = −G_eff(r̂;n̂)·m₁m₂ r̂/r²` is purely radial with angle-dependent magnitude, hence non-conservative ⇒ E also breaks.
- **Fix**: same recipe — derive from `V(r,θ) = −G₀ m₁ m₂ · [1 + ξ((r̂·n̂)² − ⅓)] / r` (or equivalent), force = `−∇V`. Then ROT is the unique break.

**A3. γ-4-1 (Pendulum, claimed PAR break).** The function `sin(θ − α tanh(θ/θ₀))` is **odd in θ** (tanh is odd, the argument is odd in θ, sin of odd-arg is odd). Under θ→−θ the entire EOM is invariant ⇒ PAR is *preserved*, the shift does not break what it claims to break.
- **Fix**: add a genuine even-in-θ piece to the EOM. E.g. `θ̈ + (g/L)·sin θ + (g/L)·α·(1−cos θ) = 0` — the `(1−cos θ)` term is even, so the EOM is no longer PAR-invariant. Equilibrium at θ=0 is preserved (since 1−cos 0 = 0), and the small-angle expansion gains an asymmetric `αθ²/2` cubic-in-V piece. Sampling `α ~ Uniform(0.05, 0.5)` keeps the equilibrium stable.

**A4. γ-5-1 (Coulomb anisotropic, ROT break).** Same non-conservative-radial-force issue as A1/A2.
- **Fix**: same — define `V_pair(r,θ) = (k q_i q_j / r)·[1 + χ((r̂·m̂)² − ⅓)]` and use `F = −∇V_pair`. Pairwise additivity preserved; ROT singularly broken.

**A5. γ-5-2 (Coulomb saturating field, LIN break).** `E_eff(x) = f(|E_lin|) · E_lin(x)` generally has nonzero curl because `∇f` is not parallel to `E_lin` (level surfaces of `|E_lin|` aren't perpendicular to `E_lin` in multi-source geometry). Hence E_eff cannot be written as `−∇φ_eff` ⇒ energy not conserved ⇒ dual break.
- **Fix**: derive the nonlinearity from the *potential* instead of the field. E.g. define `φ_eff = φ_lin + ξ · φ_lin³ / (φ_lin² + φ₀²)` (or analogous saturable scalar transform), then `E_eff = −∇φ_eff`. This automatically conservative; LIN/superposition still broken.

**A6. δ-2-1 (Gravity G(t) modulation, T-trans break).** Sampling `φ ~ Uniform(0, 2π)` makes `sin(ωt+φ)` non-even in time generically ⇒ T-rev breaks in addition to T-trans, dual break. The catalog hedge "choose φ symmetric" is not implementable with random φ.
- **Fix**: fix `φ ≡ 0` and switch to `G(t) = G₀[1 + β cos(ω_G t)]` (even in t about t=0). Identical fix-style as δ-4-1, which already does this correctly.

**A7. γ-6-2 (RLC non-reciprocal mutual, Onsager break) — doc note only.** The asymmetric `M₁₂ ≠ M₂₁` makes the energy `½ΣLᵢiᵢ² + M·i₁i₂` not strictly conserved (a `(M₁₂−M₂₁)·(i₁ di₂/dt − i₂ di₁/dt)` term survives). This is the Noether-paired E-loss that accompanies T-rev breaking; structurally the same bundling as δ-1-1 / δ-3-1.
- **Fix**: append one line to the Retained block: *"E is not separately conserved; the loss is Noether-paired with T-rev/Onsager and counted as the single break per Part A convention."* No formula change needed.

## Required Fixes — for physicist-B (Part B)

**B1. γ-7-1 (Thermal anisotropic conductivity, SO(3) break).** The `tanh(|∇T|/G₀)` gating introduces a field-magnitude-dependent nonlinearity. Under the baseline parabolic self-similar scaling `(t→λt, x→λ^{1/2}x, T→T)`, `|∇T|→λ^{−1/2}|∇T|` ⇒ tanh argument changes ⇒ parabolic scale is **independently** broken alongside SO(3). Dual break.
- **Fix (option 1)**: drop the `|∇T|` gating and use constant β: `K_{ij} = k₀[δ_{ij} + β n_i n_j]`. To stay non-textbook, sample `β` over a wide log range and randomize `n̂` per scenario; the algebraic structure is still cross-domain re-skinned from the dielectric tensor and the textbook anisotropic-Fourier case has fixed β.
- **Fix (option 2)**: replace the magnitude gate by a *direction-only* nonlinearity, e.g. `K_{ij} = k₀[δ_{ij} + β · ((∇T/|∇T|)·n̂)² · n_i n_j]` — this is dimensionless, doesn't change scale, and still single-breaks SO(3). Add small-`|∇T|` regularization to avoid 0/0.

**B2. δ-7-1 (Thermal quadratic sink, E break).** The fixed reference `T_amb` breaks the baseline `T→T+const` symmetry independently of energy conservation. Unlike T-rev/E in dissipative systems, `T→T+c` is *not* Noether-paired with the energy integral — it's a separate invariant — so the bundling argument doesn't apply. Dual break.
- **Fix**: replace `T_amb` with a comoving reference. E.g. `∂_t T = α∇²T − λ(T − ⟨T⟩_Ω(t))² / T_ref` where `⟨T⟩_Ω(t) = (1/|Ω|)∫_Ω T dV`. Under `T → T + c`, the mean shifts by `c` too, so the sink is invariant ⇒ `T→T+c` preserved, only E breaks (single label).

**B3. δ-8-1 (Wave viscous damping, E break).** The final law `∂_t² u = c²∂_x²u − α₀∂_t u` is the textbook linearly-damped wave equation. A lookup-style AI will identify it in one shot from the `−α₀∂_t u` term and recover `α₀` from the exponential envelope. Fails attack-resistance.
- **Fix**: add counterfactual texture that the textbook form lacks. Several options:
  - (a) Amplitude-gated damping: `∂_t² u = c²∂_x²u − α₀ · (|u|/u_ref) · ∂_t u` (sub-linear-in-u envelope, distinct from linear absorption).
  - (b) Spatial profile: `α(x) = α₀ · [1 + ζ cos(k_α x)]` with random `k_α` per scenario.
  - (c) Frequency-selective: `−α₀ · ∂_x² ∂_t u` (Kelvin–Voigt-like, dissipation grows with spatial frequency — qualitatively different lookup match).
  Any of these keeps single-label E break and gives the AI work to do.

**B4. γ-10-1 (Fluid anisotropic KE, SO(3) break).** Modifying the Bernoulli scalar `½ vᵢ Mᵢⱼ vⱼ` alone without specifying the corresponding modification to the Euler / momentum equation is incomplete — Bernoulli is a streamline integral of Euler, so the two must be consistent.
- **Fix**: either (i) explicitly state the modified momentum equation `ρ (Mᵢⱼ/ρ) Dvⱼ/Dt = −∂ᵢp − ρg ∂ᵢh` from which the modified Bernoulli falls out by `v·` integration along a streamline; or (ii) restrict the shift to *steady streamline diagnostics only* and explicitly note that the underlying Euler dynamics are an open modeling choice handled by the sim layer.

**B5. γ-10-2 (Fluid nonlinear `gh`, vertical S-trans break) — numerical bug.** The stated safety bound `|h| < 10·h₀ ⇒ (1 + λ(h/h₀)^q) > 0` is **false**. Counterexample: λ = −0.25, q = 2, h = 10h₀ ⇒ 1 + (−0.25)(100) = −24. Sim would compute a negative effective gravity and blow up.
- **Fix**: replace the static bound with a per-scenario constraint that *actually holds*. Suggestion: enforce at sampling time `|λ| · (h_max/h₀)^q < 0.5` where `h_max` is the physical envelope of the simulation. Concretely: tighten λ-range when q is large, e.g. `λ ~ Uniform(−ε(q), 0.5)` with `ε(q) = 0.5/(h_max/h₀)^q`. The catalog text should state the constraint as a sampler precondition, not a passive bound.

**B6. γ-12-2 (Nuclear parametric decay, T-trans break).** Same defect as A6 / δ-2-1: random `φ ~ Uniform(0, 2π)` in `cos(ωt + φ)` generically breaks T-rev in addition to T-trans ⇒ dual break.
- **Fix**: drop the phase. Use `λ(t) = λ₀ [1 + ε cos(ω t)]`. Even-in-t about t=0 ⇒ T-rev preserved, T-trans is the unique break.

## Self-audit items — resolutions

- **physicist-A: δ-1-1 / δ-5-1 T-rev as bundled consequence of E / Q break**: **ACCEPTED**. Standard Noether-pairing convention for dissipative shifts. Applies symmetrically to δ-3-1, δ-6-1, δ-8-1, δ-10-1.
- **physicist-B item 1 (δ-8-1 / δ-10-1 dissipative single-label)**: **ACCEPTED** (same convention as above).
- **physicist-B item 2 (δ-7-1 `T→T+c` synchronized with `T_amb`)**: **REJECTED** — see B2 above. Needs comoving reference.
- **physicist-B item 3 (γ-9-2 reciprocity ≡ interchange)**: **ACCEPTED**. At a passive interface these are two views of the same T-rev symmetry; single Noether-pair.
- **physicist-B item 4 (γ-11-1 / γ-7-2 fractional truncation `τ_min = Δt_sim`)**: **ACCEPTED** as sim-level cutoff. Document in the sim spec, not in the law itself.
- **physicist-B item 5 (δ-11-1 / δ-12-1 η/ξ exclusion neighborhoods)**: **ACCEPTED**. Avoids baseline degeneracy.

## Approved Shifts (ready for spec, post-fix audit pending)

γ-1-1, δ-1-1, γ-2-2, γ-3-1, γ-3-2, δ-3-1, γ-4-2, δ-4-1, δ-5-1, γ-6-1, γ-6-2 (w/ doc note), δ-6-1, γ-7-2, γ-8-1 (w/ Hamiltonian-form verify), γ-8-2, γ-9-1, γ-9-2, δ-9-1, δ-10-1, γ-11-1, γ-11-2, δ-11-1, γ-12-1, δ-12-1.

## Round-1 status

12 shifts require fixes (6 to physicist-A, 6 to physicist-B). Messages dispatched. Re-audit will follow each physicist's revision; iterating until all 36 shifts approved.

— end Round 1 —

---

# Audit Report (by invariant-checker, 2026-05-25, round 2 — final)

> Round-2 verifies physicist-A's 7 revisions (6 fixes + γ-6-2 doc note) and physicist-B's 6 revisions. A single residual sign error in γ-2-1 tangential surfaced in round-2A and was corrected in round-2A.1. All 36 shifts now pass the 5-axis audit.

## Final audit table

| Shift | Single-break | Dim | Numerical | Non-copy | Attack-res | Overall |
|---|---|---|---|---|---|---|
| γ-1-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-1-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (R1-fix: full `F = −∇V` w/ tangential piece) |
| δ-1-1 | ✓ (T-rev bundled) | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-2-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (R1-fix + R2A.1 sign correction on tangential) |
| γ-2-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| δ-2-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (R1-fix: φ dropped, pure cos) |
| γ-3-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-3-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| δ-3-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-4-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (R1-fix: `α(1−cos θ)` genuine PAR break) |
| γ-4-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| δ-4-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-5-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (R1-fix: pair-potential form, conservative) |
| γ-5-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (R1-fix: nonlinearity moved to scalar potential `φ_eff`) |
| δ-5-1 | ✓ (T-rev bundled) | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-6-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-6-2 | ✓ (Noether-paired) | ✓ | ✓ | ✓ | ✓ | **APPROVED** (R1-fix: doc note added bundling E loss w/ T-rev/Onsager) |
| δ-6-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-7-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (R1-fix: constant β, field-independent K, parabolic scale preserved) |
| γ-7-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| δ-7-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (R1-fix: comoving `⟨T⟩_Ω(t)` reference preserves `T→T+c`) |
| γ-8-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (Hamiltonian form of `∂_x³` term documented in shift body) |
| γ-8-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| δ-8-1 | ✓ (single-label) | ✓ | ✓ | ✓ | ✓ | **APPROVED** (R1-fix: amplitude-gated `(|u|/u_ref)·∂_t u`, non-textbook) |
| γ-9-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-9-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| δ-9-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-10-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (R1-fix: full Euler `M_{ij} Dv_j/Dt = −∂_i p − ρg ∂_i h` added) |
| γ-10-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (R1-fix: sampling precondition `|λ|(h_max/h₀)^q < 0.5`) |
| δ-10-1 | ✓ (T-rev bundled) | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-11-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-11-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| δ-11-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-12-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |
| γ-12-2 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** (R1-fix: `φ ≡ 0`, T-rev preserved) |
| δ-12-1 | ✓ | ✓ | ✓ | ✓ | ✓ | **APPROVED** |

**Final tally: 36 / 36 APPROVED. No outstanding fixes.**

## Round-2 verification notes

- **A1 γ-1-2**: `F_r = −K(θ) r`, `F_θ = k₀ ξ r · sin(2(θ−φ))` derived directly from `V = ½K(θ)r²`. Conservative ⇒ T-trans/E preserved. ROT singularly broken (`L_z` Noether-paired loss). PAR check: `r → −r ⇒ θ → θ+π`, both cos(2·) and sin(2·) invariant ⇒ PAR preserved. ✓
- **A2 γ-2-1**: Derived from `V = −G₀m₁m₂[1+ξ(μ²−⅓)]/r`. Round-2A flagged a sign error in the tangential decomposition (Coulomb-side sign carried over despite the `−A/r` gravity prefactor); round-2A.1 corrected to `F_⊥ = +(2G₀m₁m₂ξμ/r²)(n̂−μr̂)`. Verified by direct angular-derivative cross-check. ✓
- **A3 γ-4-1**: `θ̈ + (g/L) sin θ + (g/L) α (1−cos θ) = 0`. Under θ → −θ, `(1−cos θ)` is even, `θ̈` and `sin θ` flip ⇒ EOM not invariant ⇒ PAR genuinely broken. Equilibrium at θ=0 preserved (`V'(0)=0, V''(0)=g/L>0`). ✓
- **A4 γ-5-1**: Derived from `V_pair = (k q_i q_j/r)[1 + χ(ν²−⅓)]`. Conservative; ROT singularly broken; pairwise additivity preserved. Sign of tangential decomposition is consistent with the positive Coulomb prefactor (opposite of gravity case). ✓
- **A5 γ-5-2**: Nonlinearity moved to scalar potential level: `φ_eff = φ_lin + ξ φ_lin³/(φ_lin² + φ₀²)`, `E_eff = −∇φ_eff` automatically curl-free ⇒ conservative. Monotonicity of `φ_eff(φ_lin)` verified via positive derivative. ✓
- **A6 δ-2-1**: `G(t) = G₀[1 + β cos(ω_G t)]`, φ dropped. Cos even in t about t=0 ⇒ T-rev preserved, only T-trans broken. ✓
- **A7 γ-6-2**: Doc note explicit on E-loss being Noether-paired with T-rev/Onsager break per Part A dissipative-bundling convention. ✓
- **B1 γ-7-1**: `K_{ij} = k₀[δ_{ij} + β n_i n_j]`, constant β ∈ LogUniform(0.05, 5). K field-independent ⇒ parabolic self-similar scale preserved. Onsager (K symmetric) and `T→T+c` (K independent of T) preserved. SO(3) singularly broken. ✓
- **B2 δ-7-1**: Sink `−λ(T−⟨T⟩_Ω(t))²/T_ref`. Under T→T+c: `⟨T⟩→⟨T⟩+c ⇒ (T−⟨T⟩)` invariant ⇒ sink invariant ⇒ `T→T+c` preserved. Total-energy decay: `d/dt ∫T dV = −(λ/T_ref)·|Ω|·Var(T) ≤ 0` (only-E break). Positivity precondition on initial condition is documented. ✓
- **B3 δ-8-1**: Amplitude-gated `−α₀(|u|/u_ref)∂_t u`. Verified u→−u symmetry: equation maps to itself (LHS and dissipation term both flip sign together with the d'Alembertian wave operator). PAR (x→−x), T-trans, S-trans preserved. Attack-resistance significantly improved over textbook form. ✓
- **B4 γ-10-1**: Modified Euler `M_{ij}(∂_t v_j + (v·∇)v_j) = −∂_i p − ρg ∂_i h` with traceless anisotropic `M`. Bernoulli follows by streamline integration. Mass `∇·v=0`, horizontal Galilean (M constant), `h→h+c` preserved. Eigenvalues of `M/ρ` positive over sampling range. ✓
- **B5 γ-10-2**: Sampling-level precondition `|λ|·(h_max/h₀)^q < 0.5` rigorously bounds `(1+λ(h/h₀)^q) ∈ (0.5, 1.5)` over `|h| ≤ h_max`. Counterexample from round 1 no longer realizable. ✓
- **B6 γ-12-2**: `λ(t) = λ₀[1 + ε cos(ωt)]`, φ ≡ 0. Cos even in t ⇒ T-rev preserved; T-trans uniquely broken. ✓

## Approved shifts (full catalog, ready for spec hand-off)

All 36 shifts approved:
γ-1-1, γ-1-2, δ-1-1, γ-2-1, γ-2-2, δ-2-1, γ-3-1, γ-3-2, δ-3-1, γ-4-1, γ-4-2, δ-4-1, γ-5-1, γ-5-2, δ-5-1, γ-6-1, γ-6-2, δ-6-1, γ-7-1, γ-7-2, δ-7-1, γ-8-1, γ-8-2, δ-8-1, γ-9-1, γ-9-2, δ-9-1, γ-10-1, γ-10-2, δ-10-1, γ-11-1, γ-11-2, δ-11-1, γ-12-1, γ-12-2, δ-12-1.

## Sign-off

D6 shift catalog is consistent with single-symmetry-break discipline, dimensionally clean, numerically safe within sampling preconditions, free of direct named-effect copies, and carries enough randomization plus cross-domain re-skinning to resist lookup-style attacks. Audit closed.

— end Round 2 / final —

