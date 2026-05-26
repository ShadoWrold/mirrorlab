# Sprint 1 Recon: NewtonBench Fork Strategy

**Owner:** newtonbench-recon · **Date:** 2026-05-26 · **Status:** complete

---

## 1. Source

| field | value |
|---|---|
| Repo | https://github.com/HKUST-KnowComp/NewtonBench |
| Paper | arXiv 2510.07172 (ICLR 2026) |
| License | **MIT** (LICENSE, © 2025 HKUST-KnowComp) |
| Last commit | `912a4ba` — 2026-02-27 (`update`) |
| Size | 5.1 MB working tree, 4.5 MB `.git` |
| Python | 3.10+ (per README badge) |
| Deps | numpy ≥1.24, scipy ≥1.7, sklearn, sympy, openai ≥1.68, pandas, matplotlib, seaborn, fix-busted-json, python-dotenv |

MIT means we can vendor freely. No Plan B needed — repo is public and active.

---

## 2. Code structure

### Top-level layout
```
NewtonBench/
├── configs/            # YAML/JSON run configs
├── modules/            # 12 physics domains + common/
│   ├── common/         # ExperimentSystem enum, verlet integrators, shared evaluator
│   └── m0..m11_*/      # one package per domain
├── utils/              # noise.py, call_llm_api.py, agents, code executor
├── result_analysis/
├── quick_start.py
├── run_experiments.py  # main driver (multiprocessing pool)
├── run_all_evaluations.py
└── run_master.py
```

### 12 domains (one package each, `m{N}_<name>`)

| ID | Path | Law |
|---|---|---|
| m0 | `modules/m0_gravity/` | Newton's gravitation |
| m1 | `modules/m1_coulomb_force/` | Coulomb |
| m2 | `modules/m2_magnetic_force/` | Lorentz/magnetic |
| m3 | `modules/m3_fourier_law/` | Fourier heat conduction |
| m4 | `modules/m4_snell_law/` | Snell refraction |
| m5 | `modules/m5_radioactive_decay/` | exp decay |
| m6 | `modules/m6_underdamped_harmonic/` | damped SHO |
| m7 | `modules/m7_malus_law/` | Malus polarization |
| m8 | `modules/m8_sound_speed/` | speed of sound |
| **m9** | **`modules/m9_hooke_law/`** | **Hooke (spring potential energy)** |
| m10 | `modules/m10_be_distribution/` | Bose–Einstein |
| m11 | `modules/m11_heat_transfer/` | heat transfer |

### Per-domain file contract
Each `m*` package exports the same 4-file pattern:

```
m9_hooke_law/
├── __init__.py        # re-exports run_experiment_for_module, evaluate_law,
│                      # get_task_prompt, FUNCTION_SIGNATURE, PARAM_DESCRIPTION
├── core.py            # run_experiment_for_module(...) + evaluate_law(...)
├── laws.py            # LAW_REGISTRY[difficulty][version] -> callable + get_ground_truth_law
├── m9_types.py        # constants (HOOKE_DEFAULTS, precision tolerances)
├── physics.py         # (Hooke: empty stub; other domains: domain helpers)
└── prompts.py         # PARAM_DESCRIPTION, FUNCTION_SIGNATURE, system-specific prompts
```

### Hooke domain in detail

**`laws.py`** — ground-truth registry (this is what we shift):
```python
CONSTANT  = 231.141      # k
CONSTANT2 = 1241.9012    # k2
CONSTANT3 = 12.578       # k3

def _ground_truth_law_easy_v0(x): return 2*k*x**2          # canonical Hooke (energy)
def _ground_truth_law_easy_v1(x): return 2*k*x**0.5
def _ground_truth_law_easy_v2(x): return 2*k*x**3.4
# medium_v0/v1/v2 add a +k2*x^p term; hard adds +k3/x^q
LAW_REGISTRY = {'easy': {...}, 'medium': {...}, 'hard': {...}}

def get_ground_truth_law(difficulty, law_version=None) -> (Callable, str): ...
```

**`core.py`** — simulator. The energy law is plugged in as a **callable parameter**:
```python
def run_experiment_for_module(noise_level, difficulty, system, law_version, **kwargs):
    x = kwargs.get('x', 1.0)
    energy_law, _ = get_ground_truth_law(difficulty, law_version)   # <-- injection point

    if system == ExperimentSystem.VANILLA_EQUATION:
        return inject_noise(energy_law(x), noise_level, ABS_E_PRECISION)
    elif system == ExperimentSystem.SIMPLE_SYSTEM:
        return _run_simple_hooke_velocity_experiment(x, m, noise_level, energy_law)
    elif system == ExperimentSystem.COMPLEX_SYSTEM:
        return _run_difficult_hooke_velocity_experiment(x, m, noise_level, energy_law)
```

`_run_simple_*` / `_run_difficult_*` both take `energy_law` as an argument and call `U = energy_law(x)` once, then derive observables (v_max with air drag, KE with exponential energy-loss). **No global state; no monkey-patching needed.**

**`evaluate_law`** uses `gt_law` (same callable) to score 5000 log-uniform x samples in [1e-3, 1e0] m against the LLM's submitted `def discovered_law(x): ...` via RMSLE + an LLM symbolic-equivalence judge.

> ⚠️ **Spec wording vs. reality.** Sprint-1 spec said "swap the force routine." NewtonBench's Hooke domain is parameterized by **elastic potential energy U(x)**, not force F(x). The submitted answer is `U(x)`. Our γ-1-1 shift must therefore be expressed in the energy form (e.g. `U = 2k·x^(2+γ)` rather than `F = -k·x^(1+γ)`). This is a doc-level fix, not a blocker.

---

## 3. Shift-injection feasibility

**Verdict: YES, function-level injection is clean.** Evidence:

1. The simulator (`run_experiment_for_module`) calls `get_ground_truth_law(difficulty, law_version)` and threads the returned callable into all observable computations as an explicit argument. No `import laws; laws.X(...)` calls elsewhere.
2. `LAW_REGISTRY` is a plain dict — we add one entry and pass `law_version='gamma_1_1'` to swap. No code in `core.py` or `evaluate_law` needs to change.
3. `evaluate_law` re-derives the ground-truth via the same registry path, so adding the entry simultaneously gives us inference-time simulation **and** scoring.
4. `physics.py` for Hooke is a 2-line stub — there's no separate "EOM module" to keep in sync.

Minimum-invasive alternative (if upstream ever refactors): wrap `get_ground_truth_law` in a shim that returns our callable. But not needed today.

---

## 4. Fork strategy recommendation

**Choose Option A: git submodule under `vendor/newtonbench/`.**

Why:
- MIT license → no copyleft constraints either way; submodule preferred for the upstream sync story (active repo, ICLR 2026 in the wild → expect bugfixes/new laws).
- Their `modules/` import path is hard-coded (`from modules.common.types import ...`). A submodule + `sys.path` shim keeps their imports untouched and avoids a mass `s/modules/newtonbench.modules/g` patch.
- Repo is small (5 MB), so submodule cost is negligible.
- Our shifts live *outside* `vendor/` (in `shifts/m9_hooke/`), so submodule updates don't conflict.

License-driven constraints: MIT permits redistribution; we must preserve their `LICENSE` and copyright notice. Add an entry in our top-level NOTICE/README crediting `HKUST-KnowComp/NewtonBench (MIT, © 2025)`.

### Setup commands
```bash
cd /Data/tanh/phyLLM
git submodule add https://github.com/HKUST-KnowComp/NewtonBench.git vendor/newtonbench
git -C vendor/newtonbench checkout 912a4ba          # pin
git submodule update --init --recursive

# additional runtime deps (subset of theirs; we don't need openai/seaborn for sim)
pip install "numpy>=1.24" "scipy>=1.7" "sympy>=1.10" "scikit-learn>=1.0"
```

---

## 5. Sim-engineer recipe (Sprint 1: Hooke only)

### Target layout in our repo
```
/Data/tanh/phyLLM/
├── vendor/newtonbench/           # submodule, untouched
├── newtonbench_shim.py           # adds vendor/newtonbench to sys.path
├── domains/
│   └── hooke/
│       ├── __init__.py
│       └── adapter.py            # wraps run_experiment_for_module + evaluate_law
├── shifts/
│   └── hooke/
│       └── gamma_1_1.py          # our γ-1-1 shifted energy law
└── tests/
    └── test_hooke_shift.py
```

### Step-by-step

1. **Add submodule** — commands in §4.

2. **Create `newtonbench_shim.py`** (3 lines):
   ```python
   import sys, pathlib
   sys.path.insert(0, str(pathlib.Path(__file__).parent / "vendor" / "newtonbench"))
   ```

3. **Define the γ-1-1 shift** in `shifts/hooke/gamma_1_1.py`:
   ```python
   # γ-1-1 shift on Hooke: U(x) = 2 k x^(2+γ), γ small.
   # NOTE: NewtonBench's Hooke targets ENERGY U(x), not force F(x).
   from vendor.newtonbench.modules.m9_hooke_law.laws import CONSTANT as K

   GAMMA = 0.1   # spec-driven; confirm with team-lead

   def shifted_energy(x):
       if x < 0:
           return float('nan')
       return 2.0 * K * (x ** (2.0 + GAMMA))
   ```

4. **Register the shift** (no patch — register at import time) in `domains/hooke/adapter.py`:
   ```python
   import newtonbench_shim  # noqa
   from modules.m9_hooke_law.laws import LAW_REGISTRY
   from modules.m9_hooke_law import core as nb_core
   from shifts.hooke.gamma_1_1 import shifted_energy

   # Register under a new difficulty bucket to avoid colliding with baselines
   LAW_REGISTRY.setdefault('shift', {})['gamma_1_1'] = shifted_energy

   def run_experiment(x, *, noise_level=0.0, system='vanilla_equation'):
       return nb_core.run_experiment_for_module(
           noise_level=noise_level, difficulty='shift',
           system=system, law_version='gamma_1_1', x=x,
       )

   def evaluate(llm_function_str, **kw):
       return nb_core.evaluate_law(
           llm_function_str, param_description="x: displacement (>0)",
           difficulty='shift', law_version='gamma_1_1', **kw,
       )
   ```
   This pattern keeps `vendor/` byte-identical to upstream. `evaluate_law`'s `get_ground_truth_law('shift', 'gamma_1_1')` lookup will find our function via the same registry.

5. **Tests** (`tests/test_hooke_shift.py`):
   - `test_registry_has_shift` — `'gamma_1_1' in LAW_REGISTRY['shift']`
   - `test_run_matches_analytical` — `run_experiment(0.5, noise_level=0)` ≈ `2*K*0.5**2.1` (rtol 1e-6)
   - `test_run_noise_bounded` — at `noise_level=0.01`, deviation ≤ 5σ across 1000 samples
   - `test_evaluate_canonical_fails` — submitting canonical `2*K*x**2` yields `symbolic_equivalent=False` and non-zero RMSLE (sanity: the shift actually shifts)
   - `test_evaluate_matching_law_passes` — submitting `2*K*x**2.1` yields low RMSLE (sanity: scoring path works)

6. **Don't touch** `run_experiments.py` / `run_master.py` / `utils/call_llm_api.py` in Sprint 1 — they're the LLM agent driver; our scenario-engineer + eval-engineer will replace those with our own loop in tasks #3/#4.

### Pitfalls to surface upstream-of-implementation

- **Energy vs. force ambiguity** (see §2 warning). Confirm with team-lead whether γ-1-1 is `U ∝ x^(2+γ)` or `F ∝ x^(1+γ)` — both are defensible readings.
- `core.py` uses `np.sqrt(2*U/m)`; if our shifted `U(x)` returns negative for some γ/x, `v_max` becomes NaN. Add a clamp inside `shifted_energy` if Sprint 1 sweeps negative γ.
- The `'shift'` difficulty bucket is invisible to `prompts.py` — for vanilla LLM-driven runs we'd need to add a prompt template; for the rule-based agent in task #3 this is irrelevant.

---

**Bottom line for sim-engineer (#2):** the spec's assumption holds. Submodule + 1 shim file + 1 shift file + 1 adapter file gets you a working γ-1-1 Hooke domain in <100 LOC, no upstream patches.
