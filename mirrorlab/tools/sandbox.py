"""Per-scenario sandbox: within-scenario persistence + per-call monitoring.

Lifetime: one ``SandboxContext`` per scenario instance. A tool call records
(name, args_hash, latency_ms, ok) into ``call_log``; agent-authored Python
imports register via ``record_import(modname)``. Persistent agent state
(fitted models, intermediate arrays, named scratch values) lives in
``scratchpad``.

D5 v1 restriction: cross-scenario persistence is *not* implemented here —
each scenario instantiates a fresh ``SandboxContext``. Tests in
``tests/tools/test_persistence.py`` enforce no-leak.

The monitoring channel is described in spec §4.3 (R-2 elegant defense):
recorded but **never** fed back to the agent, only consumed by the
post-hoc analysis harness.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


def _args_hash(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> str:
    try:
        payload = json.dumps([args, kwargs], default=repr, sort_keys=True)
    except Exception:
        payload = repr((args, kwargs))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class CallRecord:
    name: str
    args_hash: str
    latency_ms: float
    ok: bool
    error: Optional[str] = None


@dataclass
class SandboxContext:
    """One scenario's sandbox.

    Attributes
    ----------
    sim
        The live ``SimInstance`` from the scenario loader. Read by ``measure.*``,
        mutated by ``manipulate.*``. ``analyze.*`` and ``knowledge.*`` ignore it.
    scratchpad
        Agent-writable key/value store; survives across tool calls within
        this scenario, wiped at scenario boundary.
    call_log
        Append-only per-call record. Tools route through ``record_call``.
    call_counts
        Name → invocation count, derived from ``call_log`` for cheap lookup.
    import_log
        List of ``(modname, t_wall_seconds)`` tuples; agent Python snippets
        call ``record_import`` from their import hook (spec §4.3).
    scenario_id
        Opaque identifier for cross-scenario leak detection in tests.
    """

    sim: Any = None
    scenario_id: str = "default"
    scratchpad: Dict[str, Any] = field(default_factory=dict)
    call_log: List[CallRecord] = field(default_factory=list)
    call_counts: Dict[str, int] = field(default_factory=dict)
    import_log: List[Tuple[str, float]] = field(default_factory=list)

    def record_call(
        self, name: str, args: Tuple[Any, ...], kwargs: Dict[str, Any],
        fn: Callable[..., Any],
    ) -> Any:
        """Invoke ``fn(*args, **kwargs)`` while logging latency + outcome."""
        h = _args_hash(args, kwargs)
        t0 = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
            dt = (time.perf_counter() - t0) * 1000.0
            self.call_log.append(CallRecord(name, h, dt, True, None))
        except Exception as exc:
            dt = (time.perf_counter() - t0) * 1000.0
            self.call_log.append(CallRecord(name, h, dt, False, repr(exc)))
            self.call_counts[name] = self.call_counts.get(name, 0) + 1
            raise
        self.call_counts[name] = self.call_counts.get(name, 0) + 1
        return result

    def record_import(self, modname: str) -> None:
        self.import_log.append((modname, time.perf_counter()))


__all__ = ["SandboxContext", "CallRecord"]
