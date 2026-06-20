"""Stage-2 numerical probe.

Per spec §6.2: a surviving entry's predictor is evaluated on a held-out test
grid composed of three sub-grids — in-domain (a), OOD (b), counterfactual (c)
— with default share weights (0.40, 0.40, 0.20) from CAL-1. Per-point error
is RMSLE (CAL-13: clamped at 1e6 before computing). Per-entry score is
``s_entry = exp(-R_bar / τ)`` with τ = 0.20 (CAL-4, calibrated).

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
TAU_DEFAULT = 0.20      # CAL-4 (calibrated: maximizes oracle/baseline-vs-shift-stub separation)
SUBGRID_WEIGHTS = {"a": 0.40, "b": 0.40, "c": 0.20}   # CAL-1

TestPoint = tuple[Mapping[str, float], float]
TestPointC = tuple[Mapping[str, float], float, Any]  # blueprint-xy §2.3
SubGrid = Sequence[TestPoint]
TestGrids = Mapping[str, Sequence]   # heterogeneous: (a)/(b) are 2-tuples, (c) is 3-tuples


# Per-cell relative floor for the signed-log metric (CAL-14). The distance is
# log1p(|x|/floor) with floor = REL_FLOOR_ALPHA · median(|ground truth|) over
# the whole cell. This removes log1p's small-magnitude bias: a plain log1p(|x|)
# collapses to a near-linear toe for |x|≪1, compressing multiplicative physics
# breaks on small-output cells into an invisible additive ripple (textbook stub
# scored spuriously high). With a relative floor every cell sits at
# |y|/floor ≈ 1/α ≈ 20 — squarely in the faithful log region — so the break's
# relative size is scored identically regardless of the output's physical
# magnitude (a force ~1e-3 N and a pressure ~1e5 Pa alike). α is small enough
# that even ~1e-8-magnitude cells stay in the log region and their oracle is
# not amplified by numerical noise.
REL_FLOOR_ALPHA = 0.05


def _slog(x: np.ndarray, floor: float = 1.0) -> np.ndarray:
    x = np.clip(x, -CLAMP, CLAMP)
    return np.sign(x) * np.log1p(np.abs(x) / floor)


def _rel_floor(truths: Sequence[float]) -> float:
    """Per-cell relative floor = α · median(|ground truth|), clamped > 0.

    Computed from the ground truth (never the predictions) so the floor is a
    fixed property of the cell that a predictor cannot game.
    """
    mags = [abs(float(y)) for y in truths if np.isfinite(y) and y != 0.0]
    if not mags:
        return 1.0
    f = REL_FLOOR_ALPHA * float(np.median(mags))
    return f if f > 0.0 else 1.0


def rmsle(predictions: Sequence[float], ground_truth: Sequence[float],
          floor: float = 1.0) -> float:
    """Signed-log RMSE between predictions and ground truth.

    Both inputs are clamped at ±1e6 (CAL-13) before the signed-log transform,
    so a divergent predictor cannot blow the score to ``inf``. ``floor`` is the
    per-cell relative scale (CAL-14) dividing |x| inside log1p; the default 1.0
    reproduces the legacy absolute-magnitude metric for callers that do not
    supply one.
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
    diff = _slog(p, floor) - _slog(y, floor)
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


def _exec_predictor_code(code: str) -> dict[str, Any]:
    """Exec predictor source into a fresh namespace, tolerating LLMs that
    emit literal ``\\n`` (backslash-n) instead of real newlines.

    Some models (observed: gemini on a minority of cells) serialize the
    predictor body with the newlines left as the two-character sequence
    ``\\n``. Python then reads ``def f(x):\\n    ...`` as a line-continuation
    backslash followed by ``n`` and raises SyntaxError, even though the
    physics is correct. We retry once with the escapes unfolded. The retry
    only fires when the as-written code fails to compile AND contains a
    literal ``\\n`` with no real newline, so well-formed multi-line code
    (and intentional ``"\\n"`` string literals inside compilable code) is
    never touched.
    """
    ns: dict[str, Any] = {}
    try:
        exec(code, ns)  # noqa: S102 — trusted within sandbox
        return ns
    except SyntaxError:
        if "\\n" in code and "\n" not in code:
            # Unfold only the literal newline escape; leave every other
            # backslash sequence intact so we don't corrupt the body.
            unfolded = code.replace("\\n", "\n")
            ns = {}
            exec(unfolded, ns)  # noqa: S102 — trusted within sandbox
            return ns
        raise


def _materialize_predictor(entry: Mapping[str, Any]) -> Callable[..., float]:
    """Extract the raw predictor callable from an entry (no closure)."""
    if callable(entry.get("_predictor")):
        return entry["_predictor"]
    pred = entry.get("predictor") or {}
    if pred.get("lang") != "python" or "code" not in pred:
        raise ValueError("entry has no usable predictor")
    ns = _exec_predictor_code(pred["code"])
    funcs = [v for k, v in ns.items() if callable(v) and not k.startswith("_")]
    if not funcs:
        raise ValueError("predictor code defined no callable")
    return funcs[0]


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

    Used for sub-grids (a) and (b). Sub-grid (c) takes the raw predictor via
    ``_entry_predictor_raw`` so per-point ``cf_params`` overrides can win
    over the declared values (blueprint-xy §2.3 Y-plumbing).
    """
    f = _materialize_predictor(entry)
    param_values = {p["name"]: p["value"] for p in entry.get("params", [])}
    allowed, has_var_kw = _predictor_signature(f)

    def bound(**kwargs):
        merged = {**param_values, **kwargs}
        if allowed is not None and not has_var_kw:
            merged = {k: v for k, v in merged.items() if k in allowed}
        return f(**merged)

    return bound


def _entry_predictor_raw(entry: Mapping[str, Any]) -> Callable[..., float]:
    """Materialize the entry's predictor with signature filtering but **no** param closure.

    Used on sub-grid (c) so the caller can merge per-point ``cf_params`` over
    declared params before invoking. Signature filtering is preserved
    (blueprint-xy §2.3 requirement A): predictors with strict positional-or-
    keyword signatures still must not see unexpected kwargs from
    scenario-enriched inputs.
    """
    f = _materialize_predictor(entry)
    allowed, has_var_kw = _predictor_signature(f)

    def raw(**kwargs):
        if allowed is not None and not has_var_kw:
            kwargs = {k: v for k, v in kwargs.items() if k in allowed}
        return f(**kwargs)

    return raw


def _alias_inputs(
    raw: Mapping[str, float],
    *,
    entry_inputs: Optional[Sequence[Mapping[str, Any]]],
    canonical_order: Optional[Sequence[str]],
) -> dict[str, float]:
    """Make the grid's values reachable under the entry's declared input names.

    Strategy (name-first, then a *safe* positional bridge):

    1. Every grid key is passed through under its own name, so a predictor
       that declared an input by its real grid name (``r``, ``t``, …) always
       receives it. This is the common case and must never be disturbed.
    2. Only when a declared input name is NOT itself a grid key do we bridge
       it positionally: the canonical grid key at the same position supplies
       the value — but only if that bridge would not overwrite a value the
       grid already exposes. This recovers the legacy "the model called the
       spring coordinate ``q`` instead of ``x``" case.

    The old implementation ``zip(canonical_order, entry_inputs)`` broke when a
    predictor declared MORE inputs than the domain's canonical order (e.g. a
    force law ``f(G, M, m, r)`` whose canonical inputs are just ``[r]``): it
    paired ``canonical[0]=r`` with ``entry[0]=G`` and renamed the grid's ``r``
    value to ``G``, so the real ``r`` vanished and the predictor was scored
    on CLAMP. Name-first matching plus the no-clobber guard fixes that without
    regressing the rename case.
    """
    if not entry_inputs or not canonical_order:
        return dict(raw)
    out: dict[str, float] = dict(raw)  # name-match: every grid key by its name
    declared_names: list[str] = []
    for spec in entry_inputs:
        try:
            declared_names.append(str(spec["name"]))
        except (KeyError, TypeError):
            declared_names.append("")
    for canon, nm in zip(canonical_order, declared_names):
        # Bridge only a renamed input (declared name differs from the grid
        # key) and only when it adds a value rather than overwriting one the
        # grid already provides under that name.
        if not nm or nm == canon:
            continue
        if canon in raw and nm not in raw:
            out.setdefault(nm, raw[canon])
    return out


def _params_to_predictor_kwargs(cf_params: Any) -> dict[str, float]:
    """Delegate to counterfactual.params_to_predictor_kwargs.

    Kept as a private alias so callers in this module do not pull in the
    counterfactual import at the top of the file (avoids a circular import
    risk if counterfactual ever needs anything from eval).
    """
    from mirrorlab.scenarios.counterfactual import params_to_predictor_kwargs
    return params_to_predictor_kwargs(cf_params)


def evaluate_entry(
    entry: Mapping[str, Any],
    test_grids: TestGrids,
    *,
    tau: float = TAU_DEFAULT,
    weights: Mapping[str, float] = SUBGRID_WEIGHTS,
    canonical_inputs: Optional[Sequence[str]] = None,
) -> float:
    """Per-entry score ``s_entry = exp(-R_bar / τ)`` per spec §6.2.

    ``test_grids`` maps sub-grid key ``"a"|"b"|"c"`` to a sequence of test
    points. Sub-grids (a) and (b) emit 2-tuples ``(inputs_dict, gt)``;
    sub-grid (c) emits 3-tuples ``(inputs_dict, gt, cf_params_obj)`` per
    blueprint-xy §2.3 (Y plumbing). Missing sub-grids drop out of the
    weighted mean and the remaining weights are renormalized.

    On (a)/(b) the predictor is bound with the entry's declared params
    (legacy behavior). On (c) the bare callable is invoked per point with
    declared params overlaid by the per-point ``cf_params`` so a frozen-
    coefficient submission cannot pass by ignoring the perturbation.

    Legacy compatibility: a 2-tuple in (c) is still accepted (treated as
    if ``cf_params_obj`` were ``None``, so declared params win). This keeps
    the Sprint-1 ``_hooke_test_grids`` path working without rewriting it.

    When ``canonical_inputs`` (the scenario's declared input-name order) is
    provided and the entry declares an ``inputs`` list with names that
    differ from the grid keys, the entry's names take over by positional
    alias — letting an LLM that calls the spring coordinate ``q`` instead of
    ``x`` still receive the grid's ``x`` values bound to ``q``.
    """
    bound = _entry_predictor(entry)
    raw: Optional[Callable[..., float]] = None
    declared_params = {p["name"]: p["value"] for p in entry.get("params", [])}
    entry_inputs = entry.get("inputs")
    # Collect (weight, preds, truths) per sub-grid first so the per-cell
    # relative floor can be computed from ALL ground-truth points before
    # scoring any sub-grid — every sub-grid then shares one consistent floor.
    collected: list[tuple[float, list[float], list[float]]] = []
    all_truths: list[float] = []
    for key, grid in test_grids.items():
        if not grid:
            continue
        w = weights.get(key, 0.0)
        if w <= 0:
            continue
        if key == "c":
            if raw is None:
                raw = _entry_predictor_raw(entry)
            preds: list[float] = []
            truths: list[float] = []
            for point in grid:
                # Accept three shapes:
                #   (ins, gt, cf_params_obj)  — XY-fix 3-tuple (default)
                #   (ins, gt)                 — legacy 2-tuple from pre-XY
                #                               builders still in tree
                # A bare scalar (the Sprint-1 hooke numpy-array path) is
                # rejected here just as it would be on (a)/(b); callers
                # that emit numpy arrays do not flow through this path.
                if isinstance(point, tuple) and len(point) == 3:
                    ins, gt, cf_params_obj = point
                elif isinstance(point, tuple) and len(point) == 2:
                    ins, gt = point
                    cf_params_obj = None
                else:
                    raise TypeError(
                        f"sub-grid (c) point must be a 2- or 3-tuple, got {type(point).__name__}"
                    )
                aliased = _alias_inputs(
                    ins,
                    entry_inputs=entry_inputs,
                    canonical_order=canonical_inputs,
                )
                cf_overrides = (
                    _params_to_predictor_kwargs(cf_params_obj)
                    if cf_params_obj is not None
                    else {}
                )
                # Merge order: declared < inputs < cf_overrides.
                # On sub-grid (c) the counterfactual params are the AUTHORITY
                # that defines the ground truth (gt is computed from the
                # perturbed cf params in the loader), so cf_overrides must win
                # over everything — including the scenario-constant values that
                # pack_grids injects into the input dict. An earlier merge let
                # `aliased` win "to stop a predictor input name colliding with
                # a coefficient", but inputs are state variables (x,v,t,…) that
                # never collide with law-coefficient names, whereas the
                # injected UNPERTURBED coefficients (eps, gamma, …) were
                # silently overriding the cf perturbation and penalising the
                # oracle on (c).
                kwargs = {**declared_params, **aliased, **cf_overrides}
                preds.append(_safe_call(raw, kwargs))
                truths.append(float(gt))
        else:
            preds = [
                _safe_call(
                    bound,
                    _alias_inputs(
                        ins,
                        entry_inputs=entry_inputs,
                        canonical_order=canonical_inputs,
                    ),
                )
                for ins, _ in grid
            ]
            truths = [float(gt) for _, gt in grid]
        collected.append((w, preds, truths))
        all_truths.extend(truths)
    if not collected:
        return 0.0
    floor = _rel_floor(all_truths)
    rbars = [(w, rmsle(preds, truths, floor)) for w, preds, truths in collected]
    wsum = sum(w for w, _ in rbars)
    r_bar = sum(w * r for w, r in rbars) / wsum
    return float(math.exp(-r_bar / tau))


__all__ = [
    "CLAMP", "TAU_DEFAULT", "SUBGRID_WEIGHTS",
    "rmsle", "evaluate_entry",
]
