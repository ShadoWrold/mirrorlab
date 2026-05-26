"""Knowledge tools. Spec §4.1.

Read-only, sim-independent textbook lookups. **CRITICAL** (spec §8 / R-1):
formulas returned here are the canonical baseline forms — *never* the
shift-specific form. `lookup_formula("Hooke's law")` MUST return ``F = -kx``
and never γ-1-1's odd-cubic form. This is enforced by a denylist of
shift-specific motif substrings (``tanh``, ``x**3``, etc.) — see
``tests/tools/test_contracts.py::test_knowledge_no_shift_leak``.
"""

from __future__ import annotations

from typing import Any, Dict, List


_CONSTANTS: Dict[str, Dict[str, Any]] = {
    "G":   {"value": 6.67430e-11, "units": "m**3*kg**-1*s**-2",
            "description": "Newtonian gravitational constant"},
    "k_B": {"value": 1.380649e-23, "units": "J*K**-1",
            "description": "Boltzmann constant"},
    "c":   {"value": 299792458.0, "units": "m*s**-1",
            "description": "speed of light in vacuum"},
    "h":   {"value": 6.62607015e-34, "units": "J*s",
            "description": "Planck constant"},
    "e":   {"value": 1.602176634e-19, "units": "C",
            "description": "elementary charge"},
    "k_e": {"value": 8.9875517873681764e9, "units": "N*m**2*C**-2",
            "description": "Coulomb constant"},
    "epsilon_0": {"value": 8.8541878128e-12, "units": "F*m**-1",
                  "description": "vacuum permittivity"},
    "N_A": {"value": 6.02214076e23, "units": "mol**-1",
            "description": "Avogadro constant"},
}


# CRITICAL: every entry here is the TEXTBOOK BASELINE law. The lookup must
# never return a shift-specific motif. See module docstring.
_FORMULAS: Dict[str, Dict[str, str]] = {
    "hooke":     {"formula": "F = -k*x", "domain": "hooke",
                  "description": "linear restoring force"},
    "hookes law":{"formula": "F = -k*x", "domain": "hooke",
                  "description": "linear restoring force"},
    "newton gravity":   {"formula": "F = G*m1*m2/r**2", "domain": "gravity",
                         "description": "inverse-square gravitational attraction"},
    "damped oscillator":{"formula": "m*x'' + b*x' + k*x = 0", "domain": "damped",
                         "description": "linear damped harmonic oscillator"},
    "pendulum": {"formula": "theta'' + (g/L)*sin(theta) = 0", "domain": "pendulum",
                 "description": "simple pendulum (small-angle linearizes to SHM)"},
    "coulomb":  {"formula": "F = k_e*q1*q2/r**2", "domain": "coulomb",
                 "description": "inverse-square electrostatic force"},
    "rlc":      {"formula": "L*q'' + R*q' + q/C = 0", "domain": "rlc",
                 "description": "linear RLC circuit"},
    "fourier":  {"formula": "q = -kappa*grad(T)", "domain": "thermal",
                 "description": "Fourier heat conduction"},
    "wave":     {"formula": "u_tt - c**2 * u_xx = 0", "domain": "wave",
                 "description": "linear scalar wave equation"},
    "snell":    {"formula": "n1*sin(theta1) = n2*sin(theta2)", "domain": "optics",
                 "description": "Snell's law of refraction"},
    "bernoulli":{"formula": "p + 0.5*rho*v**2 + rho*g*h = const", "domain": "fluid",
                 "description": "inviscid streamline energy"},
    "kinetics": {"formula": "dC/dt = -k*C", "domain": "kinetics",
                 "description": "first-order reaction kinetics"},
    "decay":    {"formula": "N(t) = N0*exp(-lambda*t)", "domain": "decay",
                 "description": "radioactive decay law"},
}


_UNIT_TO_SI: Dict[str, float] = {
    "m": 1.0, "cm": 1e-2, "mm": 1e-3, "km": 1e3,
    "s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9, "min": 60.0, "h": 3600.0,
    "kg": 1.0, "g": 1e-3, "mg": 1e-6,
    "K": 1.0,
    "N": 1.0, "kN": 1e3, "J": 1.0, "kJ": 1e3, "eV": 1.602176634e-19,
    "Hz": 1.0, "kHz": 1e3,
    "Pa": 1.0, "kPa": 1e3, "atm": 101325.0,
}


_OBSERVABLES_BY_DOMAIN: Dict[str, List[str]] = {
    "hooke":    ["x (m)", "v (m/s)", "F (N)", "E (J)"],
    "gravity":  ["r (m)", "v (m/s)", "F (N)", "E (J)"],
    "damped":   ["x (m)", "v (m/s)", "E (J)"],
    "pendulum": ["theta (rad)", "omega (rad/s)", "E (J)"],
    "coulomb":  ["r (m)", "F (N)", "U (J)"],
    "rlc":      ["q (C)", "i (A)", "V (V)"],
    "thermal":  ["T (K)", "q (W/m**2)"],
    "wave":     ["u (m)", "u_t (m/s)"],
    "optics":   ["theta1 (rad)", "theta2 (rad)", "n1", "n2"],
    "fluid":    ["p (Pa)", "v (m/s)", "h (m)"],
    "kinetics": ["C (mol/m**3)", "t (s)"],
    "decay":    ["N", "t (s)"],
}


_PROBE_SUGGESTIONS: Dict[str, str] = {
    "hooke":    "Vary amplitude and measure period; check period-amplitude independence.",
    "gravity":  "Measure force at two distinct radii; check inverse-square scaling.",
    "damped":   "Fit exponential envelope to peaks of oscillation.",
    "pendulum": "Sweep initial angle from small to large; track period drift.",
    "coulomb":  "Vary charge separation and read force; test 1/r**2.",
    "rlc":      "Sweep driving frequency; locate resonance peak.",
    "thermal":  "Impose temperature gradient; measure steady-state flux.",
    "wave":     "Excite at one boundary; measure dispersion relation.",
    "optics":   "Vary incident angle; record refracted angle pairs.",
    "fluid":    "Vary cross-section; compare velocity * area along streamline.",
    "kinetics": "Sample concentration vs time; fit exponential decay.",
    "decay":    "Count emissions per unit time over several half-lives.",
}


_SYMMETRY_GLOSSARY: Dict[str, str] = {
    "PAR": "Parity / spatial reflection: x → -x leaves the law unchanged.",
    "ROT": "Rotational invariance: law depends only on rotationally invariant scalars.",
    "T_REV": "Time-reversal: t → -t leaves the law unchanged.",
    "T_TRANS": "Time-translation: t → t + Δ leaves the law unchanged.",
    "X_TRANS": "Spatial translation: x → x + Δ leaves the law unchanged.",
    "SCALE": "Scale invariance: x → λ x rescales the law homogeneously.",
    "LIN": "Linearity in the dynamical variable.",
    "GAUGE": "Gauge invariance under a local phase / potential redefinition.",
}


_DIM_TABLE: Dict[str, str] = {
    "force":     "kg*m*s**-2",
    "energy":    "kg*m**2*s**-2",
    "power":     "kg*m**2*s**-3",
    "momentum":  "kg*m*s**-1",
    "velocity":  "m*s**-1",
    "acceleration": "m*s**-2",
    "pressure":  "kg*m**-1*s**-2",
    "charge":    "A*s",
    "current":   "A",
    "voltage":   "kg*m**2*s**-3*A**-1",
    "spring_constant": "kg*s**-2",
}


_RELATED: Dict[str, List[str]] = {
    "oscillation": ["hooke", "pendulum", "damped", "rlc"],
    "inverse_square": ["newton gravity", "coulomb"],
    "wave_propagation": ["wave", "optics"],
    "exponential_decay": ["decay", "kinetics", "damped"],
    "conservation": ["hooke", "bernoulli", "gravity"],
}


def lookup_constant(*, name: str) -> Dict[str, Any]:
    if name not in _CONSTANTS:
        raise KeyError(f"unknown constant {name!r}")
    return {"name": name, **_CONSTANTS[name]}


def lookup_formula(*, label: str) -> Dict[str, str]:
    """Return the TEXTBOOK BASELINE formula for ``label``.

    Never returns a shift-specific (γ / δ) form. See module docstring.
    """
    key = label.strip().lower().strip("'").strip("\"")
    key = key.replace("'", "").replace("`", "")
    if key in _FORMULAS:
        return {"label": label, **_FORMULAS[key]}
    # try last-word lookup ("Hooke's law" → "hookes law" → "hooke")
    first = key.split()[0]
    if first in _FORMULAS:
        return {"label": label, **_FORMULAS[first]}
    raise KeyError(f"no canonical formula registered for {label!r}")


def unit_convert(*, value: float, from_: str = None, to: str = None,
                 **kwargs: Any) -> Dict[str, Any]:
    """Convert ``value`` from one supported unit to another.

    Accepts ``from_`` (Python-reserved-word workaround) or ``from`` via kwargs.
    """
    src = from_ if from_ is not None else kwargs.get("from")
    dst = to
    if src is None or dst is None:
        raise ValueError("from/to required")
    if src not in _UNIT_TO_SI or dst not in _UNIT_TO_SI:
        raise KeyError(f"unsupported unit pair ({src!r} → {dst!r})")
    si = float(value) * _UNIT_TO_SI[src]
    out = si / _UNIT_TO_SI[dst]
    return {"value": out, "from": src, "to": dst}


def list_observables(*, domain: str) -> Dict[str, Any]:
    if domain not in _OBSERVABLES_BY_DOMAIN:
        raise KeyError(f"unknown domain {domain!r}")
    return {"domain": domain, "observables": list(_OBSERVABLES_BY_DOMAIN[domain])}


def suggest_probe(*, domain: str) -> Dict[str, str]:
    if domain not in _PROBE_SUGGESTIONS:
        raise KeyError(f"unknown domain {domain!r}")
    return {"domain": domain, "suggestion": _PROBE_SUGGESTIONS[domain]}


def symmetry_glossary(*, label: str) -> Dict[str, str]:
    key = label.upper()
    if key not in _SYMMETRY_GLOSSARY:
        raise KeyError(f"unknown symmetry label {label!r}")
    return {"label": key, "definition": _SYMMETRY_GLOSSARY[key]}


def dim_table(*, quantity: str) -> Dict[str, str]:
    key = quantity.strip().lower()
    if key not in _DIM_TABLE:
        raise KeyError(f"no dim entry for {quantity!r}")
    return {"quantity": key, "si_dim": _DIM_TABLE[key]}


def related_phenomena(*, query: str) -> Dict[str, Any]:
    key = query.strip().lower()
    hits: List[str] = []
    if key in _RELATED:
        hits = list(_RELATED[key])
    else:
        for k, v in _RELATED.items():
            if key in k:
                hits.extend(v)
    return {"query": query, "matches": sorted(set(hits))}


__all__ = ["lookup_constant", "lookup_formula", "unit_convert",
           "list_observables", "suggest_probe", "symmetry_glossary",
           "dim_table", "related_phenomena"]
