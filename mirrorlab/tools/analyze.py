"""Analyze tools. Spec §4.1.

Pure-compute helpers — no ``sim`` argument is taken (and none is allowed
in the registry binding). These wrappers normalize input shapes and
return scalar / dict outputs suitable for an LLM-callable interface.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np


def _as_array(x: Sequence[float]) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    if arr.ndim != 1:
        raise ValueError("expected 1-D sequence")
    return arr


def fit(*, model: str, data: Dict[str, Sequence[float]],
        init: Optional[Sequence[float]] = None) -> Dict[str, Any]:
    """Least-squares fit of a small library of analytic models to (x, y).

    Supported ``model`` labels: ``"linear"`` (y=a+b·x), ``"cubic_odd"``
    (y=a·x+b·x³), ``"power"`` (y=a·x^b, x>0). Returns coefficients + RMSE.
    """
    x = _as_array(data["x"])
    y = _as_array(data["y"])
    if x.shape != y.shape:
        raise ValueError("x and y must have equal length")
    if model == "linear":
        A = np.stack([np.ones_like(x), x], axis=1)
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        yhat = A @ coef
        return {"model": model, "params": {"a": float(coef[0]), "b": float(coef[1])},
                "rmse": float(np.sqrt(np.mean((y - yhat) ** 2)))}
    if model == "cubic_odd":
        A = np.stack([x, x ** 3], axis=1)
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        yhat = A @ coef
        return {"model": model, "params": {"a": float(coef[0]), "b": float(coef[1])},
                "rmse": float(np.sqrt(np.mean((y - yhat) ** 2)))}
    if model == "power":
        if np.any(x <= 0):
            raise ValueError("power model requires x > 0")
        logx = np.log(x)
        logy = np.log(np.abs(y) + 1e-30)
        A = np.stack([np.ones_like(logx), logx], axis=1)
        coef, *_ = np.linalg.lstsq(A, logy, rcond=None)
        return {"model": model, "params": {"a": float(np.exp(coef[0])),
                                            "b": float(coef[1])}}
    raise ValueError(f"unknown model {model!r}")


def regress(*, x: Sequence[float], y: Sequence[float],
            family: str = "ols") -> Dict[str, Any]:
    """Simple OLS / ridge regression for a single feature."""
    xa = _as_array(x); ya = _as_array(y)
    if xa.shape != ya.shape:
        raise ValueError("x and y must have equal length")
    if family not in {"ols", "ridge"}:
        raise ValueError(f"unsupported family {family!r}")
    A = np.stack([np.ones_like(xa), xa], axis=1)
    if family == "ols":
        coef, *_ = np.linalg.lstsq(A, ya, rcond=None)
    else:
        lam = 1e-3
        coef = np.linalg.solve(A.T @ A + lam * np.eye(2), A.T @ ya)
    yhat = A @ coef
    ss_res = float(np.sum((ya - yhat) ** 2))
    ss_tot = float(np.sum((ya - ya.mean()) ** 2)) + 1e-30
    return {"family": family, "intercept": float(coef[0]), "slope": float(coef[1]),
            "r2": 1.0 - ss_res / ss_tot}


def invariant_check(*, quantity: Sequence[float],
                    trajectory: Optional[Sequence[float]] = None,
                    tol: float = 1e-3) -> Dict[str, Any]:
    """Check whether a quantity is (approximately) conserved along a trajectory."""
    q = _as_array(quantity)
    if q.size < 2:
        raise ValueError("need at least 2 samples")
    mean = float(q.mean())
    rel = float(np.std(q) / (abs(mean) + 1e-30))
    return {"mean": mean, "relative_variation": rel,
            "conserved": rel < tol, "tol": float(tol)}


_SI_BASE = ("kg", "m", "s", "A", "K", "mol", "cd")


def dimensional_analysis(*, expr: str,
                         units: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Best-effort SI dimension parser for a single token / monomial unit string.

    ``expr`` accepted as a unit string like ``"kg*m/s**2"``; returns the
    integer exponent vector over the SI base. Unknown tokens raise.
    """
    units = units or {}
    s = units.get(expr, expr).replace(" ", "")
    exponents = {b: 0 for b in _SI_BASE}
    sign = 1
    parts: List[str] = []
    # Split on * and / preserving sign
    i = 0
    token = ""
    cur_sign = 1
    while i <= len(s):
        ch = s[i] if i < len(s) else "*"
        if ch in "*/":
            if token:
                parts.append((cur_sign, token))
            token = ""
            cur_sign = 1 if ch == "*" else -1
            # handle ** as exponent within token, not a separator
            if ch == "*" and i + 1 < len(s) and s[i + 1] == "*":
                # rewind: this was an exponent marker for previous token
                # actually we already pushed token; restore it
                base_sign, base_tok = parts.pop()
                # gather digits after **
                j = i + 2
                num = ""
                if j < len(s) and s[j] in "+-":
                    num += s[j]; j += 1
                while j < len(s) and s[j].isdigit():
                    num += s[j]; j += 1
                exp_val = int(num) if num else 1
                parts.append((base_sign, base_tok, exp_val))
                i = j
                continue
            i += 1
            continue
        token += ch
        i += 1
    for part in parts:
        if len(part) == 2:
            s_, tok = part; exp_val = 1
        else:
            s_, tok, exp_val = part
        if tok not in exponents:
            raise ValueError(f"unknown unit token {tok!r}")
        exponents[tok] += s_ * exp_val
    return {"expr": expr, "exponents": exponents}


def symbolic_simplify(*, expr: str) -> Dict[str, str]:
    """Lightweight string-level simplifier (collapses whitespace + parens)."""
    s = "".join(expr.split())
    while "((" in s and "))" in s:
        s = s.replace("((", "(").replace("))", ")")
    return {"input": expr, "simplified": s}


def numerical_solve(*, ode: Dict[str, Any]) -> Dict[str, Any]:
    """Solve a small first-order linear ODE family ``dy/dt = a*y + b``.

    ``ode = {"a": float, "b": float, "y0": float, "t": [t0,...,tn]}``.
    """
    from math import exp
    a = float(ode["a"]); b = float(ode["b"]); y0 = float(ode["y0"])
    ts = _as_array(ode["t"])
    if abs(a) < 1e-12:
        ys = y0 + b * ts
    else:
        yp = -b / a
        ys = (y0 - yp) * np.exp(a * ts) + yp
    return {"t": ts.tolist(), "y": ys.tolist()}


def spectrum_fit(*, signal: Sequence[float], dt: float = 1.0) -> Dict[str, Any]:
    """Find the dominant frequency of ``signal`` sampled at ``dt``."""
    arr = _as_array(signal)
    arr = arr - arr.mean()
    mag = np.abs(np.fft.rfft(arr))
    freqs = np.fft.rfftfreq(arr.size, d=float(dt))
    if mag.size <= 1:
        return {"peak_freq": 0.0, "peak_mag": float(mag[0]) if mag.size else 0.0}
    k = int(np.argmax(mag[1:])) + 1
    return {"peak_freq": float(freqs[k]), "peak_mag": float(mag[k])}


def statistical_test(*, hypothesis: str,
                     data: Dict[str, Sequence[float]]) -> Dict[str, Any]:
    """Two-sample mean-equality test (Welch t) or one-sample zero-mean test."""
    if hypothesis == "zero_mean":
        x = _as_array(data["x"])
        n = x.size
        if n < 2:
            raise ValueError("need at least 2 samples")
        se = float(np.std(x, ddof=1) / np.sqrt(n)) + 1e-30
        t = float(x.mean() / se)
        return {"hypothesis": hypothesis, "t_stat": t, "n": n}
    if hypothesis == "equal_means":
        a = _as_array(data["a"]); b = _as_array(data["b"])
        sa, sb = float(np.std(a, ddof=1)), float(np.std(b, ddof=1))
        se = float(np.sqrt(sa ** 2 / a.size + sb ** 2 / b.size)) + 1e-30
        t = float((a.mean() - b.mean()) / se)
        return {"hypothesis": hypothesis, "t_stat": t,
                "n_a": int(a.size), "n_b": int(b.size)}
    raise ValueError(f"unknown hypothesis {hypothesis!r}")


__all__ = ["fit", "regress", "invariant_check", "dimensional_analysis",
           "symbolic_simplify", "numerical_solve", "spectrum_fit",
           "statistical_test"]
