"""Scenario loader: maps (domain_id, shift_id) → instantiated SimInstance."""

from mirrorlab.scenarios.registry import make, REGISTRY

__all__ = ["make", "REGISTRY"]
