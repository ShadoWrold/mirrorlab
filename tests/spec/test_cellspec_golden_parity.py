"""Golden-parity guard for the CellSpec migration.

For every Params type that has been tagged with field-role metadata, the
tables DERIVED from that metadata must be byte-equal to the hand-written
legacy tables in counterfactual.py. This lets us migrate cells one at a time
with confidence that no scoring behavior drifts.

Once ALL cells are migrated and the legacy literals are deleted (P4), this
test is replaced by one asserting full coverage.
"""

from __future__ import annotations

from mirrorlab.scenarios.counterfactual import (
    _LAW_PARAM_FIELDS,
    _PREDICTOR_NAME_MAP,
)
from mirrorlab.spec import (
    is_fully_tagged,
    law_fields,
    predictor_name_map,
)


def _tagged_types():
    return [T for T in _LAW_PARAM_FIELDS if is_fully_tagged(T)]


def test_at_least_one_cell_migrated():
    # Sanity: the migration has started.
    assert _tagged_types(), "no Params type has field-role metadata yet"


def test_derived_law_fields_match_legacy():
    for T in _tagged_types():
        derived = set(law_fields(T))
        legacy = set(_LAW_PARAM_FIELDS[T])
        assert derived == legacy, (
            f"{T.__name__}: derived law fields {sorted(derived)} != "
            f"legacy {sorted(legacy)}"
        )


def test_derived_name_map_matches_legacy():
    for T in _tagged_types():
        derived = predictor_name_map(T)
        legacy = _PREDICTOR_NAME_MAP[T]
        assert derived == legacy, (
            f"{T.__name__}: derived name map {derived} != legacy {legacy}"
        )
