"""Structural-correctness probes (Phase 1 — standalone diagnostic).

The numeric stage (``eval/numeric.py``) only asks "do the predictor's *numbers*
match the truth, point by point". It is blind to whether the predictor has the
right *physical structure*: a predictor whose pointwise error is 0.4% but whose
conservation structure is completely wrong scores high (verified Phase 0). This
module adds the orthogonal axis — does the predictor have the correct
symmetry / conservation structure — as a "right numbers, wrong physics"
detector.

Design
------
Each probe maps a black-box predictor ``f(**kwargs) -> float`` to a scalar
*structure metric* M(f), computed only from repeated evaluation at transformed
input points (parity: x↦−x; scale: x↦λx; rotation: r↦R·r; time-reversal:
v↦−v). The SAME probe is run on the cell's true law (wrapped via
``make_oracle_predictor``) to get a reference M*. The structure error is
``|M(f) − M*|``: a predictor that drops the broken-symmetry term lands at the
*unbroken* metric value and is exposed even when its pointwise error is tiny.

This is a pure black-box construction: no symbolic analysis, no gradients —
only ``f`` evaluations. It composes with the single-source CellSpec: each
cell's ``break_type`` field selects which probe applies, and its
``law`` provides the truth reference.

Scope (Phase 1)
---------------
- Produces the RAW metric M and error |M−M*|, NOT a normalized [0,1] score.
  Normalization (per-probe σ calibration) is a later step.
- Fully standalone: does NOT touch ``numeric.py`` / ``scoring.py`` /
  ``ScoreDetail``. Integration into the scored S_scen is Phase 2.
- A cell whose broken symmetry has no matching probe (e.g. T_TRANS on a
  charge-pair input with no spatial/velocity axis) reports ``applicable=False``
  rather than fabricating a metric. Coverage is reported honestly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from mirrorlab.spec import CellSpec, make_oracle_predictor

Predictor = Callable[..., float]


@dataclass(frozen=True)
class StructuralResult:
    """One structural probe applied to one predictor.

    symmetry      : the cell's broken-symmetry label (PAR / TR / SCALE / ROT /
                    T_TRANS / none).
    probe_name    : which probe ran ("" if none applicable).
    applicable    : whether a probe matched this cell's symmetry + input shape.
    m_pred        : structure metric of the submitted predictor (None if N/A).
    m_star        : structure metric of the true law (reference; None if N/A).
    m_unbroken    : the metric value a structurally-UNBROKEN law takes (the
                    natural normalization anchor; None if N/A).
    raw_error     : |m_pred − m_star| (None if N/A).
    captured_fraction : how much of the true break the predictor reproduced,
                    normalized to ≈[0,1] by the unbroken anchor:
                        (m_pred − m_unbroken) / (m_star − m_unbroken)
                    ≈1.0 → captured the break (true structure); ≈0.0 →
                    collapsed to the unbroken form (the "right numbers, wrong
                    physics" cheat). This is dimensionless and cross-cell
                    comparable regardless of how small the break's magnitude is
                    — a SCALE break of metric 0.002 and a PAR break of 0.22 map
                    to the same [0,1] scale. None if N/A or the cell's break is
                    degenerate (m_star ≈ m_unbroken).
    note          : human-readable reason when not applicable.
    """

    symmetry: str
    probe_name: str
    applicable: bool
    m_pred: Optional[float] = None
    m_star: Optional[float] = None
    m_unbroken: Optional[float] = None
    raw_error: Optional[float] = None
    captured_fraction: Optional[float] = None
    note: str = ""


# ---------------------------------------------------------------------------
# Safe black-box evaluation
# ---------------------------------------------------------------------------

def _safe(f: Predictor, **kwargs: float) -> float:
    """Evaluate f, mapping any failure / non-finite to NaN (excluded later)."""
    try:
        v = float(f(**kwargs))
        return v if math.isfinite(v) else math.nan
    except Exception:
        return math.nan


def _isotonic(y: Sequence[float]) -> np.ndarray:
    """Best non-decreasing fit to ``y`` (pool-adjacent-violators, unit weights).

    Used by the time-translation probe to strip a monotone trend from f(t):
    the residual is what is left after the best monotone explanation, so a
    purely monotone signal (ordinary time evolution / a cumulative integral)
    leaves ~0 while an oscillatory coefficient modulation survives.
    """
    stack: List[List[float]] = []  # each block = [pooled mean, weight]
    for v in y:
        stack.append([float(v), 1.0])
        while len(stack) >= 2 and stack[-2][0] > stack[-1][0]:
            v2, w2 = stack.pop()
            v1, w1 = stack.pop()
            stack.append([(v1 * w1 + v2 * w2) / (w1 + w2), w1 + w2])
    out: List[float] = []
    for v, w in stack:
        out.extend([v] * int(round(w)))
    return np.asarray(out[: len(y)], dtype=float)


def _monotone_detrended_amplitude(arr: np.ndarray) -> Optional[float]:
    """Relative amplitude of the NON-monotone part of a 1-D signal.

    Subtract the best non-decreasing AND the best non-increasing isotonic fit,
    keep whichever leaves the smaller residual, and return its std normalized by
    ⟨|arr|⟩. A constant or monotone signal → ≈0; an oscillation → >0. Returns
    None if the signal is degenerate (all-zero scale).
    """
    scale = float(np.mean(np.abs(arr)))
    if scale <= 0:
        return None
    inc = _isotonic(arr)
    dec = -_isotonic(-arr[::-1])[::-1]      # best non-increasing fit
    r_inc = arr - inc
    r_dec = arr - dec
    resid = r_inc if np.std(r_inc) <= np.std(r_dec) else r_dec
    return float(np.std(resid)) / scale


def _odd_even_ratio(vals_plus: Sequence[float], vals_minus: Sequence[float]) -> Optional[float]:
    """⟨|odd|⟩ / (⟨|even|⟩+⟨|odd|⟩) over paired (f(+), f(−)) samples.

    1.0 = purely antisymmetric (odd); 0.0 = purely symmetric (even). A
    parity / time-reversal break shifts a pure-odd (or pure-even) law toward
    the middle. Returns None if no finite pairs.
    """
    even: List[float] = []
    odd: List[float] = []
    for fp, fm in zip(vals_plus, vals_minus):
        if math.isnan(fp) or math.isnan(fm):
            continue
        even.append(0.5 * (fp + fm))
        odd.append(0.5 * (fp - fm))
    if not odd:
        return None
    me = float(np.mean(np.abs(even)))
    mo = float(np.mean(np.abs(odd)))
    denom = me + mo
    return mo / denom if denom > 0 else None


# ---------------------------------------------------------------------------
# Probes — each: (predictor, probe_points) -> Optional[float] metric M
# ---------------------------------------------------------------------------
#
# probe_points is a list of input dicts sampled from the cell's real grid;
# each probe transforms them in its own way and aggregates a scalar metric.

def probe_parity(f: Predictor, points: Sequence[Mapping[str, float]],
                 axis: str = "x") -> Optional[float]:
    """Parity signature χ on a scalar axis: odd-component fraction.

    Reflects the chosen axis (x ↦ −x), holding any other inputs fixed. An odd
    law (ordinary spring) → χ≈1; a parity break injects an even component → χ<1.
    """
    plus, minus = [], []
    for p in points:
        if axis not in p:
            return None
        pm = dict(p)
        pm[axis] = -p[axis]
        plus.append(_safe(f, **p))
        minus.append(_safe(f, **pm))
    return _odd_even_ratio(plus, minus)


def probe_time_reversal(f: Predictor, points: Sequence[Mapping[str, float]],
                        vaxis: str = "v") -> Optional[float]:
    """Time-reversal asymmetry Σ_T: v-odd fraction.

    Conservative (T-even) force is unchanged under v ↦ −v (Σ_T≈0); a
    dissipative (T-odd) term flips sign (Σ_T>0). Requires a velocity axis.
    """
    plus, minus = [], []
    for p in points:
        if vaxis not in p:
            return None
        pm = dict(p)
        pm[vaxis] = -p[vaxis]
        plus.append(_safe(f, **p))
        minus.append(_safe(f, **pm))
    return _odd_even_ratio(plus, minus)


def probe_scale(f: Predictor, points: Sequence[Mapping[str, float]],
                axis: str = "x",
                lambdas: Sequence[float] = (1.3, 1.7, 2.2, 3.0)) -> Optional[float]:
    """Scale-covariance break: variance of the running scaling exponent.

    For a scale-covariant law f(λx)=λ^p f(x), s = ln|f(λx)/f(x)|/lnλ is a
    constant p for all λ. A SCALE break makes s drift with λ (running
    exponent) → Var[s] > 0. We average Var[s] across the probe points.
    """
    svars: List[float] = []
    for p in points:
        if axis not in p or p[axis] == 0:
            continue
        base = _safe(f, **p)
        if math.isnan(base) or base == 0:
            continue
        s_vals: List[float] = []
        for lam in lambdas:
            pl = dict(p)
            pl[axis] = lam * p[axis]
            fl = _safe(f, **pl)
            if math.isnan(fl) or fl == 0 or (fl / base) <= 0:
                continue
            s_vals.append(math.log(abs(fl / base)) / math.log(lam))
        if len(s_vals) >= 2:
            svars.append(float(np.var(s_vals)))
    if not svars:
        return None
    return float(np.mean(svars))


def probe_rotation(f: Predictor, points: Sequence[Mapping[str, float]],
                   axes: Tuple[str, str, str] = ("x", "y", "z"),
                   n_phi: int = 16) -> Optional[float]:
    """Rotational anisotropy: higher angular-harmonic energy fraction.

    For a vector input, hold |r| fixed and sweep an in-plane rotation R_φ in
    the (axes[0], axes[1]) plane. A scalar that is a function of |r| only is
    constant on the orbit (all harmonic energy in the m=0 mode). A rotational
    break (e.g. a quadrupole ν²−1/3 anisotropy) excites m≥1 modes. Metric =
    fraction of angular spectral energy in m≥1, averaged over probe points.
    """
    ax, ay, az = axes
    fracs: List[float] = []
    for p in points:
        if not all(a in p for a in axes):
            return None
        x0, y0 = p[ax], p[ay]
        rho = math.hypot(x0, y0)
        if rho == 0:
            continue
        phi0 = math.atan2(y0, x0)
        samples: List[float] = []
        for k in range(n_phi):
            phi = phi0 + 2 * math.pi * k / n_phi
            pr = dict(p)
            pr[ax] = rho * math.cos(phi)
            pr[ay] = rho * math.sin(phi)
            samples.append(_safe(f, **pr))
        arr = np.array(samples, dtype=float)
        if np.any(np.isnan(arr)):
            continue
        spec = np.abs(np.fft.rfft(arr)) ** 2
        total = float(np.sum(spec))
        if total <= 0:
            continue
        fracs.append(float(np.sum(spec[1:]) / total))  # m≥1 energy fraction
    if not fracs:
        return None
    return float(np.mean(fracs))


def probe_time_translation(f: Predictor, points: Sequence[Mapping[str, float]],
                           taxis: str = "t", n_t: int = 48) -> Optional[float]:
    """Time-translation break: amplitude of explicit, oscillatory t-dependence.

    Holds every NON-time input fixed at a probe point and sweeps ``t`` across
    the grid's t-span. For a time-translation-symmetric law the value at fixed
    state is independent of t (metric 0). A T_TRANS break modulates a law
    coefficient periodically (e.g. ω₀²·[1+ε cos Ω t]); the value then oscillates
    in t and the metric is > 0.

    The metric is the *monotone-detrended* relative amplitude (isotonic fit
    removed). This is the crucial distinction the probe must make: an output
    that merely *evolves* in time — a decaying N(t), a cumulative flux ∝ t^(1-p)
    — is monotone and is absorbed by the isotonic detrend (→0), so only a
    genuine periodic coefficient modulation survives. Empirically (oracle):
    damped_ho/pendulum/rlc/gravity land at 0.14–0.5; a predictor that drops the
    modulation lands at 0; depth-½ modulation lands at half — the metric is
    linear in the modulation depth.

    Requires BOTH a ``t`` axis and at least one non-t input to hold fixed: a
    t-only observable (e.g. decay N(t)) gives no way to separate coefficient
    modulation from ordinary evolution black-box, so the probe returns None
    (not-applicable) rather than fabricating a metric.
    """
    if not points:
        return None
    non_t = [k for k in points[0] if k != taxis]
    t_vals = [p[taxis] for p in points if taxis in p]
    if not t_vals or not non_t:
        return None
    t_lo, t_hi = min(t_vals), max(t_vals)
    if t_hi <= t_lo:
        return None
    t_grid = np.linspace(t_lo, t_hi, n_t)
    amps: List[float] = []
    for p in points:
        if taxis not in p:
            return None
        arr = np.array([_safe(f, **{**p, taxis: float(t)}) for t in t_grid])
        if np.any(np.isnan(arr)):
            continue
        a = _monotone_detrended_amplitude(arr)
        if a is not None:
            amps.append(a)
    if not amps:
        return None
    return float(np.mean(amps))


# ---------------------------------------------------------------------------
# Probe registry — selected by CellSpec.break_type, with the transform
# axes supplied by CellSpec.probe_spec (single source). The anchor is the
# metric value a structurally-UNBROKEN law takes — it normalizes the
# captured-fraction so the score is dimensionless and cross-cell comparable:
#   PAR : a pure-odd (unbroken-parity) force has χ = 1.0
#   TR  : a conservative (T-even) force has Σ_T = 0.0
#   SCALE: a scale-covariant law has Var[s] = 0.0
#   ROT : an isotropic scalar has m≥1 harmonic energy = 0.0
#   T_TRANS: a time-translation-symmetric law has osc-amplitude = 0.0
# ---------------------------------------------------------------------------

# Default axes per symmetry — used when a cell has no probe_spec (the original
# 7 input-matched cells keep working without an explicit declaration).
_DEFAULT_BY_SYMMETRY: Dict[str, Tuple[str, str, float]] = {
    "PAR": ("parity", "parity_chi", 1.0),
    "TR": ("time_reversal", "time_reversal_sigma", 0.0),
    "SCALE": ("scale", "scale_exponent_var", 0.0),
    "ROT": ("rotation", "rotation_anisotropy", 0.0),
    "T_TRANS": ("time_translation", "time_translation_osc", 0.0),
}

# kind → (probe callable, display name, unbroken anchor).
_PROBE_BY_KIND: Dict[str, Tuple[Callable[..., Optional[float]], str, float]] = {
    "parity": (probe_parity, "parity_chi", 1.0),
    "time_reversal": (probe_time_reversal, "time_reversal_sigma", 0.0),
    "scale": (probe_scale, "scale_exponent_var", 0.0),
    "rotation": (probe_rotation, "rotation_anisotropy", 0.0),
    "time_translation": (probe_time_translation, "time_translation_osc", 0.0),
}


def _call_probe(kind: str, f: Predictor,
                points: Sequence[Mapping[str, float]],
                axes: Tuple[str, ...]) -> Optional[float]:
    """Invoke the probe of ``kind`` with the declared transform axes.

    Scalar probes (parity/scale/time_reversal) take a single ``axis``; the
    rotation probe takes an ``axes`` triple (a 2-tuple is padded with the
    first axis so the in-plane rotation still works)."""
    probe_fn = _PROBE_BY_KIND[kind][0]
    if kind == "rotation":
        ax = tuple(axes)
        if len(ax) == 2:
            ax = (ax[0], ax[1], ax[0])  # planar rotation; 3rd unused beyond key check
        return probe_fn(f, points, axes=ax[:3])
    # scalar probes
    if not axes:
        return None
    if kind == "time_reversal":
        return probe_fn(f, points, vaxis=axes[0])
    if kind == "time_translation":
        return probe_fn(f, points, taxis=axes[0])
    return probe_fn(f, points, axis=axes[0])


def _sample_points(test_grids: Mapping[str, Sequence],
                   max_points: int = 30) -> List[Dict[str, float]]:
    """Pull input dicts from sub-grid (a) (in-domain) for probing."""
    pts: List[Dict[str, float]] = []
    grid_a = test_grids.get("a") or []
    for entry in grid_a[:max_points]:
        ins = entry[0]
        if isinstance(ins, Mapping):
            pts.append({str(k): float(v) for k, v in ins.items()})
    return pts


def _resolve_probe(spec: CellSpec) -> Optional[Tuple[str, str, float, Tuple[str, ...]]]:
    """Return (kind, probe_name, anchor, axes) for a cell, or None if no probe.

    Prefers the cell's explicit ``probe_spec`` (single-source axis
    declaration); falls back to a symmetry-keyed default with a guessed axis
    for the original input-matched cells (PAR→x, TR→v, SCALE→x, ROT→x,y,z)."""
    ps = spec.probe_spec
    if ps is not None:
        entry = _PROBE_BY_KIND.get(ps.kind)
        if entry is None:
            return None
        _, probe_name, anchor = entry
        return (ps.kind, probe_name, anchor, tuple(ps.axes))
    # legacy default: symmetry → default axis guess
    dflt = _DEFAULT_BY_SYMMETRY.get(spec.break_type)
    if dflt is None:
        return None
    kind, probe_name, anchor = dflt
    guess = {"parity": ("x",), "time_reversal": ("v",),
             "scale": ("x",), "rotation": ("x", "y", "z"),
             "time_translation": ("t",)}[kind]
    return (kind, probe_name, anchor, guess)


def structural_score(
    predictor: Predictor,
    spec: CellSpec,
    base_params: Any,
    *,
    test_grids: Mapping[str, Sequence],
) -> StructuralResult:
    """Run the cell's structural probe on ``predictor`` vs the true law.

    The probe + transform axes are resolved from ``spec.probe_spec`` (single
    source) when declared, else from a symmetry-keyed default. The truth
    reference M* is computed by running the SAME probe on the oracle predictor
    wrapping ``spec.law``. Returns raw metrics + |M−M*| + a normalized
    captured_fraction.
    """
    sym = spec.break_type
    resolved = _resolve_probe(spec)
    if resolved is None:
        return StructuralResult(
            symmetry=sym, probe_name="", applicable=False,
            note=f"no probe registered for symmetry {sym!r}",
        )
    kind, probe_name, m_unbroken, axes = resolved
    points = _sample_points(test_grids)
    if not points:
        return StructuralResult(
            symmetry=sym, probe_name=probe_name, applicable=False,
            note="no probe points available from sub-grid (a)",
        )

    m_pred = _call_probe(kind, predictor, points, axes)
    if m_pred is None:
        return StructuralResult(
            symmetry=sym, probe_name=probe_name, applicable=False,
            note="probe could not run (required input axis absent or degenerate)",
        )

    oracle = make_oracle_predictor(spec, base_params)
    m_star = _call_probe(kind, oracle, points, axes)
    if m_star is None:
        return StructuralResult(
            symmetry=sym, probe_name=probe_name, applicable=False,
            note="probe could not run on the true law",
        )

    # captured_fraction = how much of the true break the predictor reproduced,
    # normalized by the unbroken anchor. None when the true break is degenerate
    # (m_star ≈ m_unbroken, e.g. a baseline cell or a vanishingly small break)
    # so we never divide by ~0.
    signal = float(m_star) - m_unbroken
    captured = (
        (float(m_pred) - m_unbroken) / signal if abs(signal) > 1e-9 else None
    )

    return StructuralResult(
        symmetry=sym, probe_name=probe_name, applicable=True,
        m_pred=float(m_pred), m_star=float(m_star), m_unbroken=m_unbroken,
        raw_error=abs(float(m_pred) - float(m_star)),
        captured_fraction=captured,
    )


__all__ = [
    "StructuralResult",
    "structural_score",
    "probe_parity",
    "probe_time_reversal",
    "probe_scale",
    "probe_rotation",
    "probe_time_translation",
]
