"""ailab-core: the shared, discipline-agnostic machinery for the ailab-* labs.

Public surface (kept deliberately small, spar condition 6: no plugin system, no config framework,
no CLI):

* provider seam + cassette replay (``providers``)
* regression-gate primitives (``gate``)
"""

from __future__ import annotations

from ailab_core.gate import GateResult, floor_breach, require_metrics
from ailab_core.providers import (
    CassetteMissError,
    LLMProvider,
    OllamaProvider,
    ReplayProvider,
    SupportsTokenCounts,
    cassette_key,
)

__version__ = "0.1.0"

__all__ = [
    "CassetteMissError",
    "GateResult",
    "LLMProvider",
    "OllamaProvider",
    "ReplayProvider",
    "SupportsTokenCounts",
    "__version__",
    "cassette_key",
    "floor_breach",
    "require_metrics",
]
