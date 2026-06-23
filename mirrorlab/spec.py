"""Single source of truth for a benchmark cell — the CellSpec architecture.

Background
----------
Historically a cell's definition was scattered across 7 files (the shift
module, the loader grid builder, the ceiling oracle, the agent stub, two
counterfactual tables, the prompts observables, and the loader dispatch
maps). The break formula alone was copied 3 times and kept in sync by hand.

This module introduces the single-source-of-truth pieces that let a cell
declare everything once and have every consumer DERIVE from it:

  * field-role metadata  — each Params field is tagged `law / mass / ic /
    axis` right at its declaration (Pydantic-style), so "which params does
    the counterfactual perturb" and "what canonical name does the predictor
    see" stop being two hand-maintained tables and become projections of the
    field declarations.
  * CellSpec             — one frozen dataclass holding a cell's law, params
    type, sampler/validator, output channel, broken symmetry, and grid spec.
  * CELL_REGISTRY        — a central `{(domain, shift): CellSpec}` map (the
    Gymnasium `register`/`make` pattern) that every system reads, replacing
    the parallel lookup tables.

Migration is incremental: this module coexists with the legacy tables. A
golden-parity test asserts the derived counterfactual tables are byte-equal
to the hand-written ones before any legacy literal is deleted.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

# Namespace key under which we stash per-field role metadata, per the stdlib
# dataclasses convention (field metadata is a read-only mapping shared by
# third parties, each under its own key).
_META_KEY = "mirrorlab"


# --------------------------------------------------------------------------
# Field-role metadata helpers (the `P.` API used at Params declarations)
# --------------------------------------------------------------------------
#
# A field's ROLE decides two long-standing, bug-prone facts:
#   * role == "law"  -> the counterfactual sub-grid (c) perturbs it, AND the
#     predictor sees it under a CANONICAL name (e.g. internal `G0` -> `G`,
#     `q_src` -> `q_1`). These are the cell's free law coefficients.
#   * role in {"mass","ic","axis"} -> the counterfactual NEVER perturbs it.
#       - mass : a passive scale (gravity m) that is not a law coefficient
#       - ic   : an initial condition / boundary condition (r0, v0, theta_i)
#       - axis : an OBSERVATION axis swept by the test grid (wave γ-8-1's k).
#                Perturbing an axis would override the grid's swept value and
#                cap the oracle on (c) — this is exactly the bug we fixed; the
#                `axis` role freezes that fix as data.
#
# Only `law` fields carry a canonical name. The canonical name is stored
# EXPLICITLY (not derived by a rule) because real benchmark naming is
# irregular: `k0 -> k` (strip 0) but `L1 -> L_1` (keep), `q_src -> q_1`
# (role-suffix collapse). A rule would be more fragile than a hand label.


def _role(role: str, canonical: Optional[str] = None) -> Mapping[str, Any]:
    return {_META_KEY: {"role": role, "canonical": canonical}}


class P:
    """Field-role tags. Use at a Params dataclass field declaration::

        G: float = field(metadata=P.law("G"))     # perturbed by cf, seen as "G"
        m: float = field(metadata=P.mass())       # cf-excluded passive scale
        r0: float = field(metadata=P.ic())        # cf-excluded initial condition
        k: float = field(metadata=P.axis())       # cf-excluded observation axis
    """

    @staticmethod
    def law(canonical: str) -> Mapping[str, Any]:
        """A free law coefficient: perturbed by cf, seen under `canonical`."""
        return _role("law", canonical)

    @staticmethod
    def mass() -> Mapping[str, Any]:
        return _role("mass")

    @staticmethod
    def ic() -> Mapping[str, Any]:
        return _role("ic")

    @staticmethod
    def axis() -> Mapping[str, Any]:
        return _role("axis")


def field_role(f) -> Optional[str]:
    """Return the role string of a dataclass Field, or None if untagged."""
    meta = f.metadata.get(_META_KEY)
    return meta.get("role") if meta else None


def field_canonical(f) -> Optional[str]:
    meta = f.metadata.get(_META_KEY)
    return meta.get("canonical") if meta else None


def law_fields(params_type: type) -> Tuple[str, ...]:
    """Internal field names whose role is `law` (the cf-perturbed set).

    Equivalent to the legacy `_LAW_PARAM_FIELDS[params_type]`.
    """
    return tuple(f.name for f in fields(params_type) if field_role(f) == "law")


def predictor_name_map(params_type: type) -> Dict[str, str]:
    """`{internal_field: canonical_name}` for the cell's law fields.

    Equivalent to the legacy `_PREDICTOR_NAME_MAP[params_type]`.
    """
    out: Dict[str, str] = {}
    for f in fields(params_type):
        if field_role(f) == "law":
            out[f.name] = field_canonical(f) or f.name
    return out


def is_fully_tagged(params_type: type) -> bool:
    """True iff every field of the dataclass carries a mirrorlab role tag.

    Used by migration to tell apart already-migrated Params (read roles from
    metadata) from legacy ones (still read from the hand-written tables).
    """
    if not is_dataclass(params_type):
        return False
    return all(field_role(f) is not None for f in fields(params_type))


# --------------------------------------------------------------------------
# GridSpec + CellSpec
# --------------------------------------------------------------------------

# A grid builder still owns its per-cell sampling design (μ-schedules, log
# spacing, grazing-cliff ranges). We do NOT generalize sampling — only the
# GROUND-TRUTH evaluation is unified onto `CellSpec.law`. So GridSpec stays a
# thin Callable handle for now; later phases may give it structured fields.
GridBuilder = Callable[[Any, int, float], tuple]


@dataclass(frozen=True)
class ProbeSpec:
    """Which structural probe a broken cell uses, and on which input axes.

    The structural-correctness probes (mirrorlab/eval/structural.py) need to
    know WHICH input variable carries the broken symmetry — parity on `theta`
    vs `x`, scale on `r` vs `t`, rotation in the (x,y) vs (dx,dy) plane. That
    is per-cell physics knowledge, so it lives in the CellSpec single source
    rather than being guessed by the probe.

    kind  : probe selector — "parity" / "time_reversal" / "scale" /
            "rotation" / "time_translation".
    axes  : the input-variable name(s) the probe transforms. One name for
            scalar probes (parity/scale/time_reversal/time_translation), a
            2- or 3-tuple for rotation (the plane/space it rotates in).
    note  : optional human note (e.g. why a particular axis was chosen).

    A broken cell with no applicable probe simply leaves CellSpec.probe_spec
    as None — structural_score then reports applicable=False (honest coverage).
    """

    kind: str
    axes: Tuple[str, ...]
    note: str = ""


# --------------------------------------------------------------------------
# Break-type vocabulary (post-mislabel-audit taxonomy)
# --------------------------------------------------------------------------
#
# `break_type` is the single scored label (matched against the model's
# `claim_broken_symmetry` for the §6.3 bonus, and used to select a structural
# probe). It outgrew "symmetry" — it now also carries LINEARITY and
# CONSERVATION breaks — so the field is `break_type`, with a derived,
# non-scored `break_class` for probe-family routing and analysis grouping.
# Conservation labels share a `CONS_` prefix so analysis can lump-or-split by
# prefix; the existing 5 symmetry tokens are byte-identical to pre-audit.

BREAK_CLASS_OF: Dict[str, str] = {
    "PAR": "SYMMETRY",
    "TR": "SYMMETRY",
    "ROT": "SYMMETRY",
    "SCALE": "SYMMETRY",
    "T_TRANS": "SYMMETRY",
    "S_TRANS": "SYMMETRY",      # spatial translation
    "U1": "SYMMETRY",           # U(1) gauge / polarization phase
    "CONS_N": "CONSERVATION",   # particle / number
    "CONS_M": "CONSERVATION",   # mass / stoichiometry
    "CONS_E": "CONSERVATION",   # energy
    "LIN": "LINEARITY",         # superposition broken
    "none": "NONE",
}

VALID_BREAK_TYPES: frozenset = frozenset(BREAK_CLASS_OF)


def break_class_of(break_type: str) -> str:
    """Map a ``break_type`` token to its family (SYMMETRY / CONSERVATION /
    LINEARITY / NONE). Unknown tokens raise — a typo'd label should fail loudly
    rather than silently mis-route a probe or mis-score a claim."""
    try:
        return BREAK_CLASS_OF[break_type]
    except KeyError:
        raise ValueError(
            f"unknown break_type {break_type!r}; valid: {sorted(VALID_BREAK_TYPES)}"
        )


@dataclass(frozen=True)
class CellSpec:

    domain: str
    shift: str
    params_type: type
    # Unified law: law(inputs_mapping, params_obj) -> scalar ground truth.
    # The SAME callable backs both the grid GT and the oracle predictor, so
    # the formula exists exactly once.
    law: Callable[[Mapping[str, float], Any], float]
    output: str                       # scored observable name (per-cell)
    break_type: str              # scored break label; see VALID_BREAK_TYPES
    # Shift cells provide their own sampler/validator; baseline cells are built
    # by the registry factory and leave these None.
    sampler: Optional[Callable[[int], Any]] = None
    validator: Optional[Callable[[Any], bool]] = None
    grid: Optional[GridBuilder] = None  # per-cell grid builder (thin for now)
    probe_spec: Optional[ProbeSpec] = None  # structural-probe axis declaration

    @property
    def key(self) -> Tuple[str, str]:
        return (self.domain, self.shift)

    @property
    def break_class(self) -> str:
        """Derived family (SYMMETRY / CONSERVATION / LINEARITY / NONE) — for
        probe-family routing and analysis grouping; never scored."""
        return break_class_of(self.break_type)


CELL_REGISTRY: Dict[Tuple[str, str], CellSpec] = {}


def register_cell(spec: CellSpec) -> None:
    """Register (or replace) a cell's spec. Called at the cell module's import."""
    CELL_REGISTRY[spec.key] = spec


def get_cell(domain: str, shift: str) -> CellSpec:
    return CELL_REGISTRY[(domain, shift)]


def has_cell(domain: str, shift: str) -> bool:
    return (domain, shift) in CELL_REGISTRY


# --------------------------------------------------------------------------
# Oracle derivation from a CellSpec
# --------------------------------------------------------------------------
#
# The ceiling oracle is just `spec.law` invoked with the base params, but with
# the law coefficients exposed as CANONICAL kwargs so sub-grid (c) can override
# them with the cf-perturbed values (the eval delivers cf overrides under the
# canonical predictor names). This adapter reconstructs the params object from
# those overrides and calls the one unified law — so the oracle and the grid GT
# are literally the same function.

from dataclasses import replace as _dc_replace


def make_oracle_predictor(spec: "CellSpec", base_params: Any) -> Callable[..., float]:
    """Wrap `spec.law` as a predictor `f(**kwargs)` for build_submission.

    kwargs at call time = grid inputs + (on sub-grid (c)) the cf-perturbed law
    coefficients under their canonical names. Canonical→internal mapping is
    derived from field metadata; any canonical kwarg present rebuilds the params
    via `replace`, then the unified law runs on the (possibly perturbed) params.
    """
    name_map = predictor_name_map(spec.params_type)      # internal -> canonical
    canon_to_internal = {c: i for i, c in name_map.items()}

    def pred(**kwargs: float) -> float:
        overrides = {
            canon_to_internal[c]: v
            for c, v in kwargs.items()
            if c in canon_to_internal
        }
        params = _dc_replace(base_params, **overrides) if overrides else base_params
        return spec.law(kwargs, params)

    return pred


def declared_params(spec: "CellSpec", base_params: Any) -> list:
    """`[{name: canonical, value: float}]` for the cell's law fields.

    Equivalent to the hand-written ceiling `_xxx_params` functions.
    """
    return [
        {"name": canonical, "value": float(getattr(base_params, internal))}
        for internal, canonical in predictor_name_map(spec.params_type).items()
    ]


__all__ = [
    "P", "CellSpec", "GridBuilder", "ProbeSpec",
    "BREAK_CLASS_OF", "VALID_BREAK_TYPES", "break_class_of",
    "CELL_REGISTRY", "register_cell", "get_cell", "has_cell",
    "field_role", "field_canonical", "law_fields", "predictor_name_map",
    "is_fully_tagged", "make_oracle_predictor", "declared_params",
]
