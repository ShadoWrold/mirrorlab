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
class CellSpec:
    """Everything one benchmark cell needs, declared once.

    Consumers DERIVE from this instead of holding parallel tables:
      * registry.make        -> sampler/validator/build
      * loader grid GT       -> law(inputs, params)
      * ceiling oracle        -> law(inputs, params_with_cf_overrides)
      * cf perturbation set   -> law_fields(params_type)
      * predictor name map    -> predictor_name_map(params_type)
      * declared params       -> law fields under canonical names
    """

    domain: str
    shift: str
    params_type: type
    # Unified law: law(inputs_mapping, params_obj) -> scalar ground truth.
    # The SAME callable backs both the grid GT and the oracle predictor, so
    # the formula exists exactly once.
    law: Callable[[Mapping[str, float], Any], float]
    sampler: Callable[[int], Any]
    validator: Callable[[Any], bool]
    output: str                       # scored observable name (per-cell)
    broken_symmetry: str              # e.g. "SCALE", "ROT", "T_TRANS"
    grid: Optional[GridBuilder] = None  # per-cell grid builder (thin for now)

    @property
    def key(self) -> Tuple[str, str]:
        return (self.domain, self.shift)


CELL_REGISTRY: Dict[Tuple[str, str], CellSpec] = {}


def register_cell(spec: CellSpec) -> None:
    """Register (or replace) a cell's spec. Called at the cell module's import."""
    CELL_REGISTRY[spec.key] = spec


def get_cell(domain: str, shift: str) -> CellSpec:
    return CELL_REGISTRY[(domain, shift)]


def has_cell(domain: str, shift: str) -> bool:
    return (domain, shift) in CELL_REGISTRY


__all__ = [
    "P", "CellSpec", "GridBuilder",
    "CELL_REGISTRY", "register_cell", "get_cell", "has_cell",
    "field_role", "field_canonical", "law_fields", "predictor_name_map",
    "is_fully_tagged",
]
