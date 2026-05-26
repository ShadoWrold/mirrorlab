"""Lookup-style adversarial attacker (spec §8 / CAL-8 / CAL-9).

The attacker is an LLM agent whose strategy is locked to "identify which
textbook physical law the scenario instantiates and submit that law".
We verify that this attacker scores below 0.50 on the γ ∪ δ slice
(CAL-9) before releasing the benchmark.
"""

from mirrorlab.attacker.lookup import (
    ATTACKER_SYSTEM_PROMPT,
    AttackResult,
    LookupAttacker,
)
from mirrorlab.attacker.runner import (
    ATTACK_SLICE,
    AttackReport,
    PASS_THRESHOLD,
    run_attack_sweep,
)

__all__ = [
    "ATTACKER_SYSTEM_PROMPT",
    "ATTACK_SLICE",
    "AttackReport",
    "AttackResult",
    "LookupAttacker",
    "PASS_THRESHOLD",
    "run_attack_sweep",
]
