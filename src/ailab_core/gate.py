"""Shared regression-gate primitives for the ailab-* labs.

Each lab's eval owns its DOMAIN gate logic (which metrics, which floors, injection/saturation
rules). What is shared is the SHAPE: a tolerance-band floor check, a presence check, and the
contract that a gate returns a list of human-readable failure messages (empty = pass) while the
CLI exits non-zero and NAMES the failing metric. "A gate you cannot see fail is not a gate", so
these primitives fail CLOSED: a missing or empty metric is a failure, never a silent pass.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GateResult:
    """Accumulates regression messages. ``passed`` is true only when there are none."""

    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures

    def add(self, message: str | None) -> None:
        """Append a failure message; ``None`` (a passing check) is ignored."""
        if message:
            self.failures.append(message)


def floor_breach(
    label: str, score: float | None, floor: float, tolerance: float = 0.0
) -> str | None:
    """Return a failure message if ``score`` is below ``floor - tolerance``, else ``None``.

    Fail-closed: a ``None`` score against an enforced floor is a failure, not a skip. A floor of
    ``0.0`` or less is treated as "not enforced" (the per-lab convention) and returns ``None``.
    """
    if floor <= 0.0:
        return None
    if score is None:
        return f"{label} is missing; cannot verify against floor {floor:.4f} (fail-closed)"
    if score < floor - tolerance:
        return f"{label} {score:.4f} < floor {floor:.4f} - tolerance {tolerance:.4f}"
    return None


def require_metrics(metrics: Mapping[str, Any] | None, required: Iterable[str]) -> list[str]:
    """Fail-closed presence check: one failure message per required key missing or ``None``.

    An empty or absent metrics mapping is itself a failure, so a gate can never pass vacuously on
    a metric set that was never populated.
    """
    required_keys = sorted(set(required))
    if not metrics:
        return [f"no metrics to gate (expected {required_keys}); fail-closed"]
    return [
        f"required metric {key!r} missing or null; fail-closed"
        for key in required_keys
        if metrics.get(key) is None
    ]
