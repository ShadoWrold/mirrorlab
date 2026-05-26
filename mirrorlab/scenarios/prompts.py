"""Agent-visible scenario prompts.

Per spec §3 / §3.2: the prompt exposes the domain narrative, observable
variables, and available tool names. It does NOT include the shift label
(e.g. ``gamma_1_1``, ``PAR``) nor any hint of the formula family
(no ``Hooke``, ``linear``, ``tanh``, ``F = -k x``, etc.). The leak-check
test in ``tests/scenarios/test_loader_hooke.py`` enforces this.

Sprint 1 ships the Hooke-domain template only.
"""

from __future__ import annotations

from typing import Sequence

HOOKE_OBSERVABLES: tuple[str, ...] = ("t", "x", "v", "F")

HOOKE_TOOL_NAMES: tuple[str, ...] = (
    "measure.position",
    "measure.velocity",
    "measure.trajectory",
    "analyze.fit",
    "analyze.dim_check",
    "analyze.residual",
)


def hooke_prompt(
    observables: Sequence[str] = HOOKE_OBSERVABLES,
    tool_names: Sequence[str] = HOOKE_TOOL_NAMES,
) -> str:
    """Compose a domain-narrative prompt for the Hooke domain.

    The narrative describes a 1-D mechanical body whose position evolves
    under a state-dependent restoring influence. It deliberately avoids
    naming the law, asserting linearity, or referencing any parity /
    symmetry property of the underlying force.
    """
    obs_line = ", ".join(observables)
    tool_lines = "\n".join(f"  - {name}" for name in tool_names)
    return (
        "You are investigating a 1-D mechanical system. A single body of "
        "mass m moves along one axis under a state-dependent restoring "
        "influence directed toward an equilibrium point. You may interrogate "
        "the system by issuing tool calls; each call returns a measurement "
        "of the system's instantaneous state.\n"
        "\n"
        f"Observable variables: {obs_line}.\n"
        "\n"
        "Available tools:\n"
        f"{tool_lines}\n"
        "\n"
        "Your task is to propose one or more candidate laws relating the "
        "restoring force to the system's observable state, together with the "
        "SI dimensional signature of every quantity in the law. Submit your "
        "answer in the format specified by the benchmark protocol."
    )


__all__ = ["HOOKE_OBSERVABLES", "HOOKE_TOOL_NAMES", "hooke_prompt"]
