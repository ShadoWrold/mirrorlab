"""Stage-2 numerical probe.

Per spec §6.2: a surviving entry's predictor is evaluated on a held-out test
grid composed of three sub-grids — in-domain (a), OOD (b), counterfactual (c)
— with default share weights (0.40, 0.40, 0.20) from CAL-1. Per-point error
is RMSLE (CAL-13: clamped at 1e6 before computing). Per-entry score is
``s_entry = exp(-R_bar / τ)`` with τ = 0.5 (CAL-4 default).

Force-channel values can be negative, so we use the signed-log variant
``slog(x) = sign(x) · log1p(|x|)`` for RMSLE — this preserves RMSLE's
scale-spanning robustness while extending it across zero, consistent with
NewtonBench's predictor-distance metric.
"""

from __future__ import annotations

import inspect
import math
from typing import Any, Callable, Mapping, Optional, Sequence

import numpy as np

CLAMP = 1.0e6           # CAL-13
TAU_DEFAULT = 0.5       # CAL-4
SUBGRID_WEIGHTS = {"a": 0.40, "b": 0.40, "c": 0.20}   # CAL-1

TestPoint = tuple[Mapping[str, float], float]
SubGrid = Sequence[TestPoint]
TestGrids = Mapping[str, SubGrid]


def _slog(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, -CLAMP, CLAMP)
    return np.sign(x) * np.log1p(np.abs(x))


def rmsle(predictions: Sequence[float], ground_truth: Sequence[float]) -> float:
    """Signed-log RMSE between predictions and ground truth.

    Both inputs are clamped at ±1e6 (CAL-13) before the signed-log transform,
    so a divergent predictor cannot blow the score to ``inf``.
    """
    p = np.asarray(list(predictions), dtype=float)
    y = np.asarray(list(ground_truth), dtype=float)
    if p.shape != y.shape:
        raise ValueError(f"shape mismatch: {p.shape} vs {y.shape}")
    if p.size == 0:
        return 0.0
    # Substitute NaN/Inf with the clamp limits so a single bad point cannot
    # poison the mean. sign(NaN)=0 in numpy → would give 0 contribution; force
    # NaN to the clamp ceiling instead.
    p = np.where(np.isfinite(p), p, np.sign(np.nan_to_num(p, nan=CLAMP)) * CLAMP)
    p = np.nan_to_num(p, nan=CLAMP, posinf=CLAMP, neginf=-CLAMP)
    diff = _slog(p) - _slog(y)
    return float(np.sqrt(np.mean(diff ** 2)))


def _safe_call(predictor: Callable[..., float], inputs: Mapping[str, float]) -> float:
    try:
        val = predictor(**inputs)
        if not np.isfinite(val):
            return math.copysign(CLAMP, val) if val != 0 else CLAMP
        return float(val)
    except Exception:
        return CLAMP


def _predictor_signature(f: Callable[..., float]) -> tuple[Optional[set[str]], bool]:
    """Return (allowed_param_names, accepts_var_kw).

    ``allowed_param_names`` is ``None`` when the signature cannot be
    introspected (e.g. built-ins) — callers should then pass all kwargs
    unchanged.
    """
    try:
        sig = inspect.signature(f)
    except (TypeError, ValueError):
        return None, True
    allowed: set[str] = set()
    has_var_kw = False
    for name, p in sig.parameters.items():
        if p.kind == inspect.Parameter.VAR_KEYWORD:
            has_var_kw = True
        elif p.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            allowed.add(name)
    return allowed, has_var_kw


def _entry_predictor(entry: Mapping[str, Any]) -> Callable[..., float]:
    """Materialize the entry's predictor callable bound with its declared params.

    The entry format from spec §5 may either provide a Python ``predictor``
    block with ``code`` defining a function ``f(...)``, or attach a callable
    directly under ``entry["_predictor"]`` (test-friendly path). Declared
    parameter values from ``entry["params"]`` are partially applied so the
    predictor only consumes input-variable kwargs at call time. Extra kwargs
    (e.g. scenario constants the grid packer enriched in but the predictor
    does not consume) are silently filtered against the predictor signature
    so a strict positional-or-keyword signature is not poisoned by them.
    """
    if callable(entry.get("_predictor")):
        f = entry["_predictor"]
    else:
        pred = entry.get("predictor") or {}
        if pred.get("lang") != "python" or "code" not in pred:
            raise ValueError("entry has no usable predictor")
        ns: dict[str, Any] = {}
        exec(pred["code"], ns)  # noqa: S102 — trusted within sandbox
        funcs = [v for k, v in ns.items() if callable(v) and not k.startswith("_")]
        if not funcs:
            raise ValueError("predictor code defined no callable")
        f = funcs[0]
    param_values = {p["name"]: p["value"] for p in entry.get("params", [])}
    allowed, has_var_kw = _predictor_signature(f)

    def bound(**kwargs):
        merged = {**param_values, **kwargs}
        if allowed is not None and not has_var_kw:
            merged = {k: v for k, v in merged.items() if k in allowed}
        return f(**merged)

    return bound


def _alias_inputs(
    raw: Mapping[str, float],
    *,
    entry_inputs: Optional[Sequence[Mapping[str, Any]]],
    canonical_order: Optional[Sequence[str]],
) -> dict[str, float]:
    """Rename grid keys to entry-declared input names when they disagree.

    When the LLM's submission declares input names that differ from the
    test-grid keys, the canonical order from the scenario dim signature
    serves as the positional bridge: ``canonical_order[i]`` (the grid key)
    is renamed to ``entry_inputs[i]['name']``. Keys not covered by the
    canonical order are passed through untouched so scenario constants
    (q1/q2/k_e/...) the grid packer injected remain available.
    """
    if not entry_inputs or not canonical_order:
        return dict(raw)
    pairs = list(zip(canonical_order, entry_inputs))
    out: dict[str, float] = {}
    renamed: set[str] = set()
    for canon, spec in pairs:
        if canon not in raw:
            continue
        try:
            new_name = spec["name"]
        except (KeyError, TypeError):
            new_name = canon
        out[str(new_name)] = raw[canon]
        renamed.add(canon)
    for k, v in raw.items():
        if k in renamed:
            continue
        out.setdefault(k, v)
    return out


def evaluate_entry(
    entry: Mapping[str, Any],
    test_grids: TestGrids,
    *,
    tau: float = TAU_DEFAULT,
    weights: Mapping[str, float] = SUBGRID_WEIGHTS,
    canonical_inputs: Optional[Sequence[str]] = None,
) -> float:
    """Per-entry score ``s_entry = exp(-R_bar / τ)`` per spec §6.2.

    ``test_grids`` maps sub-grid key ``"a"|"b"|"c"`` to a sequence of
    ``(inputs_dict, ground_truth_scalar)`` tuples. Missing sub-grids drop out
    of the weighted mean and the remaining weights are renormalized.

    When ``canonical_inputs`` (the scenario's declared input-name order) is
    provided and the entry declares an ``inputs`` list with names that
    differ from the grid keys, the entry's names take over by positional
    alias — letting an LLM that calls the spring coordinate ``q`` instead of
    ``x`` still receive the grid's ``x`` values bound to ``q``.
    """
    predictor = _entry_predictor(entry)
    entry_inputs = entry.get("inputs")
    rbars: list[tuple[float, float]] = []
    for key, grid in test_grids.items():
        if not grid:
            continue
        w = weights.get(key, 0.0)
        if w <= 0:
            continue
        preds = [
            _safe_call(
                predictor,
                _alias_inputs(
                    ins,
                    entry_inputs=entry_inputs,
                    canonical_order=canonical_inputs,
                ),
            )
            for ins, _ in grid
        ]
        truths = [gt for _, gt in grid]
        rbars.append((w, rmsle(preds, truths)))
    if not rbars:
        return 0.0
    wsum = sum(w for w, _ in rbars)
    r_bar = sum(w * r for w, r in rbars) / wsum
    return float(math.exp(-r_bar / tau))


__all__ = [
    "CLAMP", "TAU_DEFAULT", "SUBGRID_WEIGHTS",
    "rmsle", "evaluate_entry",
]
